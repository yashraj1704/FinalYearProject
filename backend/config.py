import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")

    # Embeddings
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")  # 'openai' or 'huggingface'
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Vector store
    faiss_index_path: Optional[str] = os.getenv("FAISS_INDEX_PATH")  # e.g., ./data/index.faiss
    docstore_path: Optional[str] = os.getenv("DOCSTORE_PATH")  # e.g., ./data/docstore.jsonl
    top_k: int = int(os.getenv("TOP_K", "5"))
    retrieval_min_score: float = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.3"))

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # 'openai' or 'huggingface' or 'dummy'
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # HuggingFace (optional)
    hf_api_key: Optional[str] = os.getenv("HF_API_KEY")
    hf_model: str = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

    # Misc
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
