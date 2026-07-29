import os
import tempfile
import pandas as pd
import gradio as gr
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType
from google import genai

# --- 1. Real computation: actually quantize the uploaded model, don't just talk about it ---
def quantize_model(file_path: str, weight_type_choice: str):
    """Runs real ONNX dynamic quantization on an uploaded model and reports the real
    before/after size. Returns (size_df, op_df, output_file_path, error_message)."""
    if file_path is None:
        return None, None, None, "Upload an .onnx file first."

    original_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    try:
        model = onnx.load(file_path)
        onnx.checker.check_model(model)
    except Exception as e:
        return None, None, None, f"Could not load this as a valid ONNX model: {e}"

    op_counts = {}
    for node in model.graph.node:
        op_counts[node.op_type] = op_counts.get(node.op_type, 0) + 1
    op_df = pd.DataFrame(
        sorted(op_counts.items(), key=lambda x: -x[1]), columns=["op_type", "count"]
    ).head(10)

    weight_type = QuantType.QInt8 if "QInt8" in weight_type_choice else QuantType.QUInt8
    output_path = os.path.join(tempfile.gettempdir(), "quantized_model.onnx")

    try:
        quantize_dynamic(file_path, output_path, weight_type=weight_type)
    except Exception as e:
        return None, op_df, None, f"Quantization failed: {e}"

    quantized_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    reduction_pct = round((1 - quantized_size_mb / original_size_mb) * 100, 1) if original_size_mb else 0

    size_df = pd.DataFrame([
        {"stage": "original", "size_mb": round(original_size_mb, 3)},
        {"stage": "quantized", "size_mb": round(quantized_size_mb, 3)},
    ])
    size_df.attrs["reduction_pct"] = reduction_pct
    size_df.attrs["output_path"] = output_path
    return size_df, op_df, output_path, None


# --- 2. Gemini client -- used ONLY to explain the real result, never to guess a reduction number ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7862:7862 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(size_df: pd.DataFrame, op_df: pd.DataFrame, weight_type_choice: str) -> str:
    if size_df is None:
        return ""
    prompt = (
        f"An ONNX model was dynamically quantized to weight type {weight_type_choice}.\n"
        f"Real measured sizes (do not recompute or contradict): {size_df.to_dict(orient='records')}\n"
        f"Top operator types in the graph (real, from parsing the model): {op_df.to_dict(orient='records')}\n\n"
        "In 3-4 sentences for a hackathon demo audience: state the real size reduction, explain "
        "that dynamic quantization mainly shrinks weight-heavy ops (MatMul/Gemm/Conv), and note "
        "that accuracy should be validated separately since this process doesn't measure it. "
        "Do not invent any number not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Upload-and-report UI (not a chatbot) ---
def run_quantize(file_obj, weight_type_choice):
    if file_obj is None:
        return None, None, "Upload an .onnx file first.", None
    size_df, op_df, output_path, error = quantize_model(file_obj, weight_type_choice)
    if error:
        return None, None, error, None
    explanation = explain(size_df, op_df, weight_type_choice)
    reduction = size_df.attrs.get("reduction_pct", 0)
    headline = f"**Real measured reduction: {reduction}%** ({size_df.iloc[0]['size_mb']}MB -> {size_df.iloc[1]['size_mb']}MB)"
    return size_df, op_df, f"{headline}\n\n{explanation}", output_path


with gr.Blocks(title="Edge AI Compression Advisor") as demo:
    gr.Markdown(
        "# Edge AI Compression Advisor\n"
        "Upload a real ONNX model, pick a quantization type, click Quantize. This actually runs "
        "ONNX Runtime's dynamic quantization on your file -- the size reduction shown is measured, "
        "not estimated. Download the quantized model when it's done."
    )
    with gr.Row():
        file_input = gr.File(label="Upload ONNX model (.onnx)", file_types=[".onnx"], type="filepath")
        weight_type_input = gr.Dropdown(
            choices=["INT8 (QInt8) -- signed, typical default", "UINT8 (QUInt8) -- unsigned"],
            value="INT8 (QInt8) -- signed, typical default",
            label="Quantization weight type",
        )
        quantize_btn = gr.Button("Quantize", variant="primary")

    with gr.Row():
        with gr.Column(scale=1):
            size_chart = gr.BarPlot(x="stage", y="size_mb", title="Model size: before vs after (MB)", height=280)
        with gr.Column(scale=1):
            op_table = gr.Dataframe(label="Top operator types in the graph (real, parsed from the model)")

    result_panel = gr.Markdown(label="Result")
    download_file = gr.File(label="Download quantized model")

    quantize_btn.click(
        fn=run_quantize,
        inputs=[file_input, weight_type_input],
        outputs=[size_chart, op_table, result_panel, download_file],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7862)
