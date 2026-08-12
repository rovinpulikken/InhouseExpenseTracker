import requests
import streamlit as st
from typing import Optional, Dict

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

@st.cache_data(ttl=86400) # Cache for 24 hours
def get_amfi_data() -> Dict[str, str]:
    """
    Fetches the AMFI NAV list and returns a dictionary mapping Scheme Code to Scheme Name.
    """
    try:
        response = requests.get(AMFI_URL, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        
        amfi_dict = {}
        current_category = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # If line doesn't contain a semicolon and looks like a category header
            if ';' not in line:
                if '(' in line and ')' in line and 'Scheme' in line:
                    # Clean up the category name (e.g. "Open Ended Schemes(Equity Scheme - Large Cap Fund)" -> "Equity Scheme - Large Cap Fund")
                    cat_start = line.find('(')
                    cat_end = line.rfind(')')
                    if cat_start != -1 and cat_end != -1:
                        current_category = line[cat_start+1:cat_end].strip()
                    else:
                        current_category = line
                continue
                
            parts = line.split(';')
            if len(parts) >= 4:
                scheme_code = parts[0].strip()
                scheme_name = parts[3].strip()
                if scheme_code.isdigit():
                    amfi_dict[scheme_code] = {
                        "name": scheme_name,
                        "category": current_category
                    }
        return amfi_dict
    except Exception as e:
        print(f"Error fetching AMFI data: {e}")
        return {}

def resolve_amfi_code(code: str) -> Optional[Dict[str, str]]:
    """
    Attempts to resolve an AMFI scheme code into a scheme name and category.
    Returns a dict with 'name' and 'category' if successful, else returns None.
    """
    code_str = str(code).strip()
    if not code_str.isdigit():
        return None # Not a numeric AMFI code
        
    amfi_data = get_amfi_data()
    return amfi_data.get(code_str, None)
