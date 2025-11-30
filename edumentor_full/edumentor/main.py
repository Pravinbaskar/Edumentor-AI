from __future__ import annotations

import json
import logging
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator
from typing import Literal

from edumentor.agents.orchestrator import AgentOrchestrator
from edumentor.services.session import SessionService
from edumentor.services.profile import ProfileService
from edumentor.services.vector_store import VectorStore
from edumentor.services.pdf_processor import PDFProcessor
from edumentor.services.chat_history import ChatHistoryDB
from edumentor.services.quiz import QuizGenerator
from edumentor.services.quiz_results import QuizResultsDB
from edumentor.services.pdf_generator import pdf_generator
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
profile_service = ProfileService()
vector_store = VectorStore()
chat_history_db = ChatHistoryDB()
quiz_generator = QuizGenerator()
quiz_results_db = QuizResultsDB()
orchestrator = AgentOrchestrator(session_service=session_service, profile_service=profile_service, vector_store=vector_store)


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None
    subject: Optional[str] = None


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
        subject=req.subject,
    )
    
    # Save Q&A to database
    try:
        chat_history_db.save_qa(
            user_id=req.user_id,
            session_id=session_id,
            question=req.message,
            answer=reply,
            subject=req.subject
        )
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")
    
    return ChatResponse(session_id=session_id, reply=reply)


