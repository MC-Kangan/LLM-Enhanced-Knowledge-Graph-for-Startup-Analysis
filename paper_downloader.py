import requests
import re
import os
from bs4 import BeautifulSoup

# Path to the markdown file
markdown_file = 'PAPERREADME.md'
# Path to the directory where PDFs will be saved
download_dir = 'reading_resource'
# Path to the log file
log_file = 'reading_resource/download_log.txt'

if not os.path.exists(download_dir):
    os.makedirs(download_dir)

def read_markdown(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def extract_links(markdown_content):
    pattern = r'\[arxiv\]\((https://arxiv.org/abs/\d+\.\d+)\)'
    return re.findall(pattern, markdown_content)

def get_pdf_url(arxiv_url):
    return arxiv_url.replace('/abs/', '/pdf/')

def get_paper_title(arxiv_url):
    response = requests.get(arxiv_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', class_='title mathjax').text.replace('Title:', '').strip()
        return title
    return None

def download_pdf(pdf_url, save_path):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return True
    return False

def log_download(log_path, message):
    with open(log_path, 'a') as log:
        log.write(message + '\n')

def main():
    markdown_content = read_markdown(markdown_file)
    links = extract_links(markdown_content)
    
    for link in links:
        pdf_url = get_pdf_url(link)
        title = get_paper_title(link)
        
        if title:
            save_path = os.path.join(download_dir, f"{title}.pdf")
            if download_pdf(pdf_url, save_path):
                log_download(log_file, f"Downloaded: {title} from {pdf_url}")
                print(f"Downloaded: {title}")
            else:
                log_download(log_file, f"Failed to download from {pdf_url}")
                print(f"Failed to download: {pdf_url}")
        else:
            log_download(log_file, f"Failed to fetch title for {link}")
            print(f"Failed to fetch title for: {link}")

if __name__ == '__main__':
    main()
