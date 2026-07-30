import pytest
from src.agent.tools import search_internet_and_arxiv, generate_citations
from src.agent.graph import research_graph

def test_search_tool():
    results = search_internet_and_arxiv.invoke({"topic": "Quantum Computing", "include_academic": True})
    assert len(results) >= 2
    assert any("Quantum" in r["title"] for r in results)

def test_citation_generator_tool():
    sources = [{
        "title": "Quantum AI",
        "author": "Dr. Smith",
        "year": 2026,
        "url": "https://example.com/paper"
    }]
    apa = generate_citations.invoke({"sources": sources, "style": "APA"})
    assert "Dr. Smith (2026)" in apa[0]

def test_research_graph_pipeline():
    initial_state = {
        "research_id": "test-res-999",
        "topic": "Graph Neural Networks",
        "depth": "Detailed",
        "include_academic": True,
        "citation_style": "APA",
        "search_results": [],
        "document_summaries": [],
        "keywords": [],
        "report_markdown": "",
        "references": [],
        "ppt_outline": [],
        "topic_matrix": None,
        "status": "init",
        "error": None
    }
    out = research_graph.invoke(initial_state)
    assert out["status"] == "completed"
    assert len(out["references"]) > 0
    assert "Executive Research Report" in out["report_markdown"]
