"""
merge_scraped_data.py
---------------------
Merges the per-worker scraped_data_N.json files produced by a SLURM array
job into a single output_files/scraped_data.json.

Run this on the HPC login node (or locally) after all array tasks complete.

Usage:
    python merge_scraped_data.py
    python merge_scraped_data.py --total-workers 20   # explicit worker count
"""

import json
import os
import glob
import argparse


def main():
    parser = argparse.ArgumentParser(description="Merge per-worker scraped data files")
    parser.add_argument("--input-dir", type=str, default="output_files",
                        help="Directory containing scraped_data_N.json files")
    parser.add_argument("--output", type=str, default="output_files/scraped_data.json",
                        help="Output merged file path")
    args = parser.parse_args()

    pattern = os.path.join(args.input_dir, "scraped_data_*.json")
    worker_files = sorted(glob.glob(pattern))

    if not worker_files:
        print(f"No worker files found matching: {pattern}")
        print("If running single-process, scraped_data.json already exists — no merge needed.")
        return

    print(f"Found {len(worker_files)} worker files to merge:")

    all_documents = []
    seen_urls: set[str] = set()

    for filepath in worker_files:
        with open(filepath, "r", encoding="utf-8") as f:
            docs = json.load(f)

        new_count = 0
        for doc in docs:
            url = doc.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                all_documents.append(doc)
                new_count += 1

        print(f"  {os.path.basename(filepath)}: {new_count} docs added ({len(docs)} total in file)")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=2)

    print(f"\nMerged {len(all_documents)} unique documents → {args.output}")


if __name__ == "__main__":
    main()
