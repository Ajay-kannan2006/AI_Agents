import ast
import re
from typing import Dict, Any, List
from langchain_core.tools import tool
from config.logging_config import logger

@tool
def parse_python_ast(code_string: str) -> Dict[str, Any]:
    """Parses Python source code AST to inspect imports, function definitions, classes, and complexity metrics."""
    logger.info("Executing AST parsing analysis on source code")
    if not code_string or not code_string.strip():
        return {"ast_valid": False, "functions": [], "classes": [], "imports": []}

    try:
        tree = ast.parse(code_string)
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}")

        return {
            "ast_valid": True,
            "function_count": len(functions),
            "functions": functions,
            "class_count": len(classes),
            "classes": classes,
            "imports": imports,
            "line_count": len(code_string.splitlines())
        }
    except SyntaxError as e:
        logger.warning(f"AST SyntaxError detected: {e}")
        return {
            "ast_valid": False,
            "syntax_error": str(e),
            "line_number": e.lineno
        }

@tool
def detect_hardcoded_secrets(code_string: str) -> List[Dict[str, Any]]:
    """Performs static pattern matching to detect exposed API keys, passwords, or hardcoded tokens."""
    issues = []
    patterns = {
        "Hardcoded API Key": r'(?i)(api[_-]?key|secret|token|password)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']',
        "SQL Injection Vulnerability": r'(?i)(execute|query)\s*\(\s*["\'].*SELECT.*%.*["\']',
        "Bare Except Handler": r'except\s*:'
    }

    lines = code_string.splitlines()
    for i, line in enumerate(lines, 1):
        for vuln_type, pattern in patterns.items():
            if re.search(pattern, line):
                issues.append({
                    "issue_type": "Security" if "Key" in vuln_type or "SQL" in vuln_type else "CodeSmell",
                    "severity": "Critical" if "Key" in vuln_type else "High",
                    "line_number": i,
                    "title": vuln_type,
                    "description": f"Potential security vulnerability detected at line {i}: '{line.strip()}'",
                    "suggested_fix": "Use environment variables or parameterized queries instead of inline strings."
                })
    return issues

@tool
def calculate_code_quality_index(issues: List[Dict[str, Any]], line_count: int = 100) -> float:
    """Calculates overall code quality score (0.0 to 100.0) based on defect weights."""
    score = 100.0
    for issue in issues:
        sev = issue.get("severity", "Low").lower()
        if sev == "critical":
            score -= 20.0
        elif sev == "high":
            score -= 10.0
        elif sev == "medium":
            score -= 5.0
        else:
            score -= 2.0

    return round(max(0.0, score), 1)
