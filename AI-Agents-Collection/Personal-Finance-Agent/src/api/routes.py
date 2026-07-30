from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.models.schemas import FinancialAnalysisRequest, FinanceReportResponse
from src.services.core_service import PersonalFinanceService

router = APIRouter(prefix="/api/v1/finance", tags=["Personal Finance Agent"])

@router.post("/analyze", response_model=FinanceReportResponse, status_code=status.HTTP_201_CREATED)
async def analyze_bank_statement(
    monthly_income: float = Form(5000.0),
    savings_goal: float = Form(1000.0),
    statement_file: UploadFile = File(None),
    statement_csv_text: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Analyzes bank statements (CSV upload or text), categorizes expenses, forecasts budget, and scores financial health."""
    csv_content = ""
    if statement_file:
        raw_bytes = await statement_file.read()
        csv_content = raw_bytes.decode("utf-8", errors="ignore")
    elif statement_csv_text:
        csv_content = statement_csv_text

    req = FinancialAnalysisRequest(
        monthly_income=monthly_income,
        savings_goal=savings_goal,
        statement_csv_content=csv_content
    )
    return await PersonalFinanceService.analyze_financial_statement(req, db)
