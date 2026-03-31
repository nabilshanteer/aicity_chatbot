# Citizens Advice AI Chatbot

AI-powered advisory assistant for Citizens Advice staff, using RAG over Citizens Advice source documents.

---

## Setup

**Prerequisites:** Python 3.10+, Node.js 18+

**1. Backend env** — create `backend/.env`:
```
DATABASE_URL=...
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
CORS_ORIGINS=http://localhost:3000
NEXTAUTH_SECRET=...
```

**2. Frontend env** — create `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

**3. Install dependencies**
```bash
pip install -r backend/requirements.txt
npm install
```

---

## Run

```bash
npm run dev
```

Frontend → http://localhost:3000 · Backend → http://localhost:8000
