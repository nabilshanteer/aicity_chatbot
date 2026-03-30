import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def build_vector_database(input_filename="output_files/chunked_data.json", index_filename="output_files/faiss_index.bin", mapping_filename="output_files/chunk_mapping.json"):
    """
    Reads chunked text, converts it to vector embeddings, and stores it in a FAISS index.
    """
    print("Loading Sentence Transformer model (this may take a moment the first time)...")
    # 'all-MiniLM-L6-v2' is a fast, lightweight, and highly effective model for local PoCs
    model = SentenceTransformer('all-MiniLM-L6-v2')

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {input_filename}. Run the chunker first!")
        return

    if not chunks:
        print("No chunks found in the input file.")
        return

    print(f"Generating embeddings for {len(chunks)} chunks...")
    
    # Extract just the text to feed into the model
    texts = [chunk['text'] for chunk in chunks]
    
    # Convert text to vector embeddings
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # FAISS requires the embeddings to be a specific numpy data type (float32)
    embeddings = np.array(embeddings).astype('float32')

    # Create the FAISS index
    # The dimension (384) must match the output size of our specific SentenceTransformer model
    dimension = embeddings.shape[1] 
    index = faiss.IndexFlatL2(dimension)
    
    # Add our embeddings to the database
    index.add(embeddings)
    
    # Save the FAISS index to disk
    faiss.write_index(index, index_filename)
    
    # IMPORTANT: FAISS only stores numbers. We need to save a mapping file so we know 
    # which chunk of text belongs to which vector ID.
    with open(mapping_filename, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4) 

    print(f"\nSuccess! FAISS index created with {index.ntotal} vectors.")
    print(f"Saved database to: {index_filename}")
    print(f"Saved text mapping to: {mapping_filename}")

# ==========================================
# Run the Embedder
# ==========================================
if __name__ == "__main__":
    build_vector_database()