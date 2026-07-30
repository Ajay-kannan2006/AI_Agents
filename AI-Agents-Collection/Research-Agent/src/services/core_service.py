import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.logging_config import logger
from src.agent.graph import research_graph
from src.agent.memory import memory_store
from src.db.models import ResearchReportModel
from src.models.schemas import ResearchRequest, ResearchReportResponse, PresentationSlide

class ResearchService:

    @staticmethod
    async def execute_research(request: ResearchRequest, db: AsyncSession) -> ResearchReportResponse:
        research_id = str(uuid.uuid4())
        logger.info(f"Starting research job {research_id} for topic: {request.topic}")

        initial_state = {
            "research_id": research_id,
            "topic": request.topic,
            "depth": request.depth,
            "include_academic": request.include_academic,
            "citation_style": request.citation_style,
            "search_results": [],
            "document_summaries": [],
            "keywords": [],
            "report_markdown": "",
            "references": [],
            "ppt_outline": [],
            "topic_matrix": None,
            "status": "initialized",
            "error": None
        }

        # Run LangGraph pipeline
        result_state = research_graph.invoke(initial_state)
        memory_store.save_state(research_id, result_state)

        report_md = result_state.get("report_markdown", "")
        summary_excerpt = report_md.split("\n\n")[1] if "\n\n" in report_md else report_md[:300]

        # Save to DB
        report_db = ResearchReportModel(
            research_id=research_id,
            topic=request.topic,
            keywords_json=json.dumps(result_state.get("keywords", [])),
            executive_summary=summary_excerpt,
            report_markdown=report_md,
            references_json=json.dumps(result_state.get("references", [])),
            ppt_outline_json=json.dumps(result_state.get("ppt_outline", []))
        )
        db.add(report_db)
        await db.commit()

        ppt_slides = [
            PresentationSlide(**s) for s in result_state.get("ppt_outline", [])
        ]

        return ResearchReportResponse(
            research_id=research_id,
            topic=request.topic,
            executive_summary=summary_excerpt,
            keywords=result_state.get("keywords", []),
            key_findings=result_state.get("document_summaries", []),
            full_report_markdown=report_md,
            references=result_state.get("references", []),
            ppt_outline=ppt_slides,
            topic_comparison_matrix=result_state.get("topic_matrix")
        )

    @staticmethod
    async def get_report_by_id(research_id: str, db: AsyncSession) -> ResearchReportResponse:
        logger.info(f"Retrieving research report for ID: {research_id}")
        result = await db.execute(select(ResearchReportModel).filter_by(research_id=research_id))
        report_db = result.scalars().first()

        if not report_db:
            raise ValueError(f"Research report with ID {research_id} not found.")

        keywords = json.loads(report_db.keywords_json)
        references = json.loads(report_db.references_json)
        ppt_json = json.loads(report_db.ppt_outline_json)

        return ResearchReportResponse(
            research_id=report_db.research_id,
            topic=report_db.topic,
            executive_summary=report_db.executive_summary,
            keywords=keywords,
            key_findings=keywords,
            full_report_markdown=report_db.report_markdown,
            references=references,
            ppt_outline=[PresentationSlide(**s) for s in ppt_json]
        )
