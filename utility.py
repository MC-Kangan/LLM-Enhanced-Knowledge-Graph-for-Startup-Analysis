import json

# Function to read a markdown file
def read_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to read a JSON file
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def process_company_name(name):
    name = name.lower()
    return name.replace(' ', '_').replace('/', '_').replace(';', '_').replace('-', '_').replace(',', '').replace('.', '_').replace("(", '').replace(')', '')
    