class ProfileModel(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    grade_field: Optional[str] = None
    syllabus: Optional[str] = None
    proficiency: Optional[Literal["beginner", "intermediate", "advanced"]] = Field(
        None
    )
    gender: Optional[Literal["male", "female", "other"]] = Field(None)

    @validator("grade_field")
    def grade_not_empty(cls, v):
        if v is None:
            return v
        if not str(v).strip():
            raise ValueError("grade_field must not be empty")
        return v

    @validator("name")
    def name_strip_empty(cls, v):
        if v is None:
            return v
        s = str(v).strip()
        return s or None


@app.get("/profile/{user_id}")
async def get_profile(user_id: str) -> dict:
    prof = profile_service.get_profile(user_id)
    return prof or {}


@app.post("/profile/{user_id}")
async def upsert_profile(user_id: str, profile: ProfileModel) -> dict:
    # Map `grade_field` to `grade` to avoid using reserved word in pydantic
    p = profile.dict()
    if "grade_field" in p:
        p["grade"] = p.pop("grade_field")
    # Ensure subject is included
    profile_service.upsert_profile(user_id, p)
    return p


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


@app.post("/upload-pdf/{subject}")
async def upload_pdf(subject: str, file: UploadFile = File(...)) -> dict:
    """Upload a PDF file for a specific subject."""
    if subject not in ["maths", "science", "evs"]:
        raise HTTPException(status_code=400, detail="Invalid subject. Must be maths, science, or evs.")
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    try:
        # Read PDF content
        pdf_bytes = await file.read()
        
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty PDF file.")
        
        # Process PDF and extract text chunks
        chunks = PDFProcessor.process_pdf(pdf_bytes, chunk_size=500)
        
        if not chunks:
            raise HTTPException(
                status_code=400, 
                detail="No text content found in PDF. This might be a scanned/image-based PDF. "
                       "Please use a PDF with text layer or convert it using OCR."
            )
        
        # Add to vector store
        num_chunks = vector_store.add_documents(
            subject=subject,
            texts=chunks,
            source=file.filename
        )
        
        logger.info(f"Uploaded {file.filename} to {subject}: {num_chunks} chunks")
        
        return {
            "success": True,
            "subject": subject,
            "filename": file.filename,
            "chunks_added": num_chunks
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload PDF: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process PDF: {str(e)}"
        )


@app.get("/subject-stats/{subject}")
async def get_subject_stats(subject: str) -> dict:
    """Get statistics for a subject's document store."""
    if subject not in ["maths", "science", "evs"]:
        raise HTTPException(status_code=400, detail="Invalid subject.")
    
    stats = vector_store.get_subject_stats(subject)
    return stats


@app.delete("/subject-data/{subject}")
async def delete_subject_data(subject: str) -> dict:
    """Delete all documents for a subject."""
    if subject not in ["maths", "science", "evs"]:
        raise HTTPException(status_code=400, detail="Invalid subject.")
    
    vector_store.delete_subject_data(subject)
    return {"success": True, "message": f"Deleted all data for {subject}"}


@app.get("/chat-history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 50, subject: Optional[str] = None) -> dict:
    """Get chat history for a user."""
    try:
        history = chat_history_db.get_user_history(user_id, limit=limit, subject=subject)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat-history/{user_id}/sessions")
async def get_recent_sessions(user_id: str, limit: int = 10) -> dict:
    """Get recent chat sessions."""
    try:
        sessions = chat_history_db.get_recent_sessions(user_id, limit=limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to fetch sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat-history/{user_id}/stats")
async def get_chat_stats(user_id: str) -> dict:
    """Get chat history statistics."""
    try:
        stats = chat_history_db.get_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat-history/{user_id}")
async def delete_chat_history(user_id: str) -> dict:
    """Delete all chat history for a user."""
    try:
        deleted_count = chat_history_db.delete_user_history(user_id)
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to delete chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# Quiz endpoints
class QuizRequest(BaseModel):
    user_id: str
    subject: str
    topic: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    num_questions: int = Field(default=5, ge=1, le=20)


class QuizSubmission(BaseModel):
    user_id: str
    result_id: int
    answers: list[int]
    time_taken_seconds: Optional[int] = None


@app.post("/quiz/generate")
async def generate_quiz(req: QuizRequest) -> dict:
    """Generate a new quiz."""
    try:
        # Get user profile for context
        student_profile = profile_service.get_profile(req.user_id)
        
        questions = quiz_generator.generate_quiz(
            subject=req.subject,
            topic=req.topic,
            difficulty=req.difficulty,
            num_questions=req.num_questions,
            student_profile=student_profile
        )
        
        # Return questions without correct answers and explanations
        quiz_questions = [
            {
                "question": q["question"],
                "options": q["options"]
            }
            for q in questions
        ]
        
        # Store full questions temporarily (in a real app, use Redis or similar)
        # For now, we'll store it in the database immediately with empty answers
        result_id = quiz_results_db.save_result(
            user_id=req.user_id,
            subject=req.subject,
            topic=req.topic,
            difficulty=req.difficulty,
            questions=questions,
            user_answers=[],  # Empty until submitted
            time_taken_seconds=None
        )
        
        return {
            "result_id": result_id,
            "subject": req.subject,
            "topic": req.topic,
            "difficulty": req.difficulty,
            "questions": quiz_questions
        }
    except ValueError as e:
        logger.error(f"Quiz generation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate quiz: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@app.post("/quiz/submit")
async def submit_quiz(submission: QuizSubmission) -> dict:
    """Submit quiz answers and get results."""
    try:
        # Get the quiz details
        result = quiz_results_db.get_result_details(submission.result_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        if result["user_id"] != submission.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        questions = result["questions"]
        
        # Calculate score
        correct_answers = sum(
            1 for i, q in enumerate(questions)
            if i < len(submission.answers) and submission.answers[i] == q["correct_answer"]
        )
        
        score_percentage = (correct_answers / len(questions) * 100) if questions else 0
        
        # Update the result with user answers
        import sqlite3
        conn = sqlite3.connect(quiz_results_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE quiz_results
            SET user_answers = ?, 
                correct_answers = ?,
                score_percentage = ?,
                time_taken_seconds = ?
            WHERE id = ?
        """, (
            json.dumps(submission.answers),
            correct_answers,
            score_percentage,
            submission.time_taken_seconds,
            submission.result_id
        ))
        
        conn.commit()
        conn.close()
        
        # Prepare detailed results
        detailed_results = []
        for i, q in enumerate(questions):
            user_answer = submission.answers[i] if i < len(submission.answers) else None
            is_correct = user_answer == q["correct_answer"]
            
            detailed_results.append({
                "question": q["question"],
                "options": q["options"],
                "user_answer": user_answer,
                "correct_answer": q["correct_answer"],
                "is_correct": is_correct,
                "explanation": q["explanation"]
            })
        
        return {
            "result_id": submission.result_id,
            "total_questions": len(questions),
            "correct_answers": correct_answers,
            "score_percentage": round(score_percentage, 2),
            "passed": score_percentage >= 60,
            "detailed_results": detailed_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/results/{user_id}")
async def get_quiz_results(user_id: str, limit: int = 20) -> dict:
    """Get quiz results history for a user."""
    try:
        results = quiz_results_db.get_user_results(user_id, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Failed to fetch quiz results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/result/{result_id}")
async def get_quiz_result_detail(result_id: int) -> dict:
    """Get detailed quiz result."""
    try:
        result = quiz_results_db.get_result_details(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch quiz result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/statistics/{user_id}")
async def get_quiz_statistics(user_id: str) -> dict:
    """Get quiz statistics for a user."""
    try:
        stats = quiz_results_db.get_statistics(user_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch quiz statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/quiz/results/{user_id}")
async def delete_quiz_results(user_id: str) -> dict:
    """Delete all quiz results for a user."""
    try:
        deleted_count = quiz_results_db.delete_user_results(user_id)
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to delete quiz results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/download/{result_id}")
async def download_quiz_pdf(result_id: int, student_name: str = "Student") -> Response:
    """Download quiz result as PDF.
    
    Args:
        result_id: Quiz result ID
        student_name: Name of the student (query parameter)
        
    Returns:
        PDF file as response
    """
    try:
        # Get the quiz result details
        result = quiz_results_db.get_result_details(result_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Quiz result not found")
        
        # Generate PDF
        pdf_data = pdf_generator.generate_quiz_result_pdf(
            student_name=student_name,
            subject=result["subject"],
            topic=result["topic"],
            difficulty=result["difficulty"],
            total_questions=result["total_questions"],
            correct_answers=result["correct_answers"],
            score_percentage=result["score_percentage"],
            questions_data=result["questions"],
            user_answers=result["user_answers"],
            date=result["timestamp"].split()[0] if result.get("timestamp") else None
        )
        
        # Return PDF as response
        filename = f"quiz_result_{result['subject']}_{result['topic']}_{result_id}.pdf"
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
