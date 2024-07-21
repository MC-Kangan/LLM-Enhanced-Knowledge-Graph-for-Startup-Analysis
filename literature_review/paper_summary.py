import requests
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json
import openai
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import StrOutputParser


# OpenAI API Key
openai.api_key = os.getenv('OPENAI_KEY')

# Path to the markdown file
markdown_file = 'PAPERREADME.md'

def read_markdown(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def extract_links(markdown_content):
    pattern = r'\[arxiv\]\((https://arxiv.org/abs/\d+\.\d+)\)'
    return re.findall(pattern, markdown_content)

def get_abstract(arxiv_url):
    response = requests.get(arxiv_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        abstract = soup.find('blockquote', class_='abstract mathjax').text.replace('Abstract:', '').strip()
        return abstract
    return None

def summarize_abstract(abstract):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant that summarizes research paper abstracts into concise bullet points. Focus on main findings and contributions."),
            ("human", f"Summarize the following abstract in bullet points:\n\n{abstract}"),
            ("human", """
                Here are the rules that you need to adhere:
                ## Rules:
                - Make sure to answer in the standard text format.
                - DO NOT HALLUCINATE.
             """),
        ]
    )
    
    llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_KEY'),
                    temperature=0, 
                    model_name="gpt-4o-mini")

    llm_chain = prompt | llm | StrOutputParser()

    response = llm_chain.invoke({'input': abstract})
    return response

def save_to_json(data, title):
    file_name = re.sub(r'\W+', '_', title) + '.json'
    file_path = os.path.join("reading_resource", file_name)
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    print(f"Saved: {file_path}")

def main():
    markdown_content = read_markdown(markdown_file)
    links = extract_links(markdown_content)
    
    for link in links:
        try:
            title = get_paper_title(link)
            abstract = get_abstract(link)
            
            if title and abstract:
                summary = summarize_abstract(abstract)
                data = {
                    'Title': title,
                    'Abstract': abstract,
                    'Summary': summary
                }
                save_to_json(data, title)
                print(f"Processed: {title}")
            else:
                print(f"Failed to process: {link}")
        except Exception as e:
            print(f"Error processing {link}: {e}")


def get_paper_title(arxiv_url):
    response = requests.get(arxiv_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', class_='title mathjax').text.replace('Title:', '').strip()
        return title
    return None

if __name__ == '__main__':
    main()
