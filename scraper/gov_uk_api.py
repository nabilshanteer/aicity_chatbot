import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

def clean_html_text(html_content):
    """Takes raw HTML from the API and returns clean, readable text."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    # get_text() extracts all text and separates blocks with a space
    return soup.get_text(separator=' ', strip=True)


def build_structured_sections(page_title, details):
    sections = []

    if 'parts' in details:
        for part in details['parts']:
            text = clean_html_text(part.get('body', ''))
            if not text:
                continue

            heading = part.get('title') or page_title
            sections.append({
                "section_order": len(sections),
                "heading": heading,
                "heading_level": 2,
                "heading_path": f"{page_title} > {heading}" if heading != page_title else page_title,
                "text": text,
            })

    if not sections and 'body' in details and isinstance(details['body'], str):
        text = clean_html_text(details['body'])
        if text:
            sections.append({
                "section_order": 0,
                "heading": page_title,
                "heading_level": 1,
                "heading_path": page_title,
                "text": text,
            })

    return sections

def fetch_govuk_advice(topic, max_results=3):
    """
    Searches GOV.UK for a topic, handles different page formats (Answers vs Guides),
    and cleans the HTML.
    """
    print(f"Searching GOV.UK for: '{topic}'...")
    search_url = f"https://www.gov.uk/api/search.json?q={topic}&count={max_results}"
    
    try:
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        search_results = search_response.json().get('results', [])
        
        extracted_documents = []

        for result in search_results:
            page_path = result.get('link')
            if not page_path:
                continue
                
            print(f"Fetching full content for: {page_path}")
            content_url = f"https://www.gov.uk/api/content{page_path}"
            content_response = requests.get(content_url)
            
            if content_response.status_code == 200:
                content_data = content_response.json()
                details = content_data.get('details', {})
                
                page_title = content_data.get('title') or f"https://www.gov.uk{page_path}"
                sections = build_structured_sections(page_title, details)
                clean_text = "\n\n".join(section["text"] for section in sections)
                
                # Only save if we actually found text
                if clean_text:
                    document = {
                        "source_url": f"https://www.gov.uk{page_path}",
                        "last_scraped": datetime.utcnow().isoformat() + "Z",
                        "page_title": page_title,
                        "sections": sections,
                        "content": clean_text
                    }
                    extracted_documents.append(document)
                else:
                    print(f"  -> Warning: No readable text found for {page_path}")
                
        return extracted_documents

    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {e}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {e}")
        return None

# ==========================================
# Run the API Fetcher with the Whitelist
# ==========================================
if __name__ == "__main__":
    # 1. Your pre-approved list chosen from the taxonomy snapshot
    approved_topics = [
        "Benefits", 
        "Housing and local services", 
        "Money and tax", 
        "Work"
    ]
    
    all_gov_data = []
    
    print(f"Starting GOV.UK ingestion for {len(approved_topics)} approved topics...\n")
    
    # 2. Loop through each approved topic
    for topic in approved_topics:
        # Fetch the top 10 pages for each topic (you can increase this later)
        results = fetch_govuk_advice(topic, max_results=10)
        
        if results:
            all_gov_data.extend(results)
            print(f"  ✓ Successfully fetched data for: {topic}")
        else:
            print(f"  ✗ Failed to fetch or find data for: {topic}")
            
    # 3. Save everything into one master GOV.UK JSON file
    if all_gov_data:
        with open("output_files/gov_uk_data.json", "w", encoding="utf-8") as f:
            json.dump(all_gov_data, f, ensure_ascii=False, indent=4)
        print(f"\nPipeline Complete! Saved {len(all_gov_data)} total documents to gov_uk_data.json")
