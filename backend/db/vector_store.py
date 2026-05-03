from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None  # type: ignore

from config import settings
from utils.logger import logger
from pathlib import Path


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    score: float
    metadata: dict


class VectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = None
        self.docstore: dict[str, dict] = {}
        # NumPy fallback index
        self._np_mat: Optional[np.ndarray] = None  # shape: (N,D) normalized
        self._np_ids: list[str] = []

    def load(self) -> None:
        # Resolve defaults relative to backend/ folder so it works no matter the CWD
        backend_dir = Path(__file__).resolve().parents[1]
        index_dir = backend_dir / "data" / "index"
        default_faiss = index_dir / "faiss.index"
        default_docstore = index_dir / "docstore.jsonl"
        emb_path = index_dir / "embeddings.npy"
        ids_path = index_dir / "ids.txt"

        faiss_path = Path(settings.faiss_index_path) if settings.faiss_index_path else default_faiss
        docstore_path = Path(settings.docstore_path) if settings.docstore_path else default_docstore

        if faiss is not None and faiss_path.exists():
            logger.info(f"Loading FAISS index from {settings.faiss_index_path}")
            self.index = faiss.read_index(str(faiss_path))
            if docstore_path.exists():
                logger.info(f"Loading docstore from {docstore_path}")
                with open(docstore_path, "r", encoding="utf-8") as f:
                    for line in f:
                        rec = json.loads(line)
                        self.docstore[rec["id"]] = rec
            else:
                logger.warning("Docstore path missing; retrieval metadata may be limited.")
            return

        # NumPy fallback index
        if emb_path.exists() and ids_path.exists():
            logger.info(f"Loading NumPy index from {emb_path}")
            mat = np.load(emb_path).astype(np.float32)
            # normalize
            norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
            self._np_mat = mat / norms
            with open(ids_path, "r", encoding="utf-8") as f:
                self._np_ids = [line.strip() for line in f if line.strip()]
            # Load docstore if present
            if docstore_path.exists():
                logger.info(f"Loading docstore from {docstore_path}")
                with open(docstore_path, "r", encoding="utf-8") as f:
                    for line in f:
                        rec = json.loads(line)
                        self.docstore[rec["id"]] = rec
            return

        # Final fallback: small demo in-memory corpus
        logger.warning(
            "No FAISS/NumPy index found. Using small demo in-memory corpus. "
            f"Checked paths: emb={emb_path} ids={ids_path} docstore={docstore_path}"
        )
        self.index = None
        self.docstore = {
            "doc1": {"id": "doc1", "text": "This project is a RAG-based chatbot using FastAPI and React.", "metadata": {"source": "sample"}},
            "doc2": {"id": "doc2", "text": "It uses FAISS for retrieval and streams answers over WebSockets.", "metadata": {"source": "sample"}},
        }

    def is_ready(self) -> bool:
        return self.index is not None or self._np_mat is not None or len(self.docstore) > 0

    def search(self, query_vec: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        if self.index is not None and faiss is not None:
            # Normalize query for cosine similarity with IndexFlatIP built on normalized vectors
            q = query_vec.astype(np.float32)
            q = q / (np.linalg.norm(q) + 1e-8)
            query_vec = np.expand_dims(q, axis=0)
            scores, idxs = self.index.search(query_vec, top_k)
            results: List[Tuple[str, float]] = []
            for i, score in zip(idxs[0], scores[0]):
                if i == -1:
                    continue
                # We used ids.txt when building FAISS in ingest, but FAISS doesn't store ids.
                # Assume ids are 0..N-1 in the same order as embeddings; fallback to string index if missing.
                if 0 <= i < len(self.docstore):
                    # Attempt to map via insertion order (may not be reliable). Prefer NumPy path for exact ids.
                    doc_id = list(self.docstore.keys())[i]
                else:
                    doc_id = str(i)
                results.append((doc_id, float(score)))
            return results
        if self._np_mat is not None:
            # Cosine similarity with normalized matrix
            q = query_vec.astype(np.float32)
            q = q / (np.linalg.norm(q) + 1e-8)
            sims = self._np_mat @ q
            idxs = np.argsort(-sims)[:top_k]
            results: List[Tuple[str, float]] = []
            for i in idxs.tolist():
                did = self._np_ids[i] if 0 <= i < len(self._np_ids) else str(i)
                results.append((did, float(sims[i])))
            return results
        # Fallback: naive random ranking for demo mode
        rng = np.random.default_rng(abs(int(np.sum(query_vec) * 1e6)) % (2 ** 32))
        ids = list(self.docstore.keys())
        scores = rng.random(len(ids))
        ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def get(self, doc_id: str) -> Optional[dict]:
        return self.docstore.get(doc_id)
