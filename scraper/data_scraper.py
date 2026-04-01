"""
data_scraper.py
---------------
Scrapes every URL in output_files/whitelist.json and saves structured,
cleaned documents to output_files/scraped_data.json.

Supports parallel execution via --worker-id / --total-workers for SLURM
array jobs on HPC. Each worker processes its own slice of the URL list and
writes to a separate output file (scraped_data_<worker_id>.json).
Merge the outputs afterwards with merge_scraped_data.py.

Local usage (single process):
    python data_scraper.py

HPC array job usage (e.g. 20 parallel workers):
    python data_scraper.py --worker-id $SLURM_ARRAY_TASK_ID --total-workers 20
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WHITELIST_FILE = "output_files/whitelist.json"
DELAY_SECONDS = 2.0

HEADERS = {
    "User-Agent": "CitizensAdviceChatbot/1.0 (research; University of Southampton)"
}

MAIN_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    "#main-content",
    "#content",
    ".main-content",
    ".article-content",
    ".content",
]

DROP_TAGS = ["nav", "footer", "header", "aside", "script", "style", "form", "button", "iframe"]
CONTENT_TAGS = ["h1", "h2", "h3", "p", "ul", "ol", "table"]
HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3}
MIN_SECTION_TEXT_LENGTH = 40

NOISE_KEYWORDS = {
    "cookie",
    "cookies",
    "breadcrumb",
    "newsletter",
    "feedback",
    "survey",
    "consent",
    "privacy",
    "accessibility",
    "skip-link",
    "skip link",
}

BOILERPLATE_PATTERNS = [
    re.compile(r"how we use cookies", re.I),
    re.compile(r"accept or reject cookies", re.I),
    re.compile(r"cookie settings", re.I),
    re.compile(r"essential cookies", re.I),
    re.compile(r"additional cookies", re.I),
    re.compile(r"let you watch videos", re.I),
    re.compile(r"keep your data safe", re.I),
    re.compile(r"javascript turned off", re.I),
    re.compile(r"give feedback", re.I),
    re.compile(r"report a problem", re.I),
]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalises whitespace without losing basic list/table readability."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def section_parent_path(path: str) -> str:
    if " > " not in path:
        return ""
    return path.rsplit(" > ", 1)[0]


def attrs_contain_noise(element: Tag) -> bool:
    values = []

    for key in ("id", "role", "aria-label"):
        value = element.get(key)
        if isinstance(value, str):
            values.append(value.lower())

    class_values = element.get("class", [])
    if isinstance(class_values, list):
        values.extend(str(item).lower() for item in class_values)
    elif isinstance(class_values, str):
        values.append(class_values.lower())

    joined = " ".join(values)
    return any(keyword in joined for keyword in NOISE_KEYWORDS)


def is_boilerplate_text(text: str) -> bool:
    compact = normalize_text(text)
    if len(compact) < MIN_SECTION_TEXT_LENGTH:
        return True
    return any(pattern.search(compact) for pattern in BOILERPLATE_PATTERNS)


def element_to_text(element: Tag) -> str:
    """Extracts readable text from paragraphs, lists, and tables."""
    if element.name in {"ul", "ol"}:
        items = [normalize_text(li.get_text(" ", strip=True)) for li in element.find_all("li")]
        items = [item for item in items if item]
        return " ".join(f"- {item}" for item in items)

    if element.name == "table":
        rows = []
        for row in element.find_all("tr"):
            cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(" | ".join(cells))
        return " ".join(rows)

    return normalize_text(element.get_text(" ", strip=True))


# ---------------------------------------------------------------------------
# HTML extraction
# ---------------------------------------------------------------------------

def remove_boilerplate(soup: BeautifulSoup) -> None:
    for element in soup.find_all(DROP_TAGS):
        element.decompose()

    for element in soup.find_all(True):
        if attrs_contain_noise(element):
            element.decompose()


def select_content_root(soup: BeautifulSoup) -> Tag:
    for selector in MAIN_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag) and normalize_text(node.get_text(" ", strip=True)):
            return node

    return soup.body or soup


def build_sections_from_html(root: Tag, page_title: str) -> list[dict]:
    sections: list[dict] = []
    heading_stack: dict[int, str] = {}
    active_heading = page_title or "Page Content"
    active_level = 1
    current_parts: list[str] = []

    def flush_section() -> None:
        nonlocal current_parts, sections
        text = normalize_text(" ".join(current_parts))
        if not text or is_boilerplate_text(text):
            current_parts = []
            return

        path_parts = [heading_stack[level] for level in sorted(heading_stack) if heading_stack[level]]
        heading_path = " > ".join(path_parts) if path_parts else active_heading
        sections.append({
            "section_order": len(sections),
            "heading": active_heading,
            "heading_level": active_level,
            "heading_path": heading_path,
            "text": text,
        })
        current_parts = []

    for element in root.find_all(CONTENT_TAGS):
        if element.find_parent(["nav", "footer", "header", "aside"]):
            continue

        if element.name in HEADING_TAGS:
            flush_section()

            active_level = HEADING_TAGS[element.name]
            active_heading = normalize_text(element.get_text(" ", strip=True)) or page_title or "Page Content"

            heading_stack[active_level] = active_heading
            for level in list(heading_stack.keys()):
                if level > active_level:
                    heading_stack.pop(level, None)
            continue

        text = element_to_text(element)
        if text and not is_boilerplate_text(text):
            current_parts.append(text)

    flush_section()
    return sections


def extract_html_document(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    remove_boilerplate(soup)
    root = select_content_root(soup)

    h1 = root.find("h1") or soup.find("h1")
    title_tag = soup.title.string if soup.title and soup.title.string else ""
    page_title = normalize_text(h1.get_text(" ", strip=True) if h1 else title_tag) or url

    sections = build_sections_from_html(root, page_title)
    content = "\n\n".join(section["text"] for section in sections)

    return {
        "source_url": url,
        "last_scraped": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "sections": sections,
        "content": content,
    }


# ---------------------------------------------------------------------------
# GOV.UK API extraction
# ---------------------------------------------------------------------------

def extract_govuk_document(url: str) -> dict | None:
    parsed = urlparse(url)
    content_url = f"https://www.gov.uk/api/content{parsed.path}"

    try:
        response = requests.get(content_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return None

    details = payload.get("details", {})
    page_title = normalize_text(payload.get("title", "")) or url
    sections = []

    if "parts" in details and isinstance(details["parts"], list):
        for part in details["parts"]:
            raw_body = part.get("body", "")
            if not raw_body:
                continue

            soup = BeautifulSoup(raw_body, "html.parser")
            text = normalize_text(soup.get_text(" ", strip=True))
            if not text or is_boilerplate_text(text):
                continue

            heading = normalize_text(part.get("title", "")) or page_title
            sections.append({
                "section_order": len(sections),
                "heading": heading,
                "heading_level": 2,
                "heading_path": f"{page_title} > {heading}" if heading != page_title else page_title,
                "text": text,
            })
    elif isinstance(details.get("body"), str) and details["body"].strip():
        soup = BeautifulSoup(details["body"], "html.parser")
        text = normalize_text(soup.get_text(" ", strip=True))
        if text and not is_boilerplate_text(text):
            sections.append({
                "section_order": 0,
                "heading": page_title,
                "heading_level": 1,
                "heading_path": page_title,
                "text": text,
            })

    if not sections:
        return None

    return {
        "source_url": url,
        "last_scraped": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "sections": sections,
        "content": "\n\n".join(section["text"] for section in sections),
    }


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def scrape_and_clean_page(url: str, source_type: str = "unknown") -> dict | None:
    """
    Scrapes a single URL and returns structured sections plus flattened content.
    """
    if source_type == "gov_uk" or "www.gov.uk" in urlparse(url).netloc:
        gov_doc = extract_govuk_document(url)
        if gov_doc:
            return gov_doc

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return extract_html_document(url, response.text)
    except requests.RequestException as e:
        print(f"  -> Failed: {url} - {e}")
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

        source_type = record.get("source", "unknown")
        data = scrape_and_clean_page(url, source_type=source_type)

        if data and data.get("content", "").strip():
            data["source"] = source_type
            data["category"] = record.get("category", "unknown")
            all_documents.append(data)

        time.sleep(DELAY_SECONDS)

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=2)

    print(f"\n  Scraped {len(all_documents)}/{len(url_records)} pages -> {output_filename}")


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

    if all_records and isinstance(all_records[0], str):
        all_records = [{"url": u, "source": "unknown", "category": "unknown"}
                       for u in all_records]

    worker_slice = all_records[args.worker_id::args.total_workers]

    if args.total_workers == 1:
        output_file = "output_files/scraped_data.json"
    else:
        output_file = f"output_files/scraped_data_{args.worker_id}.json"

    print(f"Worker {args.worker_id}/{args.total_workers} - "
          f"processing {len(worker_slice)} of {len(all_records)} URLs")
    print(f"Output: {output_file}\n")

    process_url_list(worker_slice, output_file)


if __name__ == "__main__":
    main()
