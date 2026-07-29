# Edge AI Device Recommender

This agent helps compare edge devices for machine-learning workloads using a deterministic scoring approach. It evaluates a selected device against a curated set of AI tasks and model-size references to estimate feasibility for deployment.

## Overview

The app is intended for early-stage hardware planning. It helps answer questions such as:

- which edge devices are suitable for a target AI task?
- how well does a device fit a specific model size?
- which tasks are clearly feasible, marginal, or unrealistic for that device?

## Architecture

1. The selected device is matched against a built-in dataset of hardware specifications.
2. A set of reference benchmarks and model sizes is used as the task baseline.
3. A deterministic feasibility score is calculated from RAM headroom, accelerator support, and power budget.
4. The results are shown in a score table and chart.
5. A short explanation of the outcome is generated for the user.

## Tech stack

- Python 3.11
- Gradio for the web UI
- Pandas for device and benchmark data handling
- Google GenAI for explaining the computed results

## Project files

- `app.py` - device data, scoring logic, UI, and result explanation
- `requirements.txt` - Python dependencies
- `Dockerfile` - container build and runtime setup
- `README.md` - project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd edge-device-recommender
docker build -t edge-device-recommender .
docker run -p 7860:7860 -e GEMINI_API_KEY=your_key_here edge-device-recommender
```

Open http://localhost:7860 in a browser and select a device to analyze.

## Notes

- The scoring is heuristic and intended for initial comparison, not production benchmarking.
- The app uses a small curated dataset and can be extended with more devices or benchmarks.
- The current implementation focuses on feasibility and fit rather than measuring real runtime performance.
- The container exposes port `7860` by default.

