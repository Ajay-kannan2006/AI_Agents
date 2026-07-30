# Code Review Agent - API Specification

## Base URL
`http://localhost:8004/api/v1/code-review`

## Endpoints

### 1. Analyze Code Snippet
- **URL**: `/analyze`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `code_filename` (string): Target filename
  - `language` (string): Code language ("python", "javascript", "go")
  - `code_file` (file): Source code file upload
  - `code_content` (string): Raw source code fallback text
