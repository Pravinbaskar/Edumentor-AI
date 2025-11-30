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


def build_history_prompt(messages: List[Dict[str, str]], student_profile: Dict | None = None) -> str:
    """Convert recent message list into a compact text block.

    If `student_profile` is provided, include a compact profile header so the
    model sees the student's details alongside the recent conversation.
    """
    lines: list[str] = []
    if student_profile:
        # compact profile representation
        prof_lines: list[str] = []
        for k in ("name", "age", "grade", "syllabus", "subject", "proficiency", "gender"):
            if k in student_profile and student_profile.get(k) is not None:
                prof_lines.append(f"{k}: {student_profile.get(k)}")
        if prof_lines:
            lines.append("Student profile:")
            lines.extend(prof_lines)
            lines.append("")

    for msg in messages:
        prefix = "Student:" if msg.get("role") == "user" else "Tutor:"
        lines.append(f"{prefix} {msg.get('content', '')}")
    return "\n".join(lines)


def build_tutor_system_prompt(student_profile: Dict | None = None, vector_context: str | None = None) -> str:
    """Inject personalisation into the system prompt using the student's profile.

    The prompt includes explicit, structured student information so downstream
    prompt templates can adapt tone, examples, and difficulty.
    """
    prompt = BASE_TUTOR_SYSTEM_PROMPT
    if not student_profile:
        return prompt

    parts: List[str] = []
    # Preferred keys: name, age, grade, syllabus, subject, proficiency, gender
    name = student_profile.get("name")
    age = student_profile.get("age")
    grade = student_profile.get("grade")
    syllabus = student_profile.get("syllabus")
    subject = student_profile.get("subject")
    proficiency = student_profile.get("proficiency")
    gender = student_profile.get("gender")

    if name:
        parts.append(f"Name: {name}")
    if age is not None:
        parts.append(f"Age: {age}")
    if grade:
        parts.append(f"Grade: {grade}")
    if syllabus:
        parts.append(f"Syllabus: {syllabus}")
    if subject:
        parts.append(f"Subject: {subject}")
    if proficiency:
        parts.append(f"Proficiency: {proficiency}")
    if gender:
        parts.append(f"Gender: {gender}")

    if parts:
        # More concise, human-friendly profile header
        prompt += "\nStudent Profile (for personalization):\n- " + "\n- ".join(parts) + ".\n"

        # Guidance to the model about how to use the profile
        prompt += (
            "Adapt explanations using the profile: use simpler language and more "
            "scaffolding for younger/beginner students; provide deeper examples for "
            "advanced students. Focus your expertise on the student's selected subject. "
            "Where helpful, address the student by name and refer to their grade or "
            "age when giving examples."
        )
    
    if vector_context:
        prompt += (
            "\n\nIMPORTANT: Relevant content from uploaded PDF documents has been "
            "provided in the context. Use this information to answer the student's "
            "question accurately. If the uploaded content contains the answer, "
            "prioritize it over general knowledge. Always cite the source when using "
            "information from uploaded documents."
        )

    return prompt
