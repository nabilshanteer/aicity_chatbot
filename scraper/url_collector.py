"""
url_collector.py
----------------
Builds a comprehensive URL whitelist from two sources:
  1. Citizens Advice (www.citizensadvice.org.uk) — crawled across all major categories
  2. GOV.UK Content API — fetched by taxon for approved topic areas

Supports resuming — completed categories are saved to a checkpoint file so a
network failure or interruption doesn't lose progress.

Usage:
    python url_collector.py               # full run (resumes if checkpoint exists)
    python url_collector.py --max-pages 50   # cap per CA category (testing)
    python url_collector.py --dry-run        # discover URLs but don't save
    python url_collector.py --reset          # ignore checkpoint, start fresh
"""

import json
import time
import argparse
import os
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_FILE     = "output_files/whitelist.json"
CHECKPOINT_FILE = "output_files/whitelist_checkpoint.json"

CA_CATEGORIES = [
    "https://www.citizensadvice.org.uk/benefits/",
    "https://www.citizensadvice.org.uk/work/",
    "https://www.citizensadvice.org.uk/debt-and-money/",
    "https://www.citizensadvice.org.uk/family/",
    "https://www.citizensadvice.org.uk/housing/",
    "https://www.citizensadvice.org.uk/law-and-courts/",
    "https://www.citizensadvice.org.uk/immigration/",
    "https://www.citizensadvice.org.uk/consumer/",
    "https://www.citizensadvice.org.uk/health/",
]

CA_DOMAIN = "www.citizensadvice.org.uk"

# Paths to skip — non-content or login-gated pages
CA_SKIP_PREFIXES = [
    "about", "contact", "local", "search", "static", "media",
    "cymraeg",       # Welsh language — skip for English-only index
    "advisernet",    # Login-gated advisor portal
    "cookie-preferences",
    "print",
]

GOVUK_TAXON_PATHS = [
    "/welfare/benefits-entitlement",
    "/welfare/tax-credits",
    "/welfare/universal-credit",
    "/housing-local-and-community/renting",
    "/housing-local-and-community/homelessness-and-rough-sleeping",
    "/money/personal-tax",
    "/money/debt-management-credit",
    "/employment/rights-trade-unions",
    "/employment/redundancies-dismissals",
    "/childcare-parenting/financial-help-if-you-have-children",
    "/health-and-social-care/disabilities",
    "/entering-and-staying-uk",
]

CA_DELAY    = 1.0
GOVUK_DELAY = 0.5

HEADERS = {
    "User-Agent": "CitizensAdviceChatbot/1.0 (research; University of Southampton)"
}


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    """
    Returns a checkpoint dict:
        {
          "completed_ca_categories": [...],
          "completed_govuk_taxons": [...],
          "urls": [...]
        }
    """
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_ca_categories": [], "completed_govuk_taxons": [], "urls": []}


def save_checkpoint(checkpoint: dict) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Citizens Advice Crawler
# ---------------------------------------------------------------------------

def is_valid_ca_url(url: str) -> bool:
    """Returns True if the URL is a content page worth crawling."""
    parsed = urlparse(url)
    if parsed.netloc != CA_DOMAIN:
        return False
    path = parsed.path.lstrip("/")
    if any(path.startswith(skip) for skip in CA_SKIP_PREFIXES):
        return False
    # Skip query strings (e.g. ?ReturnUrl=...)
    if parsed.query:
        return False
    return True


def crawl_ca_category(start_url: str, max_pages: int) -> list[str]:
    """Crawls a single CA category and returns all discovered content URLs."""
    visited: set[str] = set()
    queue:   list[str] = [start_url]
    found:   list[str] = []

    while queue and len(found) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                continue
            if "text/html" not in response.headers.get("Content-Type", ""):
                continue

            found.append(url)

            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                full_url = urljoin(url, a_tag["href"]).split("#")[0].rstrip("/")
                if is_valid_ca_url(full_url) and full_url not in visited and full_url not in queue:
                    queue.append(full_url)

            time.sleep(CA_DELAY)

        except requests.RequestException as e:
            print(f"    Error crawling {url}: {e}")

    return found


def collect_ca_urls(max_pages_per_category: int, checkpoint: dict) -> list[dict]:
    """
    Crawls all CA categories. Skips categories already in the checkpoint.
    Saves checkpoint after each completed category.
    """
    all_urls  = list(checkpoint["urls"])
    seen: set[str] = {r["url"] for r in all_urls}
    completed = set(checkpoint["completed_ca_categories"])

    for category_url in CA_CATEGORIES:
        category_name = category_url.rstrip("/").split("/")[-1]

        if category_name in completed:
            print(f"\n  Skipping CA category (already done): {category_name}")
            continue

        print(f"\n  Crawling CA category: {category_name}")
        urls = crawl_ca_category(category_url, max_pages_per_category)

        new_count = 0
        for url in urls:
            if url not in seen:
                seen.add(url)
                all_urls.append({"url": url, "source": "citizens_advice", "category": category_name})
                new_count += 1

        print(f"    Found {new_count} new URLs (total so far: {len(all_urls)})")

        # Save checkpoint after every category
        checkpoint["completed_ca_categories"].append(category_name)
        checkpoint["urls"] = all_urls
        save_checkpoint(checkpoint)
        print(f"    Checkpoint saved.")

    return all_urls


