from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage 
from dotenv import load_dotenv
from datetime import datetime
from os.path import exists
import tiktoken
from firecrawl_scraping import *
from utility import *
import re
import os
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import StrOutputParser
import json



class ProductDescription(BaseModel):
    name: str = Field(..., alias='summarised name of product')
    description: str = Field(..., alias='concise features description of the product or service')

class SummaryProductDescription(BaseModel):
    name: str = Field(..., alias='summarised name of the main product offerings of the company')
    description: str = Field(..., alias='summary of product offering of the company')

class ClientDescription(BaseModel):
    name: str = Field(..., alias='name of the client or partner')
    description: Optional[str] = Field(None, alias='description of the usecase')

class ExtractedInformation(BaseModel):
    product_descriptions: Optional[List[ProductDescription]] = None
    summary_product_description: Optional[SummaryProductDescription] = None
    client_descriptions: Optional[List[ClientDescription]] = None
    
class ValidatedClientDescription(BaseModel):
    name: str = Field(..., alias='name of the client or partner')
    entity_type: Literal["person", "company", "general_entity", "other", "school"]
    product_used: Optional[str] = Field(None, alias='summary of the product or service used by the client or partner')
    description: Optional[str] = Field(None, alias='description of the usecase')

class ValidatedExtractedInformation(BaseModel):
    # product_descriptions: Optional[List[ProductDescription]] = None
    # summary_product_description: Optional[SummaryProductDescription] = None
    client_descriptions: Optional[List[ValidatedClientDescription]] = None

def remove_irregular_js_content(markdown_content):
    # Regex patterns to identify unwanted content
    patterns = [
        # r"(?s){.*?}",  # Matches JSON-like structures
        # r"\<.*?\>",  # Matches HTML tags
        r"vwo_\$.*?\;",  # Matches specific unwanted JS code snippets
        # r"\[.*?\]",  # Matches content inside square brackets (if not markdown links)
        # r"\\{2,}",  # Matches multiple backslashes
        # r"\\n",  # Matches escaped newlines
        # r"\*{2,}",  # Matches multiple asterisks
        # r'^[\s\W]*$' # lines with only signs
    ]

    # Remove patterns from the content
    for pattern in patterns:
        markdown_content = re.sub(pattern, '', markdown_content, flags=re.MULTILINE)

    # Remove lines that contain "vwo" and its variants
    markdown_content = "\n".join([line for line in markdown_content.splitlines() if not re.search(r'vwo', line, re.IGNORECASE)])

    return markdown_content

def remove_lines_with_only_signs(markdown_content):
    # Regex patterns to identify unwanted content
    patterns = [
        r'^[\s\W]*$' # lines with only signs
    ]

    # Remove patterns from the content
    for pattern in patterns:
        markdown_content = re.sub(pattern, '', markdown_content, flags=re.MULTILINE)

    return markdown_content

def remove_links_and_images(markdown_text):
    # Regex to match content inside parentheses following an image or link markdown pattern, including the parentheses
    pattern = r'(\[.*?\])\(.*?\)'
    
    # Replace the entire match with only the content inside the square brackets
    cleaned_text = re.sub(pattern, r'\1', markdown_text)
    
    return cleaned_text

def remove_duplicate_lines(text):
    seen_lines = set()
    unique_lines = []
    for line in text.splitlines():
        if line not in seen_lines:
            unique_lines.append(line)
            seen_lines.add(line)
    return "\n".join(unique_lines)

def remove_empty_lines(markdown_content):
    # Remove empty lines but keep lines with spaces
    markdown_content = "\n".join([line for line in markdown_content.splitlines() if line.strip() != ""])
    return markdown_content

def clean_scraped_content(markdown_content):
    # Remove irregular JS content
    cleaned_content = remove_irregular_js_content(markdown_content)
    
    # Remove links and images
    cleaned_content = remove_links_and_images(cleaned_content)
    
    # Remove duplicated lines
    cleaned_content = remove_duplicate_lines(cleaned_content)
    
    # Remove lines with only signs
    cleaned_content = remove_lines_with_only_signs(cleaned_content)
    
    # Remove empty lines only
    cleaned_content = remove_empty_lines(cleaned_content)

    return cleaned_content

