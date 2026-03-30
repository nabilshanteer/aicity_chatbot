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

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/` (copy from `.env.example`) and fill in your keys.

Then start the server:

```bash
uvicorn app.main:app --reload
```

API runs at http://localhost:8000 — interactive docs at http://localhost:8000/docs

---

### 2. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local` with the following:

```env
# Supabase (find these in Supabase dashboard → your project → Settings → API)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Google OAuth (Google Cloud Console → APIs & Services → Credentials)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# NextAuth (generate secret with: openssl rand -base64 32)
NEXTAUTH_SECRET=your-random-secret
NEXTAUTH_URL=http://localhost:3000

# Backend URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Then start the dev server:

```bash
npm run dev
```

App runs at http://localhost:3000
