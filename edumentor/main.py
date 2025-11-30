from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from edumentor.agents.orchestrator import AgentOrchestrator
from edumentor.services.session import SessionService
from edumentor.services.metrics import metrics
from edumentor.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("edumentor.main")

app = FastAPI(title="EduMentor AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = SessionService()
orchestrator = AgentOrchestrator(session_service=session_service)


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    metrics.total_requests += 1
    logger.info("/chat request user_id=%s", req.user_id)
    session_id = req.session_id or session_service.create_session(req.user_id)
    reply = await orchestrator.handle_message(
        user_id=req.user_id,
        session_id=session_id,
        message=req.message,
    )
    return ChatResponse(session_id=session_id, reply=reply)


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: Optional[str] = None
    user_id = "demo_user"
    try:
        while True:
            data = await websocket.receive_text()
            metrics.total_requests += 1
            logger.info("/ws/chat message user_id=%s", user_id)
            if session_id is None:
                session_id = session_service.create_session(user_id)
            reply = await orchestrator.handle_message(
                user_id=user_id,
                session_id=session_id,
                message=data,
            )
            await websocket.send_text(reply)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


@app.get("/metrics")
async def get_metrics() -> dict:
    avg_tutor_latency = (
        metrics.total_tutor_latency_ms / metrics.total_requests_with_latency
        if metrics.total_requests_with_latency
        else 0.0
    )
    return {
        "total_requests": metrics.total_requests,
        "total_tutor_requests": metrics.total_tutor_requests,
        "total_planner_requests": metrics.total_planner_requests,
        "total_analyzer_requests": metrics.total_analyzer_requests,
        "total_errors": metrics.total_errors,
        "avg_tutor_latency_ms": round(avg_tutor_latency, 2),
        "tool_usage": metrics.tool_usage,
    }
