# Edge AI Performance Estimator

This agent estimates how demanding an ONNX model is for edge deployment. It counts parameters, computes FLOPs for supported operators, and compares the workload against a set of representative edge devices.

## Overview

The app is useful for early-stage model selection and hardware planning. It helps answer questions such as:

- how large is this model in parameter count?
- how much compute does it appear to require?
- which devices are likely to be the most suitable for running it?

## Architecture

1. The uploaded ONNX model is loaded and validated.
2. Parameters are counted directly from the model initializer tensors.
3. ONNX shape inference is used to resolve tensor dimensions where possible.
4. FLOPs are estimated for common operators such as `Conv`, `Gemm`, and `MatMul`.
5. A rough latency estimate is produced for each device based on a simple compute-class heuristic.
6. The results are displayed in a chart and a short explanation is generated.

## Tech stack

- Python 3.11
- Gradio for the web interface
- ONNX and ONNX shape inference for model analysis
- NumPy and Pandas for numerical and tabular processing
- Google GenAI for summarizing the results

## Project files

- `app.py` - model analysis, FLOPs estimation, device comparison, and UI
- `requirements.txt` - Python dependencies
- `Dockerfile` - container build and runtime setup
- `README.md` - project documentation

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

Open http://localhost:7864 in a browser and upload an ONNX model.

## Notes

- The latency estimates are heuristic and should not be treated as benchmark results.
- FLOPs are only estimated for supported operators. Operators that cannot be resolved statically are marked as unknown.
- Models with dynamic shapes can produce incomplete FLOPs estimates.
- The container exposes port `7864` by default.
