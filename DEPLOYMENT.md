# 🚀 Deploying HybridSight to Hugging Face Spaces
### A microscopic, zero-assumptions guide — from local VS Code to a live public URL

You've already done the hard part: HybridSight works locally. Everything from here is mechanical — follow every step in order, don't skip the checklists, and you'll have a live URL within 20-30 minutes.

> **Read this before touching anything:** the single most common way people leak API keys is by uploading their `.env` file "just this once, I'll delete it later." Section 1 and Section 5 exist to make sure that never happens to you.

---

## 1. 🚫 Files You Must NEVER Upload

**These files must not exist anywhere in what you upload to Hugging Face — not even briefly.**

| File / Folder | Why it must never be uploaded |
|---|---|
| `.env` | Contains your **real, live** Groq API key in plaintext. If this reaches a public repo, treat the key as compromised the moment it's visible — even for one commit. |
| `__pycache__/` | Compiled Python bytecode. Useless on the server, can cause stale-import bugs, bloats upload size. |
| `venv/` or `.venv/` | Your entire local virtual environment (hundreds of MB). Spaces builds its own from `requirements.txt` — this is never needed. |
| `chroma_store/` | Your local vector database. It may contain content from PDFs you tested with (potentially personal), and Spaces will rebuild it fresh from user uploads anyway. |
| `.git/` (if visible) | Only relevant if you're doing something unusual with drag-and-drop; normally hidden, just don't manually grab it. |
| `.vscode/`, `.idea/` | Editor config, irrelevant to the running app, unnecessary noise. |

**🛑 STOP AND CHECK:** Before you upload anything, run this in your project folder to see exactly what's in your `.gitignore` (it should already block all of the above from Week 5):

```powershell
cat .gitignore
```

You should see `.env`, `chroma_store/`, `__pycache__/`, and `venv/` listed. If any are missing, add them now, before proceeding.

---

## 2. ✅ Files You MUST Upload

This is the complete, minimal set HybridSight needs to run on Spaces:

```
week6-hybridsight/
├── agent.py              ← LangGraph agent + system prompt + startup guard
├── app.py                 ← Gradio UI (tabs, progress bars, chat)
├── chroma_client.py        ← Shared ChromaDB client
├── ingest.py                ← PDF indexing with progress reporting
├── tools_rag.py              ← search_documents tool
├── tools_vision.py            ← describe_image tool
├── tools_web.py                 ← duckduckgo_search & wikipedia tools
├── image_utils.py                ← image → base64 data URI helper
├── safety.py                       ← @safe_call decorator
├── requirements.txt                 ← exact pinned dependencies (Section 3)
├── README.md                         ← MUST include the special frontmatter (Section 6)
└── .gitignore                          ← optional but good practice
```

**Do NOT upload `.env`.** Instead, `.env.example` (placeholders only) is fine to include if you want — it documents what variables exist without exposing anything.

---

## 3. 📦 The Exact `requirements.txt`

Use this exactly — every version here was actually installed together in a clean environment and verified to work (not just guessed from memory). Do not remove the version pins; unpinned installs are the #1 cause of "it worked locally but broke on Spaces."

```
langchain==1.3.11
langchain-community==0.4.2
langchain-groq==1.1.3
langchain-chroma==1.1.0
langchain-huggingface==1.2.2
langchain-text-splitters==1.1.2
langgraph==1.2.7
chromadb==1.5.9
sentence-transformers==5.6.0
ddgs==9.14.4
wikipedia==1.4.0
gradio==6.19.0
python-dotenv==1.2.2
groq==0.37.1
pypdf==6.14.2
```

**Note on `ddgs`:** LangChain's DuckDuckGo tool now depends on a package called `ddgs` (renamed from `duckduckgo-search`). If you ever see `ModuleNotFoundError: No module named 'ddgs'`, this is why — make sure it's in your `requirements.txt`, not the old package name.

**⚠️ CRITICAL:** the `gradio` version here (`6.19.0`) must **exactly match** the `sdk_version` you put in your README.md frontmatter in Section 6. A mismatch is a common cause of Spaces builds failing silently or behaving unexpectedly.

---

## 4. 🔧 Code Refinements Already Applied

Before deploying, your `app.py` should have three production-readiness upgrades. If you're using the files provided alongside this guide, all three are already in place — here's what they do and why they matter for a *deployed*, public app specifically (not just local dev):

### a) Multi-tab layout

```python
with gr.Tabs():
    with gr.Tab("💬 Chat"):
        ...
    with gr.Tab("📄 Documents"):
        ...
    with gr.Tab("🖼️ Image Studio"):
        ...
    with gr.Tab("⚙️ Settings"):
        ...
```

