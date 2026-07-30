# Edge AI Performance Estimator

This agent provides a web interface for estimating model compute cost and cross-device latency for ONNX models. It accepts an uploaded `.onnx` file, computes the real parameter count and FLOPs from the model graph, and produces a heuristic latency estimate across a set of edge devices.

## Overview

This project is built for a practical edge-AI workflow: get a compute-cost estimate for a model before committing to a device, without relying on the model author's claims or an LLM's guess.

### What it delivers

- exact parameter count, computed from the model's real weight tensors
- estimated FLOPs for Conv (1D/2D/3D), Gemm, and MatMul operators, computed from real operator shapes via ONNX shape inference
- an optional override for models with dynamic input dimensions (e.g. audio/sequence models), so FLOPs can be computed exactly instead of defaulting to an undercount
- a heuristic latency estimate across 14 reference edge devices, sorted fastest to slowest
- a short plain-language summary of the results

## Architecture

1. The uploaded ONNX model is loaded and validated.
2. Parameter count is computed by summing the size of every initializer tensor.
3. Any dynamic input dimensions are resolved — either from a user-supplied override or a default value of 1 — so shape inference can proceed; every substitution is logged.
4. ONNX shape inference runs on the resolved model to determine real intermediate tensor shapes.
5. FLOPs are computed per operator using real weight shapes and real inferred output shapes.
6. Estimated latency per device is computed from FLOPs divided by a heuristic effective-compute figure for that device's compute class.
7. Results are shown in the interface: a model stats panel, a per-device latency chart, and a generated summary.

## Tech stack

- Python 3.11
- Gradio for the web UI
- ONNX for model loading, validation, and shape inference
- NumPy and Pandas for numerical computation and result tables
- Google GenAI for generating a short summary of the result

## Project files

- `app.py` — the Gradio interface, parameter/FLOPs computation, dynamic-dimension resolution, latency estimation, and result summary
- `requirements.txt` — Python dependencies
- `Dockerfile` — container build and runtime setup
- `README.md` — project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-performance-estimator
docker build -t edge-performance-estimator .
docker run -p 7864:7864 -e GEMINI_API_KEY=your_key_here edge-performance-estimator
```

Open http://localhost:7864 in a browser, upload an ONNX model, and click Estimate Performance.

## Notes

- FLOPs are only computed for Conv, Gemm, and MatMul operators. Models dominated by other operator types will show a lower FLOPs count than their real compute cost.
- Latency is a heuristic estimate based on assumed per-device-class compute throughput, not a measured benchmark. Treat it as a relative comparison across devices, not an exact prediction.
- Models with a dynamic input dimension (common in audio/sequence models) will default that dimension to 1 unless a real value is supplied in the override field. This is stated explicitly in the result panel whenever it happens.
- The container exposes port `7864` by default.
