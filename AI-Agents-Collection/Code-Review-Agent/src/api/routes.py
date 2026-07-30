from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.models.schemas import CodeReviewRequest, CodeReviewReportResponse
from src.services.core_service import CodeReviewService

router = APIRouter(prefix="/api/v1/code-review", tags=["Code Review Agent"])

@router.post("/analyze", response_model=CodeReviewReportResponse, status_code=status.HTTP_201_CREATED)
async def analyze_code_snippet(
    code_filename: str = Form("main.py"),
    language: str = Form("python"),
    code_file: UploadFile = File(None),
    code_content: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Audits source code files or text snippets for security vulnerabilities, bugs, code smells, and generates refactored code and Pytest unit tests."""
    content = ""
    if code_file:
        raw_bytes = await code_file.read()
        content = raw_bytes.decode("utf-8", errors="ignore")
    elif code_content:
        content = code_content

    req = CodeReviewRequest(
        code_filename=code_filename,
        language=language,
        code_content=content
    )
    return await CodeReviewService.analyze_code(req, db)
