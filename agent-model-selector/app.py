import os
import pandas as pd
import gradio as gr
from huggingface_hub import HfApi
from google import genai

hf_api = HfApi()


# --- 1. Real computation: live Hugging Face Hub search + deterministic ranking ---
def search_models_for_task(task: str, top_k: int = 8, max_size_mb: float = 0) -> pd.DataFrame:
    """Search the live Hugging Face Hub for real candidate models, ranked by a deterministic
    popularity score. Not an LLM guess -- a live API call plus arithmetic."""
    rows = []
    # Deliberately no sort/direction kwargs here: different huggingface_hub versions have
    # changed/removed these over time (e.g. `direction` was dropped in some releases). We fetch
    # a wider candidate pool unsorted and do the real ranking ourselves in Python below, which
    # works identically regardless of installed SDK version.
    raw_candidates = list(hf_api.list_models(search=task, limit=top_k * 6))
    raw_candidates.sort(key=lambda m: m.downloads or 0, reverse=True)

    for m in raw_candidates:
        size_mb = None
        try:
            info = hf_api.model_info(m.id, files_metadata=True)
            sizes = [s.size for s in (info.siblings or []) if getattr(s, "size", None)]
            if sizes:
                size_mb = round(sum(sizes) / (1024 * 1024), 2)
        except Exception:
            pass

        if max_size_mb and size_mb is not None and size_mb > max_size_mb:
            continue

        downloads = m.downloads or 0
        likes = m.likes or 0
        popularity_score = round(min(100, (downloads ** 0.15) * 8 + (likes ** 0.2) * 3), 1)

        rows.append({
            "model_id": m.id,
            "pipeline_tag": m.pipeline_tag,
            "downloads": downloads,
            "likes": likes,
            "estimated_size_mb": size_mb,
            "popularity_score": popularity_score,
        })
        if len(rows) >= top_k:
            break

    df = pd.DataFrame(rows)
    return df.sort_values("popularity_score", ascending=False) if not df.empty else df


# --- 2. Gemini client -- used ONLY to write the summary, never to pick or score models ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Run the container with: "
        "docker run -e GEMINI_API_KEY=your_key -p 7861:7861 <image>"
    )
client = genai.Client(api_key=api_key)


def summarize(task: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"No models found on the Hugging Face Hub matching **'{task}'** with the given size limit."
    prompt = (
        f"Task searched: {task}\n"
        f"Real ranked candidates from a live Hugging Face Hub search (already ranked, do not "
        f"re-rank or invent new candidates): {df.to_dict(orient='records')}\n\n"
        "In 3-4 sentences for a hackathon demo audience, summarize the top pick and why, "
        "mentioning its real download count and size if available."
    )
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text


# --- 3. Form-and-report UI (not a chatbot) ---
def run_search(task, size_limit):
    df = search_models_for_task(task, top_k=8, max_size_mb=size_limit or 0)
    summary = summarize(task, df)
    return df, df, summary


with gr.Blocks(title="Edge AI Model Selector") as demo:
    gr.Markdown(
        "# Edge AI Model Selector\n"
        "Enter a task, optionally cap the model size, click Search. Results come from a live "
        "query to the Hugging Face Hub -- real download counts, real sizes -- ranked by a "
        "reproducible popularity score. The LLM only summarizes the top result, it never "
        "picks or invents one."
    )
    with gr.Row():
        task_input = gr.Textbox(
            label="Task",
            placeholder="e.g. keyword-spotting, image-classification, object-detection",
            value="keyword-spotting",
        )
        size_slider = gr.Slider(
            label="Max size (MB, 0 = no limit)", minimum=0, maximum=500, value=0, step=5,
        )
        search_btn = gr.Button("Search", variant="primary")

    results_table = gr.Dataframe(label="Ranked candidates (live Hugging Face Hub data)", interactive=False)
    results_chart = gr.BarPlot(
        x="model_id", y="popularity_score", title="Popularity score by model", height=300,
    )
    summary_panel = gr.Markdown(label="Summary")

    search_btn.click(
        fn=run_search,
        inputs=[task_input, size_slider],
        outputs=[results_table, results_chart, summary_panel],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)
