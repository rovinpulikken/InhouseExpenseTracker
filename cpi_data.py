"""
Indian Consumer Price Index (CPI Combined, Base 2012=100) Benchmark Data & Analytics.
Source: Ministry of Statistics and Programme Implementation (MOSPI) & Reserve Bank of India (RBI).
"""

from typing import Dict, List, Tuple
import pandas as pd

# Historical Annual Average CPI (Combined) Index Numbers & YoY Inflation Rates for India
INDIAN_CPI_SERIES = {
    # Year: (Annual CPI Index, YoY Inflation %)
    2018: (138.8, 3.94),
    2019: (144.0, 3.73),
    2020: (153.6, 6.62),
    2021: (161.5, 5.13),
    2022: (172.3, 6.70),
    2023: (182.1, 5.65),
    2024: (192.3, 5.60),
    2025: (201.2, 4.63),
    2026: (209.6, 4.17)
}

# Major CPI Group Weights & Estimated Average Category Inflation (2020-2026 CAGR)
CPI_CATEGORY_INFLATION = {
    "Groceries & Provisions": {"cpi_group": "Food & Beverages", "cpi_weight": 45.86, "avg_inflation": 6.8},
    "Vegetables & Fruits": {"cpi_group": "Food - Vegetables", "cpi_weight": 6.04, "avg_inflation": 8.5},
    "Milk & Dairy": {"cpi_group": "Food - Milk", "cpi_weight": 6.61, "avg_inflation": 6.2},
    "Utilities (Electricity/Water/Gas)": {"cpi_group": "Fuel & Light", "cpi_weight": 6.84, "avg_inflation": 5.8},
    "Rent & Housing": {"cpi_group": "Housing", "cpi_weight": 10.07, "avg_inflation": 4.5},
    "Dining & Swiggy/Zomato": {"cpi_group": "Prepared Meals & Snacks", "cpi_weight": 5.55, "avg_inflation": 6.5},
    "Transportation & Fuel": {"cpi_group": "Transport & Communication", "cpi_weight": 8.59, "avg_inflation": 6.0},
    "Healthcare & Medicines": {"cpi_group": "Health", "cpi_weight": 5.89, "avg_inflation": 6.9},
    "Education & Books": {"cpi_group": "Education", "cpi_weight": 4.46, "avg_inflation": 5.5},
    "Entertainment & OTT": {"cpi_group": "Recreation & Amusement", "cpi_weight": 1.68, "avg_inflation": 4.0},
    "Shopping & Apparel": {"cpi_group": "Clothing & Footwear", "cpi_weight": 6.53, "avg_inflation": 5.2},
    "Insurance & Investments": {"cpi_group": "Financial Services", "cpi_weight": 2.00, "avg_inflation": 5.0},
    "Domestic Help & Services": {"cpi_group": "Personal Care & Services", "cpi_weight": 3.89, "avg_inflation": 7.0},
    "Maintenance & Repairs": {"cpi_group": "Household Goods & Services", "cpi_weight": 3.80, "avg_inflation": 5.5},
    "Miscellaneous": {"cpi_group": "Miscellaneous", "cpi_weight": 3.00, "avg_inflation": 5.5}
}

def get_cpi_df() -> pd.DataFrame:
    """Returns a pandas DataFrame of historical CPI index and inflation percentages."""
    data = []
    for yr, (idx, inf) in INDIAN_CPI_SERIES.items():
        data.append({"Year": yr, "CPI Index (2012=100)": idx, "CPI Inflation (%)": inf})
    return pd.DataFrame(data)

def get_cpi_for_year(year: int) -> float:
    """Get Indian CPI index for a given year."""
    if year in INDIAN_CPI_SERIES:
        return INDIAN_CPI_SERIES[year][0]
    elif year < min(INDIAN_CPI_SERIES.keys()):
        return INDIAN_CPI_SERIES[min(INDIAN_CPI_SERIES.keys())][0]
    else:
        return INDIAN_CPI_SERIES[max(INDIAN_CPI_SERIES.keys())][0]

def calculate_cpi_inflation(start_year: int, end_year: int) -> float:
    """Calculate cumulative Indian CPI inflation % between start_year and end_year."""
    cpi_start = get_cpi_for_year(start_year)
    cpi_end = get_cpi_for_year(end_year)
    if cpi_start == 0:
        return 0.0
    return round(((cpi_end - cpi_start) / cpi_start) * 100, 2)

def calculate_personal_inflation_rate(category_breakdown_df: pd.DataFrame) -> float:
    """
    Calculate the personalized inflation rate based on a user's historical category spending weights.
    Requires a DataFrame with 'category' and 'Total_Amount' columns.
    """
    if category_breakdown_df.empty or 'Total_Amount' not in category_breakdown_df.columns or 'category' not in category_breakdown_df.columns:
        # Default to a standard blended inflation rate if no data is available
        return 6.0
    
    total_spend = category_breakdown_df['Total_Amount'].sum()
    if total_spend <= 0:
        return 6.0
        
    personal_inflation = 0.0
    for _, row in category_breakdown_df.iterrows():
        cat = row['category']
        amt = row['Total_Amount']
        weight = amt / total_spend
        
        # Get category average inflation, default to 5.5% if not found
        cat_inflation = 5.5
        if cat in CPI_CATEGORY_INFLATION:
            cat_inflation = CPI_CATEGORY_INFLATION[cat]['avg_inflation']
            
        personal_inflation += (weight * cat_inflation)
        
    return round(personal_inflation, 2)
