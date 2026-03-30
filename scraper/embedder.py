"""
embedder.py
-----------
Encodes all chunks from output_files/chunked_data.json using Sentence
Transformers and upserts them into the Supabase `chunks` table (pgvector).

Chunks are upserted (not inserted) on chunk_id, so re-running after a
weekly re-scrape only updates changed content.

Prerequisites:
    - Supabase `chunks` table created (see schema below)
    - SUPABASE_URL and SUPABASE_KEY set in scraper/.env

Required Supabase schema:
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE chunks (
        id           BIGSERIAL PRIMARY KEY,
        chunk_id     TEXT UNIQUE NOT NULL,
        source_url   TEXT NOT NULL,
        source       TEXT,
        category     TEXT,
        last_scraped TIMESTAMPTZ,
        text         TEXT NOT NULL,
        embedding    VECTOR(384)
    );

    CREATE INDEX ON chunks USING hnsw (embedding vector_l2_ops);

Usage:
    python embedder.py

    # Only embed chunks from a specific category (useful for weekly updates)
    python embedder.py --category benefits

    # Adjust batch size if running on limited memory
    python embedder.py --batch-size 64
"""

import json
import os
import argparse
from datetime import timezone

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILE  = "output_files/chunked_data.json"
MODEL_NAME  = "all-MiniLM-L6-v2"
BATCH_SIZE  = 128   # chunks to embed and upsert per batch

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# ---------------------------------------------------------------------------
# Embedding + Upsert
# ---------------------------------------------------------------------------

def upsert_batch(supabase: Client, batch: list[dict]) -> None:
    """Upserts a batch of chunk records into the Supabase chunks table."""
    supabase.table("chunks").upsert(batch, on_conflict="chunk_id").execute()


def embed_and_upload(chunks: list[dict], batch_size: int) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    total = len(chunks)
    print(f"Embedding and upserting {total} chunks in batches of {batch_size}...\n")

    for batch_start in range(0, total, batch_size):
        batch_chunks = chunks[batch_start: batch_start + batch_size]

        texts = [c["text"] for c in batch_chunks]
        embeddings = model.encode(texts, show_progress_bar=False)

        records = []
        for chunk, embedding in zip(batch_chunks, embeddings):
            records.append({
                "chunk_id":    chunk["chunk_id"],
                "source_url":  chunk["source_url"],
                "source":      chunk.get("source", "unknown"),
                "category":    chunk.get("category", "unknown"),
                "last_scraped": chunk.get("last_scraped"),
                "text":        chunk["text"],
                "embedding":   embedding.tolist(),
            })

        upsert_batch(supabase, records)

        batch_end = min(batch_start + batch_size, total)
        print(f"  Upserted {batch_end}/{total} chunks")

    print(f"\nDone. {total} chunks stored in Supabase.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Embed chunks and upsert to Supabase pgvector")
    parser.add_argument("--input", type=str, default=INPUT_FILE,
                        help=f"Path to chunked_data.json (default: {INPUT_FILE})")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"Chunks per batch (default: {BATCH_SIZE})")
    parser.add_argument("--category", type=str, default=None,
                        help="Only embed chunks matching this category (e.g. 'benefits')")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' not found. Run chunker.py first.")
        return

    with open(args.input, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if args.category:
        chunks = [c for c in chunks if c.get("category") == args.category]
        print(f"Filtered to {len(chunks)} chunks in category '{args.category}'")

    if not chunks:
        print("No chunks to process.")
        return

    embed_and_upload(chunks, args.batch_size)


if __name__ == "__main__":
    main()
