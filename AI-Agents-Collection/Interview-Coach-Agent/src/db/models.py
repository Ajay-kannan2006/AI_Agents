import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base

class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    session_id = Column(String, primary_key=True, index=True)
    candidate_name = Column(String, nullable=False)
    target_role = Column(String, nullable=False)
    difficulty = Column(String, default="Intermediate")
    parsed_skills_json = Column(Text, nullable=True)
    overall_score = Column(Float, default=0.0)
    hiring_recommendation = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluations = relationship("AnswerEvaluationModel", back_populates="session", cascade="all, delete-orphan")

class AnswerEvaluationModel(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.session_id"), nullable=False)
    question_id = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    candidate_answer = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    technical_accuracy = Column(Float, nullable=False)
    communication_score = Column(Float, nullable=False)
    strengths_json = Column(Text, nullable=False)
    weaknesses_json = Column(Text, nullable=False)
    feedback = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSessionModel", back_populates="evaluations")
