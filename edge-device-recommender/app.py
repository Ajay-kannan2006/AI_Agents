import os
import pandas as pd
import gradio as gr
from google import genai
from google.genai import types

# --- 1. Knowledge base ---
devices = pd.DataFrame([
    {"device_name": "Arduino Nano 33 BLE Sense", "compute_class": "MCU",          "ram_mb": 0.25,  "accelerator": "none",                            "power_budget_w": 0.15},
    {"device_name": "Generic Cortex-M7 MCU",     "compute_class": "MCU",          "ram_mb": 1,     "accelerator": "none",                            "power_budget_w": 0.5},
    {"device_name": "ESP32-S3",                  "compute_class": "MCU",          "ram_mb": 0.5,   "accelerator": "none (optional vector instr.)",  "power_budget_w": 0.5},
    {"device_name": "Generic Cortex-M4 MCU",     "compute_class": "MCU",          "ram_mb": 0.25,  "accelerator": "none",                            "power_budget_w": 0.3},
    {"device_name": "Raspberry Pi Zero 2 W",     "compute_class": "SBC-CPU",      "ram_mb": 512,   "accelerator": "none",                            "power_budget_w": 1},
    {"device_name": "Raspberry Pi 4",            "compute_class": "SBC-CPU",      "ram_mb": 4096,  "accelerator": "none",                            "power_budget_w": 5},
    {"device_name": "Raspberry Pi 5",            "compute_class": "SBC-CPU",      "ram_mb": 8192,  "accelerator": "none",                            "power_budget_w": 5},
    {"device_name": "Generic Cortex-A72 SBC",    "compute_class": "SBC-CPU",      "ram_mb": 2048,  "accelerator": "none",                            "power_budget_w": 4},
    {"device_name": "Coral Dev Board",           "compute_class": "SBC-accel",    "ram_mb": 1024,  "accelerator": "Edge TPU",                        "power_budget_w": 2},
    {"device_name": "BeagleBone AI-64",          "compute_class": "SBC-accel",    "ram_mb": 4096,  "accelerator": "C7x DSP + MMA (~8 TOPS)",         "power_budget_w": 10},
    {"device_name": "NVIDIA Jetson Nano",        "compute_class": "SBC-GPU",      "ram_mb": 4096,  "accelerator": "128-core Maxwell GPU",            "power_budget_w": 10},
    {"device_name": "NVIDIA Jetson Orin Nano Super", "compute_class": "SBC-GPU",  "ram_mb": 8192,  "accelerator": "1024-core Ampere GPU, up to 67 TOPS", "power_budget_w": 15},
    {"device_name": "NVIDIA Jetson AGX Orin 32GB", "compute_class": "SBC-GPU",    "ram_mb": 32768, "accelerator": "2048-core Ampere GPU + 2x NVDLA, up to 200 TOPS", "power_budget_w": 60},
    {"device_name": "Generic mobile SoC w/ NPU", "compute_class": "Mobile-accel", "ram_mb": 8192,  "accelerator": "vendor NPU (e.g. Hexagon/NNAPI)", "power_budget_w": 5},
])

benchmarks = pd.DataFrame([
    {"task": "keyword_spotting",     "model": "DS-CNN",          "model_size_kb": 52.5,  "quality_target": "90% top-1",          "dataset": "Speech Commands", "source": "MLPerf Tiny v0.5",          "latency_ms": None},
    {"task": "visual_wake_words",    "model": "MobileNetV1",     "model_size_kb": 325,   "quality_target": "80% top-1",          "dataset": "VWW Dataset",     "source": "MLPerf Tiny v0.5",          "latency_ms": None},
    {"task": "image_classification", "model": "ResNet (custom)", "model_size_kb": 96,    "quality_target": "85% top-1",          "dataset": "CIFAR10",         "source": "MLPerf Tiny v0.5",          "latency_ms": None},
    {"task": "image_classification", "model": "MobileNetV2",     "model_size_kb": 14000, "quality_target": "71.8% top-1",        "dataset": "ImageNet",        "source": "MobileNetV2 paper",         "latency_ms": None},
    {"task": "anomaly_detection",    "model": "FC-AutoEncoder",  "model_size_kb": 270,   "quality_target": "0.85 AUC",           "dataset": "ToyADMOS",        "source": "MLPerf Tiny v0.5",          "latency_ms": None},
    {"task": "object_detection",     "model": "YOLOv8n",         "model_size_kb": 6200,  "quality_target": "37.3% mAP@0.5:0.95", "dataset": "COCO",            "source": "Ultralytics docs",          "latency_ms": None},
    {"task": "speech_recognition",   "model": "Whisper-tiny",    "model_size_kb": 76800, "quality_target": "~5.6% WER (en)",     "dataset": "LibriSpeech",     "source": "OpenAI Whisper model card", "latency_ms": None},
])


