import os
import uuid
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH     = os.getenv("CHROMA_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

client     = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("vini_memory")
embedder   = SentenceTransformer(EMBEDDING_MODEL)


def add_memory(text: str, category: str = "event"):
    vec = embedder.encode(text).tolist()
    collection.add(
        documents=[text],
        embeddings=[vec],
        metadatas=[{"category": category}],
        ids=[str(uuid.uuid4())],
    )


def retrieve(query: str, n: int = 5) -> list[str]:
    count = collection.count()
    if count == 0:
        return []
    vec = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[vec],
        n_results=min(n, count),
    )
    return results["documents"][0] if results["documents"] else []