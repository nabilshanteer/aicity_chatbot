import json
import uuid
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.genai as genai
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager
from supabase import create_client, Client
from passlib.context import CryptContext

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Check your .env file!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print("Starting server: Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
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

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1"},
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    depth: str = "Standard"


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


class SummariseRequest(BaseModel):
    transcript: str


class SummaryPoint(BaseModel):
    point: str
    excerpt: str


class SummariseResponse(BaseModel):
    points: list[SummaryPoint]


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

def retrieve_chunks(query: str, top_k: int = 5) -> list[dict]:
    embedding = model.encode(query).tolist()
    result = supabase.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
    }).execute()
    return result.data or []


def generate_ai_response(user_query, retrieved_chunks, history, case_summary=None):
    context = "\n\n".join([
        f"[Source: {doc.get('source_url', 'Unknown')}]\n{doc['text']}"
        for doc in retrieved_chunks
    ])
    sources = [doc.get('source_url', 'Unknown') for doc in retrieved_chunks if doc.get('source_url')]

    history_str = ""
    for entry in history:
        speaker = "User" if entry['role'] == "advisor" else "Advisor"
        history_str += f"{speaker}: {entry['content']}\n"

    summary_context = f"\n[Case Summary]\n{case_summary}\n" if case_summary else ""

    prompt = f"""You are a professional advisor for Citizens Advice. Use the provided context and conversation history to answer the user's question accurately and helpfully.

IMPORTANT: Always cite your sources from the provided context. When referencing information, include the source URL in square brackets like this: [Source: URL]

If you don't have relevant information in the context, say so explicitly.
{summary_context}
History:
{history_str}

Relevant Information:
{context}

User Question: {user_query}"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text, sources
    except Exception as e:
        return f"Error generating response: {str(e)}", sources


def generate_case_summary(messages, previous_summary=None):
    messages_str = ""
    for entry in messages:
        speaker = "User" if entry['role'] == "advisor" else "Advisor"
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
        return response.text.strip()
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

        case_res = supabase.table("cases").select("id", "summary").eq("id", case_id).execute()
        if not case_res.data:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in database.")
        case_summary = case_res.data[0].get("summary")

        print(f"[QUERY] Encoding question for vector search...")
        retrieved = retrieve_chunks(request.query)
        print(f"[QUERY] Retrieved {len(retrieved)} documents")

        history_res = (
            supabase.table("messages")
            .select("role", "content")
            .eq("case_id", case_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        history = history_res.data[::-1] if history_res.data else []
        print(f"[QUERY] Retrieved {len(history)} messages from history")

        print(f"[QUERY] Generating response with Gemini...")
        answer, sources = generate_ai_response(request.query, retrieved, history, case_summary)
        print(f"[QUERY] Generated response successfully")

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
        print(f"[QUERY] Saved messages successfully")

        message_count_res = (
            supabase.table("messages")
            .select("id", count="exact")
            .eq("case_id", case_id)
            .execute()
        )
        total_messages = message_count_res.count
        print(f"[QUERY] Total messages in conversation: {total_messages}")

        if total_messages > 0 and total_messages % 8 == 0:
            print(f"[QUERY] Generating summary at message {total_messages}...")
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

        print(f"[QUERY] Query completed successfully")
        return {
            "answer": answer,
            "sources": list(set(sources)),
            "retrieved_documents": len(retrieved),
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
            f"Reply with ONLY the title — no punctuation, no quotes, no explanation.\n\n"
            f"{payload.message[:500]}"
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        title = response.text.strip().strip('"').strip("'")
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
        f"{i + 1}. \"{f}\"" for i, f in enumerate(payload.fragments)
    )
    context_line = f"Case context: {payload.context}\n\n" if payload.context else ""

    prompt = f"""{context_line}A Citizens Advice caseworker is taking rapid notes during a phone call. \
They have jotted down these short fragments:

{fragments_list}

For each fragment, suggest the most likely completing phrase (1–3 words) that makes the note clear \
in a Citizens Advice housing, benefits, employment, or family law context.

Return ONLY a valid JSON array — no markdown, no explanation. Each object must have:
- "fragment": the original fragment exactly as given
- "suggestion": 1–3 completing words (null if the fragment is already clear on its own)
- "full": the complete phrase (fragment + suggestion, or just fragment if suggestion is null)

Example: [{{"fragment": "2 years", "suggestion": "tenancy", "full": "2 years tenancy"}}]"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
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


@app.post("/api/notes/summarise", response_model=SummariseResponse)
def summarise_transcript(payload: SummariseRequest):
    if not payload.transcript.strip():
        return SummariseResponse(points=[])

    prompt = f"""You are assisting a Citizens Advice caseworker who has just finished a client call. \
The following is a raw speech transcript from that call.

Summarise the key points into a concise list. For each point also extract a short verbatim excerpt \
from the transcript that directly supports it. Each point must be 1–2 sentences, factual, and written \
in plain English. Ignore filler words, repetition, and mid-sentence thinking pauses. Focus only on \
meaningful information relevant to a Citizens Advice case.

Return ONLY a valid JSON array — no markdown, no explanation. Each object must have:
- "point": 1–2 sentence summary of the key point
- "excerpt": a short verbatim snippet (1–2 phrases) from the transcript that led to this point

Example: [{{"point": "Client has rented for 3 years with no written tenancy agreement.", "excerpt": "ive been there about three years and never had anything in writing"}}]

Transcript: {payload.transcript}"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return SummariseResponse(points=[
            SummaryPoint(point=item["point"], excerpt=item.get("excerpt", ""))
            for item in data if isinstance(item, dict) and "point" in item
        ])
    except Exception:
        return SummariseResponse(points=[
            SummaryPoint(point=payload.transcript.strip(), excerpt="")
        ])


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
        insert_res = supabase.table("users").insert(new_user).execute()
        user = insert_res.data[0]

    return UserResponse(id=user["id"], email=user["email"], name=user.get("name"), role=user["role"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}
