from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import faiss
import json
import numpy as np
import uuid
import requests
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
        model = SentenceTransformer('all-MiniLM-L6-v2')
        # Adjust these paths to where your files actually are
        index = faiss.read_index("../../scraper/output_files/faiss_index.bin")
        with open("../../scraper/output_files/chunk_mapping.json", 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"System ready! Loaded {index.ntotal} documents.")
    except Exception as e:
        print(f"Error loading system: {e}")
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

# --- HELPER: Talk to Ollama ---
def generate_ai_response(user_query, retrieved_chunks, history):
    # Combine retrieved text for context
    context = "\n\n".join([doc['text'] for doc in retrieved_chunks])
    
    # Format the Supabase history to keep the AI on track
    history_str = ""
    for entry in history:
        # Check if the role is 'advisor' or 'assistant' and format accordingly
        speaker = "User" if entry['role'] == "advisor" else "AI"
        history_str += f"{speaker}: {entry['content']}\n"

    prompt = f"""
    You are a professional advisor for Citizens Advice. 
    Use the following context and conversation history to answer the user's question.
    
    History:
    {history_str}

    Context:
    {context}

    Question: {user_query}
    Helpful Answer:"""

    try:
        response = requests.post("http://localhost:11434/api/generate", 
            json={"model": "llama3.2:3b", "prompt": prompt, "stream": False})
        return response.json().get("response", "Error generating response.")
    except:
        return "Local AI (Ollama) is not responding. Is it running?"

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
    # 1. Verification: Does the case exist in Supabase?
    case_check = supabase.table("cases").select("id").eq("id", case_id).execute()
    
    if not case_check.data:
        # Changed the error message slightly so we know for sure this code is running!
        raise HTTPException(status_code=404, detail="Case not found in Supabase database.")

    # 2. Retrieval (Your existing FAISS search)
    query_vec = np.array(model.encode([request.query])).astype('float32')
    _, indices = index.search(query_vec, 5)
    retrieved = [mapping[idx] for idx in indices[0] if idx != -1]

    # 3. Fetch recent history from Supabase (instead of a local dict)
    history_res = supabase.table("messages").select("role", "content").eq("case_id", case_id).order("created_at", desc=True).limit(5).execute()
    history = history_res.data[::-1] # Reverse to get chronological order

    # 4. Generate AI Answer (Ollama)
    answer = generate_ai_response(request.query, retrieved, history)

    # 5. PERMANENT SAVE: Push the Q&A to Supabase
    # Save user question
    supabase.table("messages").insert({
        "case_id": case_id, 
        "role": "advisor", 
        "content": request.query
    }).execute()
    
    # Save AI response
    supabase.table("messages").insert({
        "case_id": case_id, 
        "role": "assistant", 
        "content": answer
    }).execute()

    return {
        "answer": answer,
        "sources": list(set([r['source_url'] for r in retrieved])),
        "persistent_history_count": len(history) + 2
    }