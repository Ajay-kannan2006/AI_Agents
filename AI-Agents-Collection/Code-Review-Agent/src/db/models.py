from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from src.db.database import Base

class CodeReviewReportModel(Base):
    __tablename__ = "code_review_reports"

    review_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    language = Column(String, nullable=False)
    quality_score = Column(Float, nullable=False)
    total_issues = Column(Integer, nullable=False)
    issues_json = Column(Text, nullable=False)
    refactored_code = Column(Text, nullable=True)
    generated_unit_tests = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
