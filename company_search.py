
import requests
from urllib.parse import urlparse, urlunparse
from collections import Counter
import os
from dotenv import load_dotenv

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
            print(f'Company {company_name}: Try evaluate the confidance of Google result')
        
            result = evaluate_confidence(google_links)
            if result:
                print(f"Company {company_name}: The Google search is confident. The primary URL is: {result}")
            else:
                print(f"Company {company_name}: The Google search is not confident in the primary URL.")        
                return None
        else:
            return None

