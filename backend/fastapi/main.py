from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import requests
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Check your .env file!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

class QueryRequest(BaseModel):
    query: str
    depth: str = "Standard"


def retrieve_chunks(query: str, top_k: int = 5) -> list[dict]:
    """Embeds the query and retrieves the top_k most similar chunks from pgvector."""
    embedding = model.encode(query).tolist()

    result = supabase.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
    }).execute()

    return result.data or []


def generate_ai_response(user_query: str, retrieved_chunks: list[dict], history: list[dict]) -> str:
    context = "\n\n".join([doc["text"] for doc in retrieved_chunks])

    history_str = ""
    for entry in history:
        speaker = "User" if entry["role"] == "advisor" else "AI"
        history_str += f"{speaker}: {entry['content']}\n"

    prompt = f"""You are a professional advisor for Citizens Advice.
Use the following context and conversation history to answer the user's question.

History:
{history_str}

Context:
{context}

Question: {user_query}
Helpful Answer:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:3b", "prompt": prompt, "stream": False}
        )
        return response.json().get("response", "Error generating response.")
    except Exception:
        return "Local AI (Ollama) is not responding. Is it running?"


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
    case_check = supabase.table("cases").select("id").eq("id", case_id).execute()
    if not case_check.data:
        raise HTTPException(status_code=404, detail="Case not found in Supabase database.")

    # Retrieve relevant chunks from pgvector
    retrieved = retrieve_chunks(request.query)

    # Fetch recent conversation history
    history_res = (
        supabase.table("messages")
        .select("role", "content")
        .eq("case_id", case_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    history = history_res.data[::-1]

    answer = generate_ai_response(request.query, retrieved, history)

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

    return {
        "answer": answer,
        "sources": list(set([r["source_url"] for r in retrieved])),
        "persistent_history_count": len(history) + 2,
    }
