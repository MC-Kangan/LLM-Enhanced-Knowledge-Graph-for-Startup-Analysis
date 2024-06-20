

def get_category(SIC):
    category = None
    if 1110 <= SIC and SIC <= 3220:
        category = 'Agriculture, Forestry and Fishing'
    elif 5101 <= SIC and SIC <= 9900:
        category = 'Mining and Quarrying'
    elif 10110 <= SIC and SIC <= 33200:
        category = 'Manufacturing'
    elif 35110 <= SIC and SIC <= 35300:
        category = 'Electricity, gas, steam and air conditioning supply'
    elif 36000 <= SIC and SIC <= 39000:
        category = 'Water supply, sewerage, waste management and remediation activities'
    elif 41100 <= SIC and SIC <= 43999:
        category = 'Construction'
    elif 45111 <= SIC and SIC <= 47990:
        category = 'Wholesale and retail trade; repair of motor vehicles and motorcycles'
    elif 49100 <= SIC and SIC <= 53202:
        category = 'Transportation and storage'
    elif 55100 <= SIC and SIC <= 56302:
        category = 'Accommodation and food service activities'
    elif 58110 <= SIC and SIC <= 63990:
        category = 'Information and communication'
    elif 64110 <= SIC and SIC <= 66300:
        category = 'Financial and insurance activities'
    elif 68100 <= SIC and SIC <= 68320:
        category = 'Real estate activities'
    elif 69101 <= SIC and SIC <= 75000:
        category = 'Professional, scientific and technical activities'
    elif 77110 <= SIC and SIC <= 82990:
        category = 'Administrative and support service activities'
    elif 84110 <= SIC and SIC <= 84300:
        category = 'Public administration and defence; compulsory social security' 
    elif 85100 <= SIC and SIC <= 85600:
        category = 'Education'
    elif 86101 <= SIC and SIC <= 88990:
        category = 'Human health and social work activities'
    elif 90010 <= SIC and SIC <= 93290:
        category = 'Arts, entertainment and recreation'
    elif 94110 <= SIC and SIC <= 96090:
        category = 'Other service activities'
    elif 97000 <= SIC and SIC <= 98200:
        category = 'Activities of households as employers; undifferentiated goods- and services-producing activities of households for own use'
    elif 99000 <= SIC and SIC <= 99999:
        category = 'Activities of extraterritorial organisations and bodies'
        
    return category
    