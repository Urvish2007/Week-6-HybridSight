from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chroma_client import client, CHROMA_DIR, COLLECTION_NAME

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

vectorstore = Chroma(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding_function=embedding_model,
    persist_directory=CHROMA_DIR,
)


@tool
def search_documents(query: str) -> str:
    """Search the user's uploaded documents for information relevant to
    the query. Use this when the user asks about content from a PDF they
    uploaded, or references 'the document', 'my notes', or 'the file'.
    Do NOT use this for general knowledge or current events."""
    try:
        count = vectorstore._collection.count()
    except Exception:
        # If the private API changes shape in a future chromadb version,
        # fail safe instead of crashing the whole agent turn.
        count = None

    if count == 0:
        return "No documents uploaded yet. Please ask the user to upload a PDF first."

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    chunks = retriever.invoke(query)

    if not chunks:
        return "No relevant content found in the uploaded documents."

    return "\n\n".join([
        f"[p.{c.metadata.get('page', '?')}] {c.page_content}"
        for c in chunks
    ])