"""
RAG Engine
Embeds table schema descriptions into ChromaDB.
At query time, retrieves the most relevant table schemas
to inject into the SQL-generation prompt.
"""

from __future__ import annotations
import os
import json
import hashlib
import chromadb
from chromadb.utils import embedding_functions

from backend.schema_registry import SCHEMA_REGISTRY, get_schema_text

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CHROMA_PATH   = os.getenv("CHROMA_PATH", "./chroma_store")
COLLECTION    = "analytiq_schemas"
OPENAI_KEY    = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# We default to OpenAI embeddings; fall back to Chroma's built-in
# sentence-transformers model when no key is present (local, no API cost).
def _get_embedding_function():
    if OPENAI_KEY:
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_KEY,
            model_name="text-embedding-3-small",
        )
    # Local fallback — uses all-MiniLM-L6-v2 via sentence-transformers
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


class RAGEngine:
    """
    Manages the ChromaDB vector store for AnalytIQ schema retrieval.

    Usage:
        rag = RAGEngine()
        rag.build()           # Only needed once (or when schemas change)
        context = rag.retrieve("Which outlets had overstock last week?")
    """

    def __init__(self):
        self._client   = chromadb.PersistentClient(path=CHROMA_PATH)
        self._ef       = _get_embedding_function()
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ── BUILD ──────────────────────────────────────────────────────────────────
    def build(self, force: bool = False) -> None:
        """
        Embed all schema descriptions into ChromaDB.
        Each table gets one document per semantic chunk:
          - Full schema description
          - Each sample question independently
        Skips rebuild if collection already has documents (unless force=True).
        """
        existing = self._collection.count()
        if existing > 0 and not force:
            print(f"  Vector store already has {existing} docs. Skipping rebuild.")
            return

        print("  Building vector store …")
        docs, ids, metas = [], [], []

        for table, schema in SCHEMA_REGISTRY.items():
            # Full schema text as one document
            full_text = get_schema_text(table)
            doc_id    = f"{table}__full"
            docs.append(full_text)
            ids.append(doc_id)
            metas.append({"table": table, "chunk": "full_schema"})

            # Each sample question as its own document (boosts recall)
            for i, q in enumerate(schema.get("sample_questions", [])):
                docs.append(f"Table: {table}\nQuestion: {q}\n{schema['description'][:300]}")
                ids.append(f"{table}__q{i}")
                metas.append({"table": table, "chunk": f"sample_q_{i}"})

        # Upsert (safe to re-run)
        self._collection.upsert(documents=docs, ids=ids, metadatas=metas)
        print(f"  ✓ Vector store built: {len(docs)} documents across {len(SCHEMA_REGISTRY)} tables")

    # ── RETRIEVE ───────────────────────────────────────────────────────────────
    def retrieve(self, query: str, top_k: int = 4) -> str:
        """
        Given a natural-language query, return the most relevant
        table schema descriptions as a formatted string.
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # De-duplicate: keep one entry per table (the best-scoring one)
        seen_tables = set()
        context_blocks = []

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            table = meta["table"]
            if table not in seen_tables:
                seen_tables.add(table)
                context_blocks.append(
                    f"[Relevance: {1 - dist:.2f}]\n{get_schema_text(table)}"
                )

        return "\n\n---\n\n".join(context_blocks)

    # ── STATS ──────────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        return {
            "total_documents": self._collection.count(),
            "tables_indexed":  list(SCHEMA_REGISTRY.keys()),
            "store_path":      CHROMA_PATH,
        }


# ── Singleton accessor ─────────────────────────────────────────────────────────
_rag_instance: RAGEngine | None = None

def get_rag_engine() -> RAGEngine:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
        _rag_instance.build()
    return _rag_instance
