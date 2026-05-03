# RAG Chatbot (FastAPI + React)

A Retrieval-Augmented Generation chatbot with a FastAPI backend (WebSocket streaming) and a React frontend.

## Features
- WebSocket real-time streaming from backend `ws://localhost:8000/chat`.
- Modular backend: `services/` (embeddings, retriever, LLM, RAG), `db/` (vector store), `utils/`, `config.py`.
- Vector DB: FAISS (optional). Falls back to in-memory demo data if not present.
- Frontend React app with live typing effect.

## Prerequisites
- Python 3.10+
- Node.js 18+

## Setup

### 1) Backend
```bash
# From project root
cd backend

# Create virtual environment (Windows PowerShell)


1 # first run this script 
python -m venv .venv

2 # then run this 
.venv/Scripts/Activate.ps1

3 # Install deps
pip install -r requirements.txt

# environment file 
make a ".env" file in backend after this copy ".env.example" file from backend and paste in ".env.example"
or you can just rename ".env.example" to ".env"


# put documents 

you have to keep your all documents in /backend/data/docs
make sure your all documents are in this dir mentioned above .

# run this command 

python scripts/ingest.py



# Start server
uvicorn main:app --reload --port 8000
```

now your backend is running . now open another terminal ..

### 2) Frontend
```bash
# In another terminal from project root
cd frontend
npm install
npm run dev
```

now you can access the chatbot using localhost link which is on your terminal . 

Open http://localhost:5173 and ask a question.

## Config
- Edit `backend/.env` or environment variables. See `backend/.env.example` for available options.

## Notes
- For production, add proper FAISS index persistence, auth, rate limiting, and observability.
- Consider Dockerizing and adding HTTPS, reverse proxy, and CI.
