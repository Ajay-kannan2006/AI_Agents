# Edge AI Monitoring & Drift Detector

This agent provides a web interface for detecting distribution drift between a baseline dataset and current production data. It accepts two uploaded CSV files, computes real drift statistics per shared numeric column, and reports which columns have drifted significantly.

## Overview

This project is built for a practical edge-AI workflow: know whether a deployed model's input or output distribution has shifted since validation time, using standard statistical drift metrics rather than a qualitative impression.

### What it delivers

- Population Stability Index (PSI) per shared numeric column between the two files
- KL divergence per column, computed over the same histogram bins as the PSI calculation
- a verdict per column (no significant drift / moderate drift / significant drift) using standard PSI thresholds
- a distribution comparison chart (baseline vs. current) for the most-drifted column
- a short plain-language summary of the results

## Architecture

1. Both uploaded CSV files are read and their shared numeric columns identified.
2. For each shared column, real values from both files are binned into a common histogram.
3. PSI and KL divergence are computed from those real histogram bin counts.
4. Each column's PSI is mapped to a verdict using standard thresholds (< 0.1 no significant drift, 0.1-0.25 moderate, > 0.25 significant).
5. A distribution comparison chart is generated for the column with the highest PSI.
6. Results are shown in the interface: a per-column statistics table, the distribution chart, and a generated summary.

## Tech stack

- Python 3.11
- Gradio for the web UI
- Pandas and NumPy for the drift calculations
- Matplotlib for the distribution comparison chart
- Google GenAI for generating a short summary of the result

## Project files

- `app.py` — the Gradio interface, PSI/KL divergence computation, and chart generation
- `requirements.txt` — Python dependencies
- `Dockerfile` — container build and runtime setup
- `README.md` — project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-monitoring-drift
docker build -t edge-monitoring-drift .
docker run -p 7868:7868 -e GEMINI_API_KEY=your_key_here edge-monitoring-drift
```

Open http://localhost:7868 in a browser, upload a baseline CSV and a current CSV, and click Analyze Drift.

## Notes

- Only columns present as numeric in both files are compared; non-numeric or non-shared columns are ignored.
- Histograms use 10 bins by default for PSI/KL calculation; very small datasets (under a few hundred rows per column) will produce noisy statistics.
- PSI thresholds used here (0.1 and 0.25) are the commonly used industry convention, not a universal standard — adjust in `app.py` if your use case calls for different sensitivity.
- The container exposes port `7868` by default.
