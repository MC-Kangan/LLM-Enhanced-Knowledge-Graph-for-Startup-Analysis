
from neo4j_utility import *
from llm_extraction import *
from firecrawl_scraping import *
from utility import *
import os
import pandas as pd
import logging
import time

if __name__ == "__main__":
    
    # Logging configuration
    logging.basicConfig(filename='pipeline.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')
    
    df = pd.read_csv('data/merge_url_companies.csv')
    random_sample = df.sample(n=20, random_state=42)

    scrape_file_dir = f'test/scraping_output_v2_raw'
    summary_file_dir = f'test/extraction_summary_v2'
    extraction_file_dir = f'test/extraction_output_v2'
    client_file_dir = f'test/client_info.json'

    inspection_url_list = ['https://www.housecanary.com', 'https://www.tooodooo.com', 'https://www.360factors.com', 'https://www.rakenapp.com', 'https://www.digitalonboarding.com']    
    inspection_processed_name_list = ['housecanary', 'tooodooo', '360factors', 'raken', 'digital_onboarding']
    
    # for index, row in random_sample.iterrows():
        
    #     base_url = f'https://'+row['processed_url']
       
    #     all_urls, related_urls = get_related_urls(base_url)

    #     logging.info(f'Function get_related_urls executed on company {row["processed_name"]}')
        
    #     # If there are over 10 
    #     # if len(related_urls) > 10:
    #     #     related_urls = select_urls(related_urls, 10)

    #     processed_name = row["processed_name"]
        
    #     result = crawl_data(base_url, related_urls, f'{scrape_file_dir}/{processed_name}.json', overwrite=False)
    #     logging.info(f'Function crawl_data executed on company {row["processed_name"]} with {len(related_urls)} pages')
        
    # for index in range(len(inspection_url_list)):
    #     base_url = inspection_url_list[index]
    #     processed_name = inspection_processed_name_list[index]
        
    #     all_urls, related_urls = get_related_urls(base_url)

    #     logging.info(f'Function get_related_urls executed on company {processed_name}')
        

    #     result = crawl_data(base_url, related_urls, f'{scrape_file_dir}/{processed_name}.json', overwrite=False)
    #     logging.info(f'Function crawl_data executed on company {processed_name} with {len(related_urls)} pages')
        

    
    doc_list = os.listdir(f'{scrape_file_dir}')
    for doc in doc_list[1:]:
        processed_name = doc.replace('.json', '')
        
        scrape_file_path = f'{scrape_file_dir}/{processed_name}.json'
        summary_file_path = f'{summary_file_dir}/{processed_name}_summary.json'
        extraction_file_path = f'{extraction_file_dir}/{processed_name}_extraction.json'
        
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
        
        _ = troubleshoot_llm_output(processed_name = processed_name,
                            extraction_file_path = extraction_file_path)

        _ = update_client_list(processed_name = processed_name,
                        extraction_file_path = extraction_file_path,
                        client_file_path = client_file_dir)




    