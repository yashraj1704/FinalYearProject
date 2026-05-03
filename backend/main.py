from __future__ import annotations

import json
import os
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from utils.logger import logger
from services.embeddings import EmbeddingClient
from db.vector_store import VectorStore
from services.retriever import Retriever
from services.llm import LLMClient
from services.rag import RAGPipeline

app = FastAPI(title="RAG Chatbot Backend")

# CORS for local dev
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=".*",  # Allow all origins during development
)

# Ensure data directories exist
DATA_DIR = Path(__file__).parent / "data" / "docs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Global variables for services
_embedder = EmbeddingClient()
_store = VectorStore(dim=_embedder.dim or 384)
_store.load()
_retriever = Retriever(_embedder, _store)
_llm = LLMClient()
_rag = RAGPipeline(_retriever, _llm)

async def reindex_documents():
    """Re-index all documents and reload services"""
    try:
        logger.info("Starting document re-indexing...")
        
        # Run ingestion in a separate process
        import subprocess
        import sys
        
        result = await asyncio.create_subprocess_exec(
            sys.executable, "scripts/ingest.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            logger.info("Re-indexing completed successfully")
            logger.info(f"Ingestion output: {stdout.decode()}")
            
            # Reload services with new data
            global _store, _retriever, _rag
            _store = VectorStore(dim=_embedder.dim or 384)
            _store.load()
            _retriever = Retriever(_embedder, _store)
            _rag = RAGPipeline(_retriever, _llm)
            logger.info("Services reloaded with new documents")
            return True
        else:
            logger.error(f"Re-indexing failed: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"Error during re-indexing: {e}")
        return False


@app.get("/health")
async def health():
    return {"status": "ok", "vector_store_ready": _store.is_ready()}


@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents = []
        for file_path in DATA_DIR.glob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                stat = file_path.stat()
                documents.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        return {"documents": sorted(documents, key=lambda x: x["modified"], reverse=True)}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {"documents": []}


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a specific document and re-index"""
    try:
        file_path = DATA_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete the file
        file_path.unlink()
        logger.info(f"Deleted document: {filename}")
        
        # Re-index remaining documents
        reindex_success = await reindex_documents()
        
        return JSONResponse({
            "message": f"Document '{filename}' deleted and re-indexed successfully",
            "reindexed": reindex_success
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document file (PDF, TXT, MD) and re-index the vector store"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.txt', '.md'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not allowed. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 10MB."
            )
        
        # Save file
        file_path = DATA_DIR / file.filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"File uploaded successfully: {file.filename} ({len(file_content)} bytes)")
        
        # Re-index documents
        reindex_success = await reindex_documents()
        
        return JSONResponse({
            "message": f"File uploaded and {'re-indexed' if reindex_success else 'saved'} successfully",
            "filename": file.filename,
            "size": len(file_content),
            "type": file_extension,
            "reindexed": reindex_success
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@app.post("/reindex")
async def manual_reindex():
    """Manually trigger re-indexing of all documents"""
    try:
        success = await reindex_documents()
        return JSONResponse({
            "message": "Re-indexing completed" if success else "Re-indexing failed",
            "success": success
        })
    except Exception as e:
        logger.error(f"Manual re-index error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during re-indexing")


@app.websocket("/chat")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket connected")
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
                question: Optional[str] = payload.get("question")
            except Exception:
                question = raw

            if not question:
                await ws.send_text("Error: empty question.")
                continue

            # Start streaming answer
            async for token in _rag.stream_answer(question):
                await ws.send_text(token)
            # Signal completion to client
            await ws.send_text("__END__")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await ws.send_text("__ERROR__")
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
