from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import time
from firecrawl_scraping import FirecrawlApp
from requests.exceptions import HTTPError
from collections import Counter
import time
from datetime import datetime


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
    


def crawl_data(base_url, url_list: list, file_path: str, overwrite: bool = False):
    load_dotenv()
    # Initialize the FirecrawlApp with your API key
    app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_KEY'))
    
    # Load existing data if the file exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            result = json.load(file)
    else:
        result = {}
        
    processed_name = file_path.split('/')[1].replace('.json', '')
    result['processed_company'] = processed_name
    result['url'] = base_url

    rate_limit_reset_time = 0
    
    for url in url_list:
        # Determine the endpoint
        if base_url == url:
            endpoint = 'main_page'
        else:
            if base_url in url:
                endpoint = url.replace(base_url, '')
            else:
                endpoint = url
        
        # Check if the endpoint already exists in the result
        if endpoint in result and not overwrite:
            print(f"Skipping {url} as it already exists and overwrite is set to False.")
            continue  # Skip this URL and move to the next one

        # Respect rate limit by waiting until the reset time
        if time.time() < rate_limit_reset_time:
            wait_time = rate_limit_reset_time - time.time()
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
            time.sleep(wait_time)
        
        try:
            # Scrape a single URL
            print(f"Scraping {url}.")
            
            current_dateTime = datetime.now(pytz.timezone('Etc/GMT'))
            result['timestamp'] = current_dateTime.strftime(format = "%Y-%m-%d %H:%M") + ' Etc/GMT'

            scraped_data = app.scrape_url(url, {'pageOptions': {'onlyMainContent': True}})
            
            # Check if 'markdown' key exists in the scraped data
            if 'markdown' in scraped_data:
                result[endpoint] = scraped_data['markdown']
        
        except HTTPError as e:
            # Handle rate limit exceeded error
            if e.response.status_code == 429:
                rate_limit_reset_time = int(e.response.headers.get('Retry-After', 60)) + time.time()
                print(f"Rate limit exceeded. Retrying after {rate_limit_reset_time - time.time()} seconds.")
                time.sleep(rate_limit_reset_time - time.time())
                continue  # Skip the rest of the code in this iteration and retry scraping the same URL
            else:
                print(f"Unexpected error: {e}")


    # Write the updated JSON data back to the file
    with open(file_path, 'w') as file:
        json.dump(result, file, indent=4)
    
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
    keywords_wanted = ['platform', 'product', 'service', 'solution', 'client', 'partner', 'customer', 'case']
    filtered_urls = [url for url in urls if any(keyword in url.lower() for keyword in keywords_wanted)]
    keywords_unwanted = ['login', 'news', 'support', 'blog', 'term', 'faq', 'demo']
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
    

def standardize_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme == "https" and not parsed_url.netloc.startswith("www."):
        netloc = "www." + parsed_url.netloc
        standardized_url = urlunparse((parsed_url.scheme, netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))
        return standardized_url
    return url

def extract_base_url(url):
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return base_url

def evaluate_confidence(urls):
    base_urls = [extract_base_url(url) for url in urls]
    url_counts = Counter(base_urls)
    most_common_url, count = url_counts.most_common(1)[0]
    
    if count > len(urls) / 2:
        return most_common_url
    else:
        return None

# Function to get the company's domain using Clearbit Autocomplete API
def clearbit_get_domain(company_name):
    base_url_clearbit = "https://autocomplete.clearbit.com/v1/companies/suggest?"
    params = {
        'query': company_name
    }
    
    response = requests.get(base_url_clearbit, params=params)
    
    if response.status_code == 200:
        suggest_response_text = response.json()
        if suggest_response_text:
            domain = suggest_response_text[0].get('domain')
            return f'https://www.{domain}'
    return None

# Function to search for a company's website
def search_company_website(company_name):
    search_query = f'Company "{company_name}"'
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": search_query,
        "key": os.getenv("GOOGLE_SEARCH_KEY"),
        "cx": os.getenv("SEARCH_ENGINE_ID"),
        "num": 5  # Retrieve up to 5 results
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    if 'items' in result:
        links = [result['items'][i]['link'] for i in range(5)]
    
    return links, result

def get_and_verify_client_link(company_name):
    
    try:
        clearbit_link = clearbit_get_domain(company_name)
        google_links, _ = search_company_website(company_name)
        google_links = [standardize_url(link) for link in google_links]
        google_links_clean = [link.replace('/', '') for link in google_links]
        if clearbit_link and clearbit_link.replace('/', '') in google_links_clean:
            print(f"Company {company_name}: The primary URL is: {clearbit_link}")
            return clearbit_link
        else:
            print(f'Company {company_name}: The URL cannot be verified.\n- clearbit output: {clearbit_link}\n- Google output: {google_links}')
            
            if len(google_links) == 5:
                print(f'Company {company_name}: Try evaluate the confidance of Google result.')
            
                result = evaluate_confidence(google_links)
                if result:
                    print(f"Company {company_name}: The Google search is confident. The primary URL is: {result}")
                else:
                    print(f"Company {company_name}: The Google search is not confident in the primary URL.")        
                    return None
            else:
                return None
            
    except Exception as e:
        print(f'Company {company_name}: Error has occured when getting urls: {e}')
        return None

    
    
if __name__ == "__main__":
    filename = 'New Construct'
    filename = filename.lower().replace(' ', '_')
    print(filename)
    