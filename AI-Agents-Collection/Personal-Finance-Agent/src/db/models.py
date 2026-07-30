from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime
from src.db.database import Base

class FinancialReportModel(Base):
    __tablename__ = "financial_reports"

    report_id = Column(String, primary_key=True, index=True)
    total_income = Column(Float, nullable=False)
    total_expenses = Column(Float, nullable=False)
    net_savings = Column(Float, nullable=False)
    financial_health_score = Column(Float, nullable=False)
    category_breakdown_json = Column(Text, nullable=False)
    recurring_expenses_json = Column(Text, nullable=False)
    suggestions_json = Column(Text, nullable=False)
    investments_json = Column(Text, nullable=False)
    forecast_next_month = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
