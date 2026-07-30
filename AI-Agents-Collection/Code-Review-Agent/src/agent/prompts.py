SECURITY_BUG_AUDIT_PROMPT = """You are a Principal Application Security Engineer & Static Analysis Expert.
Audit the following {language} code snippet for OWASP Top 10 vulnerabilities, memory leaks, SQL injection, hardcoded secrets, and logical bugs.

Code Snippet ({filename}):
{code_content}

Return JSON with key "issues": array of objects containing:
- issue_type: "Bug", "Security", "Performance", "CodeSmell", or "Duplicate"
- severity: "Critical", "High", "Medium", or "Low"
- line_number: integer line estimate
- title: concise issue title
- description: clear architectural explanation of the defect
- suggested_fix: drop-in code fix
"""

REFACTORING_TEST_PROMPT = """You are a Principal Software Architect.
Provide optimized refactored code and write complete Pytest unit test suites for the provided {language} code.

Original Code:
{code_content}

Identified Issues:
{issues_json}

Return JSON with:
- refactored_code: clean optimized source code fixing identified defects
- generated_unit_tests: fully functional Pytest test module
- docstring_suggestion: updated module & function documentation
"""
