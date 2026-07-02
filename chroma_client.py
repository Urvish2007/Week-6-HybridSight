"""
Single shared Chroma client for the whole app.

Why this file exists:
Both ingest.py (writes) and tools_rag.py (reads) need to talk to the same
on-disk ChromaDB store at ./chroma_store. If each file independently opens
its own chromadb.PersistentClient / Chroma() pointed at that same path,
you get one of two failures depending on chromadb version:
  - "An instance of Chroma already exists ... with different settings"
  - or the two clients silently don't see each other's writes.

Fix: create exactly ONE client, once, and have everyone import it from here.
"""
import os
import chromadb

CHROMA_DIR = "./chroma_store"
COLLECTION_NAME = "lecture_notes"

os.makedirs(CHROMA_DIR, exist_ok=True)

# One process-wide client. Both ingest.py and tools_rag.py import this.
client = chromadb.PersistentClient(path=CHROMA_DIR)