A single long scrolling page reads as a prototype. Tabs read as a product — this matters when this URL is the first thing a recruiter or hackathon judge sees.

### b) Real progress bars during indexing

```python
@safe_call
def handle_pdf_upload(file, progress=gr.Progress()):
    ...
    def _on_progress(fraction, description):
        progress(fraction, desc=description)
    n_chunks = index_pdf(filepath, progress_callback=_on_progress)
```

`ingest.py` now reports its actual stages (reading → splitting → embedding) instead of the UI just freezing until the whole thing finishes. On a public Space, PDF embedding can take longer than on your local machine — a progress bar is the difference between a user waiting patiently and a user assuming the app is broken and leaving.

### c) The `@safe_call` decorator on every handler

```python
# safety.py
def safe_call(func):
    ...
    except Exception as e:
        traceback.print_exc()          # full detail — server logs only
        raise gr.Error(f"Something went wrong: {e}")
```

Applied to `chat` and `handle_pdf_upload`. This is your **last line of defense**: even if something unexpected slips past your specific try/except blocks, the user sees a clean toast message — never a raw Python traceback. On a public URL, a stack trace isn't just ugly, it can leak internal file paths and implementation details you don't want strangers seeing.

**Test all three before deploying — do this now, locally:**

```powershell
python app.py
```

1. Click **Send** with an empty textbox → should NOT crash.
2. Upload a `.txt` file to the PDF uploader → should show a friendly error, not a traceback.
3. Ask a document question before uploading any PDF → should get the graceful "no documents" message.
4. Upload a real PDF → watch the progress bar actually move through stages.

If any of these produce a raw error in your terminal (not just the UI), fix it before moving to deployment — Spaces will expose that same bug to the public.

---

## 5. 🔐 API Key Security — The Idiot-Proof Version

**Read this section twice. This is the part where a mistake actually costs you something.**

Your Groq API key must **only** ever live in one place when deployed: **Hugging Face's Repository Secrets**, which are encrypted and never shown in your code, your files, or your public repo.

### Step-by-step:

1. Go to your Space's page on huggingface.co (you'll create this in Section 6).
2. Click the **⚙️ Settings** tab at the top of your Space.
3. Scroll to **Variables and secrets**.
4. Click **New secret**.
5. In the **Name** field, type exactly: `GROQ_API_KEY`
   - **⚠️ It must match this exact spelling and capitalization** — your code reads `os.getenv("GROQ_API_KEY")`, and this is case-sensitive.
6. In the **Value** field, paste your real Groq API key.
7. Click **Save**.

That's it. Your running app on Spaces will automatically see this as an environment variable — no `.env` file needed on the server at all. This is *exactly* why your code uses `os.getenv("GROQ_API_KEY")` rather than hardcoding anything: the same code works identically whether the key comes from a local `.env` file (dev) or an HF secret (production).

### 🛑 Final verification, non-negotiable:

Before you consider deployment "done," run this locally in your project folder:

```powershell
git log -p | Select-String "GROQ_API_KEY"
```

*(If you're not using git for this project and are uploading via drag-and-drop instead, just open every file you're about to upload and visually confirm none of them contain `gsk_...`.)*

