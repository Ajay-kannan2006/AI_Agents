"""Human-readable rendering for API results."""

from compatibility_agent import CompatibilityResult


def render_report(result: CompatibilityResult) -> str:
    lines = [
        "MODEL COMPATIBILITY REPORT",
        f"Model: {result.model_name}",
        f"Device: {result.device}",
        f"Score: {result.compatibility_score}/100 ({result.verdict})",
        "",
        "Checks:",
    ]
    lines.extend(f"- {'PASS' if item.passed else 'FAIL'} | {item.name}: {item.detail}" for item in result.checks)
    lines.extend(["", "Recommendations:"])
    lines.extend(f"- {item}" for item in result.recommendations)
    if result.ai_insight:
        lines.extend(["", f"AI insight: {result.ai_insight}"])
    return "\n".join(lines)
