from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.models.schemas import ResearchRequest, ResearchReportResponse
from src.services.core_service import ResearchService

router = APIRouter(prefix="/api/v1/research", tags=["Research Agent"])

@router.post("/run", response_model=ResearchReportResponse, status_code=status.HTTP_201_CREATED)
async def run_research_job(
    payload: ResearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Triggers an autonomous research workflow across search engines, arXiv, and document summarization."""
    return await ResearchService.execute_research(payload, db)

@router.get("/report/{research_id}", response_model=ResearchReportResponse)
async def get_research_report(
    research_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves a previously generated research report by research ID."""
    try:
        return await ResearchService.get_report_by_id(research_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
