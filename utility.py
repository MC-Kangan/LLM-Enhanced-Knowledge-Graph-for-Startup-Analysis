import json
import pandas as pd

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

def get_additional_info(processed_name:str, column_name:str, verbose:bool = False):
    
    try: 
        df_all = pd.read_csv('data/PitchBook_All_Columns_2024_07_04_14_48_36_accessibility.csv')
        df_all['companies'] = df_all['companies'].str.replace(r'\s*\(.*?\)\s*', '', regex=True)
        df_all['processed_name'] = df_all['companies'].apply(process_company_name)
        
        df_select = df_all[df_all['processed_name'] == processed_name]
        if len(df_select) > 0:
            return df_select[column_name].iloc[0]
        else:
            return None
    except Exception as e:
        if verbose:
            print(f'Error has occured when searching {processed_name}: {e}')
        return None
    
def get_additional_client_info(processed_name:str, feature_name:str, verbose:bool = False):
    try:
        data = read_json_file('data/client_info.json')
        
        for url, details in data.items():
            if details['processed_name'] == processed_name:
                return details[feature_name]
        return None
    except Exception as e:
        if verbose:
            print(f'Error has occured when searching {processed_name}: {e}')
        return None

    