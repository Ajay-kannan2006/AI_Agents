import os
import pandas as pd
import gradio as gr
import onnx
from google import genai

# --- 1. Curated reference: real framework op-support characteristics ---
# "yes"/"partial"/"no" reflect general, well-established framework behavior. This is a curated
# best-effort reference, not a live per-version check -- framework op support changes between
# releases, so always verify against your exact target framework version before a final
# deployment decision. Ops not listed here are marked "unknown" rather than assumed supported.
COMPAT_TABLE = {
    "Conv":                  {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Gemm":                  {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "partial", "openvino": "yes"},
    "MatMul":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "partial", "openvino": "yes"},
    "Relu":                  {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "LeakyRelu":              {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Sigmoid":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Tanh":                   {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Softmax":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "BatchNormalization":     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "InstanceNormalization":  {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "partial", "openvino": "yes"},
    "MaxPool":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "AveragePool":            {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "GlobalAveragePool":      {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Reshape":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Transpose":               {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Concat":                  {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Split":                   {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Slice":                   {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Resize":                  {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "Upsample":                {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "LSTM":                    {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "GRU":                     {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "NonMaxSuppression":       {"onnxruntime": "yes", "tensorrt": "no",      "tflite": "yes",     "openvino": "yes"},
    "Gather":                  {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "Where":                   {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "Erf":                     {"onnxruntime": "yes", "tensorrt": "partial", "tflite": "partial", "openvino": "yes"},
    "Clip":                    {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Pad":                     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Cast":                    {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Constant":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Identity":                {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Flatten":                 {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Add":                     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Sub":                     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Mul":                     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Div":                     {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "ReduceMean":              {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Squeeze":                 {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
    "Unsqueeze":               {"onnxruntime": "yes", "tensorrt": "yes",     "tflite": "yes",     "openvino": "yes"},
}

STATUS_SYMBOL = {"yes": "\u2705 supported", "partial": "\u26a0\ufe0f partial/conditional", "no": "\u274c unsupported", "unknown": "\u2754 not in reference table"}
STATUS_WEIGHT = {"yes": 1.0, "partial": 0.5, "no": 0.0, "unknown": 0.0}

FRAMEWORKS = ["onnxruntime", "tensorrt", "tflite", "openvino"]


# --- 2. Real computation: parse the uploaded model's actual op graph ---
def analyze_model(file_path: str):
    if file_path is None:
        return None, None, "Upload an .onnx file first."
    try:
        model = onnx.load(file_path)
        onnx.checker.check_model(model)
    except Exception as e:
        return None, None, f"Could not load this as a valid ONNX model: {e}"

    op_counts = {}
    for node in model.graph.node:
        op_counts[node.op_type] = op_counts.get(node.op_type, 0) + 1
    return op_counts, model, None


def check_compatibility(op_counts: dict, frameworks: list):
    rows = []
    for op, count in sorted(op_counts.items(), key=lambda x: -x[1]):
        row = {"op_type": op, "count": count}
        for fw in frameworks:
            status = COMPAT_TABLE.get(op, {}).get(fw, "unknown")
            row[fw] = STATUS_SYMBOL[status]
        rows.append(row)
    detail_df = pd.DataFrame(rows)

    total = sum(op_counts.values()) or 1
    score_rows = []
    for fw in frameworks:
        weighted = sum(
            count * STATUS_WEIGHT[COMPAT_TABLE.get(op, {}).get(fw, "unknown")]
            for op, count in op_counts.items()
        )
        score_rows.append({"framework": fw, "compatibility_pct": round(100 * weighted / total, 1)})
    score_df = pd.DataFrame(score_rows)
    return detail_df, score_df


# --- 3. Gemini client -- used ONLY to explain the real computed scores ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7863:7863 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(score_df: pd.DataFrame, detail_df: pd.DataFrame) -> str:
    unsupported = detail_df[detail_df.apply(lambda r: "\u274c" in " ".join(str(v) for v in r.values), axis=1)]
    prompt = (
        f"Real computed framework compatibility scores (do not recompute or contradict): "
        f"{score_df.to_dict(orient='records')}\n"
        f"Ops flagged unsupported on at least one framework: {unsupported['op_type'].tolist() if not unsupported.empty else 'none'}\n\n"
        "In 3-4 sentences for a hackathon demo audience, recommend the best-fit framework(s) "
        "from the scores above, call out any unsupported ops by name as a real risk, and remind "
        "the audience this is a best-effort static reference -- always confirm against the exact "
        "target framework version before final deployment. Do not invent any op or score not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 4. Upload-and-report UI (not a chatbot), distinct color theme from other agents ---
def run_check(file_obj, frameworks):
    op_counts, model, error = analyze_model(file_obj)
    if error:
        return None, None, error
    if not frameworks:
        frameworks = FRAMEWORKS
    detail_df, score_df = check_compatibility(op_counts, frameworks)
    explanation = explain(score_df, detail_df)
    return score_df, detail_df, explanation


theme = gr.themes.Soft(primary_hue="orange", secondary_hue="amber", neutral_hue="stone")

with gr.Blocks(title="Edge AI Toolchain Advisor") as demo:
    gr.Markdown(
        "# \U0001f9f0 Edge AI Toolchain Advisor\n"
        "Upload a real ONNX model, pick which deployment frameworks to check against, click "
        "Check Compatibility. Every operator in your model's actual graph is looked up against a "
        "curated real framework op-support reference -- the score is computed, not guessed."
    )
    with gr.Row():
        file_input = gr.File(label="Upload ONNX model (.onnx)", file_types=[".onnx"], type="filepath")
        framework_input = gr.CheckboxGroup(
            choices=FRAMEWORKS, value=FRAMEWORKS, label="Frameworks to check"
        )
        check_btn = gr.Button("Check Compatibility", variant="primary")

    score_chart = gr.BarPlot(
        x="framework", y="compatibility_pct", title="Compatibility score by framework (%)",
        y_lim=[0, 100], height=280,
    )
    detail_table = gr.Dataframe(label="Per-operator compatibility (real, parsed from your model)")
    explanation_panel = gr.Markdown(label="Recommendation")

    check_btn.click(
        fn=run_check,
        inputs=[file_input, framework_input],
        outputs=[score_chart, detail_table, explanation_panel],
    )

if __name__ == "__main__":
    # Gradio 6.0+ moved `theme` from Blocks() to launch(); older installs still accept it on
    # Blocks() only. Try the new location first, fall back for older pinned environments.
    try:
        demo.launch(server_name="0.0.0.0", server_port=7863, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7863)
