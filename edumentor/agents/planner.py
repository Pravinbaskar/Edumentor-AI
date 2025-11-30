from __future__ import annotations

from typing import Dict, Any, List
import logging

from edumentor.tools.content_tool import get_quiz_questions

logger = logging.getLogger("edumentor.planner")


class CurriculumPlannerAgent:
    """Lightweight agent that generates a simple day-wise study plan."""

    async def create_plan(
        self,
        student_profile: Dict[str, Any],
        goal: str,
        days: int = 5,
    ) -> str:
        logger.info("Planner.create_plan goal=%r days=%d", goal, days)
        grade = student_profile.get("grade", 8)
        syllabus = student_profile.get("syllabus", "CBSE")

        topics = [
            "Basic concepts & revision",
            "Practice problems",
            "Advanced problems",
            "Mock test",
            "Revision & weak areas",
        ]

        lines: List[str] = []
        lines.append(f"📘 Personalized Study Plan ({days} days)")
        lines.append(f"Grade: {grade} | Syllabus: {syllabus}")
        lines.append(f"Goal: {goal}\n")

        for day in range(days):
            topic = topics[day % len(topics)]
            lines.append(f"Day {day + 1}: {topic}")
            quiz_preview = get_quiz_questions("fractions")
            if quiz_preview:
                lines.append("  - Practice quiz included ✅")

        lines.append("\nStay consistent and review mistakes every day!")
        return "\n".join(lines)
