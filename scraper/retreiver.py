import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def load_database(index_filename="output_files/faiss_index.bin", mapping_filename="output_files/chunk_mapping.json"):
    """Loads the FAISS index and the text mapping file from disk."""
    try:
        index = faiss.read_index(index_filename)
        with open(mapping_filename, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        return index, mapping
    except Exception as e:
        print(f"Error loading database: {e}")
        return None, None

def search_database(query, index, mapping, model, top_k=3):
    """
    Converts the user's query to a vector, searches FAISS, and retrieves the text.
    """
    # 1. Convert the text query into a mathematical vector
    query_vector = model.encode([query])
    query_vector = np.array(query_vector).astype('float32')

    # 2. Search FAISS for the closest matches
    # distances = how close the match is mathematically (lower is better)
    # indices = the ID numbers of the matching vectors
    distances, indices = index.search(query_vector, top_k)

    results = []
    # 3. Look up the actual text and metadata for the returned IDs
    for i, vector_id in enumerate(indices[0]):
        # FAISS returns -1 if it can't find enough matches
        if vector_id != -1 and vector_id < len(mapping): 
            match = mapping[vector_id]
            results.append({
                "score": float(distances[0][i]),
                "text": match['text'],
                "source_url": match['source_url'],
                "last_scraped": match['last_scraped']
            })
            
    return results

# ==========================================
# Run the Interactive Terminal Search
# ==========================================
if __name__ == "__main__":
    print("Loading AI model and database... (This takes a few seconds)")
    # We must use the exact same model we used to build the database
    model = SentenceTransformer('all-MiniLM-L6-v2')
    index, mapping = load_database()

    if index and mapping:
        print(f"\n✅ Database loaded successfully! ({index.ntotal} chunks available)")
        print("Type 'exit' to quit.")
        
        while True:
            user_query = input("\nAsk a Citizens Advice question: ")
            
            if user_query.lower() == 'exit':
                print("Closing search...")
                break
            
            # Perform the search (Quick Mode: top 3 results)
            results = search_database(user_query, index, mapping, model, top_k=3)
            
            print(f"\n--- Top {len(results)} Results ---")
            for i, res in enumerate(results):
                print(f"\nResult {i+1} (Distance Score: {res['score']:.2f})")
                print(f"Source: {res['source_url']}")
                print(f"Text: {res['text']}")
                print("-" * 40)