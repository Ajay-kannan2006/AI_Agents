from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from src.db.database import Base

class ResearchReportModel(Base):
    __tablename__ = "research_reports"

    research_id = Column(String, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    keywords_json = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=False)
    report_markdown = Column(Text, nullable=False)
    references_json = Column(Text, nullable=False)
    ppt_outline_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
