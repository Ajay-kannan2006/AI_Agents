from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TransactionItem(BaseModel):
    date: str
    description: str
    amount: float
    category: Optional[str] = "Uncategorized"
    is_recurring: Optional[bool] = False

class FinancialAnalysisRequest(BaseModel):
    monthly_income: float = Field(default=5000.0, description="Monthly net income")
    savings_goal: float = Field(default=1000.0, description="Target monthly savings goal")
    statement_csv_content: Optional[str] = Field(None, description="Raw CSV text content")

class CategoryBreakdown(BaseModel):
    category: str
    total_amount: float
    percentage_of_total: float

class FinanceReportResponse(BaseModel):
    report_id: str
    total_income: float
    total_expenses: float
    net_savings: float
    financial_health_score: float = Field(description="Score out of 100")
    category_breakdown: List[CategoryBreakdown]
    recurring_expenses: List[TransactionItem]
    savings_suggestions: List[str]
    investment_recommendations: List[str]
    spending_forecast_next_month: float
    chart_svg: Optional[str] = Field(None, description="SVG markup for pie chart")
    created_at: datetime = Field(default_factory=datetime.utcnow)
