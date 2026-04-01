import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import google.genai as genai
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Check your .env file!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1"},
)

model = None

DEPTH_CANDIDATE_COUNTS = {
    "quick": 5,
    "balanced": 12,
    "deep": 20,
}

DEPTH_FINAL_COUNTS = {
    "quick": 3,
    "balanced": 5,
    "deep": 8,
}

STOPWORDS = {
    "about", "again", "also", "and", "are", "been", "being", "between", "can",
    "for", "from", "had", "has", "have", "into", "its", "just", "not", "now",
    "our", "out", "over", "said", "should", "some", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "those", "through",
    "under", "using", "very", "what", "when", "where", "which", "with", "would",
    "your",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print("Starting server: Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model ready.")
    yield
    print("Shutting down...")


app = FastAPI(title="Citizens Advice AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    depth: Literal["quick", "balanced", "deep"] = "balanced"
    notes: list[str] = Field(default_factory=list)
    selected_sources: list[str] = Field(default_factory=list)
    selected_documents: list[str] = Field(default_factory=list)


class TitleRequest(BaseModel):
    message: str


class SuggestRequest(BaseModel):
    fragments: list[str]
    context: str = ""


class NoteSuggestion(BaseModel):
    fragment: str
    suggestion: str | None
    full: str


class SuggestResponse(BaseModel):
    suggestions: list[NoteSuggestion]


class SaveNotesRequest(BaseModel):
    notes: list[str]


class SyncUserRequest(BaseModel):
    email: str
    name: str | None = None
    google_id: str | None = None


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str


# ---------------------------------------------------------------------------
# RAG helpers
# ---------------------------------------------------------------------------

def unique_nonempty(values: list[str], limit: int | None = None) -> list[str]:
    seen = set()
    result = []

    for value in values:
        normalised = value.strip()
        if not normalised:
            continue
        if normalised in seen:
            continue
        seen.add(normalised)
        result.append(normalised)
        if limit is not None and len(result) >= limit:
            break

    return result


def parse_notes_value(notes_value) -> list[str]:
    if notes_value is None:
        return []
    if isinstance(notes_value, list):
        return [str(note) for note in notes_value]
    if isinstance(notes_value, str):
        raw = notes_value.strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(note) for note in data]
        except json.JSONDecodeError:
            return [raw]
    return []


def strip_fences(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("```"):
        return raw

    parts = raw.split("```")
    if len(parts) < 2:
        return raw

    content = parts[1].strip()
    if content.startswith("json"):
        content = content[4:].strip()
    return content


def heading_label(chunk: dict) -> str:
    return (
        chunk.get("heading_path")
        or chunk.get("heading")
        or chunk.get("page_title")
        or "Page Content"
    )


def tokenize_keywords(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def fetch_known_sources() -> set[str]:
    response = supabase.table("chunks").select("source").limit(1000).execute()
    return {
        item["source"].strip().lower()
        for item in (response.data or [])
        if item.get("source") and item["source"].strip()
    }


def resolve_document_filters(selected_documents: list[str]) -> list[str]:
    if not selected_documents:
        return []

    known_sources = fetch_known_sources()
    matches = []
    for name in unique_nonempty(selected_documents, limit=10):
        lowered = name.lower()
        if lowered in known_sources:
            matches.append(lowered)
    return matches


def format_history_for_rewrite(history: list[dict], limit: int = 5) -> str:
    recent_history = history[-limit:]
    if not recent_history:
        return "No prior case messages available."

    lines = []
    for entry in recent_history:
        role = entry.get("role")
        speaker = "Advisor" if role == "advisor" else "Assistant"
        content = (entry.get("content") or "").strip()
        if content:
            lines.append(f"{speaker}: {content}")

    return "\n".join(lines) if lines else "No prior case messages available."


def rewrite_search_query(
    user_query: str,
    notes: list[str],
    history: list[dict],
    selected_sources: list[str],
    selected_documents: list[str],
) -> str:
    notes = unique_nonempty(notes, limit=12)
    selected_sources = unique_nonempty(selected_sources, limit=10)
    selected_documents = unique_nonempty(selected_documents, limit=10)

    context_bits = []
    if notes:
        context_bits.append("Notes:\n" + "\n".join(f"- {note}" for note in notes))
    context_bits.append("Recent case messages:\n" + format_history_for_rewrite(history))
    if selected_sources:
        context_bits.append("Selected source URLs:\n" + "\n".join(f"- {url}" for url in selected_sources))
    if selected_documents:
        context_bits.append("Selected document names:\n" + "\n".join(f"- {name}" for name in selected_documents))

    context_block = "\n\n".join(context_bits) if context_bits else "No extra case context provided."
    prompt = f"""Rewrite the user's question into a single retrieval search query for a legal-advice RAG system.

Rules:
- Output JSON only with exactly one key: "search_query"
- Keep exact legal or domain terms from the original question
- Use note context only when it sharpens retrieval
- Do not answer the question
- Do not invent facts
- One sentence only
- Maximum 220 characters

Original question:
{user_query}

Additional case context:
{context_block}
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = strip_fences(response.text or "")
        data = json.loads(raw)
        search_query = (data.get("search_query") or "").strip()
        if search_query:
            return search_query[:220]
    except Exception:
        pass

    return user_query


def retrieve_chunks(
    query: str,
    top_k: int,
    source_urls: list[str] | None = None,
    sources: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    embedding = model.encode(query).tolist()
    params = {
        "query_embedding": embedding,
        "match_count": top_k,
        "source_urls": source_urls or None,
        "sources": sources or None,
        "categories": categories or None,
    }
    result = supabase.rpc("match_chunks", params).execute()
    return result.data or []


def rerank_chunks(
    chunks: list[dict],
    rewritten_query: str,
    selected_sources: list[str],
    selected_documents: list[str],
    depth: str,
) -> list[dict]:
    if not chunks:
        return []

    selected_sources = set(unique_nonempty(selected_sources))
    selected_documents_lower = {name.lower() for name in unique_nonempty(selected_documents)}
    query_tokens = tokenize_keywords(rewritten_query)

    if depth == "quick" and not selected_sources and not selected_documents_lower:
        return chunks[:DEPTH_FINAL_COUNTS[depth]]

    ranked = []
    for chunk in chunks:
        similarity = float(chunk.get("similarity") or 0.0)
        score = similarity

        if chunk.get("source_url") in selected_sources:
            score += 0.10

        if (chunk.get("source") or "").lower() in selected_documents_lower:
            score += 0.08

        overlap = len(query_tokens & tokenize_keywords(chunk.get("text", "")))
        score += min(overlap * 0.03, 0.12)

        ranked.append((score, chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in ranked[:DEPTH_FINAL_COUNTS[depth]]]


def generate_ai_response(user_query: str, retrieved_chunks: list[dict], history: list[dict], case_summary: str | None = None):
    if not retrieved_chunks:
        return (
            "I couldn't find relevant indexed information for that question in the current knowledge base. "
            "Try refining the question or adding a more specific source.",
            [],
        )

    context = "\n\n".join([
        "\n".join([
            f"[Source: {doc.get('source_url', 'Unknown')}]",
            f"[Heading: {heading_label(doc)}]",
            doc.get("text", ""),
        ])
        for doc in retrieved_chunks
    ])
    sources = unique_nonempty([
        doc.get("source_url", "Unknown")
        for doc in retrieved_chunks
        if doc.get("source_url")
    ])

    history_str = ""
    for entry in history:
        speaker = "User" if entry["role"] == "advisor" else "Assistant"
        history_str += f"{speaker}: {entry['content']}\n"

    summary_context = f"\n[Case Summary]\n{case_summary}\n" if case_summary else ""
    prompt = f"""You are a professional advisor for Citizens Advice.
Use only the provided context and conversation history to answer the user's question accurately and helpfully.

Requirements:
- Stay grounded in the supplied context
- Cite sources using [Source: URL]
- If the context is insufficient, say so explicitly

{summary_context}
History:
{history_str}

Relevant Information:
{context}

User Question: {user_query}
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return (response.text or "").strip(), sources
    except Exception as e:
        return f"Error generating response: {str(e)}", sources


def generate_case_summary(messages, previous_summary=None):
    messages_str = ""
    for entry in messages:
        speaker = "User" if entry["role"] == "advisor" else "Assistant"
        messages_str += f"{speaker}: {entry['content']}\n"

    previous_context = f"\n\nPrevious Summary for Context:\n{previous_summary}" if previous_summary else ""

    summarization_prompt = f"""Create a concise summary of this Citizens Advice case conversation.
Capture key issues, questions asked, advice given, and any important context or decisions.
Keep it brief but comprehensive (2-3 sentences max).{previous_context}

Recent Conversation:
{messages_str}"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=summarization_prompt,
        )
        return (response.text or "").strip()
    except Exception as e:
        return f"Unable to generate summary: {str(e)}"


# ---------------------------------------------------------------------------
# Cases / chat endpoints
# ---------------------------------------------------------------------------

@app.post("/api/cases/start")
async def start_case():
    try:
        response = supabase.table("cases").insert({}).execute()
        if response.data and len(response.data) > 0:
            return {"case_id": response.data[0]["id"]}
        raise HTTPException(status_code=500, detail="Supabase inserted the row but returned no data.")
    except Exception as e:
        print(f"Supabase Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cases/{case_id}/query")
async def ask_question(case_id: str, request: QueryRequest):
    try:
        print(f"[QUERY] Received query for case_id: {case_id}")
        print(f"[QUERY] Question: {request.query}")

        case_res = supabase.table("cases").select("id", "summary", "notes").eq("id", case_id).execute()
        if not case_res.data:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in database.")
        case_record = case_res.data[0]
        case_summary = case_record.get("summary")
        case_notes = parse_notes_value(case_record.get("notes"))

        history_res = (
            supabase.table("messages")
            .select("role", "content")
            .eq("case_id", case_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        history = history_res.data[::-1] if history_res.data else []
        retrieval_notes = unique_nonempty(case_notes + request.notes, limit=12)

        rewritten_query = rewrite_search_query(
            request.query,
            retrieval_notes,
            history,
            request.selected_sources,
            request.selected_documents,
        )
        source_filters = unique_nonempty(request.selected_sources, limit=10)
        document_source_filters = resolve_document_filters(request.selected_documents)

        print(f"[QUERY] Retrieval query: {rewritten_query}")
        candidates = retrieve_chunks(
            rewritten_query,
            DEPTH_CANDIDATE_COUNTS[request.depth],
            source_urls=source_filters,
            sources=document_source_filters or None,
        )
        print(f"[QUERY] Retrieved {len(candidates)} candidate chunks")

        final_chunks = rerank_chunks(
            candidates,
            rewritten_query,
            source_filters,
            request.selected_documents,
            request.depth,
        )
        print(f"[QUERY] Kept {len(final_chunks)} reranked chunks")

        answer, sources = generate_ai_response(request.query, final_chunks, history, case_summary)

        supabase.table("messages").insert({
            "case_id": case_id,
            "role": "advisor",
            "content": request.query,
        }).execute()
        supabase.table("messages").insert({
            "case_id": case_id,
            "role": "assistant",
            "content": answer,
        }).execute()

        message_count_res = (
            supabase.table("messages")
            .select("id", count="exact")
            .eq("case_id", case_id)
            .execute()
        )
        total_messages = message_count_res.count

        if total_messages > 0 and total_messages % 8 == 0:
            recent_msgs_res = (
                supabase.table("messages")
                .select("role", "content")
                .eq("case_id", case_id)
                .order("created_at", desc=True)
                .limit(8)
                .execute()
            )
            recent_msgs = recent_msgs_res.data[::-1]
            new_summary = generate_case_summary(recent_msgs, case_summary)
            supabase.table("cases").update({"summary": new_summary}).eq("id", case_id).execute()
            print(f"[Summary Generated] Case {case_id} at message count: {total_messages}")

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_documents": len(final_chunks),
            "persistent_history_count": len(history) + 2,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unhandled exception in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------------------------------------------------------------------------
# Chat title endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat/title")
def generate_title(payload: TitleRequest):
    try:
        prompt = (
            f"Summarise this message as a 1-6 word conversation title. "
            f"Reply with ONLY the title - no punctuation, no quotes, no explanation.\n\n"
            f"{payload.message[:500]}"
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        title = (response.text or "").strip().strip('"').strip("'")
        return {"title": title}
    except Exception:
        words = payload.message.strip().split()
        return {"title": " ".join(words[:4])}


# ---------------------------------------------------------------------------
# Notes endpoints
# ---------------------------------------------------------------------------

@app.post("/api/notes/suggest", response_model=SuggestResponse)
def suggest_notes(payload: SuggestRequest):
    if not payload.fragments:
        return SuggestResponse(suggestions=[])

    fragments_list = "\n".join(
        f'{i + 1}. "{f}"' for i, f in enumerate(payload.fragments)
    )
    context_line = f"Case context: {payload.context}\n\n" if payload.context else ""

    prompt = f"""{context_line}A Citizens Advice caseworker is taking rapid notes during a phone call. \
They have jotted down these short fragments:

{fragments_list}

For each fragment, suggest the most likely completing phrase (1-3 words) that makes the note clear \
in a Citizens Advice housing, benefits, employment, or family law context.

Return ONLY a valid JSON array - no markdown, no explanation. Each object must have:
- "fragment": the original fragment exactly as given
- "suggestion": 1-3 completing words (null if the fragment is already clear on its own)
- "full": the complete phrase (fragment + suggestion, or just fragment if suggestion is null)

Example: [{{"fragment": "2 years", "suggestion": "tenancy", "full": "2 years tenancy"}}]"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = strip_fences(response.text or "")
        data = json.loads(raw.strip())
        suggestions = [
            NoteSuggestion(
                fragment=item["fragment"],
                suggestion=item.get("suggestion"),
                full=item["full"],
            )
            for item in data
        ]
        return SuggestResponse(suggestions=suggestions)
    except Exception:
        return SuggestResponse(
            suggestions=[
                NoteSuggestion(fragment=f, suggestion=None, full=f)
                for f in payload.fragments
            ]
        )


@app.get("/api/notes/{chat_id}")
def get_notes(chat_id: str):
    res = supabase.table("cases").select("notes").eq("id", chat_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Case not found")
    notes_raw = res.data[0].get("notes")
    notes = json.loads(notes_raw) if notes_raw else []
    return {"notes": notes}


@app.put("/api/notes/{chat_id}")
def save_notes(chat_id: str, payload: SaveNotesRequest):
    res = supabase.table("cases").select("id").eq("id", chat_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Case not found")
    supabase.table("cases").update({"notes": json.dumps(payload.notes)}).eq("id", chat_id).execute()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/signup", response_model=UserResponse)
def signup(payload: SignupRequest):
    existing = supabase.table("users").select("id").eq("email", payload.email).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_pw = pwd_context.hash(payload.password)
    new_user = {
        "id": str(uuid.uuid4()),
        "email": payload.email,
        "name": payload.name or payload.email.split("@")[0],
        "hashed_password": hashed_pw,
        "role": "advisor",
    }
    res = supabase.table("users").insert(new_user).execute()
    user = res.data[0]
    return UserResponse(id=user["id"], email=user["email"], name=user.get("name"), role=user["role"])


@app.post("/api/auth/login", response_model=UserResponse)
def login(payload: LoginRequest):
    res = supabase.table("users").select("*").eq("email", payload.email).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = res.data[0]
    hashed = user.get("hashed_password")
    if not hashed or not pwd_context.verify(payload.password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return UserResponse(id=user["id"], email=user["email"], name=user.get("name"), role=user["role"])


@app.post("/api/auth/sync", response_model=UserResponse)
def sync_user(payload: SyncUserRequest):
    res = supabase.table("users").select("*").eq("email", payload.email).execute()

    if res.data:
        user = res.data[0]
    else:
        new_user = {
            "id": str(uuid.uuid4()),
            "email": payload.email,
            "name": payload.name,
            "google_id": payload.google_id,
            "role": "advisor",
        }
        insert_res = supabase.table("users").upsert(new_user).execute()
        user = insert_res.data[0]

    return UserResponse(id=user["id"], email=user["email"], name=user.get("name"), role=user["role"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}
