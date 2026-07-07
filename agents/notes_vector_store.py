"""
RAG semantic cache for NAGA-approved study notes.

Storage:   data/chroma_db/  (persistent ChromaDB)
Embeddings: sentence-transformers/all-MiniLM-L6-v2  (local, free, 384-dim)
Collection: study_notes

Lifecycle:
  1. ContentAgent generates notes via LLM  →  saved as pending
  2. NAGA approves in Approvals tab        →  approve_note() calls add()
  3. Next student asks same topic          →  search() returns cached note
     Similarity ≥ THRESHOLD               →  no LLM call needed
     Similarity < THRESHOLD               →  generate fresh, queue for NAGA
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
_COLLECTION  = "study_notes"
THRESHOLD    = 0.80      # cosine similarity; tune upward if too many false hits

# Lazy-loaded singletons — avoid startup cost when vector store isn't used
_client:    "chromadb.PersistentClient | None" = None
_col:       "chromadb.Collection | None"        = None
_embedder:  "SentenceTransformer | None"        = None
_lock = threading.Lock()


def _init() -> tuple["chromadb.Collection", "SentenceTransformer"]:
    global _client, _col, _embedder
    if _col is not None and _embedder is not None:
        return _col, _embedder
    with _lock:
        if _col is not None and _embedder is not None:
            return _col, _embedder

        import chromadb
        from sentence_transformers import SentenceTransformer

        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _col     = _client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("NotesVectorStore: initialised (%d docs in collection)", _col.count())
    return _col, _embedder


def _doc_id(exam: str, topic: str, lang: str) -> str:
    import hashlib
    key = f"{exam}|{topic.lower().strip()}|{lang}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


# ── Public API ─────────────────────────────────────────────────────────────────

def search(
    query: str,
    exam_key: str,
    lang: str = "en",
    n: int = 1,
    threshold: float = THRESHOLD,
) -> Optional[dict]:
    """
    Semantic search for an approved note matching *query*.

    Returns the best match dict {"content", "topic", "subject", "exam", "lang",
    "approved_at", "similarity"} if similarity ≥ threshold, else None.
    """
    try:
        col, embedder = _init()
        if col.count() == 0:
            return None

        vec = embedder.encode([query]).tolist()
        where = {"$and": [{"exam": {"$eq": exam_key}}, {"lang": {"$eq": lang}}]}

        results = col.query(
            query_embeddings=vec,
            n_results=min(n, col.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return None

        # ChromaDB cosine distance: 0 = identical, 1 = orthogonal
        # Similarity = 1 - distance
        distance   = results["distances"][0][0]
        similarity = 1.0 - distance

        if similarity < threshold:
            logger.debug(
                "NotesVectorStore: cache MISS  topic=%r  similarity=%.3f < %.2f",
                query, similarity, threshold,
            )
            return None

        meta    = results["metadatas"][0][0]
        content = results["documents"][0][0]
        logger.info(
            "NotesVectorStore: cache HIT   topic=%r  similarity=%.3f  stored_topic=%r",
            query, similarity, meta.get("topic"),
        )
        return {
            "content":     content,
            "topic":       meta.get("topic", ""),
            "subject":     meta.get("subject", ""),
            "exam":        meta.get("exam", ""),
            "lang":        meta.get("lang", "en"),
            "approved_at": meta.get("approved_at", ""),
            "similarity":  round(similarity, 4),
        }
    except Exception as e:
        logger.error("NotesVectorStore.search error: %s", e)
        return None


def add(
    topic:       str,
    subject:     str,
    exam_key:    str,
    lang:        str,
    content:     str,
    approved_at: str = "",
) -> bool:
    """
    Add or update an approved note in the vector store.
    Uses upsert so re-approving an amended note refreshes the embedding.
    """
    try:
        col, embedder = _init()
        doc_id = _doc_id(exam_key, topic, lang)
        vec    = embedder.encode([content]).tolist()

        from datetime import datetime, timezone
        col.upsert(
            ids       =[doc_id],
            embeddings=vec,
            documents =[content],
            metadatas =[{
                "exam":        exam_key,
                "subject":     subject,
                "topic":       topic,
                "lang":        lang,
                "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
            }],
        )
        logger.info(
            "NotesVectorStore: added  exam=%s  topic=%r  id=%s  total=%d",
            exam_key, topic, doc_id, col.count(),
        )
        return True
    except Exception as e:
        logger.error("NotesVectorStore.add error: %s", e)
        return False


def remove(exam_key: str, topic: str, lang: str = "en") -> bool:
    """Remove a note (e.g. when NAGA deletes an approved note)."""
    try:
        col, _ = _init()
        doc_id = _doc_id(exam_key, topic, lang)
        col.delete(ids=[doc_id])
        logger.info("NotesVectorStore: removed exam=%s topic=%r", exam_key, topic)
        return True
    except Exception as e:
        logger.error("NotesVectorStore.remove error: %s", e)
        return False


def stats() -> dict:
    """Return summary stats for the NAGA dashboard KB widget."""
    try:
        col, _ = _init()
        total = col.count()
        if total == 0:
            return {"total": 0, "by_exam": {}}

        # Fetch all metadata to aggregate per exam
        all_meta = col.get(include=["metadatas"])["metadatas"]
        by_exam: dict[str, int] = {}
        for m in all_meta:
            exam = m.get("exam", "unknown")
            by_exam[exam] = by_exam.get(exam, 0) + 1

        return {"total": total, "by_exam": by_exam}
    except Exception as e:
        logger.error("NotesVectorStore.stats error: %s", e)
        return {"total": 0, "by_exam": {}}
