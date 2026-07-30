# Edge AI Power Budget Calculator

This agent provides a web interface for estimating battery runtime and duty cycle for an edge AI deployment. It takes battery specs, power draw figures, and a target inference rate, and computes real runtime and duty-cycle numbers live as the inputs change.

## Overview

This project is built for a practical edge-AI workflow: check whether a target inference rate is achievable and how long a device will run on battery, using real arithmetic rather than a rule of thumb.

### What it delivers

- battery energy capacity in watt-hours, computed from mAh and voltage
- duty cycle: the fraction of time the device spends actively inferencing at the target rate
- a clear warning when the target inference rate exceeds what the given latency allows
- effective average power draw, blending active and idle power by duty cycle
- estimated battery runtime, compared against always-on continuous operation
- a runtime-vs-target-FPS curve across a 1-60 FPS sweep at the given latency
- a short plain-language summary of the results

## Architecture

1. Battery capacity in watt-hours is computed from the mAh and voltage inputs.
2. Duty cycle is computed from target FPS and inference latency; if the raw value exceeds 100%, the target rate is flagged as not achievable at that latency.
3. Effective average power is computed by blending active and idle power draw according to the duty cycle.
4. Estimated runtime is computed by dividing battery energy by effective power, and compared against continuous full-power runtime.
5. The same calculation is repeated across a sweep of FPS values from 1 to 60 to build the runtime curve.
6. Results are shown in the interface: a result panel, a runtime-vs-FPS chart, and a generated summary. All six inputs are sliders that recompute results immediately on release.

## Tech stack

- Python 3.11
- Gradio for the web UI
- Pandas for the runtime curve data
- Google GenAI for generating a short summary of the result

## Project files

- `app.py` — the Gradio interface and all duty-cycle/battery-runtime calculations
- `requirements.txt` — Python dependencies
- `Dockerfile` — container build and runtime setup
- `README.md` — project documentation

## Run with Docker

### Prerequisites

- Docker installed and running
- a Gemini API key available as `GEMINI_API_KEY`

### Start the app

```bash
cd agent-power-budget
docker build -t edge-power-budget .
docker run -p 7865:7865 -e GEMINI_API_KEY=your_key_here edge-power-budget
```

Open http://localhost:7865 in a browser and adjust the sliders.

## Notes

- All calculations are deterministic arithmetic; the Gemini call is used only to summarize the already-computed numbers, never to produce them.
- "Target inference rate not achievable" means the model's latency is longer than the time budget implied by the target FPS — lowering the target rate or using a faster model is the fix, not adjusting the battery inputs.
- Idle power draw should reflect the device's power state between inferences (e.g. sleep/standby), not zero, for a realistic effective-power estimate.
- The container exposes port `7865` by default.
