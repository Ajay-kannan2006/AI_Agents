import os
import zipfile
import tempfile
import gradio as gr
from google import genai

# --- 1. Real computation: deterministic template generation, not LLM invention ---
FRAMEWORK_TEMPLATES = {
    "onnxruntime": {
        "base_image": "python:3.11-slim",
        "extra_requirements": ["onnxruntime"],
        "notes": "CPU-only ONNX Runtime. For GPU acceleration, use `onnxruntime-gpu` with a CUDA base image instead.",
        "run_py": '''import onnxruntime as ort
import numpy as np

MODEL_PATH = "{model_filename}"

session = ort.InferenceSession(MODEL_PATH)
input_meta = session.get_inputs()[0]
print(f"Loaded {{MODEL_PATH}} -- input '{{input_meta.name}}', shape {{input_meta.shape}}")

# TODO: replace with real preprocessed input matching input_meta.shape
dummy_input = np.zeros([d if isinstance(d, int) else 1 for d in input_meta.shape], dtype=np.float32)
outputs = session.run(None, {{input_meta.name: dummy_input}})
print("Output shapes:", [o.shape for o in outputs])
''',
    },
    "tflite": {
        "base_image": "python:3.11-slim",
        "extra_requirements": ["tflite-runtime"],
        "notes": "tflite-runtime wheel availability is platform-specific -- check current wheels at https://github.com/google-coral/pycoral or the LiteRT docs for your target architecture before relying on this base image as-is.",
        "run_py": '''import tflite_runtime.interpreter as tflite
import numpy as np

MODEL_PATH = "{model_filename}"

interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()[0]
print(f"Loaded {{MODEL_PATH}} -- input '{{input_details['name']}}', shape {{input_details['shape']}}")

# TODO: replace with real preprocessed input matching input_details['shape']
dummy_input = np.zeros(input_details["shape"], dtype=input_details["dtype"])
interpreter.set_tensor(input_details["index"], dummy_input)
interpreter.invoke()
output_details = interpreter.get_output_details()[0]
print("Output shape:", interpreter.get_tensor(output_details["index"]).shape)
''',
    },
    "tensorrt": {
        "base_image": "nvcr.io/nvidia/tensorrt:24.08-py3",
        "extra_requirements": [],
        "notes": "Requires an NVIDIA GPU on the host. Run the container with `docker run --gpus all ...`. Verify this base image tag is still current at https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tensorrt before building.",
        "run_py": '''# TensorRT engines are typically built from an ONNX model via trtexec or the TensorRT Python
# API, then loaded for inference -- this is a minimal skeleton, not a complete pipeline.
import tensorrt as trt

MODEL_PATH = "{model_filename}"
print(f"TensorRT {{trt.__version__}} -- build/load an engine from {{MODEL_PATH}} here.")
print("See: https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html")
''',
    },
    "openvino": {
        "base_image": "openvino/ubuntu22_runtime:2024.4.0",
        "extra_requirements": [],
        "notes": "OpenVINO runtime is already included in this base image. Verify the tag is current at https://hub.docker.com/r/openvino/ubuntu22_runtime/tags before building.",
        "run_py": '''import openvino as ov
import numpy as np

MODEL_PATH = "{model_filename}"

core = ov.Core()
model = core.read_model(MODEL_PATH)
compiled_model = core.compile_model(model, "CPU")
input_layer = compiled_model.input(0)
print(f"Loaded {{MODEL_PATH}} -- input shape {{input_layer.shape}}")

# TODO: replace with real preprocessed input matching input_layer.shape
dummy_input = np.zeros(input_layer.shape, dtype=np.float32)
result = compiled_model([dummy_input])[compiled_model.output(0)]
print("Output shape:", result.shape)
''',
    },
}


