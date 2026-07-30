from typing import List, Dict, Any, Optional, TypedDict

class FinanceState(TypedDict):
    report_id: str
    monthly_income: float
    savings_goal: float
    raw_csv: str
    transactions: List[Dict[str, Any]]
    categories: Dict[str, float]
    recurring_expenses: List[Dict[str, Any]]
    health_score: float
    forecast_amount: float
    suggestions: List[str]
    investments: List[str]
    chart_svg: Optional[str]
    status: str
    error: Optional[str]
