CATEGORIZATION_PROMPT = """You are a Financial Data Analyst.
Categorize the following bank transactions into standardized expense categories:
Categories: "Housing", "Groceries", "Dining Out", "Utilities", "Subscription", "Transport", "Shopping", "Entertainment", "Other"

Transactions:
{transactions_json}

Return JSON array of updated transaction objects with "category" and "is_recurring" (boolean) fields.
"""

FINANCIAL_ADVISOR_PROMPT = """You are a Certified Financial Planner.
Analyze candidate's spending and income to generate actionable savings suggestions and investment recommendations.

Monthly Income: ${income}
Total Expenses: ${expenses}
Net Savings: ${savings}
Financial Score: {score}/100
Category Breakdown: {breakdown_json}

Return JSON with:
- savings_suggestions: list of strings (3 actionable advice items)
- investment_recommendations: list of strings (3 conservative and growth investment ideas)
"""
