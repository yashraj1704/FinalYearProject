from __future__ import annotations

from typing import List

from config import settings
from db.vector_store import VectorStore
from services.embeddings import EmbeddingClient
from utils.logger import logger


class Retriever:
    def __init__(self, embedder: EmbeddingClient, store: VectorStore):
        self.embedder = embedder
        self.store = store

    def top_k(self, query: str, k: int | None = None) -> List[str]:
        k = k or settings.top_k
        qvec = self.embedder.embed_one(query)
        results = self.store.search(qvec, k)
        texts: List[str] = []
        for doc_id, score in results:
            rec = self.store.get(doc_id)
            if rec is None:
                continue
            text = rec.get("text", "")
            texts.append(text)
            logger.debug(f"Retrieved: id={doc_id} score={score:.4f}")
        return texts

    def top_k_with_scores(self, query: str, k: int | None = None) -> List[tuple[str, float]]:
        """Return (text, score) pairs for gating on relevance."""
        k = k or settings.top_k
        qvec = self.embedder.embed_one(query)
        results = self.store.search(qvec, k)
        pairs: List[tuple[str, float]] = []
        for doc_id, score in results:
            rec = self.store.get(doc_id)
            if rec is None:
                continue
            text = rec.get("text", "")
            pairs.append((text, float(score)))
            logger.debug(f"Retrieved: id={doc_id} score={score:.4f}")
        return pairs
