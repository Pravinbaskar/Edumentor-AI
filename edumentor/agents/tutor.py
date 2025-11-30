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

        system_prompt = build_tutor_system_prompt(student_profile)
        history_prompt = build_history_prompt(session_state.get("messages", []))

        user_prompt = (
            f"Conversation so far:\n{history_prompt}\n\n"
            f"New student message: {user_message}\n\n"
        )
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

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            # Defensive access to response structure
            return getattr(response.choices[0].message, "content", "")
        except Exception as exc:  # pragma: no cover - defensive runtime handling
            logger.exception("Error calling OpenAI API: %s", exc)
            metrics.total_errors += 1
            return "Sorry — the tutor service encountered an internal error."
