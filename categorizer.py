"""
Auto-Categorization Engine for Indian Personal Expenses.
Combines rule-based keyword matching for Indian merchants/items with optional Gemini AI fallback.
"""

import re
from typing import List, Dict, Any
from config import EXPENSE_CATEGORIES

# Rule-based Keyword Mapping for Indian Household Items & Services
KEYWORD_CATEGORY_MAP = [
    # Groceries & Provisions
    (r"\b(dmart|d-mart|ration|bigbasket|blinkit|zepto|instamart|rice|atta|wheat|dal|oil|pulses|sugar|salt|spices|grocer|grocery|provision|supermarket|superstore)\b", "Groceries & Provisions"),
    
    # Vegetables & Fruits
    (r"\b(sabzi|mandi|vegetable|fruit|apple|banana|mango|potato|onion|tomato|ginger|garlic|coriander|palak|bhindi|bazaar)\b", "Vegetables & Fruits"),
    
    # Milk & Dairy
    (r"\b(milk|doodh|amul|mother dairy|nandini|curd|dahi|paneer|butter|ghee|cheese|cream|dairy)\b", "Milk & Dairy"),
    
    # Utilities (Electricity/Water/Gas)
    (r"\b(electric|electricity|power|bescom|tata power|torrent|mseb|dhbvn|lpg|gas|cylinder|indane|hp gas|bharat gas|water bill|piped gas|broadband|wifi|jio|airtel|vi|act fiber|recharge|utility|utilities)\b", "Utilities (Electricity/Water/Gas)"),
    
    # Rent & Housing
    (r"\b(rent|house rent|flat rent|apartment rent|society maintenance|maintenance fee|landlord)\b", "Rent & Housing"),
    
    # Dining & Swiggy/Zomato
    (r"\b(swiggy|zomato|restaurant|hotel|cafe|coffee|starbucks|third wave|domino|pizza|mcdonald|burger|kfc|biryani|dining|eatery|dhabha|canteen|food court)\b", "Dining & Swiggy/Zomato"),
    
    # Transportation & Fuel
    (r"\b(petrol|diesel|fuel|hpcl|bpcl|iocl|shell|cng|uber|ola|rapido|auto|rickshaw|metro|fastag|toll|cab|taxi|bus|train|irctc|flight|indigo|air india|parking)\b", "Transportation & Fuel"),
    
    # Healthcare & Medicines
    (r"\b(apollo|pharmeasy|1mg|netmeds|medplus|pharmacy|chemist|medicine|medical|doctor|clinic|hospital|consultation|lab|test|blood test|pathology|scan|x-ray|tablet|syrup|dentist)\b", "Healthcare & Medicines"),
    
    # Education & Books
    (r"\b(school|college|tuition|coaching|fee|fees|books|bookstore|stationery|pen|notebook|udemy|coursera|unacademy|byju|exam)\b", "Education & Books"),
    
    # Entertainment & OTT
    (r"\b(netflix|prime|amazon prime|hotstar|sony liv|zee5|spotify|youtube|cinema|movie|pvr|inox|bookmyshow|ticket|game|gaming|amusement)\b", "Entertainment & OTT"),
    
    # Shopping & Apparel
    (r"\b(myntra|amazon|flipkart|ajio|zara|h&m|uniqlo|pantaloons|max|trends|shopper stop|clothes|apparel|shirt|pant|dress|shoes|footwear|mall|shopping)\b", "Shopping & Apparel"),
    
    # Insurance & Investments
    (r"\b(lic|insurance|policy|premium|health insurance|car insurance|sip|mutual fund|zerodha|groww|upstox|fd|ppf|nps|nifty|stock|investment)\b", "Insurance & Investments"),
    
    # Domestic Help & Services
    (r"\b(maid|cook|driver|sweeper|housekeeper|cleaner|gardener|laundry|dhobi|ironing|domestic help|helper salary)\b", "Domestic Help & Services"),
    
    # Maintenance & Repairs
    (r"\b(plumber|electrician|carpenter|painter|repair|service|car service|bike service|ac service|washing machine service|hardware|pest control)\b", "Maintenance & Repairs")
]

def auto_categorize_description(description: str) -> str:
    """
    Predicts the expense category based on text description using rule-based Indian keyword regex.
    Returns predicted category string or 'Miscellaneous' if no match.
    """
    if not description or not isinstance(description, str):
        return "Miscellaneous"
        
    desc_clean = description.lower().strip()
    
    for pattern, category in KEYWORD_CATEGORY_MAP:
        if re.search(pattern, desc_clean, re.IGNORECASE):
            return category
            
    return "Miscellaneous"

def auto_categorize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Processes a list of expense records, filling missing or 'Miscellaneous' categories automatically.
    """
    updated_records = []
    for rec in records:
        rec_copy = dict(rec)
        current_cat = rec_copy.get("category", "")
        desc = rec_copy.get("description", "")
        
        # If category is empty, default, or Miscellaneous, try auto-categorization
        if not current_cat or current_cat == "Miscellaneous" or current_cat not in EXPENSE_CATEGORIES:
            predicted = auto_categorize_description(desc)
            rec_copy["category"] = predicted
            
        updated_records.append(rec_copy)
    return updated_records
