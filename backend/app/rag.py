"""
RAG (Retrieval-Augmented Generation) module.
Loads the sentence-transformer model once at startup, then exposes a
search() function that queries Supabase pgvector via the match_chunks RPC.
"""
import os
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client

_model = None
_supabase = None


def load():
    """Load the embedding model and Supabase client at startup."""
    global _model, _supabase

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[RAG] WARNING: Missing Supabase credentials. RAG disabled.")
        return

    try:
        print("[RAG] Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _supabase = create_client(supabase_url, supabase_key)
        print("[RAG] Ready — connected to Supabase pgvector.")
    except Exception as e:
        print(f"[RAG] ERROR during load: {e}. RAG will be disabled.")
        _model = None
        _supabase = None


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Encode query and return the top_k most relevant document chunks from pgvector.
    Returns an empty list if RAG is not loaded.
    """
    if _model is None or _supabase is None:
        return []

    embedding = _model.encode(query).tolist()
    result = _supabase.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
    }).execute()

    return result.data or []


def is_available() -> bool:
    return _model is not None and _supabase is not None
