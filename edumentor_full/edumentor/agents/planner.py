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
        # Use actual profile data
        grade = student_profile.get("grade")
        syllabus = student_profile.get("syllabus")
        subject = student_profile.get("subject")
        name = student_profile.get("name")
        proficiency = student_profile.get("proficiency")

        topics = [
            "Basic concepts & revision",
            "Practice problems",
            "Advanced problems",
            "Mock test",
            "Revision & weak areas",
        ]

        lines: List[str] = []
        lines.append(f"📘 Personalized Study Plan ({days} days)")
        
        # Show profile info if available
        profile_parts = []
        if name:
            profile_parts.append(f"Student: {name}")
        if grade:
            profile_parts.append(f"Grade: {grade}")
        if syllabus:
            profile_parts.append(f"Syllabus: {syllabus}")
        if subject:
            profile_parts.append(f"Subject: {subject}")
        if proficiency:
            profile_parts.append(f"Level: {proficiency}")
        
        if profile_parts:
            lines.append(" | ".join(profile_parts))
        
        lines.append(f"Goal: {goal}\n")

        for day in range(days):
            topic = topics[day % len(topics)]
            lines.append(f"Day {day + 1}: {topic}")
            quiz_preview = get_quiz_questions("fractions")
            if quiz_preview:
                lines.append("  - Practice quiz included ✅")

        lines.append("\nStay consistent and review mistakes every day!")
        return "\n".join(lines)
