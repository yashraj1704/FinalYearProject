from __future__ import annotations

from typing import List

import numpy as np

from config import settings
from utils.logger import logger


class EmbeddingClient:
    def __init__(self):
        self.provider = settings.embedding_provider.lower()
        self.dim = None
        self._model = None
        if self.provider == "huggingface":
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
                self._model = SentenceTransformer(settings.embedding_model)
                # Infer dim by embedding a small string once
                self.dim = int(self._model.get_sentence_embedding_dimension())
                logger.info(f"Loaded HF embeddings: {settings.embedding_model} (dim={self.dim})")
            except Exception as e:  # pragma: no cover
                logger.error(f"Failed to load HF embeddings: {e}")
                self._model = None
        elif self.provider == "openai":  # pragma: no cover - optional
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=settings.openai_api_key)
                self.dim = 1536  # typical dim; may vary by model
                logger.info(f"Using OpenAI embeddings: {settings.openai_embedding_model}")
            except Exception as e:
                logger.error(f"Failed to init OpenAI embeddings: {e}")
                self._client = None
        else:
            logger.warning("Unknown embedding provider; falling back to dummy embeddings.")

    def embed(self, texts: List[str]) -> np.ndarray:
        if self.provider == "huggingface" and self._model is not None:
            vecs = self._model.encode(texts, normalize_embeddings=True)
            return np.array(vecs, dtype=np.float32)
        if self.provider == "openai":  # pragma: no cover - optional
            if getattr(self, "_client", None) is not None and settings.openai_api_key:
                resp = self._client.embeddings.create(model=settings.openai_embedding_model, input=texts)
                mat = [d.embedding for d in resp.data]
                return np.array(mat, dtype=np.float32)
        # Dummy deterministic embedding: bag-of-words hashing
        def hash_embed(t: str, dim: int = 384) -> np.ndarray:
            vec = np.zeros(dim, dtype=np.float32)
            for w in t.split():
                idx = hash(w) % dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec) + 1e-8
            return vec / norm

        mat = np.stack([hash_embed(t) for t in texts], axis=0)
        if self.dim is None:
            self.dim = mat.shape[1]
        return mat

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
