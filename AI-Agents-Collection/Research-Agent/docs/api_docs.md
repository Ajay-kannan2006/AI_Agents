# Research Agent - API Documentation

## Base URL
`http://localhost:8002/api/v1/research`

## Endpoints

### 1. Trigger Research Job
- **URL**: `/run`
- **Method**: `POST`
- **Payload**:
```json
{
  "topic": "Autonomous AI Agent Orchestration Patterns",
  "depth": "Detailed",
  "include_academic": true,
  "citation_style": "APA"
}
```

### 2. Retrieve Report by ID
- **URL**: `/report/{research_id}`
- **Method**: `GET`
- **Response**: Full markdown report, slide deck outline, keywords, and reference list.
