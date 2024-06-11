from edgar import Company

def get_company_info_from_cik(cik):
    company = Company(cik)
    return company.to_dict(), company