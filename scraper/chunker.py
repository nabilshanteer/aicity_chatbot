"""
chunker.py
----------
Reads output_files/scraped_data.json, splits each document into
overlapping text chunks, and writes output_files/chunked_data.json.

Overlap ensures that sentences spanning a chunk boundary are represented
in both adjacent chunks, so retrieval doesn't miss context at the edges.

Usage:
    python chunker.py
"""

import json
import re
import os


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILE  = "output_files/scraped_data.json"
OUTPUT_FILE = "output_files/chunked_data.json"

TARGET_CHUNK_LENGTH = 500   # target characters per chunk
OVERLAP_SENTENCES   = 2     # sentences to repeat at the start of each new chunk


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """Splits text into sentences on punctuation boundaries."""
    return [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]


def chunk_text(text: str, target_length: int = TARGET_CHUNK_LENGTH,
               overlap: int = OVERLAP_SENTENCES) -> list[str]:
    """
    Splits text into chunks of approximately target_length characters.
    Each chunk overlaps with the previous one by `overlap` sentences to
    avoid losing context at chunk boundaries.
    """
    if not text:
        return []

    sentences = split_sentences(text)
    chunks = []
    i = 0

    while i < len(sentences):
        current_chunk = ""
        j = i

        # Build chunk up to target length
        while j < len(sentences) and len(current_chunk) + len(sentences[j]) <= target_length + 100:
            current_chunk += sentences[j] + " "
            j += 1

        # If a single sentence exceeds target length, take it anyway
        if not current_chunk and i < len(sentences):
            current_chunk = sentences[i] + " "
            j = i + 1

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Step forward, stepping back by `overlap` sentences for the next chunk
        i = max(i + 1, j - overlap)

    return chunks


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def process_scraped_file(input_filename: str, output_filename: str) -> None:
    if not os.path.exists(input_filename):
        print(f"Error: '{input_filename}' not found. Run data_scraper.py first.")
        return

    with open(input_filename, "r", encoding="utf-8") as f:
        documents = json.load(f)

    if not documents:
        print("No documents found in input file.")
        return

    print(f"Chunking {len(documents)} documents...")

    all_chunks = []
    skipped = 0

    for doc in documents:
        text      = doc.get("content", "")
        source    = doc.get("source_url", "unknown")
        timestamp = doc.get("last_scraped", "unknown")
        source_type = doc.get("source", "unknown")
        category  = doc.get("category", "unknown")

        text_chunks = chunk_text(text)

        for i, chunk in enumerate(text_chunks):
            if len(chunk) < 50:
                skipped += 1
                continue

            all_chunks.append({
                "chunk_id":    f"{source}#chunk-{i}",
                "source_url":  source,
                "source":      source_type,
                "category":    category,
                "last_scraped": timestamp,
                "text":        chunk,
            })

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents "
          f"({skipped} short chunks discarded)")
    print(f"Saved to: {output_filename}")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    process_scraped_file(INPUT_FILE, OUTPUT_FILE)
