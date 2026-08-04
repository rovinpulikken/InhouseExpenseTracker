"""
Auto-Categorization Engine for Indian Personal Expenses.
Combines rule-based keyword matching for Indian merchants/items with optional Gemini AI fallback.
"""

import re
from typing import List, Dict, Any, Tuple
import pandas as pd
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

# ----------------------------------------------------
# MACHINE LEARNING AUTO-CATEGORIZATION ENGINE
# ----------------------------------------------------
class MLCategorizer:
    """
    Machine Learning Expense Categorizer trained on historical database records.
    Learns from past user categorizations (e.g. 'kerala groceries' -> 'Groceries & Provisions').
    Supports scikit-learn TF-IDF Naive Bayes + pure-Python N-Gram similarity fallback.
    """
    def __init__(self):
        self.trained = False
        self.sample_count = 0
        self.category_tokens = {}
        self.sklearn_pipeline = None

    def _extract_tokens(self, text: str) -> set:
        if not text or not isinstance(text, str):
            return set()
        clean = text.lower().strip()
        words = re.findall(r"\w+", clean)
        bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        return set(words + bigrams)

    def train(self, records: List[Dict[str, Any]]) -> int:
        valid_samples = []
        self.category_tokens = {}
        
        for r in records:
            desc = r.get("description", "") if isinstance(r, dict) else getattr(r, "description", "")
            cat = r.get("category", "") if isinstance(r, dict) else getattr(r, "category", "")
            if desc and cat and cat in EXPENSE_CATEGORIES and cat != "Miscellaneous":
                valid_samples.append((str(desc).lower().strip(), str(cat)))

        if not valid_samples:
            self.trained = False
            self.sample_count = 0
            return 0

        self.sample_count = len(valid_samples)
        
        # 1. Try Scikit-Learn TF-IDF Pipeline if installed
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.pipeline import make_pipeline

            texts = [s[0] for s in valid_samples]
            labels = [s[1] for s in valid_samples]
            
            pipeline = make_pipeline(
                TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True),
                MultinomialNB(alpha=0.5)
            )
            pipeline.fit(texts, labels)
            self.sklearn_pipeline = pipeline
            self.trained = True
        except Exception:
            self.sklearn_pipeline = None

        # 2. Build N-Gram token dictionary for native similarity matching
        for text, cat in valid_samples:
            tokens = self._extract_tokens(text)
            if tokens:
                if cat not in self.category_tokens:
                    self.category_tokens[cat] = []
                self.category_tokens[cat].append(tokens)

        self.trained = True
        return self.sample_count

    def predict(self, description: str) -> Tuple[str, float, str]:
        """
        Predicts category and returns (predicted_category, confidence_score, method_used).
        """
        if not description or not isinstance(description, str):
            return "Miscellaneous", 0.0, "Rule Match"

        clean_desc = description.lower().strip()

        # 1. Scikit-Learn Prediction
        if self.trained and self.sklearn_pipeline is not None:
            try:
                probs = self.sklearn_pipeline.predict_proba([clean_desc])[0]
                classes = self.sklearn_pipeline.classes_
                max_idx = probs.argmax()
                best_cat = classes[max_idx]
                confidence = float(probs[max_idx])
                if confidence >= 0.30:
                    return best_cat, round(confidence, 2), "ML (scikit-learn)"
            except Exception:
                pass

        # 2. Native N-Gram Similarity Matching
        if self.trained and self.category_tokens:
            query_tokens = self._extract_tokens(clean_desc)
            if query_tokens:
                best_cat = None
                best_score = 0.0

                for cat, list_of_tokens in self.category_tokens.items():
                    for doc_tokens in list_of_tokens:
                        intersection = query_tokens.intersection(doc_tokens)
                        if intersection:
                            jaccard = len(intersection) / len(query_tokens.union(doc_tokens))
                            overlap = len(intersection) / len(query_tokens)
                            sim = (jaccard * 0.4) + (overlap * 0.6)
                            if sim > best_score:
                                best_score = sim
                                best_cat = cat

                if best_cat and best_score >= 0.20:
                    return best_cat, round(best_score, 2), "ML (Historical Learning)"

        # 3. Rule-based Keyword Matching Fallback
        rule_cat = auto_categorize_description(clean_desc)
        conf = 0.50 if rule_cat != "Miscellaneous" else 0.0
        return rule_cat, conf, "Keyword Match"

def apply_ml_auto_categorization(df: Any, historical_records: List[Dict[str, Any]], overwrite_all: bool = False) -> Tuple[Any, int, int]:
    """
    Applies ML auto-categorization on a DataFrame of expenses using historical learnings.
    Returns (updated_df, modified_count, trained_sample_count).
    """
    model = MLCategorizer()
    sample_count = model.train(historical_records)
    
    if df.empty:
        return df, 0, sample_count
        
    df_copy = df.copy()
    modified_count = 0
    
    for idx in df_copy.index:
        current_cat = str(df_copy.at[idx, "category"]) if "category" in df_copy.columns and pd.notna(df_copy.at[idx, "category"]) else ""
        desc = str(df_copy.at[idx, "description"]) if "description" in df_copy.columns and pd.notna(df_copy.at[idx, "description"]) else ""
        
        # Categorize if empty/Misc, or if overwrite_all is True
        if overwrite_all or not current_cat or current_cat == "Miscellaneous" or current_cat not in EXPENSE_CATEGORIES:
            pred_cat, conf, method = model.predict(desc)
            if pred_cat and pred_cat != current_cat:
                df_copy.at[idx, "category"] = pred_cat
                modified_count += 1

    return df_copy, modified_count, sample_count

