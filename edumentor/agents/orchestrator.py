from __future__ import annotations

import logging

from edumentor.agents.tutor import TutorAgent
from edumentor.agents.planner import CurriculumPlannerAgent
from edumentor.services.session import SessionService
from edumentor.services.metrics import metrics, Timer

logger = logging.getLogger("edumentor.orchestrator")


class AgentOrchestrator:
    """Routes incoming messages to the correct specialised agent."""

    def __init__(self, session_service: SessionService) -> None:
        self.session_service = session_service
        self.tutor_agent = TutorAgent()
        self.planner_agent = CurriculumPlannerAgent()
        # Progress Analyzer Agent could be added here

    async def handle_message(self, user_id: str, session_id: str, message: str) -> str:
        session_state = self.session_service.get_session(session_id)
        self.session_service.add_message(session_id, role="user", content=message)

        logger.info(
            "handle_message user_id=%s session_id=%s msg=%r",
            user_id,
            session_id,
            message[:80],
        )

        lower = message.lower()

        if "plan" in lower and ("study" in lower or "test" in lower):
            metrics.total_planner_requests += 1
            logger.info("Routing to PlannerAgent")
            student_profile = {"grade": 8, "syllabus": "CBSE"}
            reply = await self.planner_agent.create_plan(
                student_profile=student_profile,
                goal=message,
                days=5,
            )
        else:
            metrics.total_tutor_requests += 1
            logger.info("Routing to TutorAgent")
            student_profile = {"grade": 8, "syllabus": "CBSE"}
            with Timer() as t:
                reply = await self.tutor_agent.respond(
                    student_profile=student_profile,
                    session_state=session_state,
                    user_message=message,
                )
            metrics.total_tutor_latency_ms += t.elapsed_ms
            metrics.total_requests_with_latency += 1
            logger.info("TutorAgent latency=%.1fms", t.elapsed_ms)

        self.session_service.add_message(session_id, role="assistant", content=reply)
        return reply
