"""
retreiver.py
------------
Interactive CLI for testing retrieval from the Supabase pgvector database.
Useful for verifying the embedder ran correctly and that search results
look sensible before running the full backend.

Usage:
    python retreiver.py
"""

import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODEL_NAME   = "all-MiniLM-L6-v2"


def search(query: str, supabase: Client, model: SentenceTransformer, top_k: int = 3) -> list[dict]:
    embedding = model.encode(query).tolist()
    result = supabase.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
        "source_urls": None,
        "sources": None,
        "categories": None,
    }).execute()
    return result.data or []


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
        exit(1)

    print("Loading model and connecting to Supabase...")
    model    = SentenceTransformer(MODEL_NAME)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Quick sanity check — count chunks in DB
    count_res = supabase.table("chunks").select("id", count="exact").execute()
    total     = count_res.count or 0
    print(f"Connected. {total} chunks in database.")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Ask a Citizens Advice question: ").strip()

        if query.lower() == "exit":
            print("Closing search...")
            break

        if not query:
            continue

        results = search(query, supabase, model, top_k=3)

        if not results:
            print("No results found.\n")
            continue

        print(f"\n--- Top {len(results)} Results ---")
        for i, res in enumerate(results, start=1):
            print(f"\nResult {i}  (similarity: {float(res.get('similarity', 0.0)):.4f})")
            print(f"Source  : {res.get('source_url', 'unknown')}")
            print(f"Category: {res.get('category', 'unknown')}")
            print(f"Heading : {res.get('heading_path') or res.get('page_title', 'unknown')}")
            print(f"Text    : {res.get('text', '')[:300]}...")
            print("-" * 40)
