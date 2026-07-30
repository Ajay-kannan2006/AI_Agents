import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.logging_config import logger
from src.agent.graph import code_review_graph
from src.agent.memory import memory_store
from src.db.models import CodeReviewReportModel
from src.models.schemas import CodeReviewRequest, CodeReviewReportResponse, IssueItem

class CodeReviewService:

    @staticmethod
    async def analyze_code(request: CodeReviewRequest, db: AsyncSession) -> CodeReviewReportResponse:
        review_id = str(uuid.uuid4())
        filename = request.code_filename or "main.py"
        logger.info(f"Starting code review job {review_id} for file {filename}")

        code = request.code_content or """def process_user_data(user_id, secret_token="my_secret_key_123"):
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
    print("Executing query:", query)
    return query
"""

        initial_state = {
            "review_id": review_id,
            "filename": filename,
            "language": request.language,
            "code_content": code,
            "ast_data": None,
            "detected_issues": [],
            "quality_score": 100.0,
            "refactored_code": None,
            "docstring_suggestion": None,
            "unit_tests": None,
            "status": "initialized",
            "error": None
        }

        # Run LangGraph pipeline
        result_state = code_review_graph.invoke(initial_state)
        memory_store.save_state(review_id, result_state)

        issues_raw = result_state.get("detected_issues", [])
        issues_list = [IssueItem(**iss) for iss in issues_raw]

        bugs = sum(1 for i in issues_list if i.issue_type == "Bug")
        sec = sum(1 for i in issues_list if i.issue_type == "Security")
        smells = sum(1 for i in issues_list if i.issue_type == "CodeSmell")
        perf = sum(1 for i in issues_list if i.issue_type == "Performance")

        # Save to DB
        report_db = CodeReviewReportModel(
            review_id=review_id,
            filename=filename,
            language=request.language,
            quality_score=result_state.get("quality_score", 85.0),
            total_issues=len(issues_list),
            issues_json=json.dumps([i.dict() for i in issues_list]),
            refactored_code=result_state.get("refactored_code"),
            generated_unit_tests=result_state.get("unit_tests")
        )
        db.add(report_db)
        await db.commit()

        return CodeReviewReportResponse(
            review_id=review_id,
            filename=filename,
            language=request.language,
            total_issues=len(issues_list),
            quality_score=result_state.get("quality_score", 85.0),
            bugs_count=bugs,
            security_vulnerabilities_count=sec,
            code_smells_count=smells,
            performance_issues_count=perf,
            issues=issues_list,
            docstring_suggestion=result_state.get("docstring_suggestion"),
            refactored_code=result_state.get("refactored_code"),
            generated_unit_tests=result_state.get("unit_tests")
        )
