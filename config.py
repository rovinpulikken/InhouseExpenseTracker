import datetime
from typing import Tuple, List

# Standard Expense Categories for Indian Households
EXPENSE_CATEGORIES = [
    "Groceries & Provisions",
    "Vegetables & Fruits",
    "Milk & Dairy",
    "Utilities (Electricity/Water/Gas)",
    "Rent & Housing",
    "Dining & Swiggy/Zomato",
    "Transportation & Fuel",
    "Healthcare & Medicines",
    "Education & Books",
    "Entertainment & OTT",
    "Shopping & Apparel",
    "Insurance & Investments",
    "Domestic Help & Services",
    "Maintenance & Repairs",
    "Miscellaneous"
]

# Debt & Liabilities Categories
DEBT_CATEGORIES = [
    "Housing Loan / Mortgage",
    "Loans for Investment",
    "Education / Student Loans",
    "Credit Card Debt",
    "Auto / Car Loans",
    "Personal Loans",
    "Buy Now, Pay Later",
    "Peer-to-Peer / Family Loans",
    "Tax Liabilities",
    "Overdraft / Line of Credit",
    "Other Debt / Liability"
]

# Append debt categories to standard expense categories so they appear in Budget Planner
EXPENSE_CATEGORIES.extend(DEBT_CATEGORIES)

def get_indian_fy(dt: datetime.date) -> str:
    """
    Returns the Indian Financial Year string (e.g. 'FY 2024-25') for a given date.
    Indian FY starts on April 1st and ends on March 31st of the following calendar year.
    """
    if dt.month >= 4:
        start_year = dt.year
        end_year = dt.year + 1
    else:
        start_year = dt.year - 1
        end_year = dt.year

    return f"FY {start_year}-{str(end_year)[-2:]}"

def get_indian_quarter(dt: datetime.date) -> Tuple[str, str]:
    """
    Returns (Quarter_Code, Quarter_Label) for Indian Financial Year:
    Q1: Apr - Jun
    Q2: Jul - Sep
    Q3: Oct - Dec
    Q4: Jan - Mar
    """
    m = dt.month
    if 4 <= m <= 6:
        return ("Q1", "Q1 (Apr - Jun)")
    elif 7 <= m <= 9:
        return ("Q2", "Q2 (Jul - Sep)")
    elif 10 <= m <= 12:
        return ("Q3", "Q3 (Oct - Dec)")
    else:
        return ("Q4", "Q4 (Jan - Mar)")

def get_indian_half_year(dt: datetime.date) -> Tuple[str, str]:
    """
    Returns (Half_Code, Half_Label) for Indian Financial Year:
    H1: Apr - Sep
    H2: Oct - Mar
    """
    m = dt.month
    if 4 <= m <= 9:
        return ("H1", "H1 (Apr - Sep)")
    else:
        return ("H2", "H2 (Oct - Mar)")

def format_inr(amount: float) -> str:
    """
    Formats a numeric amount into Indian Currency notation (e.g. ₹ 1,50,000.00).
    """
    if amount is None:
        return "₹ 0.00"
    
    is_negative = amount < 0
    amount = abs(amount)
    
    s, *d = f"{amount:.2f}".split(".")
    r = []
    for i, c in enumerate(reversed(s)):
        if i == 3 or (i > 3 and (i - 3) % 2 == 0):
            r.append(",")
        r.append(c)
    
    formatted = "".join(reversed(r))
    dec = d[0] if d else "00"
    prefix = "-₹ " if is_negative else "₹ "
    return f"{prefix}{formatted}.{dec}"

def format_inr_short(amount: float) -> str:
    """
    Formats amount in Thousands (K) or Lakhs (L) for clean UI metrics.
    """
    if amount is None or amount == 0:
        return "₹ 0"
    
    abs_amt = abs(amount)
    sign = "-" if amount < 0 else ""
    
    if abs_amt >= 10000000: # 1 Crore
        return f"{sign}₹ {abs_amt/10000000:.2f} Cr"
    elif abs_amt >= 100000: # 1 Lakh
        return f"{sign}₹ {abs_amt/100000:.2f} L"
    elif abs_amt >= 1000: # 1 Thousand
        return f"{sign}₹ {abs_amt/1000:.1f} K"
    else:
        return f"{sign}₹ {abs_amt:.0f}"

def format_month_label(month_year_str: str) -> str:
    """
    Formats 'YYYY-MM' strings (e.g. '2024-05') into human-readable labels like 'May 2024 (2024-05)'.
    """
    if not month_year_str or not isinstance(month_year_str, str):
        return str(month_year_str)
    if "All" in month_year_str:
        return month_year_str
    try:
        dt = datetime.datetime.strptime(month_year_str.strip(), "%Y-%m")
        return f"{dt.strftime('%B %Y')} ({month_year_str.strip()})"
    except Exception:
        return month_year_str

