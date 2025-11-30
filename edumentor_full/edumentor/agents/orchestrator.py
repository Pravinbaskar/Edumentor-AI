from __future__ import annotations

import asyncio
import importlib
import logging
import os
from typing import Any, Dict

from edumentor.services.context import build_tutor_system_prompt, build_history_prompt

from edumentor.agents.tutor import TutorAgent
from edumentor.agents.planner import CurriculumPlannerAgent
from edumentor.services.session import SessionService
from edumentor.services.profile import ProfileService
from edumentor.services.metrics import metrics, Timer

logger = logging.getLogger("edumentor.orchestrator")


class AgentOrchestrator:
    """Routes incoming messages to the correct specialised agent.

    This implementation prefers a LangGraph-based flow when the `langgraph`
    package is installed. If LangGraph is not available, it falls back to the
    original, in-code routing logic.
    """

    def __init__(self, session_service: SessionService, profile_service: ProfileService | None = None, vector_store=None) -> None:
        self.session_service = session_service
        self.tutor_agent = TutorAgent()
        self.planner_agent = CurriculumPlannerAgent()
        self._flow = None
        self.profile_service = profile_service
        self.vector_store = vector_store

        # Try to build a LangGraph flow if langgraph is installed. Keep this
        # optional so the project still runs without the dependency.
        try:
            # Importing inside to keep import-time optional. Use importlib so
            # static analyzers don't require langgraph to be installed.
            import importlib

            lg_graph = importlib.import_module("langgraph.graph")
            StateGraph = getattr(lg_graph, "StateGraph")
            END = getattr(lg_graph, "END", None)

            # Define function nodes that wrap our existing async agent methods.
            def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
                # Synchronous wrapper for async planner
                student_profile = state.get("student_profile", {"grade": 8, "syllabus": "CBSE"})
                goal = state["message"]
                # Run async in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new loop for nested async call
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        reply = pool.submit(
                            lambda: asyncio.run(self.planner_agent.create_plan(student_profile=student_profile, goal=goal, days=5))
                        ).result()
                else:
                    reply = loop.run_until_complete(self.planner_agent.create_plan(student_profile=student_profile, goal=goal, days=5))
                state["reply"] = reply
                return state

            def tutor_node(state: Dict[str, Any]) -> Dict[str, Any]:
                student_profile = state.get("student_profile", {"grade": 8, "syllabus": "CBSE"})
                session_state = state.get("session_state", {})
                user_message = state["message"]
                vector_ctx = state.get("vector_context")
                # Run async in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        reply = pool.submit(
                            lambda: asyncio.run(self.tutor_agent.respond(
                                student_profile=student_profile,
                                session_state=session_state,
                                user_message=user_message,
                                vector_context=vector_ctx,
                            ))
                        ).result()
                else:
                    reply = loop.run_until_complete(self.tutor_agent.respond(
                        student_profile=student_profile,
                        session_state=session_state,
                        user_message=user_message,
                        vector_context=vector_ctx,
                    ))
                state["reply"] = reply
                return state

            # Create StateGraph with proper typing
            from typing import TypedDict
            
            class GraphState(TypedDict, total=False):
                user_id: str
                session_id: str
                message: str
                session_state: dict
                student_profile: dict
                vector_context: str
                reply: str
            
            # Router function to decide which node to route to
            def route_message(state: Dict[str, Any]) -> str:
                """Route message to planner or tutor based on content."""
                message = state.get("message", "").lower()
                if "plan" in message and ("study" in message or "test" in message):
                    logger.info("Router: Directing to planner node")
                    return "planner"
                else:
                    logger.info("Router: Directing to tutor node")
                    return "tutor"
            
            graph = StateGraph(GraphState)
            graph.add_node("planner", planner_node)
            graph.add_node("tutor", tutor_node)
            
            # Set entry point to router
            graph.set_entry_point("tutor")
            
            # Add conditional edges from entry point
            graph.add_conditional_edges(
                "tutor",
                route_message,
                {
                    "planner": "planner",
                    "tutor": END
                }
            )
            
            # Add edge from planner to END
            graph.add_edge("planner", END)
            
            # Compile the graph
            self._flow = graph.compile()
            logger.info("LangGraph orchestration enabled with conditional routing")
        except Exception as exc:  # pragma: no cover - optional dependency handling
            logger.info("LangGraph not available or failed to initialize: %s", exc)
            self._flow = None

    async def handle_message(self, user_id: str, session_id: str, message: str, subject: str | None = None) -> str:
        session_state = self.session_service.get_session(session_id)
        self.session_service.add_message(session_id, role="user", content=message)

        logger.info(
            "handle_message user_id=%s session_id=%s msg=%r subject=%s",
            user_id,
            session_id,
            message[:80],
            subject,
        )

        lower = message.lower()
        
        # Check vector store for relevant context if subject is provided
        vector_context = None
        if subject and self.vector_store:
            try:
                search_results = self.vector_store.search(subject, message, top_k=3)
                if search_results:
                    context_texts = [f"[From {r['source']}]: {r['text']}" for r in search_results]
                    vector_context = "\n\n".join(context_texts)
                    logger.info(f"Found {len(search_results)} relevant documents in {subject} vector store")
            except Exception as e:
                logger.error(f"Vector store search failed: {e}")

        # If we have a LangGraph flow, use it to route to planner/tutor nodes.
        if self._flow is not None:
            try:
                # Load persisted student profile
                student_profile = {}
                if self.profile_service:
                    stored = self.profile_service.get_profile(user_id)
                    if stored:
                        student_profile = {
                            "name": stored.get("name"),
                            "age": stored.get("age"),
                            "class": stored.get("class"),
                            "syllabus": stored.get("syllabus"),
                            "proficiency": stored.get("proficiency"),
                            "gender": stored.get("gender"),
                        }
                # Add subject from request
                if subject:
                    student_profile["subject"] = subject

                inputs = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": message,
                    "session_state": session_state,
                    "student_profile": student_profile,
                    "vector_context": vector_context,
                }
                
                # Track metrics based on message content
                if "plan" in lower and ("study" in lower or "test" in lower):
                    metrics.total_planner_requests += 1
                else:
                    metrics.total_tutor_requests += 1
                
                # LangGraph execution with conditional routing
                try:
                    with Timer() as t:
                        exec_result = self._flow.invoke(inputs)
                    
                    if exec_result and isinstance(exec_result, dict) and "reply" in exec_result:
                        reply = exec_result["reply"]
                    else:
                        reply = "Sorry — failed to produce a response."
                    
                    metrics.total_tutor_latency_ms += t.elapsed_ms
                    metrics.total_requests_with_latency += 1
                    logger.info("LangGraph execution latency=%.1fms", t.elapsed_ms)
                    
                except Exception as exc_run:
                    logger.exception("LangGraph execution failed: %s", exc_run)
                    metrics.total_errors += 1
                    reply = "Sorry — failed to produce a response."
                    
            except Exception as exc:  # pragma: no cover - surface-level safety
                logger.exception("Error running LangGraph flow: %s", exc)
                metrics.total_errors += 1
                reply = "Sorry — the orchestration service encountered an internal error."
        else:
            # Fallback: original orchestration logic
            if "plan" in lower and ("study" in lower or "test" in lower):
                metrics.total_planner_requests += 1
                logger.info("Routing to PlannerAgent (fallback)")
                # Load persisted student profile
                student_profile = {}
                if self.profile_service:
                    stored = self.profile_service.get_profile(user_id)
                    if stored:
                        student_profile = {
                            "name": stored.get("name"),
                            "age": stored.get("age"),
                            "class": stored.get("class"),
                            "syllabus": stored.get("syllabus"),
                            "proficiency": stored.get("proficiency"),
                            "gender": stored.get("gender"),
                        }
                # Add subject from request
                if subject:
                    student_profile["subject"] = subject
                reply = await self.planner_agent.create_plan(
                    student_profile=student_profile,
                    goal=message,
                    days=5,
                )
            else:
                metrics.total_tutor_requests += 1
                logger.info("Routing to TutorAgent (fallback)")
                # Load persisted student profile
                student_profile = {}
                if self.profile_service:
                    stored = self.profile_service.get_profile(user_id)
                    if stored:
                        student_profile = {
                            "name": stored.get("name"),
                            "age": stored.get("age"),
                            "class": stored.get("class"),
                            "syllabus": stored.get("syllabus"),
                            "proficiency": stored.get("proficiency"),
                            "gender": stored.get("gender"),
                        }
                # Add subject from request
                if subject:
                    student_profile["subject"] = subject
                with Timer() as t:
                    reply = await self.tutor_agent.respond(
                        student_profile=student_profile,
                        session_state=session_state,
                        user_message=message,
                        vector_context=vector_context,
                    )
                metrics.total_tutor_latency_ms += t.elapsed_ms
                metrics.total_requests_with_latency += 1
                logger.info("TutorAgent latency=%.1fms", t.elapsed_ms)

        self.session_service.add_message(session_id, role="assistant", content=reply)
        return reply
