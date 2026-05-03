from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

import numpy as np

# Add the parent directory to Python path for imports
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

try:
    import faiss  # type: ignore
except Exception:  # optional
    faiss = None  # type: ignore

# Local imports
from config import settings
from services.embeddings import EmbeddingClient
from utils.logger import logger
from utils.text import chunk_text

DOCS_DIR = (BACKEND_DIR / "data" / "docs").resolve()
INDEX_DIR = (BACKEND_DIR / "data" / "index").resolve()
INDEX_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_PATH = Path(settings.faiss_index_path) if settings.faiss_index_path else INDEX_DIR / "faiss.index"
DOCSTORE_PATH = Path(settings.docstore_path) if settings.docstore_path else INDEX_DIR / "docstore.jsonl"
EMB_PATH = INDEX_DIR / "embeddings.npy"  # fallback for no-FAISS runtime
IDS_PATH = INDEX_DIR / "ids.txt"


def read_txt(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def read_pdf(p: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:
        raise RuntimeError("Please install pypdf to parse PDFs: pip install pypdf") from e
    reader = PdfReader(str(p))
    texts: List[str] = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts)


def iter_documents() -> Iterable[tuple[str, str]]:
    if not DOCS_DIR.exists():
        logger.warning(f"Docs directory not found: {DOCS_DIR}")
        return []
    for p in DOCS_DIR.rglob("*"):
        if p.is_dir():
            continue
        if p.suffix.lower() in {".txt"}:
            yield (str(p), read_txt(p))
        elif p.suffix.lower() in {".pdf"}:
            yield (str(p), read_pdf(p))


def main():
    logger.info(f"Reading documents from {DOCS_DIR}")
    records: List[dict] = []
    texts_for_embed: List[str] = []
    ids: List[str] = []

    embedder = EmbeddingClient()

    for src, content in iter_documents():
        if not content.strip():
            continue
        chunks = chunk_text(content, max_tokens=300)
        for i, ch in enumerate(chunks):
            rid = f"{src}::chunk:{i}"
            records.append({
                "id": rid,
                "text": ch,
                "metadata": {"source": src, "chunk": i},
            })
            texts_for_embed.append(ch)
            ids.append(rid)

    if not records:
        logger.warning("No documents found to ingest.")
        return

    logger.info(f"Embedding {len(texts_for_embed)} chunks...")
    mat = embedder.embed(texts_for_embed).astype(np.float32)

    # Save docstore JSONL
    with open(DOCSTORE_PATH, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info(f"Wrote docstore: {DOCSTORE_PATH}")

    # Always save numpy fallback for runtime without FAISS
    np.save(EMB_PATH, mat)
    with open(IDS_PATH, "w", encoding="utf-8") as f:
        for rid in ids:
            f.write(rid + "\n")
    logger.info(f"Wrote embeddings fallback: {EMB_PATH}, ids: {IDS_PATH}")

    # Build FAISS if available
    if faiss is not None:
        index = faiss.IndexFlatIP(mat.shape[1])
        # normalize for cosine similarity
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
        mat_norm = mat / norms
        index.add(mat_norm)
        faiss.write_index(index, str(FAISS_INDEX_PATH))
        logger.info(f"Wrote FAISS index: {FAISS_INDEX_PATH}")
    else:
        logger.warning("faiss not installed; skipped writing FAISS index. Fallback NumPy index will be used at runtime.")

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