# --- 2. Deterministic computation (no LLM involved) ---
def get_device_specs(device_name: str) -> dict:
    match = devices[devices["device_name"].str.lower() == device_name.lower()]
    if match.empty:
        match = devices[devices["device_name"].str.contains(device_name, case=False, na=False)]
    if match.empty:
        return {"found": False}
    return {"found": True, "specs": match.iloc[0].to_dict()}


def score_feasibility(device_name: str) -> pd.DataFrame:
    """Deterministic 0-100 feasibility score per task for a named device. Pure arithmetic --
    same device in, same scores out, every time. See README for the exact formula."""
    dev_info = get_device_specs(device_name)
    if not dev_info["found"]:
        return pd.DataFrame()
    dev = dev_info["specs"]

    rows = []
    for task, group in benchmarks.groupby("task"):
        best = group.loc[group["model_size_kb"].idxmin()]
        model_mb = best["model_size_kb"] / 1024

        ram_ratio = model_mb / dev["ram_mb"] if dev["ram_mb"] else 1.0
        ram_score = 100 if ram_ratio < 0.05 else max(0, 100 - ram_ratio * 800)

        has_accel = dev["accelerator"] != "none"
        accel_score = 100 if has_accel else (70 if model_mb < 1 else 30)

        power_score = 100 if dev["power_budget_w"] >= 1 or model_mb < 0.5 else 50

        overall = round(0.5 * ram_score + 0.3 * accel_score + 0.2 * power_score)
        rows.append({
            "task": task,
            "reference_model": best["model"],
            "model_size_kb": best["model_size_kb"],
            "feasibility_score": overall,
            "verdict": "highly feasible" if overall >= 75 else "marginal" if overall >= 40 else "not feasible",
        })
    return pd.DataFrame(rows).sort_values("feasibility_score", ascending=False)


# --- 3. Gemini client -- used ONLY for the plain-language explanation, never for scoring ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7860:7860 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(device_name: str, scores_df: pd.DataFrame, specs: dict) -> str:
    if scores_df.empty:
        return (
            f"**'{device_name}' not found** in the device table. Known devices: "
            + ", ".join(devices["device_name"].tolist())
        )
    prompt = (
        f"Device: {device_name}\nSpecs: {specs}\n"
        f"Computed feasibility scores (already calculated, do not recompute or contradict them): "
        f"{scores_df.to_dict(orient='records')}\n\n"
        "In 3-4 sentences for a hackathon demo audience, explain why this device landed where it "
        "did, calling out the standout best-fit and worst-fit tasks by name. Do not invent any "
        "numbers not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 4. Dashboard UI (not a chatbot) ---
def analyze(device_name):
    dev_info = get_device_specs(device_name)
    scores_df = score_feasibility(device_name)
    explanation = explain(device_name, scores_df, dev_info.get("specs", {}))
    if scores_df.empty:
        return pd.DataFrame(), None, explanation, "*(device not found)*"

    spec_text = "\n".join(f"- **{k}**: {v}" for k, v in dev_info["specs"].items())
    return scores_df, scores_df, explanation, spec_text


with gr.Blocks(title="Edge AI Device Recommender") as demo:
    gr.Markdown(
        "# Edge AI Device Recommender\n"
        "Pick a device, hit Analyze. Feasibility scores are computed deterministically from real "
        "RAM/accelerator/power specs and real benchmark model sizes -- the LLM only explains the "
        "result, it never decides it."
    )
    with gr.Row():
        device_input = gr.Dropdown(
            choices=sorted(devices["device_name"].tolist()),
            allow_custom_value=True,
            value="Raspberry Pi 4",
            label="Device",
        )
        analyze_btn = gr.Button("Analyze", variant="primary")

    with gr.Row():
        with gr.Column(scale=2):
            score_table = gr.Dataframe(label="Feasibility scores (computed)", interactive=False)
        with gr.Column(scale=1):
            spec_panel = gr.Markdown(label="Device specs")

    score_chart = gr.BarPlot(
        x="task", y="feasibility_score", color="verdict",
        title="Feasibility by task", y_lim=[0, 100], height=300,
    )
    explanation_panel = gr.Markdown(label="Explanation")

    analyze_btn.click(
        fn=analyze,
        inputs=device_input,
        outputs=[score_table, score_chart, explanation_panel, spec_panel],
    )
    demo.load(fn=analyze, inputs=device_input, outputs=[score_table, score_chart, explanation_panel, spec_panel])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
