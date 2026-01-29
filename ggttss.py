import pycountry
from pathlib import Path
import json
BASE_DIR = Path(__file__).parent
COUNTRY_JSON = BASE_DIR / "countries.json"

def get_country_name(short_code):
    """
    Converts 2-letter (Alpha-2) or 3-letter (Alpha-3) 
    country codes to their full official names.
    """
    # Clean the input (remove spaces and make uppercase)
    code = short_code.strip().upper()
    
    # Try to find the country by alpha_2 or alpha_3 code
    country = pycountry.countries.get(alpha_2=code) or pycountry.countries.get(alpha_3=code)
    
    if country:
        return country.name
    else:
        return "Invalid code. Please use formats like 'US' or 'USA'."

