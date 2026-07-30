import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.logging_config import logger
from src.agent.graph import finance_graph
from src.agent.memory import memory_store
from src.db.models import FinancialReportModel
from src.models.schemas import FinancialAnalysisRequest, FinanceReportResponse, CategoryBreakdown, TransactionItem

class PersonalFinanceService:

    @staticmethod
    async def analyze_financial_statement(request: FinancialAnalysisRequest, db: AsyncSession) -> FinanceReportResponse:
        report_id = str(uuid.uuid4())
        logger.info(f"Executing financial analysis job {report_id}")

        initial_state = {
            "report_id": report_id,
            "monthly_income": request.monthly_income,
            "savings_goal": request.savings_goal,
            "raw_csv": request.statement_csv_content or "",
            "transactions": [],
            "categories": {},
            "recurring_expenses": [],
            "health_score": 0.0,
            "forecast_amount": 0.0,
            "suggestions": [],
            "investments": [],
            "chart_svg": None,
            "status": "initialized",
            "error": None
        }

        # Run LangGraph pipeline
        result_state = finance_graph.invoke(initial_state)
        memory_store.save_state(report_id, result_state)

        income = request.monthly_income
        cats = result_state.get("categories", {})
        total_exp = sum(cats.values())
        savings = income - total_exp
        total_exp_safe = total_exp if total_exp > 0 else 1.0

        breakdown_list = [
            CategoryBreakdown(
                category=cat,
                total_amount=amt,
                percentage_of_total=round((amt / total_exp_safe) * 100, 1)
            )
            for cat, amt in cats.items()
        ]

        recurring_items = [
            TransactionItem(
                date=t.get("date", "2026-07-01"),
                description=t.get("description", "Subscription"),
                amount=t.get("amount", 0.0),
                category=t.get("category", "Subscription"),
                is_recurring=True
            )
            for t in result_state.get("recurring_expenses", [])
        ]

        # Save to DB
        report_db = FinancialReportModel(
            report_id=report_id,
            total_income=income,
            total_expenses=total_exp,
            net_savings=savings,
            financial_health_score=result_state.get("health_score", 75.0),
            category_breakdown_json=json.dumps(cats),
            recurring_expenses_json=json.dumps([t.dict() for t in recurring_items]),
            suggestions_json=json.dumps(result_state.get("suggestions", [])),
            investments_json=json.dumps(result_state.get("investments", [])),
            forecast_next_month=result_state.get("forecast_amount", total_exp)
        )
        db.add(report_db)
        await db.commit()

        return FinanceReportResponse(
            report_id=report_id,
            total_income=income,
            total_expenses=total_exp,
            net_savings=savings,
            financial_health_score=result_state.get("health_score", 75.0),
            category_breakdown=breakdown_list,
            recurring_expenses=recurring_items,
            savings_suggestions=result_state.get("suggestions", []),
            investment_recommendations=result_state.get("investments", []),
            spending_forecast_next_month=result_state.get("forecast_amount", total_exp),
            chart_svg=result_state.get("chart_svg")
        )
