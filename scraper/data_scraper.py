"""
data_scraper.py
---------------
Scrapes the full text content from every URL in output_files/whitelist.json
and saves cleaned documents to output_files/scraped_data.json.

Supports parallel execution via --worker-id / --total-workers for SLURM
array jobs on HPC. Each worker processes its own slice of the URL list and
writes to a separate output file (scraped_data_<worker_id>.json).
Merge the outputs afterwards with merge_scraped_data.py.

Local usage (single process):
    python data_scraper.py

HPC array job usage (e.g. 20 parallel workers):
    python data_scraper.py --worker-id $SLURM_ARRAY_TASK_ID --total-workers 20
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import time
import os
import argparse


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WHITELIST_FILE = "output_files/whitelist.json"
DELAY_SECONDS = 2.0

HEADERS = {
    "User-Agent": "CitizensAdviceChatbot/1.0 (research; University of Southampton)"
}


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def scrape_and_clean_page(url: str) -> dict | None:
    """
    Scrapes a single URL, removes boilerplate HTML, and extracts core text.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup.find_all(["nav", "footer", "header", "aside",
                                       "script", "style", "form", "button", "iframe"]):
            element.decompose()

        core_text = soup.get_text(separator=" ", strip=True)

        return {
            "source_url": url,
            "last_scraped": datetime.now(timezone.utc).isoformat(),
            "content": core_text,
        }

    except requests.RequestException as e:
        print(f"  -> Failed: {url} — {e}")
        return None


def process_url_list(url_records: list[dict], output_filename: str) -> None:
    """
    Scrapes each URL record and writes results to output_filename.
    url_records is a list of dicts with at least a 'url' key, plus
    optional 'source' and 'category' fields passed through to output.
    """
    all_documents = []

    for i, record in enumerate(url_records, start=1):
        url = record["url"]
        print(f"  [{i}/{len(url_records)}] Scraping: {url}")

        data = scrape_and_clean_page(url)

        if data and data["content"].strip():
            # Carry through source metadata from the whitelist
            data["source"] = record.get("source", "unknown")
            data["category"] = record.get("category", "unknown")
            all_documents.append(data)

        time.sleep(DELAY_SECONDS)

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=2)

    print(f"\n  Scraped {len(all_documents)}/{len(url_records)} pages → {output_filename}")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape content from whitelisted URLs")
    parser.add_argument("--worker-id", type=int, default=0,
                        help="This worker's index (0-based). Used for SLURM array jobs.")
    parser.add_argument("--total-workers", type=int, default=1,
                        help="Total number of parallel workers. Used for SLURM array jobs.")
    parser.add_argument("--whitelist", type=str, default=WHITELIST_FILE,
                        help=f"Path to whitelist JSON (default: {WHITELIST_FILE})")
    args = parser.parse_args()

    if not os.path.exists(args.whitelist):
        print(f"Error: Whitelist not found at '{args.whitelist}'.")
        print("Run url_collector.py first.")
        return

    with open(args.whitelist, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Support old format (plain list of URL strings) as well as new format
    # (list of dicts with url/source/category)
    if all_records and isinstance(all_records[0], str):
        all_records = [{"url": u, "source": "unknown", "category": "unknown"}
                       for u in all_records]

    # Slice the URL list for this worker
    worker_slice = all_records[args.worker_id::args.total_workers]

    if args.total_workers == 1:
        output_file = "output_files/scraped_data.json"
    else:
        output_file = f"output_files/scraped_data_{args.worker_id}.json"

    print(f"Worker {args.worker_id}/{args.total_workers} — "
          f"processing {len(worker_slice)} of {len(all_records)} URLs")
    print(f"Output: {output_file}\n")

    process_url_list(worker_slice, output_file)


if __name__ == "__main__":
    main()
