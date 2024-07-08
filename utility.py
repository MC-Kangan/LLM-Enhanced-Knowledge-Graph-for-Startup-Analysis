import json

# Function to read a markdown file
def read_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to read a JSON file
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
# Update the JSON data with new fields
def update_json_data(data, new_fields):
    data.update(new_fields)
    return data

# Write the updated JSON data back to the file
def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)    

def process_company_name(name):
    name = name.lower()
    return name.replace(' ', '_').replace('/', '_').replace(';', '_').replace('-', '_').replace(',', '').replace('.', '_').replace("(", '').replace(')', '')
    