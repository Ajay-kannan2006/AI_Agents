# Personal Finance Agent - API Specification

## Base URL
`http://localhost:8003/api/v1/finance`

## Endpoints

### 1. Analyze Financial Statement
- **URL**: `/analyze`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `monthly_income` (float): Monthly net income
  - `savings_goal` (float): Target monthly savings amount
  - `statement_file` (file): Bank statement CSV file upload
  - `statement_csv_text` (string): Raw CSV text fallback
