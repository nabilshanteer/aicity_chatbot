import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import os

def scrape_and_clean_page(url):
    """
    Scrapes a single URL, removes boilerplate HTML, and extracts the core text.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Scraping: {url}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Content Cleaning (Boilerplate Removal)
        elements_to_remove = [
            'nav', 'footer', 'header', 'aside', 'script', 'style', 
            'form', 'button', 'iframe'
        ]
        
        for element in soup.find_all(elements_to_remove):
            element.decompose() 

        # Extract the remaining text, separating blocks with a space
        core_text = soup.get_text(separator=' ', strip=True)

        # 2. Metadata Tagging
        document_data = {
            "source_url": url,
            "last_scraped": datetime.utcnow().isoformat() + "Z",
            "content": core_text
        }
        
        return document_data

    except requests.exceptions.RequestException as e:
        print(f"  -> Failed to scrape {url}: {e}")
        return None

def process_url_list(url_list, output_filename="output_files/scraped_data.json"):
    """
    Processes a list of URLs and saves the output to a local JSON file.
    """
    all_documents = []
    
    for url in url_list:
        data = scrape_and_clean_page(url)
        if data and data['content'].strip(): # Ensure we don't save empty pages
            all_documents.append(data)
        
        # Polite scraping: pause for a moment between requests
        time.sleep(2) 

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=4)
        
    print(f"\nSuccessfully scraped {len(all_documents)} pages. Data saved to {output_filename}")


# ==========================================
# Run the Pipeline
# ==========================================
if __name__ == "__main__":
    whitelist_file = "output_files/whitelist.json"
    
    # Check if the whitelist file exists before trying to open it
    if not os.path.exists(whitelist_file):
        print(f"Error: Could not find '{whitelist_file}'.")
        print("Please run your spider.py script first to generate the whitelist.")
    else:
        # Load the URLs from the JSON file
        with open(whitelist_file, "r", encoding="utf-8") as f:
            target_urls = json.load(f)
            
        if not target_urls:
            print(f"Warning: '{whitelist_file}' is empty.")
        else:
            print(f"Found {len(target_urls)} URLs in the whitelist. Starting scraper...\n")
            process_url_list(target_urls)