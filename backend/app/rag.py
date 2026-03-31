"""
RAG (Retrieval-Augmented Generation) module.
Loads the FAISS index and sentence-transformer model once at startup,
then exposes a search() function used by the cases query endpoint.
"""
import os
import json
import numpy as np

# Populated by load() at application startup
_model = None
_index = None
_mapping = None


def load():
    """Load the embedding model and FAISS index from disk."""
    global _model, _index, _mapping

    # Resolve paths relative to the project root (two levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/app/
    project_root = os.path.dirname(os.path.dirname(current_dir))  # citizen_chatbot/
    output_dir = os.path.join(project_root, "scraper", "output_files")

    index_path = os.path.join(output_dir, "faiss_index.bin")
    mapping_path = os.path.join(output_dir, "chunk_mapping.json")

    if not os.path.exists(index_path) or not os.path.exists(mapping_path):
        print(f"[RAG] WARNING: FAISS index or mapping not found at {output_dir}. RAG disabled.")
        return

    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        print("[RAG] Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")

        print(f"[RAG] Loading FAISS index from {index_path}...")
        _index = faiss.read_index(index_path)

        with open(mapping_path, "r", encoding="utf-8") as f:
            _mapping = json.load(f)

        print(f"[RAG] Ready — {_index.ntotal} documents indexed.")
    except Exception as e:
        print(f"[RAG] ERROR during load: {e}. RAG will be disabled.")
        _model = _index = _mapping = None


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Encode query and return the top_k most relevant document chunks.
    Returns an empty list if RAG is not loaded.
    """
    if _model is None or _index is None or _mapping is None:
        return []

    query_vec = np.array(_model.encode([query])).astype("float32")
    _, indices = _index.search(query_vec, top_k)
    return [_mapping[idx] for idx in indices[0] if idx != -1]


def is_available() -> bool:
    return _model is not None and _index is not None and _mapping is not None
