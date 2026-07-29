# Edge AI Compression Advisor

This agent provides a lightweight web interface for compressing ONNX models with real dynamic quantization. It accepts an uploaded `.onnx` file, runs quantization through ONNX Runtime, measures the size change on disk, and returns a downloadable compressed model.

## Overview

This project is built for a practical edge-AI workflow: reduce model size before deployment without relying on a rough estimate.

### What it delivers

- the original and quantized model sizes
- the percentage reduction in size
- a table of the most common operator types in the model graph
- a downloadable quantized `.onnx` file

## Architecture

1. The uploaded ONNX model is loaded and validated.
2. The model graph is parsed to collect operator-type counts.
3. Dynamic quantization is applied using ONNX Runtime.
4. The original and quantized files are compared by actual file size.
5. The results are shown in the interface, and the quantized model is offered for download.

## Tech stack

- Python 3.11
- Gradio for the web UI
- ONNX and ONNX Runtime for model loading and quantization
- Google GenAI for generating a short explanation of the result
- Pandas for formatting the result tables

## Project files

- `app.py` - the Gradio interface, quantization logic, and result explanation
- `requirements.txt` - Python dependencies
- `Dockerfile` - container build and runtime setup
- `README.md` - project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-compression-advisor
docker build -t edge-compression-advisor .
docker run -p 7862:7862 -e GEMINI_API_KEY=your_key_here edge-compression-advisor
```

Open http://localhost:7862 in a browser, upload an ONNX model, and click Quantize.

## Notes

- This app uses dynamic quantization, not static quantization.
- It does not evaluate accuracy after compression. The quantized model should still be validated separately before deployment.
- Larger models may take longer to process, especially in a container environment.
- The container exposes port `7862` by default.
