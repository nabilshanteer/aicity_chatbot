"""
gov_taxonomy.py
---------------
Fetches all top-level (level one) taxons from the GOV.UK Content API
and displays them for review. Run this first to decide which taxons
are relevant to Citizens Advice before any scraping begins.

Usage:
    python gov_taxonomy.py

Output:
    - Prints a numbered list of all top-level taxons to stdout
    - Saves a JSON snapshot to gov_taxonomy_snapshot.json
"""

import json
import httpx
from datetime import datetime, timezone

# No trailing slash — gov.uk redirects /api/content/ → /api/content (301)
GOV_UK_ROOT_API = "https://www.gov.uk/api/content"
SNAPSHOT_FILE = "gov_taxonomy_snapshot.json"

HEADERS = {
    "User-Agent": "CitizensAdviceChatbot/1.0 (taxonomy-discovery; educational use)",
    "Accept": "application/json",
}


def fetch_root_content() -> dict:
    """
    Fetch the root GOV.UK content page, which contains
    the full list of level_one_taxons in its links block.
    follow_redirects=True handles any future redirects gracefully.
    """
    with httpx.Client(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(GOV_UK_ROOT_API)
        response.raise_for_status()
        return response.json()


def extract_taxons(root_data: dict) -> list[dict]:
    """
    Pull the level_one_taxons list from the root content JSON
    and normalise each entry into a clean dict.
    """
    raw_taxons = root_data.get("links", {}).get("level_one_taxons", [])

    taxons = []
    for t in raw_taxons:
        taxons.append({
            "title":      t.get("title", "Unknown"),
            "base_path":  t.get("base_path", ""),
            "content_id": t.get("content_id", ""),
            "api_url":    t.get("api_url", ""),
            "web_url":    t.get("web_url", ""),
            "phase":      t.get("phase", "unknown"),
            "updated_at": t.get("public_updated_at", ""),
        })

    # Sort alphabetically for easy reading
    taxons.sort(key=lambda x: x["title"])
    return taxons


def display_taxons(taxons: list[dict]) -> None:
    """Pretty-print the taxons to stdout."""
    print("\n" + "=" * 60)
    print(f"  GOV.UK Top-Level Taxons  ({len(taxons)} found)")
    print("=" * 60)

    for i, t in enumerate(taxons, start=1):
        phase_tag = f"[{t['phase'].upper()}]" if t["phase"] != "live" else ""
        print(f"\n  {i:>2}. {t['title']} {phase_tag}")
        print(f"       Path     : {t['base_path']}")
        print(f"       API URL  : {t['api_url']}")
        print(f"       Web URL  : {t['web_url']}")
        print(f"       Updated  : {t['updated_at']}")

    print("\n" + "=" * 60)
    print("  Review the list above and tell me which to include/exclude.")
    print("=" * 60 + "\n")


def save_snapshot(taxons: list[dict]) -> None:
    """Save a JSON snapshot so the result is reproducible without re-fetching."""
    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source":     GOV_UK_ROOT_API,
        "count":      len(taxons),
        "taxons":     taxons,
    }
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Snapshot saved to: {SNAPSHOT_FILE}\n")


def main() -> None:
    print("Fetching GOV.UK root taxonomy...")
    try:
        root_data = fetch_root_content()
    except httpx.HTTPStatusError as e:
        print(f"  ✗ HTTP error: {e.response.status_code} — {e.response.text}")
        return
    except httpx.RequestError as e:
        print(f"  ✗ Connection error: {e}")
        return

    taxons = extract_taxons(root_data)

    if not taxons:
        print("  ✗ No taxons found — the API response structure may have changed.")
        print("  Check: https://www.gov.uk/api/content and look for 'level_one_taxons'")
        return

    display_taxons(taxons)
    save_snapshot(taxons)


if __name__ == "__main__":
    main()
