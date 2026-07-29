import os
import numpy as np
import pandas as pd
import gradio as gr
import onnx
from onnx import shape_inference
from google import genai

# --- 1. Knowledge base: device compute classes, reused pattern from the Device Recommender ---
devices = pd.DataFrame([
    {"device_name": "Arduino Nano 33 BLE Sense",     "compute_class": "MCU"},
    {"device_name": "Generic Cortex-M7 MCU",          "compute_class": "MCU"},
    {"device_name": "ESP32-S3",                       "compute_class": "MCU"},
    {"device_name": "Generic Cortex-M4 MCU",          "compute_class": "MCU"},
    {"device_name": "Raspberry Pi Zero 2 W",          "compute_class": "SBC-CPU"},
    {"device_name": "Raspberry Pi 4",                 "compute_class": "SBC-CPU"},
    {"device_name": "Raspberry Pi 5",                 "compute_class": "SBC-CPU"},
    {"device_name": "Generic Cortex-A72 SBC",         "compute_class": "SBC-CPU"},
    {"device_name": "Coral Dev Board",                "compute_class": "SBC-accel"},
    {"device_name": "BeagleBone AI-64",               "compute_class": "SBC-accel"},
    {"device_name": "NVIDIA Jetson Nano",             "compute_class": "SBC-GPU"},
    {"device_name": "NVIDIA Jetson Orin Nano Super",  "compute_class": "SBC-GPU"},
    {"device_name": "NVIDIA Jetson AGX Orin 32GB",    "compute_class": "SBC-GPU"},
    {"device_name": "Generic mobile SoC w/ NPU",      "compute_class": "Mobile-accel"},
])

# Heuristic effective compute per class -- rough order-of-magnitude assumptions for real-world
# achievable FP32 throughput (not a benchmark, not vendor peak TOPS). Clearly a starting point
# for demo purposes -- validate against real profiling before trusting these for a real decision.
EFFECTIVE_GFLOPS = {
    "MCU": 0.02,
    "SBC-CPU": 4.0,
    "SBC-accel": 20.0,
    "SBC-GPU": 100.0,
    "Mobile-accel": 40.0,
}


# --- 2. Real computation: parse the model, compute real params, estimate real FLOPs ---
def count_params(model) -> int:
    total = 0
    for init in model.graph.initializer:
        total += int(np.prod(init.dims)) if init.dims else 1
    return total


def parse_shape_overrides(text: str) -> dict:
    """Parses 'name=d1,d2,d3;name2=d1,d2' into {name: [d1,d2,d3], ...}. Invalid/malformed
    entries are silently skipped rather than raising, so a typo in one input doesn't block
    the whole estimate."""
    overrides = {}
    if not text or not text.strip():
        return overrides
    for part in text.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, dims_str = part.split("=", 1)
        try:
            dims = [int(x.strip()) for x in dims_str.split(",") if x.strip()]
            if dims:
                overrides[name.strip()] = dims
        except ValueError:
            continue
    return overrides


def resolve_dynamic_dims(model, overrides: dict, default_dim: int = 1):
    """Root-cause fix: ONNX shape inference cannot resolve ANY downstream tensor shape once a
    single dynamic (symbolic) input dimension is present -- e.g. a variable-length audio time
    axis -- which previously zeroed out FLOPs for entire real models like ASR/CTC networks.

    This returns a model copy with every dynamic input dimension replaced by either a
    user-supplied override (for an exact estimate) or a transparent default of 1 (so a real,
    honestly-labeled number is still produced automatically with zero configuration). Every
    substitution is logged so the user can see exactly what was assumed, never silently.
    """
    resolved = onnx.ModelProto()
    resolved.CopyFrom(model)
    log = []
    for inp in resolved.graph.input:
        dims = inp.type.tensor_type.shape.dim
        override_vals = overrides.get(inp.name)
        for i, d in enumerate(dims):
            if d.dim_value <= 0:  # dynamic: either a named dim_param or completely unset
                if override_vals and i < len(override_vals):
                    val = override_vals[i]
                    log.append(f"'{inp.name}' dim {i}: set to {val} (your override)")
                else:
                    val = default_dim
                    log.append(f"'{inp.name}' dim {i}: assumed {val} (no override given -- likely undercounts if this is a sequence/time axis)")
                d.dim_value = val
                d.ClearField("dim_param")
    return resolved, log


