from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.models.schemas import (
    QuestionGenerationResponse,
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    FinalReportResponse
)
from src.services.core_service import InterviewCoachService

router = APIRouter(prefix="/api/v1/interview", tags=["Interview Coach"])

@router.post("/start", response_model=QuestionGenerationResponse, status_code=status.HTTP_201_CREATED)
async def start_interview_session(
    target_role: str = Form("Software Engineer"),
    difficulty: str = Form("Intermediate"),
    question_count: int = Form(5),
    resume_file: UploadFile = File(None),
    resume_text: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Starts a new mock interview session by uploading a resume or submitting raw text."""
    content = ""
    if resume_file:
        file_bytes = await resume_file.read()
        content = file_bytes.decode("utf-8", errors="ignore")
    elif resume_text:
        content = resume_text
    else:
        content = "Alex Johnson\nSenior Python Engineer with 5 years experience in FastAPI, Docker, and AI System Design."

    return await InterviewCoachService.initialize_interview(
        resume_text=content,
        target_role=target_role,
        difficulty=difficulty,
        question_count=question_count,
        db=db
    )

@router.post("/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_candidate_answer(
    payload: AnswerEvaluationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Evaluates candidate response to a specific question and returns feedback."""
    return await InterviewCoachService.evaluate_candidate_answer(
        session_id=payload.session_id,
        question_id=payload.question_id,
        question_text=payload.question_text,
        candidate_answer=payload.candidate_answer,
        db=db
    )

@router.get("/report/{session_id}", response_model=FinalReportResponse)
async def get_final_interview_report(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generates the final hiring and performance evaluation report for a session."""
    return await InterviewCoachService.generate_final_report(session_id, db)
