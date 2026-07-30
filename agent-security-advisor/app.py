import os
import pandas as pd
import gradio as gr
from google import genai

# --- 1. Real computation: rule-based deterministic scoring, not an LLM judgment call ---
def score_checklist(
    handles_pii, transmits_offdevice, encrypted_in_transit, encrypted_at_rest,
    physical_access_control, model_is_proprietary, model_extraction_protected,
    discards_raw_data, receives_ota_updates, ota_signed, consent_obtained,
):
    score = 100
    items = []

    def deduct(points, reason):
        nonlocal score
        score -= points
        items.append({"finding": reason, "impact": f"-{points}"})

    def ok(reason):
        items.append({"finding": reason, "impact": "0 (compliant)"})

    if transmits_offdevice:
        if not encrypted_in_transit:
            deduct(25, "Data is transmitted off-device without transit encryption (TLS/HTTPS)")
        else:
            ok("Data transmitted off-device with transit encryption")

    if handles_pii:
        if not encrypted_at_rest:
            deduct(20, "Personal data is processed without at-rest encryption")
        else:
            ok("Personal data encrypted at rest")
        if not consent_obtained:
            deduct(15, "Personal data is processed without documented user consent")
        else:
            ok("User consent obtained for personal data processing")
        if not discards_raw_data:
            deduct(15, "Personal data is retained rather than discarded after inference")
        else:
            ok("Raw personal data discarded after inference")

    if not physical_access_control:
        deduct(10, "No physical access controls on the device (locked enclosure, secure boot)")
    else:
        ok("Physical access controls present")

    if model_is_proprietary and not model_extraction_protected:
        deduct(15, "Proprietary model has no protections against extraction")
    elif model_is_proprietary:
        ok("Proprietary model protected against extraction")

    if receives_ota_updates and not ota_signed:
        deduct(20, "OTA updates are not cryptographically signed/verified")
    elif receives_ota_updates:
        ok("OTA updates are signed and verified")

    score = max(0, score)
    if score >= 80:
        risk_level = "Low risk"
    elif score >= 50:
        risk_level = "Moderate risk"
    else:
        risk_level = "High risk"

    return score, risk_level, pd.DataFrame(items) if items else pd.DataFrame([{"finding": "No applicable risk factors triggered by the answers given", "impact": "0"}])


# --- 2. Gemini client -- used only to explain the real computed score ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7869:7869 <image>"
    )
client = genai.Client(api_key=api_key)


def explain(score: int, risk_level: str, items_df: pd.DataFrame) -> str:
    findings = items_df[items_df["impact"].str.startswith("-")]["finding"].tolist()
    prompt = (
        f"Real computed security/privacy score (do not recompute or contradict): {score}/100, "
        f"risk level: {risk_level}.\n"
        f"Real deductions triggered: {findings if findings else 'none'}\n\n"
        "In 3-4 sentences for a hackathon demo audience: state the score and risk level, and if "
        "there are deductions, name the single highest-impact one and recommend fixing it first. "
        "Do not invent any finding not shown above."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Checklist form UI (not a chatbot, not a file upload) ---
def run_assess(*answers):
    score, risk_level, items_df = score_checklist(*answers)
    headline = f"## Score: {score}/100 — {risk_level}"
    explanation = explain(score, risk_level, items_df)
    return headline, items_df, explanation


theme = gr.themes.Soft(primary_hue="red", secondary_hue="orange", neutral_hue="slate")

with gr.Blocks(title="Edge AI Security & Privacy Advisor") as demo:
    gr.Markdown(
        "# \U0001f512 Edge AI Security & Privacy Advisor\n"
        "Answer the checklist below. The score is computed by a fixed set of rules, not an "
        "LLM's impression — the same answers always produce the same score."
    )
    with gr.Row():
        with gr.Column():
            handles_pii = gr.Checkbox(label="Processes or stores personal data (images/audio of people, biometric data)")
            transmits_offdevice = gr.Checkbox(label="Transmits data off-device to a cloud/server")
            encrypted_in_transit = gr.Checkbox(label="Data is encrypted in transit (TLS/HTTPS) -- if transmitting")
            encrypted_at_rest = gr.Checkbox(label="Data is encrypted at rest on the device -- if handling personal data")
            consent_obtained = gr.Checkbox(label="User consent obtained before processing personal data -- if applicable")
            discards_raw_data = gr.Checkbox(label="Raw sensor data is discarded immediately after inference", value=True)
        with gr.Column():
            physical_access_control = gr.Checkbox(label="Device has physical access controls (locked enclosure, secure boot)")
            model_is_proprietary = gr.Checkbox(label="Model is considered proprietary IP")
            model_extraction_protected = gr.Checkbox(label="Protections exist against model extraction -- if model is proprietary")
            receives_ota_updates = gr.Checkbox(label="Device receives OTA firmware/model updates")
            ota_signed = gr.Checkbox(label="OTA updates are cryptographically signed/verified -- if applicable")

    assess_btn = gr.Button("Assess Risk", variant="primary")

    score_panel = gr.Markdown(label="Score")
    findings_table = gr.Dataframe(label="Findings (real, computed from your answers)")
    explanation_panel = gr.Markdown(label="Summary")

    inputs = [
        handles_pii, transmits_offdevice, encrypted_in_transit, encrypted_at_rest,
        physical_access_control, model_is_proprietary, model_extraction_protected,
        discards_raw_data, receives_ota_updates, ota_signed, consent_obtained,
    ]
    assess_btn.click(fn=run_assess, inputs=inputs, outputs=[score_panel, findings_table, explanation_panel])

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7869, theme=theme)
    except TypeError:
        demo.launch(server_name="0.0.0.0", server_port=7869)
