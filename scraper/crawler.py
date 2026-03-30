import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse

def crawl_category(start_url, base_domain, max_pages=50):
    """
    Crawls a specific section of a website to find internal links.
    """
    visited_urls = set()
    urls_to_visit = [start_url]
    whitelist = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    print(f"Starting crawl at: {start_url}")

    while urls_to_visit and len(whitelist) < max_pages:
        current_url = urls_to_visit.pop(0)

        # Skip if we've already been here
        if current_url in visited_urls:
            continue

        try:
            print(f"Crawling: {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10)
            visited_urls.add(current_url)

            # Only process successful HTML pages
            if response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                continue

            whitelist.append(current_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all links on the page
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # Convert relative links (like /housing/renting) to full URLs
                full_url = urljoin(current_url, href)
                
                # Filter to only keep URLs that belong to our target domain AND category
                parsed_url = urlparse(full_url)
                if parsed_url.netloc == base_domain and full_url.startswith(start_url):
                    # Remove URL fragments (e.g., #section-1) to avoid duplicates
                    clean_url = full_url.split('#')[0]
                    
                    if clean_url not in visited_urls and clean_url not in urls_to_visit:
                        urls_to_visit.append(clean_url)

            # Be polite to their servers
            time.sleep(1)

        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

    return whitelist

# ==========================================
# Run the Spider
# ==========================================
if __name__ == "__main__":
    # Define where to start and what domain to stay on
    TARGET_DOMAIN = "www.citizensadvice.org.uk"
    STARTING_PAGE = "https://www.citizensadvice.org.uk/housing/"
    
    # Run the crawler (capped at 50 pages for local testing)
    discovered_urls = crawl_category(STARTING_PAGE, TARGET_DOMAIN, max_pages=20)
    
    # Save the results to a file
    with open("whitelist.json", "w", encoding="utf-8") as f:
        json.dump(discovered_urls, f, indent=4)
        
    print(f"\nDone! Discovered {len(discovered_urls)} URLs and saved to whitelist.json.")