def get_shape_map(model):
    """Runs ONNX's own shape inference and returns {tensor_name: [dims]} for every tensor
    whose shape could be statically resolved. This is real shape inference, not a guess."""
    inferred = shape_inference.infer_shapes(model)
    shape_map = {}
    for vi in list(inferred.graph.value_info) + list(inferred.graph.input) + list(inferred.graph.output):
        dims = []
        ok = True
        for d in vi.type.tensor_type.shape.dim:
            if d.dim_value > 0:
                dims.append(d.dim_value)
            else:
                ok = False
                break
        if ok and dims:
            shape_map[vi.name] = dims
    return shape_map


def estimate_flops(model, shape_overrides: dict = None):
    """Estimates FLOPs for Conv/Gemm/MatMul (the operators that dominate compute in almost
    every edge model) using real weight shapes and real inferred output shapes. Ops whose
    shapes couldn't be resolved are listed as unknown rather than silently ignored or guessed.
    Handles Conv of any spatial rank (Conv1d/2d/3d), not just 2D image convolutions -- audio/ASR
    models commonly use Conv1d, which a 4D-only formula would silently miss."""
    resolved_model, dim_log = resolve_dynamic_dims(model, shape_overrides or {})
    shape_map = get_shape_map(resolved_model)
    init_shapes = {init.name: list(init.dims) for init in model.graph.initializer}
    flops_by_op = {}
    unknown_ops = []

    for node in model.graph.node:
        try:
            if node.op_type == "Conv":
                w_shape = init_shapes.get(node.input[1])   # [out_ch, in_ch/groups, *kernel_spatial]
                out_shape = shape_map.get(node.output[0])  # [batch, out_ch, *output_spatial]
                if w_shape and out_shape and len(w_shape) >= 3 and len(out_shape) >= 3:
                    out_ch, in_ch_g = w_shape[0], w_shape[1]
                    kernel_elems = int(np.prod(w_shape[2:]))
                    output_spatial_elems = int(np.prod(out_shape[2:]))
                    flops = 2 * out_ch * in_ch_g * kernel_elems * output_spatial_elems
                    flops_by_op["Conv"] = flops_by_op.get("Conv", 0) + flops
                else:
                    unknown_ops.append(node.name or "Conv")
            elif node.op_type in ("Gemm", "MatMul"):
                w_shape = init_shapes.get(node.input[1])
                out_shape = shape_map.get(node.output[0])
                if w_shape and out_shape:
                    k = w_shape[-1] if node.op_type == "MatMul" else w_shape[-1]
                    out_elems = int(np.prod(out_shape))
                    flops = 2 * out_elems * k
                    flops_by_op[node.op_type] = flops_by_op.get(node.op_type, 0) + flops
                else:
                    unknown_ops.append(node.name or node.op_type)
        except Exception:
            unknown_ops.append(node.name or node.op_type)

    return {
        "total_flops": sum(flops_by_op.values()),
        "by_op": flops_by_op,
        "unknown_ops": unknown_ops,
        "dim_log": dim_log,
    }


def estimate_latency_per_device(total_flops: float) -> pd.DataFrame:
    """Deterministic: latency_ms = FLOPs / (effective GFLOPS for the device's compute class).
    Same FLOPs in -> same latency table out, every time."""
    rows = []
    for _, dev in devices.iterrows():
        gflops = EFFECTIVE_GFLOPS[dev["compute_class"]]
        latency_ms = round((total_flops / (gflops * 1e9)) * 1000, 2) if gflops else None
        rows.append({
            "device_name": dev["device_name"],
            "compute_class": dev["compute_class"],
            "estimated_latency_ms": latency_ms,
        })
    return pd.DataFrame(rows).sort_values("estimated_latency_ms")


