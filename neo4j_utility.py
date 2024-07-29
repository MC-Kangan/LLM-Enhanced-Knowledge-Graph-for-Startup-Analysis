import os
import glob
import json
import pandas as pd
from utility import *
from llm_extraction import *
from firecrawl_scraping import *
import numpy as np
from neo4j import GraphDatabase
from dotenv import load_dotenv
from neomodel import config, StructuredNode, StringProperty, FloatProperty, BooleanProperty, ArrayProperty, RelationshipTo

# Configure the database connection
config.DATABASE_URL = f"bolt://neo4j:{os.getenv('NEO4J_PASSWORD')}@localhost:7687"


class Company(StructuredNode):
    name = StringProperty()  # Removed unique_index
    processed_name = StringProperty(default=None)
    url = StringProperty(unique_index=True)  # Unique index on URL
    year_founded = StringProperty(default=None)
    valuation = FloatProperty(default=None)
    last_known_valuation_date = StringProperty(default=None)
    description = StringProperty(default=None)

    provides = RelationshipTo("Product", "PROVIDES")

class Product(StructuredNode):
    name = StringProperty(unique_index=True)
    description = StringProperty(default=None)
    name_embedding = ArrayProperty(default=None)
    description_embedding = ArrayProperty(default=None)
    summary_product = BooleanProperty(default=False)
    
    serves = RelationshipTo("Company", "SERVES")


def create_company_nodes(processed_name:str, extraction_file_path:str):
    company_data = read_json_file(extraction_file_path)
    company = Company.get_or_create({
        'url': company_data['url'],  # URL used as the unique index
        'name': get_additional_info(processed_name, 'companies'),
        'processed_name': processed_name,
        'year_founded': get_additional_info(processed_name, 'year_founded'),
        'valuation': get_additional_info(processed_name, 'last_known_valuation'),
        'last_known_valuation_date': get_additional_info(processed_name, 'last_known_valuation_date'),
        'description': get_additional_info(processed_name, 'description')
    })[0]
    return company

def load_json_file(directory, company_name):
    search_pattern = os.path.join(directory, f"{company_name}*.json")
    matching_files = glob.glob(search_pattern)
    
    if matching_files:
        file_path = matching_files[0]
        with open(file_path, 'r') as file:
            return json.load(file)
    else:
        print(f"No JSON file found for company {company_name}.")
        return None

def create_product_nodes(json_data):
    products = []
    if json_data:
        product_list = json_data['product_descriptions']
        product_list.append(json_data['summary_product_description'])
        
        summary_product_name = json_data['summary_product_description']['name']
        summary_product_description = json_data['summary_product_description']['description']
        summary_product_name_embedding = json_data['summary_product_description']['name_embedding']
        summary_product_description_embedding = json_data['summary_product_description']['description_embedding']
        
        for product in product_list:
            if product['name'].lower() != summary_product_name.lower():
                summary_product = False
                product_description = product['description']
                name_embedding = product['name_embedding']
                description_embedding = product['description_embedding']
            else:
                summary_product = True
                product_description = summary_product_description
                name_embedding = summary_product_name_embedding
                description_embedding = summary_product_description_embedding
            product_node = Product.get_or_create({
                'name': product['name'],
                'description': product_description,
                'summary_product': summary_product,
                'name_embedding': name_embedding,
                'description_embedding': description_embedding
            })[0]
            products.append(product_node)
    return products

def link_product_to_company(company, product):
    if not company.provides.is_connected(product):
        company.provides.connect(product)

def link_product_to_client(product, client_company):
    if not product.serves.is_connected(client_company):
        product.serves.connect(client_company)

def kg_construction(processed_name:str, extraction_file_path:str ):
    company = create_company_nodes(processed_name, extraction_file_path)
    json_data = read_json_file(extraction_file_path)
    if json_data:
        products = create_product_nodes(json_data)
        for product in products:
            link_product_to_company(company, product)
        
        if json_data['validated_client_descriptions']:
            for client in json_data['validated_client_descriptions']:
                if client['entity_type'] == 'company' and client['url']:
                    client_company = Company.get_or_create({
                        'url': client['url'],  # Use URL as the unique index
                        'name': client['name'],
                        'processed_name': process_company_name(client['name']),
                        'year_founded': None,
                        'valuation': None,
                        'last_known_valuation_date': None,
                        'description': None
                    })[0]
                    
                    product_name = client['product_used'] if client['product_used'] else json_data['summary_product_description']['name']
                    product_node = Product.get_or_create({
                        'name': product_name,
                        'description': None,
                        'summary_product': None
                    })[0]
                    
                    link_product_to_company(company, product_node)
                    link_product_to_client(product_node, client_company)
    print(f'Company {processed_name} is added to the graph.')


if __name__ == "__main__":
    pass