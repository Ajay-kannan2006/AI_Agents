# Edge AI Data Pipeline Advisor

This agent provides a web interface for checking whether a sample image or audio file is compatible with a model's expected input format. It accepts an uploaded file, measures its real properties, compares them against the expected input specification, and reports concrete preprocessing steps.

## Overview

This project is built for a practical edge-AI workflow: confirm that sensor data (camera or microphone output) actually matches what a model expects before deployment, using real measured file properties rather than assumptions.

### What it delivers

- for images: measured width, height, channel count, and color mode
- for audio: measured sample rate, channel count, duration, and bit depth
- a mismatch report comparing the measured properties against the expected model input
- concrete preprocessing steps for each mismatch found (resize, channel conversion, resampling, trimming/padding)
- a short plain-language summary of the results

## Architecture

1. The uploaded file is read directly: images via Pillow, audio via Python's built-in `wave` module (WAV files only).
2. Real properties are measured from the file — no metadata is assumed or guessed.
3. Measured properties are compared against the expected input specification entered by the user.
4. Each mismatch is translated into a specific, actionable preprocessing step.
5. Results are shown in the interface: a measured-properties panel, a mismatch list, and a generated summary.

## Tech stack

- Python 3.11
- Gradio for the web UI
- Pillow for image inspection
- Python's built-in `wave` module for audio inspection
- Google GenAI for generating a short summary of the result

## Project files

- `app.py` — the Gradio interface, file inspection, and mismatch-checking logic
- `requirements.txt` — Python dependencies
- `Dockerfile` — container build and runtime setup
- `README.md` — project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-data-pipeline
docker build -t edge-data-pipeline .
docker run -p 7866:7866 -e GEMINI_API_KEY=your_key_here edge-data-pipeline
```

Open http://localhost:7866 in a browser, upload a sample file, select the media type, enter the expected input specification, and click Check Compatibility.

## Notes

- Audio inspection currently supports WAV files only. Other formats (MP3, FLAC, etc.) must be converted to WAV first.
- This agent checks file-level properties (resolution, sample rate, channels, duration) only. It does not verify pixel value ranges, normalization, or color channel ordering (RGB vs BGR), which are also common sources of preprocessing errors.
- The container exposes port `7866` by default.
