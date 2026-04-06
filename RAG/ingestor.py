# RAG/ingestor.py

import glob
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

from embedder import get_embedder

RAG_DIR = Path(__file__).parent
KNOWLEDGE_DIR = RAG_DIR / "knowledge"
STORE_DIR = RAG_DIR / "store"


def ingest(reset=False):
    print("🚀 Starting ingestion...", flush=True)

    client = chromadb.PersistentClient(path=str(STORE_DIR))

    if reset:
        try:
            client.delete_collection("jarvis_knowledge")
        except Exception:
            # Collection might not exist yet on first run.
            pass
        print("🧹 Old data cleared", flush=True)

    collection = client.get_or_create_collection("jarvis_knowledge")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    embedder = get_embedder()

    docs = []
    ids = []
    embeddings = []
    metadatas = []

    # 🔍 Read all .md files
    files = sorted(glob.glob(str(KNOWLEDGE_DIR / "**/*.md"), recursive=True))

    if not files:
        print("❌ No files found in knowledge/", flush=True)
        return

    for file in files:
        rel_path = Path(file).relative_to(KNOWLEDGE_DIR)
        print(f"📄 Processing: {rel_path.as_posix()}", flush=True)

        with open(file, encoding="utf-8") as f:
            text = f.read()

        chunks = splitter.split_text(text)

        for i, chunk in enumerate(chunks):
            doc_id = f"{Path(file).stem}_{i}"

            docs.append(chunk)
            ids.append(doc_id)
            embeddings.append(embedder.encode(chunk).tolist())
            metadatas.append({"source": rel_path.as_posix()})

    collection.upsert(
        documents=docs,
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"✅ Done! Stored {len(docs)} chunks.", flush=True)


if __name__ == "__main__":
    import sys
    reset_flag = "--reset" in sys.argv
    ingest(reset=reset_flag)