def count_tokens(input_string: str) -> int:
    tokenizer = tiktoken.encoding_for_model("gpt-4o")

    tokens = tokenizer.encode(input_string)

    return len(tokens)

def calculate_cost(input_string: str, cost_per_million_tokens: float = 5) -> float:
    num_tokens = count_tokens(input_string)

    total_cost = (num_tokens / 1_000_000) * cost_per_million_tokens

    return total_cost

def is_markdown_file_empty(file_path):
    # Check if file exists
    if not os.path.exists(file_path):
        return True

    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read().strip()

    # Check if content is empty
    return len(content) == 0

def create_empty_json_file(output_path):
    empty_data = {}
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(empty_data, json_file, indent=4)
    print(f"Empty JSON file created at {output_path}")

def llm_summary(text, model_name="gpt-4o"):
    system_message = """
    You are an intelligent text extraction and conversion assistant. Your task is to extract information 
    from the given text and convert it into a text (string) format. 
    The output response should contain only the data extracted from the text, with no additional commentary, explanations, or extraneous information.
    If the required information could not be found from the given source, return nothing. Do not hallucinate.
    """

    # Define the extraction prompt
    extraction_prompt = """
    You are provided with a text obtained from a company's webpage. Your task is to extract any sections or paragraphs that are relevant to the specified information of interest.

    ## Information of Interest:

    1. **About Product or Service**:
    - Any details about the products or services the company offers, including their features.

    2. **About Partner or Client**:
    - Any information about the company's partners or clients.
    - Any use cases (case studies) describing how a client is using the company's product or service.
    - Any quotes or reviews by the clients.
    
    ## Note:
    Sometimes, the company does not explicit describe their clients and the client use case, instead, they will only display clients' logos. 
    You then need to extract client's name from their logos. 
    
    ## Instructions:
    - Do not summarize the content. Extract the raw lines or sections as they are.
    - If you are unsure about the relevance of the information, include it to ensure comprehensive coverage.
    - Output the extracted information in standard text format.

    ## Examples:

    ### Example 1: Product or Service
    If the input text contains:
    "Our company offers innovative cloud solutions that help businesses streamline their operations. Our key features include scalability, security, and ease of use.
    We partner with leading firms such as TechCorp and SoftInc to deliver top-notch services."

    The output should be:
    "Our company offers innovative cloud solutions that help businesses streamline their operations. Our key features include scalability, security, and ease of use.
    We partner with leading firms such as TechCorp and SoftInc to deliver top-notch services."

    ### Example 2: Client Logos
    If the input text contains:
    "Our platform and service is trusted by these innovative companies:
    ![Nationwide Logo]
    ![Freedom 365 Logo]
    ![Bestow Logo]
    ..."
    
    The output should be:
    "Our platform and service is trusted by these innovative companies: 
    Clients are: Nationwide, Freedom 365, Bestow..."
   
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("system", extraction_prompt),
            ("human", "Use the given text to extract information: {input}"),
            ("human", """
                Here are the rules that you need to adhere:
                ## Rules:
                - Make sure to answer in the standard text format.
                - If no information is provided, return nothing.
                - DO NOT HALLUCINATE.
             """),
        ]
    )
    
    llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_KEY'),
                    temperature=0, 
                    model_name=model_name)

    llm_chain = prompt | llm | StrOutputParser()

    response = llm_chain.invoke({'input': text})
    
    return response


def llm_summary_execution(processed_name:str, 
                          scrape_file_path:str,
                          summary_file_path:str,
                          overwrite:bool = False, 
                          model_name:str = 'gpt-4o-mini'):

    scrape_data = read_json_file(scrape_file_path)
    
    file_modified = False

    # Load existing data if the file exists
    if os.path.exists(summary_file_path):
        with open(summary_file_path, 'r') as file:
            extracted_data = json.load(file)
    else:
        extracted_data = {}

    for endpoint, content in scrape_data.items():
        if endpoint in ['timestamp', 'processed_company', 'url']:
            continue
        if endpoint in extracted_data and not overwrite:
            print(f"Company: {processed_name}; Skipping {endpoint} as it already exists and overwrite is set to False.")
            continue  # Skip this URL and move to the next one
        else:
            clean_content = clean_scraped_content(content)
            extracted_data[endpoint] = llm_summary(text = clean_content, model_name = model_name)
            print(f'Company: {processed_name}; Content in {endpoint} is extracted.')
            
            current_dateTime = datetime.now(pytz.timezone('Etc/GMT'))
            extracted_data['timestamp'] = current_dateTime.strftime(format = "%Y-%m-%d %H:%M") + ' Etc/GMT'
            file_modified = True
    
    if file_modified:
        extracted_data['processed_company'] = processed_name
        extracted_data['url'] = scrape_data['url']
        extracted_data['model_name'] = model_name
        write_json_file(summary_file_path, extracted_data)
        
    return extracted_data

def initial_extraction(text: str, model_name: str = 'gpt-4o', additional_context: str = None) -> ExtractedInformation:
    
    # Patch the OpenAI client with Instructor
    client = instructor.from_openai(OpenAI(api_key=os.getenv('OPENAI_KEY')))
    
    system_message = """
    You are an intelligent text extraction and conversion assistant. Your task is to extract structured information 
    from the given text and convert it into a structured format. 
    The output response should contain only the data extracted from the text, with no additional commentary, explanations, or extraneous information.
    If the required information could not be found from the given source, return nothing for that field. Do not hallucinate.
    """
    
    custom_extraction_prompt = """
    Extract the following information from the text extracted from a webpage of a company:

    1. Product Description:
    - What service or product does the company provide?
    - What features does the product or service have?
    Note: If the company has more than one product or service, automatically detect and list each product with its relevant details.
    
    2. Summary of Product Offering:
    - Summary of the description of the service that the company provide, taking into consideration of all the product offerings.
    Note: Do not include any company-specific information in the summary, such as company name and location.
    
    3. Client Description:
    - Name of the corporate client or partner. 
    - Description of the use case.
    Note: Focus on the extraction of company's name, instead of individuals.
    Note: If the description of the use case is not mentioned, it should be None.
    

    Output in a structured format.
    """
    
    rule_prompt = """
                Here are the rules that you need to adhere:
                    ## Rules:
                    - The aim is to achieve simplicity and clarity in the extracted text.
                    - Make sure to answer in the structured format.
                    - If no information is provided for any of the fields, return nothing of that field.
                    - DO NOT HALLUCINATE.
                """
    
    extraction_prompt = f"""
    {system_message}
    {custom_extraction_prompt}
    """
    
    if additional_context:
        response = client.chat.completions.create(
            model=model_name, 
            response_model=ExtractedInformation,
            messages=[
                {"role": "system", "content": extraction_prompt},
                {"role": "user", "content": f"Use the given text to extract information: {text}"},
                {"role": "user", "content": f"""Here are some additional descriptions about this company for your reference:
                                                {additional_context}"""},
                {"role": "user", "content": rule_prompt}
            ]
        )
        
    else:
        response = client.chat.completions.create(
            model=model_name, 
            response_model=ExtractedInformation,
            messages=[
                {"role": "system", "content": extraction_prompt},
                {"role": "user", "content": f"Use the given text to extract information: {text}"},
                {"role": "user", "content": rule_prompt}
            ]
        )
    return response

def information_validation(products: list, clients: list, summary: dict, model_name: str = 'gpt-4o') -> ValidatedExtractedInformation:
    
    # Patch the OpenAI client with Instructor
    client = instructor.from_openai(OpenAI(api_key=os.getenv('OPENAI_KEY')))
    
    system_message = """
    You are an intelligent text extraction and conversion assistant. Your task is to validate the client information, classify the client names into different entity types, and determine which product is likely used by the client. 
    The output response should contain only the data validated and assigned, with no additional commentary, explanations, or extraneous information.
    If the required information could not be found from the given source, return nothing for that field. Do not hallucinate.
    """
    
    product_info = "\n".join([f"Product: {p['name']}; Description: {p['description']}" for p in products])
    client_info = "\n".join([f"Client: {c['name']}; Description: {c['description']}" for c in clients])
    summary_info = f"{summary['name']}: {summary['description']}"
    
    few_shot_examples = """
        ## Example 1:
        Client Name: Mike Johnson, CEO of TechCorp
        Entity_type: person
        - Reason: Mike Johnson is the name of a person. 
        
        ## Example 2:
        Client Name: Government
        Entity_type: general_entity
        - Reason: "Government" is a general entity, not a specific company.

        ## Example 3:
        Client Name: Innovative Solutions LLC
        Entity_type: company
        - Reason: Innovative Solutions LLC is a specific company name.
        
        ## Example 4:
        Client Name: A US resort
        Entity_type: general_entity
        - Reason: "A US resort" is a general description, not a specific company name.
    
        ## Example 5: 
        Client Name: University College London
        Entity_type: school
        - Reason: University College London is a specific school name.
    """

    validation_prompt = f"""
    {system_message}
    Here is the product information extracted:
    {product_info}
    
    Here is the summary of product offerings of the company:
    {summary_info}
    
    Here are the clients and their use cases:
    {client_info}
    
    Your task is to:
    1. Classify each client name into one of the following entity types: person, company, general_entity, school, or other.
       Note: the entity type "company" should be given to specific companies, with company names.
    2. Based on the product descriptions and client use cases, assign the most likely product used by each client. 
       If you are not confident about which product the client uses, return None for that field.

    Here are some examples regarding the classifying clients into different entity types:
    {few_shot_examples}

    Output in a structured format.
    """
    
    response = client.chat.completions.create(
        model=model_name,
        response_model=ValidatedExtractedInformation,
        messages=[
            {"role": "system", "content": validation_prompt},
            {"role": "user", "content": """
                Here are the rules that you need to adhere:
                ## Rules:
                - Classify each client name into one of the following entity types: person, company, general_entity, school, or other.
                - Assign the most likely product used by each client based on the provided product descriptions and use cases.
                - If the product used is not clear, return None for that field.
                - Make sure to answer in the structured format.
                - DO NOT HALLUCINATE.
            """},
        ]
    )
    return response

def llm_extraction_execution(processed_name:str, 
                             summary_file_path:str,
                             extraction_file_path:str, 
                             include_additional_context:bool = True, 
                             model_name:str = 'gpt-4o', 
                             overwrite:bool = False):
    
    if not overwrite and os.path.exists(extraction_file_path):
        print(f"Company: {processed_name}; Skipping extraction as the extraction file already exists and overwrite is set to False.")
        return None
    else:
        if os.path.exists(summary_file_path):
            summary = read_json_file(summary_file_path)

            combined_summary = f"## Main Page:\n {summary['main_page']}\n----------------\n"

            for endpoint, text in summary.items():
                if endpoint not in ["main_page", "timestamp", "processed_company", "url"]:
                    combined_summary += f"## {endpoint}:\n{text}\n----------------\n"
            
            print(f"Company: {processed_name}; Information extraction begins.")
            if include_additional_context:
                context = get_additional_info(processed_name, 'description')
                
                print(f'Company: {processed_name}; Estimated Cost: ${calculate_cost(combined_summary + context)}')
                print(f'Company: {processed_name}; Pitchbook description obtained: {context}')
                
                initial_response = initial_extraction(text = combined_summary, 
                                                additional_context = context,
                                                model_name = model_name).dict()
                
            else:
                print(f'Company: {processed_name}; Estimated Cost: ${calculate_cost(combined_summary)}')
                initial_response = initial_extraction(text = combined_summary, 
                                            additional_context = None,
                                            model_name = model_name).dict()
            
            print(f'Company: {processed_name}; PART 1 - Initial extraction is completed.')
            
            result = initial_response
            
            if initial_response['client_descriptions']:
                products = initial_response['product_descriptions'] if initial_response['product_descriptions'] else []
                clients = initial_response['client_descriptions'] if initial_response['client_descriptions'] else []
                summary = initial_response['summary_product_description']

                validated_response = information_validation(products, clients, summary, model_name)
                print(f'Company: {processed_name}; PART 2 - Information validation is completed.')
                result['validated_client_descriptions'] = validated_response.dict()['client_descriptions']
                
            else:
                print(f'Company: {processed_name}; PART 2 - Skipped, due to lack of client information.')
                result['validated_client_descriptions'] = None
            
            current_dateTime = datetime.now(pytz.timezone('Etc/GMT'))
            result['timestamp'] = current_dateTime.strftime(format = "%Y-%m-%d %H:%M") + ' Etc/GMT'
            result['processed_company'] = processed_name
            result['url'] = read_json_file(summary_file_path)['url']
            
            if get_additional_info(processed_name, 'companies'):
                result['name'] = get_additional_info(processed_name, 'companies')
            elif get_additional_client_info(processed_name, 'name'):
                result['name'] = get_additional_client_info(processed_name, 'name')
            else:
                result['name'] = None

            write_json_file(extraction_file_path, result)
            
            return result
        else:
            print(f'Summary file: {summary_file_path} does not exist.')
            return None

def add_client_url_to_extraction_output(processed_name:str, extraction_file_path:str, verbose:bool = False, overwrite:bool = False):
    data = read_json_file(extraction_file_path)
    
    # Check if the company has any clients
    if data['validated_client_descriptions']:
        
        # If the url key already exists, meaning the urls have been added and overwrite is False
        if 'url' in data['validated_client_descriptions'][0].keys() and not overwrite:
            print(f"Company: {processed_name}; Skipping as the clients' URLs have been added and overwrite is set to False.")
        else:
            for client in data['validated_client_descriptions']:
                if client['entity_type'] != 'company':
                    client['url'] = None
                else:
                    url = get_and_verify_client_link(client['name'], verbose = verbose)
                    client['url'] = url
            print(f"Company: {processed_name}; Client is extracted.")
    else:
        print(f"Company: {processed_name}; No clients' information.")
    write_json_file(extraction_file_path, data)
    return None

    
def get_embedding(text:str, embedding_model:str="text-embedding-3-small"):
   client_openai = OpenAI(api_key=os.getenv('OPENAI_KEY'))
   
   text = text.replace("\n", " ")
   return client_openai.embeddings.create(input = [text], model=embedding_model).data[0].embedding


def get_product_embedding(processed_name:str, extraction_file_path:str, embedding_model:str="text-embedding-3-small"):
    
    data = read_json_file(extraction_file_path)
    # Check wheather embedding has already been done
    if 'name_embedding' in data['summary_product_description']:
        print(f'Company: {processed_name}; Embedding has already been done.')
        pass
    else:
        product_lst = data['product_descriptions']
        for product in product_lst:
            product['description_embedding'] = get_embedding(text = product['description'],
                                                                embedding_model = embedding_model)
            product['name_embedding'] = get_embedding(text = product['name'],
                                                                embedding_model = embedding_model)

        summary_product = data['summary_product_description']
        summary_product['description_embedding'] = get_embedding(text = summary_product['description'],
                                                                embedding_model = embedding_model)
        summary_product['name_embedding'] = get_embedding(text = summary_product['name'],
                                                                embedding_model = embedding_model)
        print(f'Company: {processed_name}; Embedding is completed.')
        write_json_file(extraction_file_path, data)
    
    return data

def update_client_list_outdated(processed_name:str, extraction_file_path:str, client_file_path:str = 'data/client_info.json', verbose:bool = False):
    
    data = read_json_file(extraction_file_path)
    client_info = read_json_file(client_file_path)
        
    if data['validated_client_descriptions']:
        try:        
            for client in data['validated_client_descriptions']:
                if client['entity_type'] != 'company':
                    continue
                # If a company's name already exists in the dictionary and the url is unchanged
                if client['name'] in client_info and client['url'] == client_info[client['name']]['url'] :
                    # If its service provider does not appear in the saved list, then append it
                    if processed_name not in client_info[client['name']]['service_provider_processed']:
                        client_info[client['name']]['service_provider_processed'].append(processed_name)
                        client_info[client['name']]['service_provider'].append(get_additional_info(processed_name, 'companies'))
                        client_info[client['name']]['service_provider_url'].append('https://' + get_additional_info(processed_name, 'processed_url'))
                    else:
                        if verbose:
                            print(f'Company {client["name"]} has already been recorded.')
                
                # If a company's name already does not exist, add the new company
                else:
                    client_info[client['name']] = {'processed_name': process_company_name(client['name']),
                                        'url': client['url'],
                                        'service_provider_processed': [processed_name],
                                        'service_provider': [get_additional_info(processed_name, 'companies')],
                                        'service_provider_url': ['https://' + get_additional_info(processed_name, 'processed_url')]
                                        }
            print(f"Company: {data['processed_company']}; Clients information is updated.")
            write_json_file(client_file_path, client_info)
        except Exception as e:
            print(f'Company: {processed_name}; Error occurred: {e}')
    else:
        print(f'Company: {processed_name}; No clients to be updated')


def update_client_list(processed_name:str, extraction_file_path:str, client_file_path:str = 'data/client_info.json', verbose:bool = False):
    
    data = read_json_file(extraction_file_path)
    client_info = read_json_file(client_file_path)
        
    if data['validated_client_descriptions']:
        try:        
            for client in data['validated_client_descriptions']:
                if client['entity_type'] != 'company':
                    continue
                
                if client['url']:
                    # If a company's name already exists in the dictionary and the url is unchanged
                    if client['url'] in client_info:
                        # If its service provider does not appear in the saved list, then append it
                        if processed_name not in client_info[client['url']]['service_provider_processed']:
                            client_info[client['url']]['service_provider_processed'].append(processed_name)
                            client_info[client['url']]['service_provider'].append(get_additional_info(processed_name, 'companies'))
                            client_info[client['url']]['service_provider_url'].append('https://' + get_additional_info(processed_name, 'processed_url'))
                        else:
                            if verbose:
                                print(f'Client {client["name"]} has already been recorded.')
                    
                    # If a company's name already does not exist, add the new company
                    else:
                        client_info[client['url']] = {
                                            'name': client['name'],
                                            'processed_name': process_company_name(client['name']),
                                            'service_provider_processed': [processed_name],
                                            'service_provider': [get_additional_info(processed_name, 'companies')],
                                            'service_provider_url': ['https://' + get_additional_info(processed_name, 'processed_url')]
                                            }
                else:
                    print(f'Client {client["name"]}: URL could not be found')
        
            print(f"Company: {data['processed_company']}; Clients information is updated.")
            write_json_file(client_file_path, client_info)
        except Exception as e:
            print(f'Company: {processed_name}; Error occurred: {e}')
    else:
        print(f'Company: {processed_name}; No clients to be updated')
        
        
        
if __name__ == "__main__":
    client = True
    processed_name = 'docmagic'
    
    if not client:
        scrape_file_path = f'scraping_output_v2_raw/{processed_name}.json'
        summary_file_path = f'extraction_summary_v2/{processed_name}_summary_str.json'
        extraction_file_path = f'extraction_output_v2/{processed_name}_extraction.json'

        _ = llm_summary_execution(processed_name = processed_name,
                                        scrape_file_path = scrape_file_path,
                                        summary_file_path = summary_file_path)

        _ = llm_extraction_execution(processed_name = processed_name,
                                summary_file_path = summary_file_path,
                                extraction_file_path = extraction_file_path, 
                                include_additional_context = True, 
                                overwrite = False)

        _ = get_product_embedding(processed_name = processed_name,
                            extraction_file_path = extraction_file_path)
        
        _ = add_client_url_to_extraction_output(processed_name = processed_name,
                                    extraction_file_path = extraction_file_path)

        _ = update_client_list(processed_name = processed_name,
                        extraction_file_path = extraction_file_path,
                        client_file_path = 'data/client_info.json')
    else:
        scrape_file_path = f'client_scraping_output/{processed_name}.json'
        summary_file_path = f'client_extraction_summary/{processed_name}_summary.json'
        extraction_file_path = f'client_extraction_output/{processed_name}_extraction.json'

        _ = llm_summary_execution(processed_name = processed_name,
                                        scrape_file_path = scrape_file_path,
                                        summary_file_path = summary_file_path,
                                        overwrite = False)

        _ = llm_extraction_execution(processed_name = processed_name,
                                summary_file_path = summary_file_path,
                                extraction_file_path = extraction_file_path, 
                                include_additional_context = False, 
                                overwrite = False)
        
        _ = get_product_embedding(processed_name = processed_name,
                    extraction_file_path = extraction_file_path)

        _ = add_client_url_to_extraction_output(processed_name = processed_name,
                                            extraction_file_path = extraction_file_path)

