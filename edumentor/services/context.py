from __future__ import annotations

from typing import List, Dict

BASE_TUTOR_SYSTEM_PROMPT = """You are EduMentor, a friendly, patient AI tutor
for middle and high school students. You explain step by step, check
understanding, and adapt difficulty.

Always:
- Use clear, simple language.
- Show intermediate steps for maths problems.
- Ask a brief follow-up question to confirm understanding.
"""


def build_history_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert recent message list into a compact text block."""
    lines: list[str] = []
    for msg in messages:
        prefix = "Student:" if msg.get("role") == "user" else "Tutor:"
        lines.append(f"{prefix} {msg.get('content', '')}")
    return "\n".join(lines)


def build_tutor_system_prompt(student_profile: Dict | None = None) -> str:
    """Inject light personalisation (grade / syllabus) into system prompt."""
    prompt = BASE_TUTOR_SYSTEM_PROMPT
    if student_profile:
        grade = student_profile.get("grade")
        syllabus = student_profile.get("syllabus")
        extra_parts: list[str] = []
        if grade is not None:
            extra_parts.append(f"grade {grade}")
        if syllabus:
            extra_parts.append(f"{syllabus} syllabus")
        if extra_parts:
            prompt += "\nThe student is " + " in ".join(extra_parts) + "."
    return prompt
