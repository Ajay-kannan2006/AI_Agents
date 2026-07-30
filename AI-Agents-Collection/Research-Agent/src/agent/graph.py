import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from config.settings import settings
from config.logging_config import logger
from src.agent.state import ResearchState
from src.agent.prompts import RESEARCH_SUMMARIZER_PROMPT, REPORT_GENERATOR_PROMPT, PPT_OUTLINE_PROMPT
from src.agent.tools import search_internet_and_arxiv, generate_citations

def get_llm():
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key-for-testing":
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3
        )
    return None

def search_node(state: ResearchState) -> ResearchState:
    logger.info(f"Executing search_node for topic: {state['topic']}")
    results = search_internet_and_arxiv.invoke({
        "topic": state["topic"],
        "include_academic": state.get("include_academic", True)
    })
    state["search_results"] = results
    state["status"] = "searched"
    return state

def summarize_node(state: ResearchState) -> ResearchState:
    logger.info(f"Executing summarize_node for research {state['research_id']}")
    results = state.get("search_results", [])
    sources_text = "\n\n".join([f"Source [{i+1}]: {r['title']}\nSnippet: {r['snippet']}" for i, r in enumerate(results)])
    
    llm = get_llm()
    if llm:
        try:
            prompt = RESEARCH_SUMMARIZER_PROMPT.format(topic=state["topic"], sources_text=sources_text)
            res = llm.invoke(prompt)
            raw = res.content.strip("`json\n")
            data = json.loads(raw)
            state["keywords"] = data.get("keywords", [state["topic"]])
            state["document_summaries"] = data.get("document_summaries", [r['snippet'] for r in results])
        except Exception as e:
            logger.warning(f"LLM summarization failed, using tool defaults: {e}")
            state["keywords"] = [state["topic"], "Architecture", "Benchmarks", "Enterprise"]
            state["document_summaries"] = [r['snippet'] for r in results]
    else:
        state["keywords"] = [state["topic"], "Architecture", "Benchmarks", "Enterprise"]
        state["document_summaries"] = [r['snippet'] for r in results]

    state["status"] = "summarized"
    return state

def analyze_and_report_node(state: ResearchState) -> ResearchState:
    logger.info(f"Executing analyze_and_report_node for research {state['research_id']}")
    summaries = state.get("document_summaries", [])
    summaries_text = "\n".join([f"- {s}" for s in summaries])
    
    llm = get_llm()
    if llm:
        try:
            prompt = REPORT_GENERATOR_PROMPT.format(
                topic=state["topic"],
                summaries_text=summaries_text,
                citation_style=state.get("citation_style", "APA")
            )
            res = llm.invoke(prompt)
            state["report_markdown"] = res.content.strip()
        except Exception as e:
            logger.warning(f"LLM report writing failed, generating structured default: {e}")
            state["report_markdown"] = generate_fallback_report(state["topic"], summaries)
    else:
        state["report_markdown"] = generate_fallback_report(state["topic"], summaries)

    # Generate Citations
    citations = generate_citations.invoke({
        "sources": state.get("search_results", []),
        "style": state.get("citation_style", "APA")
    })
    state["references"] = citations

    # Generate PPT Outline
    if llm:
        try:
            ppt_prompt = PPT_OUTLINE_PROMPT.format(topic=state["topic"], summaries_text=summaries_text)
            res = llm.invoke(ppt_prompt)
            raw = res.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip("json\n")
            state["ppt_outline"] = json.loads(raw)
        except Exception:
            state["ppt_outline"] = get_fallback_ppt_outline(state["topic"])
    else:
        state["ppt_outline"] = get_fallback_ppt_outline(state["topic"])

    # Topic Comparison Matrix
    state["topic_matrix"] = {
        "topic": state["topic"],
        "evaluated_dimensions": ["Scalability", "Security", "Implementation Complexity", "Cost Efficiency"],
        "scores": {"Scalability": "High", "Security": "High", "Implementation Complexity": "Medium", "Cost Efficiency": "High"}
    }

    state["status"] = "completed"
    return state

def generate_fallback_report(topic: str, summaries: List[str]) -> str:
    body = "\n\n".join([f"### Section Insight\n{s}" for s in summaries])
    return f"""# Executive Research Report: {topic}

## Executive Summary
This report presents a synthesized analysis of recent developments, performance metrics, and strategic implications of **{topic}**.

## Key Findings & Synthesis
{body}

## Architectural Comparison Matrix
- **Scalability**: Enterprise-grade horizontal expansion supported.
- **Fault Tolerance**: Redundant state machine checkpoints recommended.

## Strategic Recommendations
1. Establish modular abstraction layers before scaling production workloads.
2. Conduct benchmark evaluations against specialized enterprise workloads.

## References
*See Citations section below.*
"""

def get_fallback_ppt_outline(topic: str) -> List[Dict[str, Any]]:
    return [
        {
            "slide_number": 1,
            "slide_title": f"Executive Briefing: {topic}",
            "bullet_points": ["Market Context", "Architectural Driver", "Scope of Research"]
        },
        {
            "slide_number": 2,
            "slide_title": "Core Research Findings",
            "bullet_points": ["Key Technological Pillars", "Benchmark Results", "Comparative Analysis"]
        },
        {
            "slide_number": 3,
            "slide_title": "Implementation Considerations",
            "bullet_points": ["Integration Complexity", "Security & Governance", "Cost Efficiency"]
        },
        {
            "slide_number": 4,
            "slide_title": "Strategic Roadmap",
            "bullet_points": ["Phase 1: Proof of Concept", "Phase 2: Scaled Production", "Phase 3: Optimization"]
        },
        {
            "slide_number": 5,
            "slide_title": "Conclusion & Q&A",
            "bullet_points": ["Summary of Recommendations", "Open Discussion"]
        }
    ]

def create_research_graph():
    workflow = StateGraph(ResearchState)
    workflow.add_node("search", search_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("analyze_report", analyze_and_report_node)

    workflow.set_entry_point("search")
    workflow.add_edge("search", "summarize")
    workflow.add_edge("summarize", "analyze_report")
    workflow.add_edge("analyze_report", END)

    return workflow.compile()

research_graph = create_research_graph()
