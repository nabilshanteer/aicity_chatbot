from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Global variables to hold our AI model and database in memory
model = None
index = None
mapping = None

# 1. The Modern Lifespan Manager (Handles Startup and Shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, index, mapping
    print("Starting server: Loading AI Model and Database into memory...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        # Note: If you moved your files, adjust these paths (e.g., "../faiss_index.bin")
        index = faiss.read_index("../../scraper/output_files/faiss_index.bin")
        with open("../../scraper/output_files/chunk_mapping.json", 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"System ready! Loaded {index.ntotal} documents.")
    except Exception as e:
        print(f"Error loading system: {e}")
        
    yield  # Tells FastAPI: "Pause here and run the web server"
    
    print("Shutting down server and clearing memory...")
    model = None
    index = None
    mapping = None

# 2. Initialize the FastAPI app
app = FastAPI(title="Citizens Advice AI Backend", lifespan=lifespan)

# Allow the React frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Define the data format we expect from the frontend
class QueryRequest(BaseModel):
    query: str
    depth: str = "Standard" 

# 4. A friendly homepage so you don't get a 404 Error
@app.get("/")
async def root():
    return {"message": "Citizens Advice AI Backend is running! Go to /docs to test the API."}

# 5. The Core Search Endpoint
@app.post("/api/search")
async def search(request: QueryRequest):
    if not index or not mapping:
        raise HTTPException(status_code=500, detail="Database not loaded properly.")

    # Adjust the number of retrieved documents based on the spec's Depth Toggle
    depth_map = {"Quick": 3, "Standard": 5, "Deep": 7}
    top_k = depth_map.get(request.depth, 5)

    # Convert query to vector and search FAISS
    query_vector = model.encode([request.query])
    query_vector = np.array(query_vector).astype('float32')
    distances, indices = index.search(query_vector, top_k)

    results = []
    for i, vector_id in enumerate(indices[0]):
        if vector_id != -1 and vector_id < len(mapping):
            match = mapping[vector_id]
            results.append({
                "score": float(distances[0][i]),
                "text": match['text'],
                "source_url": match['source_url']
            })

    return {
        "user_query": request.query,
        "search_depth": request.depth,
        "retrieved_context": results
    }