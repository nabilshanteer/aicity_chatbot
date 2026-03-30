from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import faiss
import json
import numpy as np
import uuid
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager
from supabase import create_client, Client

# Load the variables from the .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Safety check: Stop the server if keys are missing
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Check your .env file!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Global Variables ---
model = None
index = None
mapping = None
case_sessions = {} # This is your temporary memory bank

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, index, mapping
    print("Starting server: Loading AI Model and Database...")
    try:
        # Get the project root directory dynamically
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        index_path = os.path.join(project_root, "scraper", "output_files", "faiss_index.bin")
        mapping_path = os.path.join(project_root, "scraper", "output_files", "chunk_mapping.json")
        
        print(f"Loading FAISS index from: {index_path}")
        print(f"Loading mapping from: {mapping_path}")
        
        index = faiss.read_index(index_path)
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"System ready! Loaded {index.ntotal} documents.")
    except Exception as e:
        print(f"Error loading system: {e}")
        import traceback
        traceback.print_exc()
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

# --- HELPER: Talk to Claude ---
def generate_ai_response(user_query, retrieved_chunks, history, case_summary=None):
    # Combine retrieved text for context and extract sources
    context = "\n\n".join([f"[Source: {doc.get('source_url', 'Unknown')}]\n{doc['text']}" for doc in retrieved_chunks])
    sources = [doc.get('source_url', 'Unknown') for doc in retrieved_chunks if doc.get('source_url')]

    # Format the Supabase history to keep the AI on track
    history_str = ""
    for entry in history:
        speaker = "User" if entry['role'] == "advisor" else "Advisor"
        history_str += f"{speaker}: {entry['content']}\n"

    # Include case summary if it exists
    summary_context = ""
    if case_summary:
        summary_context = f"\n[Case Summary]\n{case_summary}\n"

    system_prompt = """You are a professional advisor for Citizens Advice. Use the provided context and conversation history to answer the user's question accurately and helpfully.

IMPORTANT: Always cite your sources from the provided context. When referencing information, include the source URL in square brackets [like this].
Format citations as: [Source: URL] at the end of relevant statements.

If you don't have relevant information in the context, say so explicitly."""

    user_message = f"""{summary_context}
Conversation History:
{history_str}

Relevant Information:
{context}

User Question: {user_query}"""

    try:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        return response.content[0].text, sources
    except Exception as e:
        return f"Error generating response: {str(e)}", sources

# --- HELPER: Generate Case Summary ---
def generate_case_summary(messages, previous_summary=None):
    """
    Generate a compact summary of recent messages, optionally incorporating previous summary context.
    Called every 8 messages to compress conversation history.
    """
    # Format the messages
    messages_str = ""
    for entry in messages:
        speaker = "User" if entry['role'] == "advisor" else "Advisor"
        messages_str += f"{speaker}: {entry['content']}\n"

    # Build prompt with previous context if available
    previous_context = f"\n\nPrevious Summary for Context:\n{previous_summary}" if previous_summary else ""

    summarization_prompt = f"""Create a concise summary of this Citizens Advice case conversation.
Capture key issues, questions asked, advice given, and any important context or decisions.
Keep it brief but comprehensive (2-3 sentences max).{previous_context}

Recent Conversation:
{messages_str}"""

    try:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": summarization_prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Unable to generate summary: {str(e)}"

