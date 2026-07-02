import os
import uuid

import gradio as gr

from agent import agent, DEFAULT_CONFIG_EXTRA, AGENT_MODEL
from ingest import index_pdf
from image_utils import image_to_data_uri
from tools_vision import _describe_image_impl, VISION_MODEL
from safety import safe_call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_filepath(file):
    """gr.File can hand back either a plain path string or an object with
    a .name attribute depending on Gradio version/config. Handle both so
    this doesn't crash on upload."""
    if file is None:
        return None
    if isinstance(file, str):
        return file
    return getattr(file, "name", None)


@safe_call
def handle_pdf_upload(file, progress=gr.Progress()):
    """Indexes the uploaded PDF with a real, staged progress bar."""
    filepath = _resolve_filepath(file)
    if filepath is None:
        return "No file uploaded."

    if not filepath.lower().endswith(".pdf"):
        return "❌ Please upload a PDF file (.pdf). Other formats aren't supported yet."

    progress(0, desc="Starting...")

    def _on_progress(fraction, description):
        progress(fraction, desc=description)

    try:
        n_chunks = index_pdf(filepath, progress_callback=_on_progress)
    except ValueError as e:
        # Expected, readable failure (e.g. scanned/image-only PDF)
        return f"❌ {e}"

    return f"✅ Indexed {n_chunks} chunks into ChromaDB. Ask about it in the Chat tab."


@safe_call
def chat(message, image, history, session_id):
    """Processes user input, handles images, and streams status + the
    agent's response. This is a generator: it yields intermediate
    "thinking..." states so the reasoning trace panel updates live instead
    of freezing until the whole run finishes."""
    original_message = message or ""
    trace_log = []
    history = list(history or [])

    # Show the user's message immediately, before any processing.
    display_message = original_message or "(image uploaded)"
    history_live = history + [{"role": "user", "content": display_message}]
    yield history_live, session_id, "🧠 Thinking..."

    augmented_message = original_message

    if image is not None:
        yield history_live, session_id, "🖼️ Analyzing image..."
        try:
            data_uri = image_to_data_uri(image)
            # Call the vision model directly instead of relying on the
            # agent's LLM to copy a huge base64 string into a tool-call
            # argument. This is faster, cheaper, and can't get corrupted
            # by the model truncating a long token sequence.
            description = _describe_image_impl(data_uri)
            trace_log.append("🛠️ **Tool Activated:** `describe_image`\n   *Input:* (uploaded image)")
            augmented_message = (
                f"{original_message}\n\n[Image description: {description}]"
                if original_message
                else f"[Image description: {description}]\n\nWhat's in this picture?"
            )
        except Exception as e:
            history_live.append({"role": "assistant", "content": f"❌ Image Error: {e}"})
            yield history_live, session_id, "Error processing image."
            return

    if not augmented_message.strip():
        history_live.append({"role": "assistant", "content": "Please type a question or upload an image."})
        yield history_live, session_id, "🧠 No tools were called."
        return

    config = {
        "configurable": {"thread_id": session_id},
        **DEFAULT_CONFIG_EXTRA,
    }

    final_answer = ""

    try:
        for event in agent.stream(
            {"messages": [{"role": "user", "content": augmented_message}]},
            config=config,
            stream_mode="values",
        ):
            last = event["messages"][-1]

            if getattr(last, "tool_calls", None):
                for tc in last.tool_calls:
                    trace_log.append(f"🛠️ **Tool Activated:** `{tc['name']}`\n   *Input:* {tc['args']}")
                yield history_live, session_id, "\n\n".join(trace_log) + "\n\n⏳ Working..."

            elif getattr(last, "type", None) == "ai" and not getattr(last, "tool_calls", None):
                if last.content:
                    final_answer = last.content
    except Exception as e:
        final_answer = f"⚠️ System limit or error encountered: {str(e)}"

    if not final_answer:
        final_answer = "I wasn't able to produce an answer for that — please try rephrasing."

    history_live.append({"role": "assistant", "content": final_answer})
    trace_output = "\n\n".join(trace_log) if trace_log else "🧠 No tools were called. Answered from internal knowledge."

    yield history_live, session_id, trace_output


# ---------------------------------------------------------------------------
# GRADIO UI
# ---------------------------------------------------------------------------

custom_theme = gr.themes.Soft(primary_hue="indigo")

with gr.Blocks(title="HybridSight") as demo:
    session_id = gr.State(value=lambda: str(uuid.uuid4()))

    gr.HTML("""
    <div style="text-align: center; margin-bottom: 10px; padding-top: 10px;">
        <h1 style="font-weight: 800; font-size: 2.5rem; color: #1e1b4b;">👁️ HybridSight</h1>
        <p style="font-size: 1.1rem; color: #4b5563;">RAG + Web + Vision Agent</p>
    </div>
    """)

    with gr.Tabs():

        # ------------------------------------------------------------ CHAT
        with gr.Tab("💬 Chat"):
            with gr.Row():
                with gr.Column(scale=7):
                    chatbot = gr.Chatbot(height=520, label="Conversation")
                    with gr.Row():
                        msg_box = gr.Textbox(placeholder="Ask anything...", show_label=False, scale=5, container=False)
                        submit_btn = gr.Button("Send", variant="primary", scale=1)

                with gr.Column(scale=3):
                    with gr.Accordion("🔍 Agent Reasoning Trace", open=True):
                        trace_box = gr.Markdown(value="*Tools called will appear here...*")

        # ------------------------------------------------------- DOCUMENTS
        with gr.Tab("📄 Documents"):
            gr.Markdown(
                "Upload a PDF to index it into ChromaDB. Once indexed, ask about "
                "it in the **Chat** tab — try *\"What is in my document?\"*"
            )
            pdf_upload = gr.File(label="Upload a PDF", file_types=[".pdf"])
            index_status = gr.Textbox(label="Indexing status", interactive=False)
            pdf_upload.change(handle_pdf_upload, inputs=pdf_upload, outputs=index_status)

        # ---------------------------------------------------- IMAGE STUDIO
        with gr.Tab("🖼️ Image Studio"):
            gr.Markdown(
                "Upload an image here, then switch to the **Chat** tab and ask "
                "a question — e.g. *\"What's in this picture?\"* The image "
                "attached here is sent along with your next chat message."
            )
            image_upload = gr.Image(label="Upload an image", type="filepath")

        # -------------------------------------------------------- SETTINGS
        with gr.Tab("⚙️ Settings"):
            gr.Markdown(f"""
### About this app

**HybridSight** is a single LangGraph agent with four tools: document
search (RAG), live web search, Wikipedia, and vision — all in one
conversation, with full memory and a visible reasoning trace.

### Active configuration

| Setting | Value |
|---|---|
| Reasoning model | `{AGENT_MODEL}` |
| Vision model | `{VISION_MODEL}` |
| Vector store | ChromaDB (`./chroma_store`) |

Both models are overridable via the `GROQ_AGENT_MODEL` and
`GROQ_VISION_MODEL` environment variables without touching code — check
[console.groq.com/docs/models](https://console.groq.com/docs/models) for
current options, since Groq rotates model IDs frequently.

### Links

- [Source code](https://github.com/Urvish2007)
""")

    # WIRING EVENTS
    msg_box.submit(
        chat,
        inputs=[msg_box, image_upload, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box],
    ).then(lambda: "", outputs=msg_box)

    submit_btn.click(
        chat,
        inputs=[msg_box, image_upload, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box],
    ).then(lambda: "", outputs=msg_box)

if __name__ == "__main__":
    print("🚀 Launching HybridSight Agent...")
    demo.launch(theme=custom_theme)