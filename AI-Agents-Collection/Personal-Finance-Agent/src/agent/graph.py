import json
import re
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from config.settings import settings
from config.logging_config import logger
from src.agent.state import FinanceState
from src.agent.prompts import CATEGORIZATION_PROMPT, FINANCIAL_ADVISOR_PROMPT
from src.agent.tools import parse_statement_csv, calculate_financial_health_score, generate_pie_chart_svg

def get_llm():
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key-for-testing":
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3
        )
    return None

def parse_transactions_node(state: FinanceState) -> FinanceState:
    logger.info(f"Executing parse_transactions_node for report {state['report_id']}")
    raw_csv = state.get("raw_csv", "")
    transactions = parse_statement_csv.invoke({"csv_content": raw_csv})
    state["transactions"] = transactions
    state["status"] = "parsed"
    return state

def categorize_and_budget_node(state: FinanceState) -> FinanceState:
    logger.info(f"Executing categorize_and_budget_node for report {state['report_id']}")
    txs = state.get("transactions", [])
    
    # Categorization fallback logic
    cat_map: Dict[str, float] = {}
    recurring: List[Dict[str, Any]] = []
    
    for t in txs:
        amt = t.get("amount", 0.0)
        if amt < 0: # Income transaction
            continue
            
        desc = t.get("description", "").lower()
        if any(k in desc for k in ["rent", "apartment", "mortgage"]):
            cat = "Housing"
            is_rec = True
        elif any(k in desc for k in ["food", "market", "grocery", "walmart"]):
            cat = "Groceries"
            is_rec = False
        elif any(k in desc for k in ["net-flix", "netflix", "spotify", "hulu"]):
            cat = "Subscription"
            is_rec = True
        elif any(k in desc for k in ["electric", "gas", "water", "utility"]):
            cat = "Utilities"
            is_rec = True
        elif any(k in desc for k in ["uber", "lyft", "fuel"]):
            cat = "Transport"
            is_rec = False
        else:
            cat = "Shopping"
            is_rec = False

        t["category"] = cat
        t["is_recurring"] = is_rec
        cat_map[cat] = cat_map.get(cat, 0.0) + amt
        if is_rec:
            recurring.append(t)

    state["categories"] = cat_map
    state["recurring_expenses"] = recurring
    state["status"] = "categorized"
    return state

def forecast_and_recommend_node(state: FinanceState) -> FinanceState:
    logger.info(f"Executing forecast_and_recommend_node for report {state['report_id']}")
    income = state.get("monthly_income", 5000.0)
    cats = state.get("categories", {})
    total_exp = sum(cats.values())
    savings = income - total_exp
    goal = state.get("savings_goal", 1000.0)

    health_res = calculate_financial_health_score.invoke({
        "income": income,
        "expenses": total_exp,
        "savings_goal": goal
    })
    state["health_score"] = health_res["score"]

    # Simple 1-month spending forecast
    state["forecast_amount"] = round(total_exp * 1.03, 2) # +3% inflation/trend factor

    # Generate Chart SVG
    state["chart_svg"] = generate_pie_chart_svg.invoke({"categories": cats})

    llm = get_llm()
    if llm:
        try:
            prompt = FINANCIAL_ADVISOR_PROMPT.format(
                income=income,
                expenses=total_exp,
                savings=savings,
                score=health_res["score"],
                breakdown_json=json.dumps(cats)
            )
            res = llm.invoke(prompt)
            raw = res.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip("json\n")
            advice = json.loads(raw)
            state["suggestions"] = advice.get("savings_suggestions", [])
            state["investments"] = advice.get("investment_recommendations", [])
        except Exception as e:
            logger.warning(f"LLM advisor failed, using fallback suggestions: {e}")
            state["suggestions"] = get_fallback_suggestions(savings)
            state["investments"] = get_fallback_investments()
    else:
        state["suggestions"] = get_fallback_suggestions(savings)
        state["investments"] = get_fallback_investments()

    state["status"] = "completed"
    return state

def get_fallback_suggestions(savings: float) -> List[str]:
    return [
        "Audit monthly recurring streaming subscriptions to eliminate unused memberships.",
        "Set up automated paycheck transfers to lock in your monthly savings target first.",
        "Cap dining out expenditures at 15% of your total net monthly income."
    ]

def get_fallback_investments() -> List[str]:
    return [
        "High-Yield Savings Account (HYSA): Maintain 3-6 months of emergency fund liquidity at 4.5%+ APY.",
        "Low-Cost Broad Market Index Funds: Allocate monthly surplus into S&P 500 ETFs (e.g. VOO / SPY).",
        "Tax-Advantaged Retirement Accounts: Maximize annual IRA / 401(k) employer match options."
    ]

def create_finance_graph():
    workflow = StateGraph(FinanceState)
    workflow.add_node("parse_transactions", parse_transactions_node)
    workflow.add_node("categorize_and_budget", categorize_and_budget_node)
    workflow.add_node("forecast_and_recommend", forecast_and_recommend_node)

    workflow.set_entry_point("parse_transactions")
    workflow.add_edge("parse_transactions", "categorize_and_budget")
    workflow.add_edge("categorize_and_budget", "forecast_and_recommend")
    workflow.add_edge("forecast_and_recommend", END)

    return workflow.compile()

finance_graph = create_finance_graph()
