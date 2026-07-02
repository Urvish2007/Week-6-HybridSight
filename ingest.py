from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chroma_client import client, CHROMA_DIR, COLLECTION_NAME

# One embedding model instance, reused for both indexing and retrieval.
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def index_pdf(filepath: str, progress_callback=None) -> int:
    """Reads a PDF, chunks it, and adds it to the shared ChromaDB collection.

    progress_callback, if given, is called as progress_callback(fraction, description)
    at each stage — lets the UI show a real (not fake) progress bar instead of
    a spinner, since PDF indexing has genuinely distinct, sequential stages.

    Uses the shared PersistentClient (see chroma_client.py) so this stays
    in sync with what tools_rag.py reads from — no duplicate/competing
    client instances on the same directory.
    """
    def _report(fraction: float, description: str):
        if progress_callback:
            progress_callback(fraction, description)

    _report(0.05, "Reading PDF...")
    loader = PyPDFLoader(filepath)
    pages = loader.load()

    if not pages:
        raise ValueError("No extractable text found in this PDF (is it scanned/image-only?).")

    _report(0.35, f"Splitting {len(pages)} page(s) into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
    chunks = splitter.split_documents(pages)

    _report(0.55, "Connecting to vector store...")
    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
        persist_directory=CHROMA_DIR,
    )

    _report(0.7, f"Embedding {len(chunks)} chunk(s)...")
    vectorstore.add_documents(chunks)

    _report(1.0, "Done.")
    return len(chunks)