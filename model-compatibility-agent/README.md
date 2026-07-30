# Model Compatibility Agent

A production-oriented FastAPI service for the Edge AI Copilot Suite. It evaluates whether an ML model can be deployed to a supported edge device and returns both structured JSON and a readable report.

The core score is deterministic and works fully offline. If configured, an optional Groq free-tier call produces one additional deployment insight; an unavailable key, network failure, or quota error never prevents a response.

## Supported devices

- Raspberry Pi 5
- NVIDIA Jetson Orin Nano
- NVIDIA Jetson Xavier NX
- Intel NUC
- Google Coral Dev Board

## Setup

Use Python 3.12, then install and run:

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive docs are at `/docs`.

## Free Groq key (optional)

1. Create an account at [GroqCloud Console](https://console.groq.com/).
2. Open **API Keys**, create a key, and copy it.
3. Put it in `.env`: `GROQ_API_KEY=your_key_here`.

This project uses the OpenAI-compatible `OpenAI` client with Groq's base URL. Groq availability and free-tier limits are controlled by Groq; leave the key blank to skip LLM enhancement. No paid API is required.

## Request

```bash
curl -X POST http://127.0.0.1:8000/check-compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "MobileNetV3-Large",
    "framework": "TensorFlow Lite",
    "model_size_mb": 21,
    "required_ram_gb": 0.5,
    "required_storage_gb": 0.1,
    "architecture": "ARM64",
    "edge_device": "Raspberry Pi 5"
  }'
```

## Response excerpt

```json
{
  "compatibility": {
    "device": "Raspberry Pi 5",
    "model_name": "MobileNetV3-Large",
    "compatibility_score": 100,
    "verdict": "Compatible",
    "checks": [{"name": "Framework compatibility", "passed": true, "weight": 25}],
    "recommendations": ["Model artifact size is 21 MB; reserve space for its runtime, dependencies, and updates."],
    "ai_insight": null
  },
  "report": "MODEL COMPATIBILITY REPORT\\nModel: MobileNetV3-Large..."
}
```

An unknown device gets a clear HTTP 400 error. Field limits and types are validated by Pydantic; unexpected service errors return HTTP 500 without internal details.
