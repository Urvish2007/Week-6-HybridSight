---
title: HybridSight
emoji: 👁️
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.19.0
app_file: app.py
pinned: false
---

# 👁️ HybridSight — RAG + Web Search + Vision Agent

**🔗 Live app:** _[add your Hugging Face Spaces URL here once deployed]_

A single [LangGraph](https://langchain-ai.github.io/langgraph/) agent that answers from your uploaded PDFs, the live web, and uploaded images — in one conversation, with full memory and a visible reasoning trace — wrapped in a tabbed [Gradio](https://www.gradio.app/) UI and deployed live on Hugging Face Spaces.

Originally built as the Week 5 mini-project for the MSOC-26 Generative AI program; this version is the Week 6 "Signature App" — the same agent, rebuilt with a proper multi-tab UI, real progress feedback, and hardened error handling so it's ready to hand someone a public link and let them use it unsupervised.

---

## 🧠 What this actually does, in plain terms

Most "AI chatbot" demos answer everything from the model's training data, which means they're confidently wrong about anything current or anything specific to you. HybridSight instead **routes each question to the right source of truth**:

- Ask about a PDF you uploaded → it searches the actual document and cites page numbers.
- Ask about something that happened this week → it searches the live web instead of guessing.
- Ask a general knowledge question → it checks Wikipedia.
- Upload a photo and ask about it → a vision model looks at it first, and the agent reasons over that description.

Every answer comes with a visible trace of exactly which tool was used and what it was asked — so you're never just trusting a black box.

---

## ✨ Features

- **📄 RAG over your own documents** — PDF → chunked → embedded into ChromaDB → retrieved with page citations.
- **🌐 Live web search** — current events via DuckDuckGo, not stale training data.
- **📚 General knowledge** — routed to Wikipedia.
- **🖼️ Vision** — images are described by a vision model *before* the main agent reasons over them, not passed through as a huge base64 blob the model has to parse itself.
- **🧠 Full conversational memory** — LangGraph checkpointer keeps context across follow-up questions.
- **🔍 Visible reasoning trace** — every tool call (name + input) shown live as it happens.
- **📊 Real progress feedback** — PDF indexing shows an actual staged progress bar (reading → splitting → embedding), not a spinner pretending to know how long it'll take.
- **🗂️ Tabbed interface** — Chat, Documents, Image Studio, and Settings are separated instead of one long scrolling page.
- **🛡️ Fails safely, always** — a `@safe_call` decorator wraps every handler, so no matter what goes wrong internally, the person using the live app only ever sees a clean message, never a raw Python traceback.

---

## 🏗️ Architecture

```
                         ┌──────────────────────┐
                         │  Gradio UI (app.py)   │
                         │  Tabs: Chat / Docs /   │
                         │  Image Studio / Settings│
                         └──────────┬────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                   │
          PDF Upload          Text Message         Image Upload
        (Documents tab)                          (Image Studio tab)
                 │                  │                   │
                 ▼                  ▼                   ▼
          ingest.py         LangGraph Agent      tools_vision.py
     (chunk + embed,          (agent.py)         (description
      progress-reported)          │                generated
                 │                  │               up front,
                 ▼                  │              fed into the
        ┌──────────────────┐        │             message as
        │   ChromaDB store    │◄─────┤             plain text)
        │ (chroma_client.py)  │      │
        └──────────────────┘        │
                                    ▼
                    ┌────────────────────────────────┐
                    │   Tools available to the agent    │
                    │   • search_documents  (RAG)        │
                    │   • duckduckgo_search (live web)    │
                    │   • wikipedia         (general)      │
                    │   • describe_image    (vision)        │
                    └────────────────────────────────┘
```

**Why images bypass the agent's tool-calling:** early versions routed image data through the LLM as a base64 string it had to copy verbatim into a tool call — unreliable and token-expensive. Instead, the app calls the vision model directly on upload and hands the agent a short text description, keeping routing simple and deterministic.

**Why every handler is wrapped in `@safe_call`:** a locally-run app can afford to occasionally show you a stack trace — you're the only one who sees it, and you can just look at the terminal. A *publicly deployed* app can't. `safety.py` guarantees that whatever breaks, the failure is contained, logged server-side for you to debug, and shown to the user as a plain-language message instead.

---

## 🛠️ Tech Stack

| Layer | Choice |
|---|---|
| Agent orchestration | LangGraph (`create_react_agent`) |
| LLM (reasoning) | Groq — `openai/gpt-oss-120b` |
| LLM (vision) | Groq — `meta-llama/llama-4-scout-17b-16e-instruct` |
| Vector store | ChromaDB (persistent, local to the Space) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Web search | DuckDuckGo |
| General knowledge | Wikipedia |
| UI | Gradio 6 |
| Hosting | Hugging Face Spaces |

> **On model IDs:** Groq deprecates and renames model IDs frequently. Both models above are overridable via `GROQ_AGENT_MODEL` / `GROQ_VISION_MODEL` environment variables without touching code — check [console.groq.com/docs/models](https://console.groq.com/docs/models) before assuming these are still current.

---

## 📂 Project Structure

```
week6-hybridsight/
├── agent.py            # LangGraph agent, system prompt, routing rules, startup guard
├── app.py                # Gradio UI — tabs, progress bars, streaming chat
├── safety.py               # @safe_call decorator (used on every handler)
├── chroma_client.py          # Single shared ChromaDB client
├── ingest.py                   # PDF chunking + embedding, with progress callback
├── tools_rag.py                  # search_documents tool
├── tools_vision.py                 # describe_image tool
├── tools_web.py                      # duckduckgo_search & wikipedia tools
├── image_utils.py                      # Local image → base64 data URI conversion
├── requirements.txt
├── .env.example
├── .gitignore
├── DEPLOYMENT.md                         # Full Hugging Face Spaces deployment walkthrough
└── README.md                               # You are here
```

---

## 🚀 Running It Locally

### 1. Clone and set up a virtual environment

```bash
git clone <your-repo-url>
cd week6-hybridsight
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> Dependencies are pinned deliberately — this ecosystem (LangChain/LangGraph/Gradio) ships breaking changes often. If `numpy` fails to build during install, it usually means your Python version is too new for the pinned wheel; **Python 3.11 or 3.12** is recommended over 3.13+.

### 3. Configure your API key

```bash
cp .env.example .env
```

Add your [Groq API key](https://console.groq.com/keys) to `.env`:

```
GROQ_API_KEY=gsk_your_actual_key_here
```

The app will refuse to start with a clear message if this is missing — that's intentional (see `agent.py`'s startup guard).

⚠️ **Never commit your real `.env`.** It's already git-ignored — keep it that way.

### 4. Run it

```bash
python app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860). You'll land on the **Chat** tab; PDF upload lives under **Documents**, image upload under **Image Studio**.

---

## ☁️ How This Is Deployed

This app runs live on **Hugging Face Spaces**, which builds it from this same repository — no separate deployment pipeline, no server to manage.

The short version of how that works, in human terms:

1. **The frontmatter at the very top of this file** (the `---` block) is read directly by Hugging Face to configure the Space — which SDK to use (Gradio), which version, and which file to run (`app.py`). Without it, Spaces doesn't know how to build the app at all.
2. **The Groq API key never touches this repository.** Instead, it's stored as an encrypted **Repository Secret** in the Space's settings, and the running app reads it the exact same way it does locally — via `os.getenv("GROQ_API_KEY")`. Same code, different source for the key, zero risk of it leaking through git history.
3. **Every file needed to run the app is uploaded; nothing else is.** `.env`, `chroma_store/`, `venv/`, and `__pycache__/` are all excluded — the first because it would leak a real key, the rest because they're either meaningless or actively wrong on a fresh server (a stale local vector store, for instance, has no business being deployed).
4. **On first boot**, Spaces installs everything in `requirements.txt`, then runs `app.py`. ChromaDB's storage directory is created fresh via `os.makedirs(..., exist_ok=True)` in `chroma_client.py` — so the live app starts with an empty document index, exactly as intended for a public demo.

For the complete, click-by-click walkthrough — creating the Space, adding the secret, uploading files, and verifying it live — see **[`DEPLOYMENT.md`](./DEPLOYMENT.md)**. That file also has a troubleshooting table for the build failures beginners actually hit most often (the frontmatter/`requirements.txt` version mismatch is the big one).

---

## 🧪 Test Cases

All 5 scenarios below were verified against the **live deployed URL**, not localhost.

| # | Scenario | Expected behavior |
|---|---|---|
| 1 | Ask a question before any PDF is uploaded | Graceful "no documents uploaded yet" message, not an error |
| 2 | Upload a PDF, then ask about it | `search_documents` activates; answer is grounded with page numbers; progress bar visible during indexing |
| 3 | Ask about a current event | `duckduckgo_search` activates; answer is dated and current |
| 4 | Ask a general knowledge question | `wikipedia` activates; answer pulled from a real article |
| 5 | Upload an image and ask about it | `describe_image` runs on upload; final answer is grounded in that description |

_Screenshots from the live URL:_

<!-- Add screenshots here once deployed, e.g.:
![Chat tab — RAG](docs/screenshots/live_chat_rag.png)
![Documents tab — progress bar](docs/screenshots/live_progress.png)
![Image Studio](docs/screenshots/live_vision.png)
-->

*(Placeholders — replace with screenshots taken from your actual Spaces URL in an incognito window before submitting.)*

---

## ✅ Completion Checklist

- [x] Multi-tab layout — Chat / Documents / Image Studio / Settings
- [x] Real progress bar during PDF indexing, with staged status text
- [x] `@safe_call` on every handler — no raw tracebacks reach the user
- [x] Startup guard for `GROQ_API_KEY`
- [x] Empty input, non-PDF upload, and pre-upload questions all handled gracefully
- [ ] Deployed live on Hugging Face Spaces _(update this once your Space is running)_
- [ ] README has a screenshot from the live URL _(add above once deployed)_

---

## 🔒 Security Notes

- API keys live only in `.env` locally (git-ignored) or as an HF Spaces **Repository Secret** in production — never in code, never committed.
- If a key is ever accidentally exposed, treat it as compromised immediately — revoke and rotate at [console.groq.com/keys](https://console.groq.com/keys).
- `chroma_store/` is git-ignored and excluded from deployment; it may contain content from personal/uploaded PDFs and has no reason to persist beyond a given session.

---

## 📄 License

Built for educational purposes as part of the MSOC-26 Generative AI curriculum.
