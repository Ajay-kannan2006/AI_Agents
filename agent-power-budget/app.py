import os
import pandas as pd
import gradio as gr
from google import genai

# --- 1. Real computation: duty-cycle and battery-life arithmetic ---
def calculate(battery_mah, battery_voltage, active_power_w, idle_power_w, target_fps, latency_ms):
    battery_wh = (battery_mah / 1000) * battery_voltage

    raw_duty_cycle = target_fps * (latency_ms / 1000)  # fraction of each second spent computing
    achievable = raw_duty_cycle <= 1.0
    duty_cycle = min(1.0, raw_duty_cycle)

    effective_power_w = duty_cycle * active_power_w + (1 - duty_cycle) * idle_power_w
    runtime_hours = battery_wh / effective_power_w if effective_power_w > 0 else float("inf")
    continuous_runtime_hours = battery_wh / active_power_w if active_power_w > 0 else float("inf")

    # Sweep FPS 1-60 at the given latency to show the runtime/throughput tradeoff curve
    curve_rows = []
    for fps in range(1, 61):
        dc = min(1.0, fps * (latency_ms / 1000))
        p = dc * active_power_w + (1 - dc) * idle_power_w
        rt = battery_wh / p if p > 0 else 0
        curve_rows.append({"target_fps": fps, "estimated_runtime_hours": round(rt, 2)})
    curve_df = pd.DataFrame(curve_rows)

    result = {
        "battery_wh": round(battery_wh, 2),
        "duty_cycle_pct": round(duty_cycle * 100, 1),
        "achievable": achievable,
        "effective_power_w": round(effective_power_w, 3),
        "runtime_hours": round(runtime_hours, 2),
        "continuous_runtime_hours": round(continuous_runtime_hours, 2),
    }
    return result, curve_df


# --- 2. Gemini client -- used only to summarize the real computed numbers ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7865:7865 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(result: dict, target_fps: float, latency_ms: float) -> str:
    prompt = (
        f"Real computed values (do not recompute or contradict): {result}\n"
        f"Target FPS: {target_fps}, inference latency: {latency_ms}ms.\n\n"
        "In 3-4 sentences for a hackathon demo audience: state the estimated runtime and duty "
        "cycle, note whether the target FPS is achievable given the latency (if achievable is "
        "False, say plainly that the model is too slow for this target and lower FPS or a "
        "faster model is needed), and give one concrete suggestion for extending battery life. "
        "Do not invent any number not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Calculator UI (not a chatbot, not a file upload) ---
def run_calculate(battery_mah, battery_voltage, active_power_w, idle_power_w, target_fps, latency_ms):
    result, curve_df = calculate(battery_mah, battery_voltage, active_power_w, idle_power_w, target_fps, latency_ms)

    headline = (
        f"**Battery capacity:** {result['battery_wh']} Wh | "
        f"**Duty cycle:** {result['duty_cycle_pct']}% | "
        f"**Effective power:** {result['effective_power_w']} W\n\n"
        f"**Estimated runtime:** {result['runtime_hours']} hours "
        f"(vs {result['continuous_runtime_hours']} hours if always-on at full active power)"
    )
    if not result["achievable"]:
        headline = (
            "**⚠️ Target FPS is not achievable at this latency** — the model takes longer per "
            "frame than your target frame interval allows, so duty cycle is capped at 100%.\n\n"
            + headline
        )

    explanation = explain(result, target_fps, latency_ms)
    return headline, curve_df, explanation


theme = gr.themes.Soft(primary_hue="violet", secondary_hue="purple", neutral_hue="slate")

with gr.Blocks(title="Edge AI Power Budget Calculator") as demo:
    gr.Markdown(
        "# \U0001f50b Edge AI Power Budget Calculator\n"
        "Adjust the sliders. Duty cycle, effective power, and battery runtime are computed live "
        "from real arithmetic, not estimated by the model."
    )
    with gr.Row():
        with gr.Column():
            battery_mah = gr.Slider(100, 20000, value=3000, step=100, label="Battery capacity (mAh)")
            battery_voltage = gr.Slider(1.0, 12.0, value=3.7, step=0.1, label="Battery voltage (V)")
            active_power_w = gr.Slider(0.01, 30.0, value=2.0, step=0.01, label="Active (inferencing) power draw (W)")
        with gr.Column():
            idle_power_w = gr.Slider(0.001, 5.0, value=0.1, step=0.001, label="Idle power draw (W)")
            target_fps = gr.Slider(0.1, 60.0, value=5.0, step=0.1, label="Target inferences per second")
            latency_ms = gr.Slider(1, 2000, value=50, step=1, label="Inference latency (ms)")

    headline_panel = gr.Markdown(label="Result")
    curve_chart = gr.LinePlot(
        x="target_fps", y="estimated_runtime_hours",
        title="Estimated battery runtime vs. target FPS (at this latency)", height=300,
    )
    explanation_panel = gr.Markdown(label="Summary")

    inputs = [battery_mah, battery_voltage, active_power_w, idle_power_w, target_fps, latency_ms]
    outputs = [headline_panel, curve_chart, explanation_panel]
    for control in inputs:
        control.release(fn=run_calculate, inputs=inputs, outputs=outputs)

    demo.load(fn=run_calculate, inputs=inputs, outputs=outputs)

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7865, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7865)
