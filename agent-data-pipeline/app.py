import os
import wave
import gradio as gr
from PIL import Image
from google import genai

# --- 1. Real computation: inspect the actual uploaded file's real properties ---
def inspect_image(file_path: str) -> dict:
    with Image.open(file_path) as img:
        width, height = img.size
        channels = {"L": 1, "RGB": 3, "RGBA": 4, "CMYK": 4, "1": 1}.get(img.mode, None)
        return {"width": width, "height": height, "channels": channels, "mode": img.mode}


def inspect_audio(file_path: str) -> dict:
    with wave.open(file_path, "rb") as w:
        sample_rate = w.getframerate()
        channels = w.getnchannels()
        n_frames = w.getnframes()
        duration_sec = round(n_frames / sample_rate, 3) if sample_rate else None
        sample_width_bits = w.getsampwidth() * 8
        return {
            "sample_rate": sample_rate, "channels": channels,
            "duration_sec": duration_sec, "bit_depth": sample_width_bits,
        }


def check_image_compatibility(actual: dict, expected_w, expected_h, expected_c) -> list:
    issues = []
    if actual["width"] != expected_w or actual["height"] != expected_h:
        issues.append(
            f"Resolution mismatch: file is {actual['width']}x{actual['height']}, model expects "
            f"{expected_w}x{expected_h}. Resize (with cropping or padding, matching how the "
            f"model was trained) before inference."
        )
    if actual["channels"] != expected_c:
        issues.append(
            f"Channel mismatch: file has {actual['channels']} channel(s) ({actual['mode']}), "
            f"model expects {expected_c}. Convert color mode before inference "
            f"(e.g. RGB<->grayscale)."
        )
    return issues


def check_audio_compatibility(actual: dict, expected_sr, expected_ch, expected_dur) -> list:
    issues = []
    if actual["sample_rate"] != expected_sr:
        issues.append(
            f"Sample rate mismatch: file is {actual['sample_rate']}Hz, model expects "
            f"{expected_sr}Hz. Resample before inference -- feeding audio at the wrong sample "
            f"rate silently corrupts the pitch/timing the model was trained on."
        )
    if actual["channels"] != expected_ch:
        issues.append(
            f"Channel mismatch: file has {actual['channels']} channel(s), model expects "
            f"{expected_ch}. Downmix (stereo->mono) or upmix as needed."
        )
    if expected_dur and actual["duration_sec"] and abs(actual["duration_sec"] - expected_dur) > 0.05:
        issues.append(
            f"Duration mismatch: file is {actual['duration_sec']}s, model expects a fixed "
            f"{expected_dur}s window. Trim or pad (with silence) to the expected length."
        )
    return issues


# --- 2. Gemini client -- used only to summarize the real findings above ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7866:7866 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(actual: dict, issues: list, media_type: str) -> str:
    prompt = (
        f"Media type: {media_type}\n"
        f"Real measured properties of the uploaded file (do not recompute or contradict): {actual}\n"
        f"Real mismatches found against the expected model input (already computed, list is "
        f"authoritative): {issues if issues else 'none -- fully compatible'}\n\n"
        "In 3-4 sentences for a hackathon demo audience, summarize whether this file is ready "
        "for inference as-is, and if not, state the concrete preprocessing steps needed in the "
        "right order. Do not invent any measurement or issue not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Upload-and-report UI (not a chatbot) ---
def run_check(file_obj, media_type, exp_w, exp_h, exp_c, exp_sr, exp_ch, exp_dur):
    if file_obj is None:
        return "Upload a sample file first.", ""

    try:
        if media_type == "image":
            actual = inspect_image(file_obj)
            issues = check_image_compatibility(actual, int(exp_w), int(exp_h), int(exp_c))
        else:
            actual = inspect_audio(file_obj)
            issues = check_audio_compatibility(actual, int(exp_sr), int(exp_ch), float(exp_dur))
    except Exception as e:
        return f"Could not read this file as {media_type}: {e}", ""

    status = "✅ Compatible — no preprocessing required" if not issues else f"⚠️ {len(issues)} mismatch(es) found"
    detail_lines = "\n".join(f"- {i}" for i in issues) if issues else ""
    measured = "\n".join(f"- **{k}**: {v}" for k, v in actual.items())
    result_panel = f"**{status}**\n\n**Measured (real, from the file):**\n{measured}\n\n**Required preprocessing:**\n{detail_lines or '- none'}"

    explanation = explain(actual, issues, media_type)
    return result_panel, explanation


def toggle_fields(media_type):
    is_image = media_type == "image"
    return (
        gr.update(visible=is_image), gr.update(visible=is_image), gr.update(visible=is_image),
        gr.update(visible=not is_image), gr.update(visible=not is_image), gr.update(visible=not is_image),
    )


theme = gr.themes.Soft(primary_hue="rose", secondary_hue="pink", neutral_hue="slate")

with gr.Blocks(title="Edge AI Data Pipeline Advisor") as demo:
    gr.Markdown(
        "# \U0001f3a4 Edge AI Data Pipeline Advisor\n"
        "Upload a real sample image or audio file, enter what your model expects, click Check. "
        "The file's real properties are measured directly, not guessed."
    )
    with gr.Row():
        file_input = gr.File(label="Upload sample file (image or .wav audio)", type="filepath")
        media_type_input = gr.Radio(["image", "audio"], value="image", label="Media type")
        check_btn = gr.Button("Check Compatibility", variant="primary")

    with gr.Row():
        exp_w = gr.Number(value=224, label="Expected width (px)", visible=True)
        exp_h = gr.Number(value=224, label="Expected height (px)", visible=True)
        exp_c = gr.Number(value=3, label="Expected channels", visible=True)
        exp_sr = gr.Number(value=16000, label="Expected sample rate (Hz)", visible=False)
        exp_ch = gr.Number(value=1, label="Expected audio channels", visible=False)
        exp_dur = gr.Number(value=1.0, label="Expected duration (sec)", visible=False)

    media_type_input.change(
        fn=toggle_fields, inputs=media_type_input,
        outputs=[exp_w, exp_h, exp_c, exp_sr, exp_ch, exp_dur],
    )

    result_panel = gr.Markdown(label="Result")
    explanation_panel = gr.Markdown(label="Summary")

    check_btn.click(
        fn=run_check,
        inputs=[file_input, media_type_input, exp_w, exp_h, exp_c, exp_sr, exp_ch, exp_dur],
        outputs=[result_panel, explanation_panel],
    )

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7866, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7866)
