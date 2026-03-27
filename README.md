# Citizens Advice AI Chatbot

AI-powered advisory assistant for Citizens Advice staff. Built with FastAPI (backend) + Next.js (frontend), using Retrieval-Augmented Generation (RAG) over trusted source documents.

---

## Project Structure

```
citizen_chatbot/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── api/              # Route handlers (chat, documents, auth)
│   │   ├── core/             # Config, security
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # LLM service, vector store
│   │   ├── utils/            # Document processor
│   │   └── main.py           # FastAPI app entrypoint
│   ├── data/                 # Persisted ChromaDB vector store
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # Next.js React frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Next.js pages
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client
│   │   └── styles/           # Global CSS / Tailwind
│   ├── package.json
│   └── .env.local.example
└── documents/                # Project documentation
    ├── project_proposal.md
    └── technical_specifications.md
```

---

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Fill in your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                   # Runs on http://localhost:3000
```

API docs available at: http://localhost:8000/docs
