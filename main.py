
from neo4j_utility import *
from llm_extraction import *
from firecrawl_scraping import *
from utility import *




if __name__ == "__main__":
    client = True
    processed_name = 'beeline'
    
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


    kg_construction(processed_name, extraction_file_path)


