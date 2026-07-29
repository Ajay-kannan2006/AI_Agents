# Edge AI Model Selector

This agent helps identify suitable machine-learning models for a target task by searching the Hugging Face Hub and ranking the results with a reproducible scoring method. It is intended for fast model discovery during edge-AI project planning.

## Overview

The app answers a practical question: which public model is the best candidate for a given task when download popularity and size both matter?

### What it delivers

- a free-text task input
- an optional maximum-size filter
- live results from the Hugging Face Hub
- a ranked table of candidate models
- a popularity chart and a short summary of the top result

## Architecture

1. The app issues a live search request to the Hugging Face Hub.
2. Candidate models are collected and their metadata is retrieved.
3. A deterministic popularity score is computed from download and like counts.
4. Models above the selected size limit are removed from the result set.
5. The ranked models are displayed in a table and chart.
6. A short explanation of the best candidate is generated for the user.

## Tech stack

- Python 3.11
- Gradio for the web UI
- Hugging Face Hub API via `huggingface_hub`
- Google GenAI for summarizing the ranked result
- Pandas for tabular output

## Project files

- `app.py` - search logic, ranking logic, UI, and summary generation
- `requirements.txt` - Python dependencies
- `Dockerfile` - container build and runtime setup
- `README.md` - project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`
- outbound network access so the container can reach Hugging Face

### Start the app

```bash
cd agent-model-selector
docker build -t edge-model-selector .
docker run -p 7861:7861 -e GEMINI_API_KEY=your_key_here edge-model-selector
```

Open http://localhost:7861 in a browser and try a task such as `image-classification`.

## Notes

- The ranking is based on live Hugging Face metadata, so results can change over time.
- Some repositories do not expose reliable size information, so size-limited searches may exclude them.
- The score is a simple heuristic rather than a full benchmark or accuracy evaluation.
- The container exposes port `7861` by default.
