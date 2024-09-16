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

    
config.DATABASE_URL = f"bolt://neo4j:{os.getenv('NEO4J_PASSWORD')}@localhost:7687"

def build_connection():
    URI = os.getenv("NEO4J_URI")
    AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_INSTANCE_PASSWORD"))
    my_driver = GraphDatabase().driver(URI, auth=AUTH)
    config.DRIVER = my_driver

class Company(StructuredNode):
    name = StringProperty()  # Removed unique_index
    processed_name = StringProperty(default=None)
    url = StringProperty(unique_index=True)  # Unique index on URL
    year_founded = StringProperty(default=None)
    valuation = FloatProperty(default=None)
    last_known_valuation_date = StringProperty(default=None)
    last_known_valuation_deal_type = StringProperty(default=None)
    description = StringProperty(default=None)
    primary_industry_sector = StringProperty(default=None)
    primary_industry_group = StringProperty(default=None)
    verticals = StringProperty(default=None)
    total_raised = FloatProperty(default=None)
    hq_location = StringProperty(default=None)
    hq_country_territory_region = StringProperty(default=None)
    hq_city = StringProperty(default=None)
    cluster_name_detail = StringProperty(default=None)

    provides = RelationshipTo("Product", "PROVIDES")

class Product(StructuredNode):
    name = StringProperty()
    company_url = StringProperty()
    product_key = StringProperty(unique_index=True)
    description = StringProperty(defult=None)
    name_embedding = ArrayProperty(default=None)
    description_embedding = ArrayProperty(default=None)
    summary_product = BooleanProperty(default=False)
    
    serves = RelationshipTo("Company", "SERVES")

def get_or_create_company(url, data):
    # Attempt to find the company node by URL
    existing_nodes = Company.nodes.filter(url=url)
    if existing_nodes:
        # If the node exists, update the existing node's attributes with the new data
        company_node = existing_nodes[0]
        for key, value in data.items():
            if value is not None:
                setattr(company_node, key, value)
        company_node.save()  # Save the updated node to the database
    else:
        # If the company does not exist, create a new one
        company_node = Company(**data)
        company_node.save()
    return company_node

def create_company_nodes(processed_name: str, extraction_file_path: str):
    company_data = read_json_file(extraction_file_path)
    company_info = {
        'url': company_data['url'],  # URL used as the unique index
        'name': company_data['name'],
        'processed_name': processed_name,
        'year_founded': get_additional_info(processed_name, 'year_founded'),
        'valuation': get_additional_info(processed_name, 'last_known_valuation'),
        'last_known_valuation_date': get_additional_info(processed_name, 'last_known_valuation_date'),
        'last_known_valuation_deal_type': get_additional_info(processed_name, 'last_known_valuation_deal_type'),
        'description': get_additional_info(processed_name, 'description'),
        'primary_industry_sector': get_additional_info(processed_name, 'primary_industry_sector'),
        'primary_industry_group': get_additional_info(processed_name, 'primary_industry_group'),
        'verticals': get_additional_info(processed_name, 'verticals'),
        'total_raised': get_additional_info(processed_name, 'total_raised'),
        'hq_location': get_additional_info(processed_name, 'hq_location'),
        'hq_country_territory_region': get_additional_info(processed_name, 'hq_country_territory_region'),
        'hq_city': get_additional_info(processed_name, 'hq_city')
    }
    company_node = get_or_create_company(company_data['url'], company_info)
    return company_node

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
        company_url = json_data['url']
        
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
                
            product_key = f"{product['name']} {json_data['name']}"
            product_node = Product.get_or_create({
                'name': product['name'],
                'company_url': company_url,
                'product_key': product_key,
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


def kg_construction(processed_name: str, extraction_file_path: str):
    company = create_company_nodes(processed_name, extraction_file_path)
    json_data = read_json_file(extraction_file_path)
    if json_data:
        products = create_product_nodes(json_data)
        for product in products:
            link_product_to_company(company, product)

        if json_data['validated_client_descriptions']:
            for client in json_data['validated_client_descriptions']:
                if client['entity_type'] == 'company' and client['url']:
                    client_info = {
                        'url': client['url'],
                        'name': client['name'],
                        'processed_name': process_company_name(client['name']),
                        # Add more attributes if needed
                    }
                    client_company = get_or_create_company(client['url'], client_info)

                    product_name = client['product_used'] if client['product_used'] else json_data['summary_product_description']['name']
                    
                    product_key = f"{product_name} {json_data['name']}"
                    # This step only get the product that is previously loaded
                    product_node = Product.get_or_create({
                        'name': product_name,
                        'product_key': product_key,
                        'company_url': json_data['url'] 
                    })[0]
                    
                    link_product_to_company(company, product_node)
                    link_product_to_client(product_node, client_company)
                    
    print(f'Company {processed_name} is added to the graph.')
    

if __name__ == "__main__":
        
    processed_name = 'jll'
    extraction_file_path = f'{os.getenv("client_extraction_folder")}/{processed_name}_extraction.json'
    kg_construction(processed_name, extraction_file_path)