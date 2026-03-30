# Technical Progress Report
**Project:** Citizens Advice AI Advisory Chatbot
**Repository:** github.com/nabilshanteer/aicity_chatbot
**Date:** 30 March 2026

---

## Overview

Development has been split across two active branches, each targeting a distinct layer of the system: `scraper` covers the data pipeline and AI backend, and `user_context_data` covers authentication and the user-facing interface.

---

## Branch 1: `scraper` — Data Pipeline & AI Backend

### Web Scraping Pipeline
A modular scraping pipeline was built to collect advisory content from GOV.UK. The `data_scraper.py` module fetches pages, strips boilerplate HTML (navigation, footers, scripts) using BeautifulSoup, and tags each document with its source URL and timestamp. Polite scraping is enforced with a delay between requests. A GOV.UK taxonomy API client (`gov_uk_api.py`) was developed to systematically discover relevant page URLs, alongside a crawler (`crawler.py`) for link-following.

### Chunking & Vector Embedding
Scraped content is processed by `chunker.py`, which splits documents into retrievable segments. These chunks are embedded using the `all-MiniLM-L6-v2` sentence transformer model (via `embedder.py`) and stored in a **FAISS vector index** — a high-performance similarity search library. The resulting index (`faiss_index.bin`) and chunk mapping (`chunk_mapping.json`) together form the system's knowledge base, currently holding thousands of embedded document chunks.

### RAG Query API (FastAPI)
A FastAPI backend (`backend/fastapi/main.py`) exposes a query endpoint that implements **Retrieval-Augmented Generation (RAG)**:
1. The user's query is embedded using the same sentence transformer.
2. FAISS retrieves the top-k most semantically similar chunks.
3. Retrieved context is passed to **Grok 3** (xAI's LLM, via an OpenAI-compatible API) along with conversation history.
4. The LLM generates a grounded, context-aware response.

### Supabase Chat Persistence
Conversation history is persisted to **Supabase** (PostgreSQL). Each session is assigned a UUID, and messages are stored with role labels (`advisor` / `AI`), enabling stateful multi-turn conversations that survive page refreshes.

### Automatic Case Summarisation
To manage long conversations efficiently, a summarisation routine was implemented that triggers every 8 messages. It uses Grok 3 to compress the conversation into a 2–3 sentence case summary, which is then injected into subsequent prompts as a `[Case Summary]` block. This keeps the context window lean without losing case continuity.

---

## Branch 2: `user_context_data` — Authentication & Frontend

### Authentication System
A full authentication flow was implemented supporting two sign-in methods:

- **Email/password** — handled via **NextAuth.js** with a credentials provider, which validates against Supabase Auth on the backend.
- **Google OAuth** — integrated via NextAuth's Google provider, with a callback page (`/auth/callback`) that syncs the authenticated user into Supabase on first login via a FastAPI endpoint (`/auth/sync-user`).

A shared `AuthContext` (React Context API) wraps the application, exposing login/logout state globally. Protected routes redirect unauthenticated users to `/login`.

### Database Migrations (Alembic)
Alembic was configured for the FastAPI backend to manage the PostgreSQL schema. An initial migration defines the core tables required for user and session management.

### Chat Interface (Next.js / React)
Significant front-end progress was made on the chat experience:

- **`ChatWindow`** — the main conversation view, rendering message history.
- **`MessageBubble`** — styled user and AI message components.
- **`ChatInput`** — text input with submission handling.
- **`ChatSidebar` / `ConversationList`** — sidebar listing prior conversations, enabling session switching.
- **`ProjectSidebar` / `ProjectContextPanel`** — UI panels for attaching project or case context to a conversation.
- **`DepthSlider`** — a UI control allowing the user to set the response depth (Standard / Detailed), passed to the backend query API.

### Signup Page
A `/signup` page was built allowing new users to register with email and password via Supabase Auth, with email confirmation support.

---

## Summary Table

| Area | Branch | Status |
|---|---|---|
| GOV.UK web scraper | `scraper` | Complete |
| FAISS vector index & embeddings | `scraper` | Complete |
| RAG query API (FastAPI + Grok 3) | `scraper` | Complete |
| Supabase chat persistence | `scraper` | Complete |
| Automatic case summarisation | `scraper` | Complete |
| Email/password & Google auth | `user_context_data` | Complete |
| Alembic database migrations | `user_context_data` | Complete |
| Chat UI components | `user_context_data` | In Progress |
| Frontend–backend integration | Pending merge | Upcoming |
