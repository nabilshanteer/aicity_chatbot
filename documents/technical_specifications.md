# Technical Specifications
## Citizens Advice AI Information Retrieval Chatbot

**Version:** 0.1.0  
**Last Updated:** 2025-03  
**Status:** Draft

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Backend Specifications](#4-backend-specifications)
5. [Frontend Specifications](#5-frontend-specifications)
6. [RAG Pipeline](#6-rag-pipeline)
7. [API Reference](#7-api-reference)
8. [Data Models](#8-data-models)
9. [Security & Compliance](#9-security--compliance)
10. [Performance Targets](#10-performance-targets)
11. [Deployment](#11-deployment)
12. [Future Roadmap](#12-future-roadmap)

---

## 1. System Overview

The Citizens Advice AI Chatbot is a staff-facing, Retrieval-Augmented Generation (RAG) web application. It enables frontline advisors to retrieve accurate, source-grounded answers from a curated library of trusted policy and guidance documents — replacing slow, fragmented manual search.

### Primary Users
| Role | Description |
|---|---|
| **Advisor** | Frontline staff using the chat interface during client sessions |
| **Admin** | Manages the trusted document library (upload/delete) |
| **Read-only** | Supervisors or auditors who can view but not interact |

### Core Workflow
```
Advisor asks a question
        ↓
Query is embedded and matched against vector store
        ↓
Top-K source chunks retrieved (depth-dependent)
        ↓
LLM generates a grounded, cited answer
        ↓
Response + source links displayed to advisor
```

---

## 2. Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Advisor)                 │
│              Next.js 14 Frontend (React)             │
└────────────────────────┬────────────────────────────┘
                         │ HTTPS / REST + SSE streaming
┌────────────────────────▼────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Auth API │  │  Chat API   │  │  Documents API │  │
│  └──────────┘  └──────┬──────┘  └───────┬────────┘  │
│                       │                 │            │
│          ┌────────────▼──────┐  ┌───────▼─────────┐ │
│          │   LLM Service     │  │ Document        │ │
│          │  (Anthropic API)  │  │ Processor       │ │
│          └────────────┬──────┘  └───────┬─────────┘ │
│                       │                 │            │
│          ┌────────────▼─────────────────▼─────────┐  │
│          │          Vector Store (ChromaDB)        │  │
│          │    Sentence-Transformer Embeddings      │  │
│          └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|---|---|
| **Next.js Frontend** | Chat UI, session management, source display, auth |
| **FastAPI Backend** | API routing, request validation, orchestration |
| **LLM Service** | Prompt construction, calling Anthropic API, streaming |
| **Vector Store** | Document embedding, semantic retrieval |
| **Document Processor** | PDF/DOCX/TXT parsing, chunking, metadata extraction |
| **Auth Module** | JWT issuance and validation, role enforcement |

---

## 3. Technology Stack

### Backend
| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Framework | FastAPI | 0.111 | Async-native, auto OpenAPI docs, Pydantic validation |
| Runtime | Python | 3.11+ | Broad AI/ML library support |
| LLM | Anthropic Claude | claude-opus-4-5 | Strong instruction-following, UK context awareness |
| Embeddings | sentence-transformers | 3.0 | Local, fast, no API cost for embeddings |
| Vector DB | ChromaDB | 0.5 | Embedded, zero-infra, persistent, easy to migrate |
| Auth | python-jose + passlib | — | JWT + bcrypt, industry standard |
| Server | Uvicorn | 0.29 | ASGI, production-grade |

### Frontend
| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Framework | Next.js | 14.2 | SSR, file-based routing, TypeScript native |
| Language | TypeScript | 5.x | Type safety, better DX |
| Styling | Tailwind CSS | 3.4 | Utility-first, rapid UI development |
| HTTP Client | Axios | 1.7 | Interceptors for auth tokens, clean API |
| Icons | Lucide React | 0.383 | Consistent, accessible icon set |

---

## 4. Backend Specifications

### Directory Structure
```
backend/
├── app/
│   ├── main.py               # FastAPI app, CORS, router registration
│   ├── api/
│   │   ├── auth.py           # POST /api/auth/login
│   │   ├── chat.py           # POST /api/chat/, POST /api/chat/stream
│   │   └── documents.py      # POST /api/documents/upload, DELETE /api/documents/{name}
│   ├── core/
│   │   ├── config.py         # Pydantic settings from .env
│   │   └── security.py       # JWT creation/decoding, bcrypt helpers
│   ├── models/
│   │   ├── chat.py           # Message, Session, ChatRequest/Response, SourceChunk
│   │   └── user.py           # User, UserInDB, TokenResponse, LoginRequest
│   ├── services/
│   │   ├── llm_service.py    # Anthropic client, prompt builder, stream wrapper
│   │   └── vector_store.py   # ChromaDB client, retrieve(), add_documents()
│   └── utils/
│       └── document_processor.py  # PDF/DOCX/TXT chunking and ingestion
├── data/
│   └── chroma_db/            # Persisted vector store (gitignored)
├── requirements.txt
└── .env.example
```

### Configuration (`.env`)
| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Anthropic API key |
| `LLM_MODEL` | `claude-opus-4-5` | Model identifier |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Vector DB storage path |
| `SECRET_KEY` | — | Required. JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | 8-hour sessions |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

---

## 5. Frontend Specifications

### Directory Structure
```
frontend/src/
├── components/
│   ├── ChatWindow.tsx         # Main message thread display
│   ├── MessageBubble.tsx      # Individual message with role styling
│   ├── SourcePanel.tsx        # Collapsible source citations per message
│   ├── DepthToggle.tsx        # Quick / Standard / Deep selector
│   ├── VoiceInput.tsx         # Speech-to-text button (Web Speech API)
│   ├── SessionSidebar.tsx     # List of past sessions, new session button
│   └── DocumentUpload.tsx     # Admin: drag-and-drop document uploader
├── pages/
│   ├── index.tsx              # Redirects to /chat
│   ├── chat.tsx               # Main chat interface
│   ├── login.tsx              # Login form
│   └── admin/
│       └── documents.tsx      # Admin document management page
├── hooks/
│   ├── useChat.ts             # Chat state, send message, streaming handler
│   ├── useSession.ts          # Session CRUD, active session management
│   └── useAuth.ts             # Login, logout, token storage
├── services/
│   └── api.ts                 # Axios instance, typed API call wrappers
└── styles/
    └── globals.css            # Tailwind base imports, custom CSS variables
```

### Key UI Components

#### `ChatWindow`
- Renders full message history for the active session
- Streams tokens in real-time via SSE (EventSource)
- Auto-scrolls to bottom on new message
- Shows typing indicator during generation

#### `MessageBubble`
- Distinct visual styling for `user` vs `assistant` roles
- Assistant messages include a collapsible `SourcePanel`
- 👍 / 👎 feedback buttons on assistant messages

#### `DepthToggle`
- Three-way toggle: **Quick** | **Standard** | **Deep**
- Persisted per session in local state
- Tooltip explaining each mode's trade-off

#### `SourcePanel`
- Accordion below each assistant message
- Displays: document name, page number, relevance score, excerpt preview
- Relevance score shown as a colour-coded badge (green > 0.8, amber > 0.6, red ≤ 0.6)

#### `SessionSidebar`
- Lists all sessions with title (auto-generated from first message) and case category tag
- New Session button clears context and creates a new session ID
- Export session as plain text transcript

---

## 6. RAG Pipeline

### Document Ingestion Flow
```
Upload file (PDF / DOCX / TXT / MD)
        ↓
Extract raw text per page / paragraph
        ↓
Chunk text (500 tokens, 100-token overlap)
        ↓
Embed chunks (Sentence-Transformers)
        ↓
Store in ChromaDB with metadata:
  { source, page, section, upload_date }
```

### Query & Retrieval Flow
```
User query string
        ↓
Embed query (same model as ingestion)
        ↓
Cosine similarity search against ChromaDB
        ↓
Return top-K chunks (K = 2 / 5 / 10 by depth)
        ↓
Filter out chunks with relevance_score < 0.45
        ↓
Pass chunks as context to LLM prompt
```

### Chunking Parameters
| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 500 characters | Balances context richness vs retrieval precision |
| Overlap | 100 characters | Preserves context at chunk boundaries |
| Min chunk length | 50 characters | Filters out page headers/footers |
| Similarity metric | Cosine | Standard for semantic similarity |
| Min relevance score | 0.45 | Prevents irrelevant context injection |

### Depth Mode Configuration
| Mode | Top-K Chunks | Max LLM Tokens | Use Case |
|---|---|---|---|
| **Quick** | 2 | 400 | Fast factual lookups during live client call |
| **Standard** | 5 | 800 | Typical advisory queries |
| **Deep** | 10 | 1,600 | Complex, multi-faceted policy questions |

### Prompt Architecture
```
SYSTEM: Role definition, strict grounding rules, citation requirements
USER:   RETRIEVED CONTEXT: [chunk 1] ... [chunk N]
        QUESTION: [user query]
ASSISTANT: [grounded, cited response]
```
Prior conversation turns are prepended before the current user turn to maintain conversational memory.

---

## 7. API Reference

### Authentication

#### `POST /api/auth/login`
| Field | Type | Description |
|---|---|---|
| `username` | string | Advisor username |
| `password` | string | Password |

**Response:** `{ access_token, token_type, expires_in }`

---

### Chat

#### `POST /api/chat/`
| Field | Type | Description |
|---|---|---|
| `session_id` | string | UUID for this conversation |
| `message` | string | User query |
| `depth` | enum | `quick` \| `standard` \| `deep` |
| `case_category` | string? | Optional category tag |

**Response:** `{ session_id, message: { id, role, content, sources[], timestamp } }`

#### `POST /api/chat/stream`
Same request body as above. Returns `text/plain` SSE stream of tokens.

#### `DELETE /api/chat/{session_id}`
Clears conversation history for the given session.

---

### Documents

#### `POST /api/documents/upload`
Multipart form upload. Accepts `.pdf`, `.docx`, `.txt`, `.md`.  
**Response:** `{ detail: "Ingested N chunks from 'filename'" }`

#### `DELETE /api/documents/{document_name}`
Removes all vector store entries for the named document.

---

### Health

#### `GET /health`
**Response:** `{ status: "ok", version: "0.1.0" }`

---

## 8. Data Models

### `Message`
```typescript
{
  id: string           // UUID
  role: "user" | "assistant"
  content: string
  sources?: SourceChunk[]
  timestamp: datetime
}
```

### `SourceChunk`
```typescript
{
  document_name: string
  page?: number
  section?: string
  excerpt: string
  relevance_score: number  // 0.0 – 1.0
}
```

### `ChatRequest`
```typescript
{
  session_id: string
  message: string
  depth: "quick" | "standard" | "deep"
  case_category?: string
}
```

### `User`
```typescript
{
  id: string
  username: string
  email: string
  role: "advisor" | "admin" | "readonly"
  created_at: datetime
}
```

---

## 9. Security & Compliance

### UK GDPR Requirements
| Requirement | Implementation |
|---|---|
| **Data minimisation** | No client PII stored; query logs anonymised |
| **Purpose limitation** | System used solely for information retrieval support |
| **Storage limitation** | Session data held in-memory only; no persistent chat logs by default |
| **Integrity & confidentiality** | HTTPS/TLS in transit; bcrypt password hashing; JWT signing |

### Authentication & Authorisation
- JWT tokens with 8-hour expiry; refresh on activity
- Role-based access: admin routes protected by role claim in JWT
- Passwords hashed with bcrypt (cost factor 12)
- All API routes require `Authorization: Bearer <token>` (except `/health` and `/api/auth/login`)

### Data Handling
- Uploaded documents stored temporarily during ingestion then deleted from disk; only embeddings and metadata persist
- Vector store contains only document text excerpts — no personal advisor or client data
- `.env` secrets never committed to version control (`.gitignore` enforced)

### Audit Logging
- All chat queries logged with: timestamp, anonymised user ID, session ID, depth mode
- Document upload/delete events logged with: timestamp, admin user ID, filename
- Logs written to structured JSON via Loguru; no raw query text stored

---

## 10. Performance Targets

| Metric | Target |
|---|---|
| Quick mode end-to-end latency | < 3 seconds |
| Standard mode end-to-end latency | < 6 seconds |
| Deep mode end-to-end latency | < 12 seconds |
| Streaming first-token latency | < 1.5 seconds |
| Document ingestion (10-page PDF) | < 10 seconds |
| Vector retrieval (top-5) | < 200ms |
| Concurrent sessions supported | 20+ (single instance) |
| Frontend initial load (LCP) | < 2.5 seconds |

---

## 11. Deployment

### Development
```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev  # http://localhost:3000
```

### Production (Recommended)
| Component | Platform | Notes |
|---|---|---|
| Backend | Docker + Gunicorn/Uvicorn workers | Behind nginx reverse proxy |
| Frontend | Vercel or Docker (Next.js standalone) | CDN edge caching for static assets |
| Vector DB | ChromaDB (local volume) or migrate to pgvector | Persistent volume mount required |
| Secrets | Environment variables / Azure Key Vault | Never hardcoded |

### Docker (Future)
A `docker-compose.yml` will be added to orchestrate backend + frontend services together with a shared volume for the ChromaDB data directory.

---

## 12. Future Roadmap

| Feature | Priority | Notes |
|---|---|---|
| Voice input (Speech-to-Text) | Medium | Web Speech API or OpenAI Whisper |
| Feedback loop (👍/👎) | High | Store ratings to flag poor retrievals for review |
| Admin document management UI | High | Drag-and-drop upload panel, document library view |
| Case category scoping | Medium | Filter retrieval to category-specific documents |
| Session export (transcript) | Medium | Download chat as PDF or plain text |
| Multi-language support | Low | Welsh language support for Welsh councils |
| SSO / Microsoft Entra integration | High | For Citizens Advice org-wide deployment |
| pgvector migration | Medium | Scales beyond single-node ChromaDB |
| Offline cached Q&A | Low | Resilience during connectivity issues |
| Evaluation harness | High | Automated RAG quality scoring (RAGAS framework) |
