# Interview Coach Agent - Architecture Documentation

## System Overview
The Interview Coach Agent is an end-to-end AI-powered mock interviewer designed using FastAPI, LangGraph, and SQLite.

```mermaid
graph TD
    User([Candidate / User]) -->|Upload Resume / Answer| FastAPI[FastAPI REST Router]
    FastAPI --> CoreService[Interview Coach Core Service]
    CoreService --> LangGraphEngine[LangGraph Workflow Engine]
    
    subgraph LangGraph Graph Execution
        N1[Extract Skills Node] --> N2[Generate Questions Node]
        N2 --> N3[Evaluate Answer Node]
        N3 --> N4[Generate Report Node]
    end

    LangGraphEngine -->|Invoke Prompts/Tools| OpenAI[OpenAI / Compatible LLM]
    CoreService --> SQLite[(SQLite Database)]
```

## State Machine
The agent manages interview progress using a stateful LangGraph execution state (`InterviewState`) persisting session data in-memory and to SQLite DB.
