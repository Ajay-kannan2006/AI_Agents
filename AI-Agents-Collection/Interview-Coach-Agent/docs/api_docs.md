# Interview Coach Agent - API Specification

## Base URL
`http://localhost:8001/api/v1/interview`

## Endpoints

### 1. Start Interview Session
- **URL**: `/start`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `target_role` (string): e.g. "Software Engineer"
  - `difficulty` (string): "Junior", "Intermediate", or "Senior"
  - `question_count` (int): default 5
  - `resume_file` (file): optional PDF/text file upload
  - `resume_text` (string): optional raw resume text

### 2. Evaluate Candidate Answer
- **URL**: `/evaluate`
- **Method**: `POST`
- **Payload**:
```json
{
  "session_id": "uuid-string",
  "question_id": 1,
  "question_text": "Describe a challenging technical problem...",
  "candidate_answer": "I redesigned our API gateway to handle high traffic..."
}
```

### 3. Export Final Report
- **URL**: `/report/{session_id}`
- **Method**: `GET`
- **Response**: Full interview summary with scores, strengths, weaknesses, and hiring recommendation.
