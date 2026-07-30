# Edge AI Security & Privacy Advisor

This agent provides a web interface for scoring the security and privacy posture of an edge AI deployment. It takes a checklist of deployment characteristics and computes a real risk score and itemized findings from a fixed set of rules.

## Overview

This project is built for a practical edge-AI workflow: get a consistent, reproducible security/privacy risk assessment from a deployment description, rather than a subjective LLM judgment that could vary between runs.

### What it delivers

- a 0-100 security/privacy score, computed from a fixed deduction ruleset
- a risk level (Low / Moderate / High) derived from the score
- an itemized findings table showing exactly which answers triggered a deduction and by how much
- a short plain-language summary highlighting the highest-impact issue to fix first

## Architecture

1. The user answers an 11-item checklist covering personal data handling, transit/at-rest encryption, physical access controls, model IP protection, OTA update signing, and data retention.
2. A fixed set of rules evaluates the answers: each risky combination (e.g. personal data handled without at-rest encryption) triggers a specific point deduction; compliant combinations are logged with no deduction.
3. The score starts at 100 and is reduced by each triggered deduction, floored at 0.
4. The score is mapped to a risk level using fixed thresholds (80+ Low, 50-79 Moderate, below 50 High).
5. Results are shown in the interface: the score, the itemized findings table, and a generated summary.

## Scoring rules

| Condition | Deduction |
|---|---|
| Data transmitted off-device without transit encryption | -25 |
| Personal data processed without at-rest encryption | -20 |
| Personal data processed without documented consent | -15 |
| Personal data retained rather than discarded after inference | -15 |
| No physical access controls on the device | -10 |
| Proprietary model with no extraction protections | -15 |
| OTA updates not cryptographically signed | -20 |

## Tech stack

- Python 3.11
- Gradio for the web UI
- Pandas for the findings table
- Google GenAI for generating a short summary of the result

## Project files

- `app.py` — the Gradio interface and the scoring ruleset
- `requirements.txt` — Python dependencies
- `Dockerfile` — container build and runtime setup
- `README.md` — project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-security-advisor
docker build -t edge-security-advisor .
docker run -p 7869:7869 -e GEMINI_API_KEY=your_key_here edge-security-advisor
```

Open http://localhost:7869 in a browser, answer the checklist, and click Assess Risk.

## Notes

- This is a fixed rule-based checklist, not a comprehensive security audit or compliance certification (e.g. GDPR, HIPAA). It surfaces common, well-established risk patterns for edge AI deployments specifically.
- Checklist items with a dependency (e.g. "encrypted in transit" only matters if "transmits off-device" is checked) only trigger a deduction when the relevant precondition is also checked — checking a dependent item alone has no effect.
- The container exposes port `7869` by default.
