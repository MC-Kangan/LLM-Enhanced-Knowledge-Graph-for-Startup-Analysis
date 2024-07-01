from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import os

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
    