# --- ENDPOINT 1: Start a Case ---
@app.post("/api/cases/start")
async def start_case():
    try:
        # In the current Python SDK, insert() returns the data automatically
        # You do NOT need .select() here
        response = supabase.table("cases").insert({}).execute()
        
        # Access the data from the response object
        if response.data and len(response.data) > 0:
            new_case_id = response.data[0]['id']
            return {"case_id": new_case_id}
        else:
            raise HTTPException(status_code=500, detail="Supabase inserted the row but returned no data.")
            
    except Exception as e:
        print(f"Supabase Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT 2: Search & Generate with Memory ---
@app.post("/api/cases/{case_id}/query")
async def ask_question(case_id: str, request: QueryRequest):
    try:
        print(f"[QUERY] Received query for case_id: {case_id}")
        print(f"[QUERY] Question: {request.query}")
        
        # 1. Verification: Does the case exist in Supabase?
        try:
            case_check = supabase.table("cases").select("id").eq("id", case_id).execute()
            print(f"[QUERY] Case check result: {case_check.data}")
            
            if not case_check.data:
                raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in database.")
        except Exception as e:
            print(f"[ERROR] Supabase case lookup failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # 2. Retrieval (Your existing FAISS search)
        print(f"[QUERY] Encoding question for vector search...")
        query_vec = np.array(model.encode([request.query])).astype('float32')
        _, indices = index.search(query_vec, 5)
        retrieved = [mapping[idx] for idx in indices[0] if idx != -1]
        print(f"[QUERY] Retrieved {len(retrieved)} documents")

        # 3. Fetch recent history from Supabase (instead of a local dict)
        try:
            history_res = supabase.table("messages").select("role", "content").eq("case_id", case_id).order("created_at", desc=True).limit(5).execute()
            history = history_res.data[::-1] if history_res.data else []  # Reverse to get chronological order
            print(f"[QUERY] Retrieved {len(history)} messages from history")
        except Exception as e:
            print(f"[WARNING] Failed to fetch history: {str(e)}, continuing without history")
            history = []
        
        # 3b. Fetch case summary if it exists (to include in context)
        try:
            case_data = supabase.table("cases").select("summary").eq("id", case_id).execute()
            case_summary = None
            if case_data.data and case_data.data[0].get("summary"):
                case_summary = case_data.data[0]["summary"]
                print(f"[QUERY] Found case summary")
        except Exception as e:
            print(f"[WARNING] Failed to fetch case summary: {str(e)}")
            case_summary = None

        # 4. Generate AI Answer with Claude
        print(f"[QUERY] Generating response with Claude...")
        answer, sources = generate_ai_response(request.query, retrieved, history, case_summary)
        print(f"[QUERY] Generated response successfully")

        # 5. PERMANENT SAVE: Push the Q&A to Supabase
        try:
            print(f"[QUERY] Saving user question to database...")
            supabase.table("messages").insert({
                "case_id": case_id, 
                "role": "advisor", 
                "content": request.query
            }).execute()
            
            print(f"[QUERY] Saving assistant response to database...")
            supabase.table("messages").insert({
                "case_id": case_id, 
                "role": "assistant", 
                "content": answer,
                "sources": sources
            }).execute()
            print(f"[QUERY] Saved messages successfully")
        except Exception as e:
            print(f"[ERROR] Failed to save messages: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save messages: {str(e)}")
        
        # 6. CHECK: Has the conversation hit 8 new messages? If so, generate a summary
        try:
            message_count_res = supabase.table("messages").select("id", count="exact").eq("case_id", case_id).execute()
            total_messages = message_count_res.count
            print(f"[QUERY] Total messages in conversation: {total_messages}")
            
            if total_messages > 0 and total_messages % 8 == 0:
                print(f"[QUERY] Generating summary at message {total_messages}...")
                recent_msgs_res = supabase.table("messages").select("role", "content").eq("case_id", case_id).order("created_at", desc=True).limit(8).execute()
                recent_msgs = recent_msgs_res.data[::-1]  # Chronological order
                
                prev_summary = case_summary
                new_summary = generate_case_summary(recent_msgs, prev_summary)
                
                supabase.table("cases").update({"summary": new_summary}).eq("id", case_id).execute()
                print(f"[Summary Generated] Case {case_id} at message count: {total_messages}")
        except Exception as e:
            print(f"[WARNING] Summary generation failed: {str(e)}")

        print(f"[QUERY] Query completed successfully")
        return {
            "answer": answer,
            "sources": list(set(sources)),
            "retrieved_documents": len(retrieved),
            "persistent_history_count": len(history) + 2
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unhandled exception in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")