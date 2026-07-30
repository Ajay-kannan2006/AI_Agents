RESEARCH_SUMMARIZER_PROMPT = """You are a Senior Academic Researcher.
Summarize the key insights, methodology, and findings from the provided source articles related to the topic: "{topic}".

Sources:
{sources_text}

Return JSON with:
- keywords: list of top 5-8 extracted keywords
- document_summaries: list of concise paragraph summaries per source
"""

REPORT_GENERATOR_PROMPT = """You are an Executive Technology Analyst writing a comprehensive research paper on "{topic}".

Summaries & Data:
{summaries_text}

Citation Style: {citation_style}

Produce a complete Markdown report containing:
# Executive Summary
# Introduction & Background
# Key Architectural Findings & Comparisons
# Strategic Recommendations
# Conclusion

Include inline bracketed citations like [1], [2].
"""

PPT_OUTLINE_PROMPT = """Create a 5-slide presentation outline based on the following report summaries:

Topic: {topic}
Summaries: {summaries_text}

Return JSON array of slide objects:
[
  {{
    "slide_number": 1,
    "slide_title": "Title of Slide",
    "bullet_points": ["Point 1", "Point 2", "Point 3"]
  }}
]
"""
