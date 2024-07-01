from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage 
from dotenv import load_dotenv
from datetime import datetime
from os.path import exists
from firecrawl_scraping import *
from utility import *
import re
import os

def remove_irregular_content(markdown_content):
    # Regex patterns to identify unwanted content
    patterns = [
        # r"(?s){.*?}",  # Matches JSON-like structures
        # r"\<.*?\>",  # Matches HTML tags
        r"vwo_\$.*?\;",  # Matches specific unwanted JS code snippets
        # r"\[.*?\]",  # Matches content inside square brackets (if not markdown links)
        # r"\\{2,}",  # Matches multiple backslashes
        # r"\\n",  # Matches escaped newlines
        # r"\*{2,}",  # Matches multiple asterisks
    ]

    # Remove patterns from the content
    for pattern in patterns:
        markdown_content = re.sub(pattern, '', markdown_content)

    # Remove lines that contain "vwo" and its variants
    markdown_content = "\n".join([line for line in markdown_content.splitlines() if not re.search(r'vwo', line, re.IGNORECASE)])

    return markdown_content

def remove_empty_lines_only(markdown_content):
    # Remove empty lines but keep lines with spaces
    markdown_content = "\n".join([line for line in markdown_content.splitlines() if line.strip() != ""])
    return markdown_content

def clean_scraped_content(markdown_content):
    # Remove irregular content
    cleaned_content = remove_irregular_content(markdown_content)

    # Remove empty lines only
    cleaned_content = remove_empty_lines_only(cleaned_content)

    # Additional heuristics can be added here if needed

    return cleaned_content


def info_extraction(text, model_name = "gpt-4o"):
    system_message_1 = """

        You are an intelligent text extraction and conversion assistant. Your task is to extract structured information 
        from the given text and convert it into a pure JSON format. 
        The JSON should contain only the structured data extracted from the text, with no additional commentary, explanations, or extraneous information. 
        You could encounter cases where you can't find the data of the fields you have to extract.
        Please process the following text and provide the output in pure JSON format with no words before or after the JSON:
        """
        
    system_message_2 = """          
        Extract the following information from the text extracted from a webpage of a company:

        ## 1. Product offering:
            - What service or product does the company provide?
            - What features does the product or service have?
            Note: If the company has more than 1 product or service, try to summarise information and return three main products only.

        ## 2. Client or partnership:
            - Who are the partners or clients of the company?
            - What are the clients or partners use this product for?
            - Logo of the clients or partners. The logo usually appears after some text regarding clients or partners. They are png or jpg format.
            Note: Not all the images files are logos of the clients or partners. Do not just extract all images that you found.

        Output in JSON format:
        {{
            "product_offering": {{
                "summarised_name_of_product_1": "concise features description of the product or service",
                "summarised_name_of_product_2": "concise features description of the product or service",
                "summarised_name_of_product_3": "concise features description of the product or service",
            }}
            "partners": {{
                "partner_name_1": "description of the usecase",
                "partner_name_2": "description of the usecase",
                ...
            }}
            "logos": "logo of client 1, such as https://www.company/client1_Logo.png", "logo of client 1, such as https://www.company/client2_Logo.png", ...
        }}

        Here are the rules that you need to adhere:
        ## Rules:
            - The aim is to achieve simplicity and clarity in the extracted text.
            - Make sure to answer in the correct JSON format.
            - If no information is provided for any of the fields, return nothing of that field.
            - DO NOT HALLUCINATE.
        """
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message_1),
            ("system", system_message_2),
            ("human", "Use the given text to extract information: {input}"),
            ("human", "Tip: Make sure to answer in the correct JSON format"),
        ]
    )

    llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_KEY'),
                    temperature = 0, 
                    model_name = "gpt-4o")

    llm_chain = prompt | llm | SimpleJsonOutputParser()

    response = llm_chain.invoke({'input': text})
    
    return response

def LLM_extraction_agent(filename, url):
    try:
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d')
        file_exists = exists(f'scraping_output/{filename}_{timestamp}.md')
        
        # Scrape data
        print('1. Scrape URL with Firecrawl')
        
        if file_exists:
            print('This URL has been scraped today')
            print('2: Read the scraped contents as a MD file')
        else:
            raw_data = scrape_data(url)
        
            print('2: Save scraped contents as a MD file')
            # Save raw data
            save_raw_data(raw_data, filename, timestamp, output_folder='scraping_output')
        
        raw_data = read_markdown_file(f'scraping_output/{filename}_{timestamp}.md')
        
        print('3: Clean scraped contents')
        # Clean the markdown file before further processing
        clean_data = clean_scraped_content(raw_data)
        
        print('4: Extract information using LLM')
        response = info_extraction(clean_data)
        
        print('4: Save extracted information as a JSON file')
        # Save the response dictionary to a JSON file
        output_file = f"extraction_output/{filename}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=4)

        print(f"Output saved to {output_file}")
        return response
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    
    