# --- 3. Gemini client -- used ONLY to explain the real computed numbers ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7864:7864 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(params: int, flops_info: dict, latency_df: pd.DataFrame) -> str:
    prompt = (
        f"Real computed model stats (do not recompute or contradict): "
        f"{params} parameters, {flops_info['total_flops']:.0f} estimated FLOPs "
        f"(from real op shapes; {len(flops_info['unknown_ops'])} ops had unresolvable shapes "
        f"and were excluded from the FLOPs count).\n"
        f"Real computed latency estimates per device (heuristic effective-GFLOPS model, not a "
        f"benchmark): {latency_df.to_dict(orient='records')}\n\n"
        "In 3-4 sentences for a hackathon demo audience: state the real param/FLOPs numbers, "
        "call out the fastest and slowest device by name, and remind the audience this is a "
        "heuristic estimate, not a measured benchmark -- real profiling on hardware is the next "
        "step. Do not invent any number not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 4. Upload-and-report UI (not a chatbot), its own color theme ---
def run_estimate(file_obj, override_text):
    if file_obj is None:
        return None, "", "Upload an .onnx file first."
    try:
        model = onnx.load(file_obj)
        onnx.checker.check_model(model)
    except Exception as e:
        return None, "", f"Could not load this as a valid ONNX model: {e}"

    overrides = parse_shape_overrides(override_text)
    params = count_params(model)
    flops_info = estimate_flops(model, overrides)
    latency_df = estimate_latency_per_device(flops_info["total_flops"])

    headline = (
        f"**{params:,} parameters** | "
        f"**{flops_info['total_flops']/1e6:.2f} MFLOPs** (estimated from resolvable op shapes)"
    )
    if flops_info["unknown_ops"]:
        headline += f"\n\n*{len(flops_info['unknown_ops'])} ops excluded from the FLOPs estimate (shape could not be statically resolved even after dynamic-dim resolution).*"
    if flops_info["dim_log"]:
        assumed = [l for l in flops_info["dim_log"] if "assumed" in l]
        overridden = [l for l in flops_info["dim_log"] if "your override" in l]
        if overridden:
            headline += "\n\n**Applied your shape overrides:**\n" + "\n".join(f"- {l}" for l in overridden)
        if assumed:
            headline += (
                "\n\n**⚠️ Dynamic dimensions found and defaulted to 1** (may badly undercount "
                "FLOPs if any of these are a real sequence/time axis -- e.g. audio or text "
                "length). Use the override field above to set the real value for an accurate "
                "estimate:\n" + "\n".join(f"- {l}" for l in assumed)
            )

    explanation = explain(params, flops_info, latency_df)
    return latency_df, headline, explanation


theme = gr.themes.Soft(primary_hue="cyan", secondary_hue="teal", neutral_hue="slate")

with gr.Blocks(title="Edge AI Performance Estimator") as demo:
    gr.Markdown(
        "# \u26a1 Edge AI Performance Estimator\n"
        "Upload a real ONNX model, click Estimate. Parameters are counted exactly from the "
        "model's real weights; FLOPs are computed from real operator shapes via ONNX's own "
        "shape inference -- then a heuristic per-device-class compute figure turns that into an "
        "estimated latency across every device in the suite's dataset."
    )
    with gr.Row():
        file_input = gr.File(label="Upload ONNX model (.onnx)", file_types=[".onnx"], type="filepath")
        estimate_btn = gr.Button("Estimate Performance", variant="primary")

    override_input = gr.Textbox(
        label="Dynamic dimension override (optional, e.g. for audio/sequence models)",
        placeholder="audio_signal=1,64,1280",
        info="If your model has a dynamic axis (e.g. audio time steps, text length), name it "
             "here with its real shape for an accurate FLOPs estimate. Leave blank and dynamic "
             "dims default to 1, which will undercount sequence models -- the result will say "
             "so explicitly either way.",
    )

    headline_panel = gr.Markdown(label="Model stats")
    latency_chart = gr.BarPlot(
        x="device_name", y="estimated_latency_ms", color="compute_class",
        title="Estimated latency by device (ms, lower is better)", height=420, x_label_angle=-45,
    )
    explanation_panel = gr.Markdown(label="Summary")

    estimate_btn.click(
        fn=run_estimate,
        inputs=[file_input, override_input],
        outputs=[latency_chart, headline_panel, explanation_panel],
    )

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7864, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7864)
