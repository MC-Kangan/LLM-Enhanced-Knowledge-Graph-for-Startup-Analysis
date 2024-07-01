from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import os
import requests


def is_webpage_accessible(url):
    url = 'https://' + url
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
    
    
def save_raw_data(raw_data, filename, timestamp, output_folder='scraping_output'):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    filename = filename.lower().replace(' ', '_')
    
    # Save the raw markdown data with timestamp in filename
    raw_output_path = os.path.join(output_folder, f'{filename}_{timestamp}.md')
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {raw_output_path}")
    
    
if __name__ == "__main__":
    filename = 'New Construct'
    filename = filename.lower().replace(' ', '_')
    print(filename)
    