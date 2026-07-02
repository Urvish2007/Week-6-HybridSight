import os
import datetime
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq

from tools_rag import search_documents
from tools_vision import describe_image
from tools_web import duckduckgo_search, wikipedia

load_dotenv()

# ---------------------------------------------------------------------------
# STARTUP GUARD — fail loudly and immediately if the key is missing, instead
# of letting the app boot and only breaking on the first Groq call deep
# inside a chat turn (which produces a confusing error for end users).
# ---------------------------------------------------------------------------
if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError(
        "\n\n"
        "❌ GROQ_API_KEY is not set.\n"
        "   • Local dev:  copy .env.example to .env and paste your key in.\n"
        "   • Hugging Face Spaces:  add it under Settings → Repository secrets\n"
        "     (never commit it in code or in a .env file).\n"
    )

# NOTE: llama-3.3-70b-versatile was deprecated by Groq on 2026-06-17.
# openai/gpt-oss-120b is Groq's current recommended replacement for
# general reasoning + tool-calling. Override via env var if Groq ships
# something newer — check https://console.groq.com/docs/models.
AGENT_MODEL = os.getenv("GROQ_AGENT_MODEL", "openai/gpt-oss-120b")

llm = ChatGroq(model=AGENT_MODEL, temperature=0)

tools = [
    duckduckgo_search,
    wikipedia,
    search_documents,
    describe_image,
]

TODAY = datetime.date.today().isoformat()
SYSTEM_PROMPT = f"""You are HybridSight, an assistant with access to these tools
(call them by these EXACT names — they are case-sensitive):
- search_documents
- duckduckgo_search
- describe_image
- wikipedia

Today's date is {TODAY}.

ROUTING RULES — follow these in order:
1. If the user's message already contains a section starting with
   "[Image description:", a vision model has ALREADY analyzed the
   uploaded image for you. Use that description directly to answer —
   do NOT call describe_image again for it.
2. If the user asks about uploaded documents, "my notes", or "the file",
   use search_documents.
3. If the user asks about current events or recent news, use
   duckduckgo_search — not wikipedia.
4. If the user asks a general knowledge question, use wikipedia.
5. Always state which tool provided each piece of information.
6. If no tool returns useful information, say so honestly — don't guess.
"""

memory = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)

DEFAULT_CONFIG_EXTRA = {"recursion_limit": 12}