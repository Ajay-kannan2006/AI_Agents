import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import gradio as gr
from google import genai

# --- 1. Real computation: distribution-shift statistics from real uploaded data ---
def compute_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index -- a standard, real drift metric. PSI < 0.1: no significant
    drift. 0.1-0.25: moderate drift, worth monitoring. > 0.25: significant drift."""
    lo = min(baseline.min(), current.min())
    hi = max(baseline.max(), current.max())
    if lo == hi:
        return 0.0
    breakpoints = np.linspace(lo, hi, bins + 1)
    baseline_counts, _ = np.histogram(baseline, bins=breakpoints)
    current_counts, _ = np.histogram(current, bins=breakpoints)

    epsilon = 1e-6
    baseline_pct = np.where(baseline_counts == 0, epsilon, baseline_counts / len(baseline))
    current_pct = np.where(current_counts == 0, epsilon, current_counts / len(current))
    psi = float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))
    return psi


def compute_kl_divergence(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """KL divergence D(baseline || current) over the same real histogram bins as the PSI calc."""
    lo = min(baseline.min(), current.min())
    hi = max(baseline.max(), current.max())
    if lo == hi:
        return 0.0
    breakpoints = np.linspace(lo, hi, bins + 1)
    p, _ = np.histogram(baseline, bins=breakpoints)
    q, _ = np.histogram(current, bins=breakpoints)
    p = p.astype(float) + 1e-10
    q = q.astype(float) + 1e-10
    p /= p.sum()
    q /= q.sum()
    return float(np.sum(p * np.log(p / q)))


def verdict_for_psi(psi: float) -> str:
    if psi < 0.1:
        return "no significant drift"
    elif psi < 0.25:
        return "moderate drift -- monitor"
    return "significant drift -- investigate/retrain"


def analyze_drift(baseline_df: pd.DataFrame, current_df: pd.DataFrame):
    numeric_cols = [
        c for c in baseline_df.columns
        if c in current_df.columns
        and pd.api.types.is_numeric_dtype(baseline_df[c])
        and pd.api.types.is_numeric_dtype(current_df[c])
    ]
    rows = []
    for col in numeric_cols:
        b = baseline_df[col].dropna().to_numpy()
        c = current_df[col].dropna().to_numpy()
        if len(b) < 2 or len(c) < 2:
            continue
        psi = compute_psi(b, c)
        kl = compute_kl_divergence(b, c)
        rows.append({
            "column": col, "psi": round(psi, 4), "kl_divergence": round(kl, 4),
            "verdict": verdict_for_psi(psi),
        })
    result_df = pd.DataFrame(rows).sort_values("psi", ascending=False) if rows else pd.DataFrame()
    return result_df, numeric_cols


def make_distribution_plot(baseline_df: pd.DataFrame, current_df: pd.DataFrame, column: str):
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist(baseline_df[column].dropna(), bins=20, alpha=0.5, label="baseline", density=True)
    ax.hist(current_df[column].dropna(), bins=20, alpha=0.5, label="current", density=True)
    ax.set_title(f"Distribution comparison: {column} (most drifted column)")
    ax.set_xlabel(column)
    ax.set_ylabel("density")
    ax.legend()
    fig.tight_layout()
    return fig


# --- 2. Gemini client -- used only to explain the real computed drift statistics ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7868:7868 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(result_df: pd.DataFrame) -> str:
    if result_df.empty:
        return "No shared numeric columns found between the two files -- nothing to compare."
    prompt = (
        f"Real computed drift statistics per column (do not recompute or contradict): "
        f"{result_df.to_dict(orient='records')}\n\n"
        "In 3-4 sentences for a hackathon demo audience: name the most-drifted column and its "
        "real PSI value, state the overall verdict, and give one concrete recommendation "
        "(retrain, investigate the specific column, or no action needed). Do not invent any "
        "column or number not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Upload-and-report UI (not a chatbot) ---
def run_analysis(baseline_file, current_file):
    if baseline_file is None or current_file is None:
        return None, None, "Upload both a baseline and a current CSV file."
    try:
        baseline_df = pd.read_csv(baseline_file)
        current_df = pd.read_csv(current_file)
    except Exception as e:
        return None, None, f"Could not read one of the files as CSV: {e}"

    result_df, numeric_cols = analyze_drift(baseline_df, current_df)
    if result_df.empty:
        return None, None, "No shared numeric columns found between the two files."

    top_col = result_df.iloc[0]["column"]
    fig = make_distribution_plot(baseline_df, current_df, top_col)
    explanation = explain(result_df)
    return result_df, fig, explanation


theme = gr.themes.Soft(primary_hue="emerald", secondary_hue="lime", neutral_hue="slate")

with gr.Blocks(title="Edge AI Monitoring & Drift Detector") as demo:
    gr.Markdown(
        "# \U0001f4c8 Edge AI Monitoring & Drift Detector\n"
        "Upload a baseline CSV (e.g. validation-time predictions/features) and a current CSV "
        "(e.g. recent production logs). Drift is computed as a real Population Stability Index "
        "and KL divergence per shared numeric column -- not an LLM's impression of the data."
    )
    with gr.Row():
        baseline_input = gr.File(label="Baseline CSV", file_types=[".csv"], type="filepath")
        current_input = gr.File(label="Current (production) CSV", file_types=[".csv"], type="filepath")
        analyze_btn = gr.Button("Analyze Drift", variant="primary")

    result_table = gr.Dataframe(label="Drift statistics per column (real, computed)")
    distribution_plot = gr.Plot(label="Distribution comparison (most-drifted column)")
    explanation_panel = gr.Markdown(label="Summary")

    analyze_btn.click(
        fn=run_analysis,
        inputs=[baseline_input, current_input],
        outputs=[result_table, distribution_plot, explanation_panel],
    )

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7868, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7868)
