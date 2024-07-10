from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse



def is_webpage_accessible(url):
    # url = 'https://' + url
    print(url)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True, verify=False)
        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to access {url}. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return False
    

def scrape_data(url):
    load_dotenv()
    # Initialize the FirecrawlApp with your API key
    app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_KEY'))
    
    # Scrape a single URL
    scraped_data = app.scrape_url(url,{'pageOptions':{'onlyMainContent': True}})
    
    # Check if 'markdown' key exists in the scraped data
    if 'markdown' in scraped_data:
        return scraped_data['markdown']
    else:
        raise KeyError("The key 'markdown' does not exist in the scraped data.")
    
    
def crawl_data(url_list: list):
    load_dotenv()
    # Initialize the FirecrawlApp with your API key
    app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_KEY'))
    
    result = ''
    
    for url in url_list:
        # Scrape a single URL
        scraped_data = app.scrape_url(url,{'pageOptions':{'onlyMainContent': True}})
        
        # Check if 'markdown' key exists in the scraped data
        if 'markdown' in scraped_data:
            result+= '\n' + scraped_data['markdown']
            
    return result

    
def save_raw_data(raw_data, filename, timestamp, output_folder='scraping_output'):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    filename = filename.lower().replace(' ', '_')
    
    # Save the raw markdown data with timestamp in filename
    raw_output_path = os.path.join(output_folder, f'{filename}_{timestamp}.md')
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {raw_output_path}")
    
def fetch_webpage(url):
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.google.com'
    }
    session = requests.Session()
    session.headers.update(headers)
    response = session.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    return response.text
    
def extract_urls(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    urls = set()
    for a_tag in soup.find_all('a', href=True):
        # This function from the urllib.parse module combines the base URL with the relative URL to create a full URL. 
        # If the href is already an absolute URL, it will remain unchanged.
        full_url = urljoin(base_url, a_tag['href'])
        # Make sure the URL is within the same domain
        # This condition checks if the constructed full URL belongs to the same domain as the base URL.
        if urlparse(full_url).netloc == urlparse(base_url).netloc:
            urls.add(full_url)
    return urls

def filter_urls(urls):
    keywords_wanted = ['platform', 'product', 'service', 'solution', 'client', 'partner', 'customer']
    filtered_urls = [url for url in urls if any(keyword in url.lower() for keyword in keywords_wanted)]
    keywords_unwanted = ['login', 'news', 'support', 'blog', 'term']
    filtered_urls = [url for url in filtered_urls if not any(keyword in url.lower() for keyword in keywords_unwanted)]
    return filtered_urls

def get_related_urls(base_url):
    if is_webpage_accessible(base_url):
        html = fetch_webpage(base_url)
        all_urls = extract_urls(html, base_url)
        related_urls = filter_urls(all_urls)
        
        return all_urls, [base_url] + related_urls
    else:
        return None, None
    
if __name__ == "__main__":
    filename = 'New Construct'
    filename = filename.lower().replace(' ', '_')
    print(filename)
    