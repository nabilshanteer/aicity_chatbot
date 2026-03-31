from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.genai as genai
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
    embedding = model.encode(query).tolist()
    result = supabase.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
    }).execute()
    return result.data or []


gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1"},
)


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