If this returns anything containing an actual key value (starting with `gsk_`) rather than just the variable name being referenced in code, **stop, do not deploy, and rotate that key immediately** at [console.groq.com/keys](https://console.groq.com/keys) before proceeding.

---

## 6. 🖱️ Every Click, In Order

### Step 1 — Create your Hugging Face account (skip if you have one)

Go to [huggingface.co/join](https://huggingface.co/join), sign up, and verify your email.

### Step 2 — Create a new Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Owner:** your username.
3. **Space name:** e.g. `hybridsight`.
4. **License:** pick anything reasonable (e.g. `mit`) or leave default.
5. **Select the Space SDK:** click **Gradio**.
6. **Space hardware:** leave as **CPU basic · Free**.
7. **Visibility:** **Public** (it needs to be public for your resume/LinkedIn link to work for others).
8. Click **Create Space**.

You'll land on your new (empty) Space's page — it currently shows placeholder instructions.

### Step 3 — Add your secret BEFORE uploading any code

Do this now, not after — so you never have a moment where the app is live without its key configured.

1. Click the **Settings** tab (top of the Space page).
2. Scroll to **Variables and secrets** → **New secret**.
3. Name: `GROQ_API_KEY`, Value: your real key. Click **Save**.

### Step 4 — Prepare your `README.md` with the required frontmatter

Hugging Face Spaces uses the very top of your `README.md` to configure the Space itself — this is not optional, and it's the #1 thing beginners miss. Open your `README.md` and make sure the **very first lines** of the file are exactly this block (before any other content):

```yaml
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
```

**⚠️ `sdk_version` must match the `gradio` version in your `requirements.txt` exactly** (`6.19.0` in Section 3). Your normal descriptive README content (features, screenshots, setup instructions) goes *below* this block — it will render as your Space's page description.

### Step 5 — Upload your files

You have two options — pick whichever you're comfortable with:

**Option A: Drag-and-drop via the web UI (simplest for beginners)**

1. On your Space's page, click the **Files** tab.
2. Click **Add file** → **Upload files**.
3. From your VS Code file explorer / Windows File Explorer, select every file listed in Section 2 (agent.py, app.py, chroma_client.py, ingest.py, tools_rag.py, tools_vision.py, tools_web.py, image_utils.py, safety.py, requirements.txt, README.md).
4. **Double-check the file list in the upload dialog before confirming** — make sure `.env` is NOT in the selection. If you see it, remove it from the selection now.
5. Scroll down, add a short commit message like "Initial deployment," and click **Commit changes to main**.

**Option B: Git push (if you're comfortable with git)**

```powershell
git clone https://huggingface.co/spaces/<your-username>/hybridsight
cd hybridsight
# copy in all files from Section 2 (NOT .env)
git add .
git commit -m "Initial deployment"
git push
```

### Step 6 — Watch it build

1. Go to the **App** tab on your Space.
2. You'll see a **Building** status with a live log — this installs everything in `requirements.txt`, which can take 3-8 minutes the first time (embedding models and `chromadb` are not tiny).
3. If it fails, click **Logs** to read the actual error — 90% of the time it's either a missing package in `requirements.txt` or the `sdk_version` mismatch from Step 4.
4. Once it says **Running**, your app is live.

### Step 7 — Verify it actually works, from a stranger's perspective

1. Copy the URL — it looks like `https://huggingface.co/spaces/<your-username>/hybridsight`.
2. Open it in an **incognito/private browser window** (this rules out any of your own cached local state fooling you).
3. Run through all 5 Week 5 test scenarios again, live:
   - Ask a document question before uploading a PDF → graceful message.
   - Upload a PDF, watch the progress bar, ask about it.
   - Ask a current-events question.
   - Ask a general-knowledge question.
   - Upload an image and ask about it.

If all 5 work in the incognito window, you're done.

---

## ✅ Final Deployment Checklist

Go through this literally, one line at a time, before you call it done:

| Check | How to verify |
|---|---|
| Live URL works | Opened in an incognito window, ran a full query, got a real answer |
| No API key in code | Searched every uploaded file for `gsk_` and found nothing |
| `.env` was never uploaded | Confirmed in the Files tab of your Space — `.env` does not appear |
| `GROQ_API_KEY` is a secret | Settings → Variables and secrets shows it listed (value hidden) |
| Empty input handled | Clicked Send with nothing typed — no crash, no raw traceback |
| Progress bar visible | Uploaded a PDF and watched the bar move through real stages |
| Multi-tab layout present | Chat / Documents / Image Studio / Settings all switchable |
| README has frontmatter | First lines of README.md are the `---` YAML block from Step 4 |
| README has a screenshot | Screenshot is from the **live URL**, not `127.0.0.1` |

---

## 🆘 Troubleshooting Common Build Failures

| Symptom | Likely Cause | Fix |
|---|---|---|
| Space stuck on "Building" for 15+ min | Large dependency install (`chromadb`, `sentence-transformers`) is genuinely slow the first time | Wait it out once; if it never finishes, check Logs for a real error |
| `ModuleNotFoundError` in Logs | A package used in your code is missing from `requirements.txt` | Add it with a specific version, re-commit |
| App builds but crashes immediately on load | `GROQ_API_KEY` secret not set, or typo in the name | Recheck Settings → Variables and secrets — name must be exact |
| Space shows a blank/wrong page instead of your app | `sdk_version` in README frontmatter doesn't match `requirements.txt` gradio version | Make them identical |
| "File not found" errors referencing `chroma_store` | This is expected on first run — the folder is created automatically by `chroma_client.py`'s `os.makedirs(..., exist_ok=True)` | No action needed, it self-heals |

---

You now have a live, public, portfolio-grade GenAI application. Put the URL in your README, your LinkedIn, and your resume — this is the project you demo at the hackathon.
