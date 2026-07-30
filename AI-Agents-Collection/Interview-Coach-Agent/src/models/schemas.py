from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SkillExtractionResult(BaseModel):
    candidate_name: str = Field(description="Extracted candidate name")
    experience_years: float = Field(description="Years of relevant experience")
    primary_skills: List[str] = Field(description="List of primary technical skills")
    secondary_skills: List[str] = Field(description="List of secondary or soft skills")
    roles_suited: List[str] = Field(description="Suitable job roles derived from resume")

class QuestionGenerationRequest(BaseModel):
    resume_text: str = Field(..., description="Raw text of candidate resume")
    target_role: str = Field(default="Software Engineer", description="Target position")
    difficulty: str = Field(default="Intermediate", description="Junior, Intermediate, or Senior")
    question_count: int = Field(default=5, description="Number of questions to generate")

class QuestionItem(BaseModel):
    question_id: int
    category: str = Field(description="Behavioral or Technical")
    question_text: str
    target_skill: str
    difficulty: str

class QuestionGenerationResponse(BaseModel):
    session_id: str
    candidate_skills: SkillExtractionResult
    questions: List[QuestionItem]

class AnswerEvaluationRequest(BaseModel):
    session_id: str
    question_id: int
    question_text: str
    candidate_answer: str

class AnswerEvaluationResponse(BaseModel):
    session_id: str
    question_id: int
    score: float = Field(description="Score out of 10")
    technical_accuracy: float = Field(description="Technical score out of 10")
    communication_score: float = Field(description="Communication clarity out of 10")
    strengths: List[str]
    weaknesses: List[str]
    improvement_feedback: str
    suggested_followup_question: Optional[str] = None

class InterviewSessionCreate(BaseModel):
    candidate_name: str
    target_role: str
    difficulty: str = "Intermediate"

class FinalReportResponse(BaseModel):
    session_id: str
    candidate_name: str
    target_role: str
    total_questions: int
    average_score: float
    overall_strengths: List[str]
    critical_weaknesses: List[str]
    hiring_recommendation: str
    detailed_evaluations: List[AnswerEvaluationResponse]
    created_at: datetime = Field(default_factory=datetime.utcnow)
