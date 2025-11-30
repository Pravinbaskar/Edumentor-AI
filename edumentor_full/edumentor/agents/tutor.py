from __future__ import annotations

from typing import Dict, Any
import os
import logging
from pathlib import Path

from openai import OpenAI

from edumentor.services.context import build_history_prompt, build_tutor_system_prompt
from edumentor.tools.code_exec_tool import code_exec_tool
from edumentor.tools.content_tool import get_quiz_questions
from edumentor.services.metrics import metrics

logger = logging.getLogger("edumentor.tutor")

def _parse_env_file_for_key(path: Path, key: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            val = v.strip()
            # strip surrounding quotes if present
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            return val
    return None


# ✅ API key resolution: environment variable first, then .env, then .env.example
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Look for .env or .env.example in the repository root
    repo_root = Path(__file__).resolve().parents[2]
    for fname in (repo_root / ".env", repo_root / ".env.example"):
        if fname.exists():
            loaded = _parse_env_file_for_key(fname, "OPENAI_API_KEY")
            if loaded:
                OPENAI_API_KEY = loaded
                logger.info("Loaded OPENAI_API_KEY from %s", fname)
                break

# Create client (may still be used even if key missing; calls will fail later).
client = OpenAI(api_key=OPENAI_API_KEY)


class TutorAgent:
    """Main teaching agent that interacts directly with the student."""

    async def respond(
        self,
        student_profile: Dict[str, Any] | None,
        session_state: Dict[str, Any],
        user_message: str,
        vector_context: str | None = None,
    ) -> str:
        logger.info("TutorAgent.respond msg=%r", user_message[:80])

        lower = user_message.lower()
        use_math_tool = any(sym in user_message for sym in ["+", "-", "*", "/", "=", "^"])
        use_quiz_tool = "quiz" in lower or "practice" in lower

        tool_outputs: list[str] = []

        if use_quiz_tool:
            logger.info("TutorAgent using content_tool")
            metrics.inc_tool("content_tool")
            quiz = get_quiz_questions(topic=session_state.get("current_topic", "fractions"))
            if quiz:
                out_lines = ["Here are some practice questions:", ""]
                for i, q in enumerate(quiz, start=1):
                    out_lines.append(f"{i}. {q['question']}")
                    for opt in q["options"]:
                        out_lines.append(f"   - {opt}")
                    out_lines.append("")
                return "\n".join(out_lines).strip()

        if use_math_tool:
            logger.info("TutorAgent using code_exec_tool")
            metrics.inc_tool("code_exec_tool")
            result = code_exec_tool(user_message)
            tool_outputs.append(f"Math tool result: {result}")

        system_prompt = build_tutor_system_prompt(student_profile, vector_context)
        history_prompt = build_history_prompt(session_state.get("messages", []), student_profile)

        user_prompt = (
            f"Conversation so far:\n{history_prompt}\n\n"
            f"New student message: {user_message}\n\n"
        )
        if vector_context:
            user_prompt += f"Relevant content from uploaded documents:\n{vector_context}\n\n"
        if tool_outputs:
            user_prompt += "Tools output:\n" + "\n".join(tool_outputs) + "\n\n"

        # If the API key wasn't configured, return a helpful, non-500 response.
        if not OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured; skipping API call")
            metrics.total_errors += 1
            return (
                "OpenAI API key is not configured on the server. "
                "Set the OPENAI_API_KEY environment variable to enable model responses."
            )

        def _extract_response_text(resp: object) -> str:
            """Try multiple known response shapes and return a best-effort text.

            This handles both the newer `responses.create` result shapes and the
            older ChatCompletion `choices` shapes.
            """
            try:
                # new Responses API: resp.output_text
                if hasattr(resp, "output_text"):
                    return getattr(resp, "output_text") or ""

                # new Responses API: resp.output -> list of items
                out = getattr(resp, "output", None)
                if out:
                    # often output is a list of dicts
                    if isinstance(out, list) and out:
                        first = out[0]
                        if isinstance(first, dict):
                            # try common nested structures
                            # 1) {'content':[{'type':'output_text','text':'...'}]}
                            content = first.get("content")
                            if isinstance(content, list) and content:
                                for c in content:
                                    if isinstance(c, dict):
                                        for k in ("text", "output_text", "content"):
                                            if k in c and c[k]:
                                                return c[k]
                            # 2) first.get('text')
                            for k in ("text", "output_text"):
                                if k in first and first[k]:
                                    return first[k]

                # older ChatCompletion API shape: resp.choices[0].message.content or resp.choices[0].text
                choices = getattr(resp, "choices", None)
                if choices:
                    # choices may be a list of dicts or objects
                    first = choices[0]
                    # dict-like
                    if isinstance(first, dict):
                        message = first.get("message") or first.get("text")
                        if isinstance(message, dict):
                            # message may be { 'content': '...' } or { 'content': { 'text': '...' } }
                            content = message.get("content")
                            if isinstance(content, str):
                                return content
                            if isinstance(content, dict):
                                for k in ("text", "content"):
                                    if k in content and content[k]:
                                        return content[k]
                        if isinstance(message, str):
                            return message
                    else:
                        # object-like
                        msg_obj = getattr(first, "message", None) or getattr(first, "text", None)
                        if isinstance(msg_obj, str):
                            return msg_obj
                        if hasattr(msg_obj, "get"):
                            return msg_obj.get("content") or msg_obj.get("text") or ""

                # Fallback: stringify the resp
                return str(resp)
            except Exception:
                try:
                    return str(resp)
                except Exception:
                    return ""

        try:
            # Log the prompts being sent to LLM
            logger.info("=" * 80)
            logger.info("LLM PROMPT - System:")
            logger.info(system_prompt)
            logger.info("-" * 80)
            logger.info("LLM PROMPT - User:")
            logger.info(user_prompt)
            logger.info("=" * 80)
            
            # Use the standard ChatCompletion API
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            # Extract response using the standard ChatCompletion structure
            if resp.choices and len(resp.choices) > 0:
                content = resp.choices[0].message.content
                logger.info("LLM RESPONSE:")
                logger.info(content)
                logger.info("=" * 80)
                return content if content else ""
            return ""
        except Exception as exc:  # pragma: no cover - defensive runtime handling
            logger.exception("Error calling OpenAI API: %s", exc)
            metrics.total_errors += 1
            return "Sorry — the tutor service encountered an internal error."