# ---------------------------------------------------------------------------
# GOV.UK URL Collector
# ---------------------------------------------------------------------------

def resolve_taxon_content_id(taxon_path: str) -> str | None:
    """Looks up a taxon's content_id UUID from the GOV.UK Content API."""
    try:
        response = requests.get(
            f"https://www.gov.uk/api/content{taxon_path}",
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("content_id")
    except requests.RequestException as e:
        print(f"    Could not resolve content_id for {taxon_path}: {e}")
        return None


def fetch_govuk_taxon_urls(taxon_path: str, max_results: int = 200) -> list[str]:
    """Fetches all GOV.UK content URLs under a taxon using the Search API."""
    content_id = resolve_taxon_content_id(taxon_path)
    if not content_id:
        print(f"    Skipping {taxon_path} — could not resolve content_id")
        return []

    print(f"    Resolved content_id: {content_id}")

    urls      = []
    start     = 0
    page_size = 100

    while len(urls) < max_results:
        params = {
            "filter_part_of_taxonomy_tree": content_id,
            "count": min(page_size, max_results - len(urls)),
            "start": start,
            "fields[]": "link",
        }

        try:
            response = requests.get(
                "https://www.gov.uk/api/search.json",
                params=params,
                headers=HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            data    = response.json()
            results = data.get("results", [])

            if not results:
                break

            for result in results:
                link = result.get("link", "")
                if link:
                    urls.append(f"https://www.gov.uk{link}")

            if len(results) < page_size:
                break

            start += len(results)
            time.sleep(GOVUK_DELAY)

        except requests.RequestException as e:
            print(f"    GOV.UK API error for {taxon_path}: {e}")
            break

    return urls


def collect_govuk_urls(checkpoint: dict) -> list[dict]:
    """
    Fetches URLs from all approved GOV.UK taxons. Skips completed taxons.
    Saves checkpoint after each completed taxon.
    """
    all_urls  = [r for r in checkpoint["urls"] if r["source"] == "gov_uk"]
    seen: set[str] = {r["url"] for r in all_urls}
    completed = set(checkpoint["completed_govuk_taxons"])

    for taxon_path in GOVUK_TAXON_PATHS:
        taxon_name = taxon_path.strip("/").replace("/", "_")

        if taxon_path in completed:
            print(f"\n  Skipping GOV.UK taxon (already done): {taxon_path}")
            continue

        print(f"\n  Fetching GOV.UK taxon: {taxon_path}")
        urls = fetch_govuk_taxon_urls(taxon_path)

        new_count = 0
        for url in urls:
            if url not in seen:
                seen.add(url)
                all_urls.append({"url": url, "source": "gov_uk", "category": taxon_name})
                new_count += 1

        print(f"    Found {new_count} new URLs (total so far: {len(all_urls)})")

        checkpoint["completed_govuk_taxons"].append(taxon_path)
        # Merge gov_uk results back into full checkpoint url list
        checkpoint["urls"] = [r for r in checkpoint["urls"] if r["source"] != "gov_uk"] + all_urls
        save_checkpoint(checkpoint)
        print(f"    Checkpoint saved.")

    return all_urls


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Collect URLs from Citizens Advice and GOV.UK")
    parser.add_argument("--max-pages", type=int, default=2000,
                        help="Max pages per CA category (default: 2000)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover URLs but do not save final output")
    parser.add_argument("--reset", action="store_true",
                        help="Ignore existing checkpoint and start fresh")
    args = parser.parse_args()

    os.makedirs("output_files", exist_ok=True)

    if args.reset and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("Checkpoint cleared.\n")

    checkpoint = load_checkpoint()
    if checkpoint["completed_ca_categories"] or checkpoint["completed_govuk_taxons"]:
        print(f"Resuming from checkpoint — "
              f"{len(checkpoint['completed_ca_categories'])} CA categories and "
              f"{len(checkpoint['completed_govuk_taxons'])} GOV.UK taxons already done.")

    print("=" * 60)
    print("  URL Collector")
    print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"  CA max pages per category: {args.max_pages}")
    print("=" * 60)

    print("\n[1/2] Crawling Citizens Advice...")
    ca_urls = collect_ca_urls(args.max_pages, checkpoint)
    print(f"\n  Citizens Advice total: {len(ca_urls)} URLs")

    print("\n[2/2] Fetching GOV.UK URLs...")
    govuk_urls = collect_govuk_urls(checkpoint)
    print(f"\n  GOV.UK total: {len(govuk_urls)} URLs")

    all_urls = ca_urls + govuk_urls
    print(f"\n{'=' * 60}")
    print(f"  Grand total: {len(all_urls)} URLs")
    print(f"    Citizens Advice : {len(ca_urls)}")
    print(f"    GOV.UK          : {len(govuk_urls)}")
    print(f"{'=' * 60}")

    if args.dry_run:
        print("\n  Dry run — skipping save.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_urls, f, ensure_ascii=False, indent=2)

    # Clean up checkpoint now that we have the final output
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\n  Saved to: {OUTPUT_FILE}")
    print(f"  Completed: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