def generate_deployment(framework: str, model_filename: str, port: int, device_name: str):
    template = FRAMEWORK_TEMPLATES[framework]

    dockerfile = f"""# Generated for target device: {device_name or 'unspecified'}
# Framework: {framework}
FROM {template['base_image']}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY {model_filename} .
COPY run.py .

EXPOSE {int(port)}

CMD ["python", "run.py"]
"""
    requirements_txt = "\n".join(template["extra_requirements"]) + ("\n" if template["extra_requirements"] else "# no extra pip packages -- runtime is included in the base image\n")
    run_py = template["run_py"].format(model_filename=model_filename)

    return dockerfile, requirements_txt, run_py, template["notes"]


def package_zip(dockerfile: str, requirements_txt: str, run_py: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    with open(os.path.join(tmp_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)
    with open(os.path.join(tmp_dir, "requirements.txt"), "w") as f:
        f.write(requirements_txt)
    with open(os.path.join(tmp_dir, "run.py"), "w") as f:
        f.write(run_py)

    zip_path = os.path.join(tmp_dir, "deployment_package.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(os.path.join(tmp_dir, "Dockerfile"), "Dockerfile")
        zf.write(os.path.join(tmp_dir, "requirements.txt"), "requirements.txt")
        zf.write(os.path.join(tmp_dir, "run.py"), "run.py")
    return zip_path


# --- 2. Gemini client -- used only to explain the real generated files ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7867:7867 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(framework: str, notes: str, device_name: str) -> str:
    prompt = (
        f"A deployment package (Dockerfile, requirements.txt, run.py) was just generated for "
        f"framework '{framework}' targeting device '{device_name or 'unspecified'}'.\n"
        f"Real notes about this template (already written, do not contradict): {notes}\n\n"
        "In 2-3 sentences for a hackathon demo audience, explain what the generated package "
        "does and call out the single most important thing to check or edit before building it "
        "for real (base image tag currency, GPU requirement, or similar, if applicable)."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Form-and-generate UI (not a chatbot) ---
def run_generate(framework, model_filename, port, device_name):
    dockerfile, requirements_txt, run_py, notes = generate_deployment(framework, model_filename, port, device_name)
    zip_path = package_zip(dockerfile, requirements_txt, run_py)
    explanation = explain(framework, notes, device_name)
    return dockerfile, requirements_txt, run_py, zip_path, explanation


DEVICE_CHOICES = [
    "", "Raspberry Pi 4", "Raspberry Pi 5", "Coral Dev Board", "BeagleBone AI-64",
    "NVIDIA Jetson Nano", "NVIDIA Jetson Orin Nano Super", "NVIDIA Jetson AGX Orin 32GB",
    "Generic mobile SoC w/ NPU",
]

theme = gr.themes.Soft(primary_hue="blue", secondary_hue="sky", neutral_hue="slate")

with gr.Blocks(title="Edge AI Deployment Packager") as demo:
    gr.Markdown(
        "# \U0001f4e6 Edge AI Deployment Packager\n"
        "Pick a framework, click Generate. A real Dockerfile, requirements.txt, and inference "
        "run script are generated from templates -- not written by the LLM -- and bundled into "
        "a downloadable zip."
    )
    with gr.Row():
        framework_input = gr.Dropdown(
            choices=list(FRAMEWORK_TEMPLATES.keys()), value="onnxruntime", label="Target framework"
        )
        model_filename_input = gr.Textbox(value="model.onnx", label="Model filename")
        port_input = gr.Number(value=8080, label="Port")
        device_input = gr.Dropdown(choices=DEVICE_CHOICES, value="", label="Target device (optional, for documentation)")
        generate_btn = gr.Button("Generate", variant="primary")

    with gr.Row():
        dockerfile_out = gr.Code(label="Dockerfile", language="dockerfile")
        requirements_out = gr.Code(label="requirements.txt", language="shell")
    run_py_out = gr.Code(label="run.py", language="python")

    download_zip = gr.File(label="Download deployment package (.zip)")
    explanation_panel = gr.Markdown(label="Notes")

    generate_btn.click(
        fn=run_generate,
        inputs=[framework_input, model_filename_input, port_input, device_input],
        outputs=[dockerfile_out, requirements_out, run_py_out, download_zip, explanation_panel],
    )

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7867, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7867)
