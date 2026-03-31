import json
import re
import os

def chunk_text(text, target_length=500):
    """
    Splits text into chunks of approximately the target length.
    It splits by sentences to avoid cutting off mid-thought (semantic chunking).
    """
    if not text:
        return []
        
    # Split text into sentences using regular expressions (looks for punctuation followed by a space)
    sentences = re.split(r'(?<=[.!?]) +', text)
    
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding the next sentence keeps us roughly around our target, add it
        if len(current_chunk) + len(sentence) <= target_length + 100: 
            current_chunk += sentence + " "
        else:
            # Otherwise, save the current chunk and start a new one
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            
    # Don't forget the last chunk!
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def process_multiple_files(input_filenames, output_filename="output_files/chunked_data.json"):
    """
    Reads multiple scraped JSON files, chunks the content, 
    and merges them into a single unified dataset.
    """
    all_chunks = []
    total_documents_processed = 0

    print(f"Starting unified chunking process for {len(input_filenames)} files...\n")

    for filename in input_filenames:
        if not os.path.exists(filename):
            print(f"  ✗ Skipping '{filename}' (File not found)")
            continue

        print(f"  Processing '{filename}'...")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                documents = json.load(f)
        except json.JSONDecodeError:
            print(f"  ✗ Error reading '{filename}' (Invalid JSON)")
            continue

        total_documents_processed += len(documents)

        for doc in documents:
            # Safely grab the text, falling back to an empty string if missing
            text = doc.get('content', '')
            source = doc.get('source_url', 'Unknown URL')
            timestamp = doc.get('last_scraped', 'Unknown Time')
            
            # Break the massive text into smaller pieces
            text_chunks = chunk_text(text)
            
            # Create a new record for EVERY chunk
            for i, chunk in enumerate(text_chunks):
                # Only keep chunks that have meaningful content
                if len(chunk) > 50: 
                    chunk_record = {
                        "chunk_id": f"{source}-chunk-{i}",
                        "source_url": source,
                        "last_scraped": timestamp,
                        "text": chunk
                    }
                    all_chunks.append(chunk_record)
                    
        print(f"  ✓ Finished '{filename}'")

    # Save the properly formatted, unified chunks
    if all_chunks:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=4)
            
        print(f"\nSuccess! Created {len(all_chunks)} individual chunks from {total_documents_processed} total documents.")
        print(f"Unified data saved to {output_filename}")
    else:
        print("\nNo chunks were created. Check your input files.")

# ==========================================
# Run the Unified Chunker
# ==========================================
if __name__ == "__main__":
    # List all the raw data files you want to combine
    files_to_process = [
        "output_files/scraped_data.json",  # Your Citizens Advice data
        "output_files/gov_uk_data.json"    # Your GOV.UK API data
    ]
    
    process_multiple_files(files_to_process)