"""
chunker.py
----------
Reads output_files/scraped_data.json, converts structured page sections into
heading-aware chunks, and writes output_files/chunked_data.json.

Usage:
    python chunker.py
"""

import json
import os
import re


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILE = "output_files/scraped_data.json"
OUTPUT_FILE = "output_files/chunked_data.json"

TARGET_CHUNK_LENGTH = 600
HARD_MAX_CHUNK_LENGTH = 900
OVERLAP_CHARS = 120
MIN_CHUNK_LENGTH = 80


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def parent_heading_path(path: str) -> str:
    if " > " not in path:
        return ""
    return path.rsplit(" > ", 1)[0]


def split_oversized_section(text: str) -> list[str]:
    """
    Splits a long section into overlapping sentence-based chunks while staying
    within a single heading boundary.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks = []
    i = 0

    while i < len(sentences):
        current = ""
        j = i

        while j < len(sentences):
            candidate = (current + " " + sentences[j]).strip() if current else sentences[j]
            if len(candidate) > TARGET_CHUNK_LENGTH and current:
                break
            current = candidate
            j += 1
            if len(current) >= TARGET_CHUNK_LENGTH:
                break

        if not current:
            current = sentences[i]
            j = i + 1

        chunks.append(current.strip())

        if j >= len(sentences):
            break

        overlap_length = 0
        next_start = j
        while next_start > i:
            overlap_length += len(sentences[next_start - 1]) + 1
            next_start -= 1
            if overlap_length >= OVERLAP_CHARS:
                break

        if next_start == i:
            i = j
        else:
            i = next_start

    return chunks


def normalise_sections(doc: dict) -> list[dict]:
    sections = doc.get("sections") or []

    if not sections and doc.get("content"):
        sections = [{
            "section_order": 0,
            "heading": doc.get("page_title") or "Page Content",
            "heading_level": 1,
            "heading_path": doc.get("page_title") or "Page Content",
            "text": doc.get("content", ""),
        }]

    cleaned = []
    for section in sections:
        text = normalize_text(section.get("text", ""))
        if not text:
            continue
        cleaned.append({
            "section_order": section.get("section_order", len(cleaned)),
            "heading": section.get("heading") or doc.get("page_title") or "Page Content",
            "heading_level": section.get("heading_level", 1),
            "heading_path": section.get("heading_path") or section.get("heading") or doc.get("page_title") or "Page Content",
            "text": text,
        })

    merged = []
    i = 0
    while i < len(cleaned):
        current = dict(cleaned[i])

        if len(current["text"]) < MIN_CHUNK_LENGTH and i + 1 < len(cleaned):
            next_section = dict(cleaned[i + 1])
            if parent_heading_path(current["heading_path"]) == parent_heading_path(next_section["heading_path"]):
                next_section["text"] = f"{current['text']} {next_section['text']}".strip()
                cleaned[i + 1] = next_section
                i += 1
                continue

        if len(current["text"]) >= MIN_CHUNK_LENGTH:
            merged.append(current)
        i += 1

    for order, section in enumerate(merged):
        section["section_order"] = order

    return merged


def chunk_document(doc: dict) -> list[dict]:
    source_url = doc.get("source_url", "unknown")
    source = doc.get("source", "unknown")
    category = doc.get("category", "unknown")
    last_scraped = doc.get("last_scraped", "unknown")
    page_title = doc.get("page_title") or source_url

    sections = normalise_sections(doc)
    chunks = []

    for section in sections:
        section_text = section["text"]
        if len(section_text) <= HARD_MAX_CHUNK_LENGTH:
            text_chunks = [section_text]
        else:
            text_chunks = split_oversized_section(section_text)

        for chunk_order, chunk_text in enumerate(text_chunks):
            chunk_text = normalize_text(chunk_text)
            if len(chunk_text) < MIN_CHUNK_LENGTH:
                continue

            chunks.append({
                "chunk_id": f"{source_url}#s{section['section_order']}-c{chunk_order}",
                "source_url": source_url,
                "source": source,
                "category": category,
                "last_scraped": last_scraped,
                "page_title": page_title,
                "heading": section["heading"],
                "heading_level": section["heading_level"],
                "heading_path": section["heading_path"],
                "section_order": section["section_order"],
                "chunk_order": chunk_order,
                "text": chunk_text,
            })

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
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
    print(f"Saved to: {output_filename}")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    process_scraped_file(INPUT_FILE, OUTPUT_FILE)
