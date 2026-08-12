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
        for line in lines:
            if not line or ';' not in line:
                continue
            parts = line.split(';')
            if len(parts) >= 4:
                scheme_code = parts[0].strip()
                scheme_name = parts[3].strip()
                if scheme_code.isdigit():
                    amfi_dict[scheme_code] = scheme_name
        return amfi_dict
    except Exception as e:
        print(f"Error fetching AMFI data: {e}")
        return {}

def resolve_amfi_code(code: str) -> str:
    """
    Attempts to resolve an AMFI scheme code into a scheme name.
    Returns the resolved name if successful, else returns the original code or empty string.
    """
    code_str = str(code).strip()
    if not code_str.isdigit():
        return "" # Not a numeric AMFI code
        
    amfi_data = get_amfi_data()
    return amfi_data.get(code_str, "")
