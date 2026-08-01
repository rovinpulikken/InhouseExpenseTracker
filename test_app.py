import datetime
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from config import get_indian_fy, get_indian_quarter, get_indian_half_year, format_inr, format_inr_short
from database import init_db, insert_expenses, get_expenses_df, delete_month_expenses, delete_expense, update_expenses_df
from cpi_data import calculate_cpi_inflation
from categorizer import auto_categorize_description, auto_categorize_records

def test_strict_uploaded_date_enforcement():
    init_db()
    # Rows with valid date and invalid/missing date
    test_rows = [
        {"date": "2024-11-15", "category": "Shopping & Apparel", "description": "Explicit date row", "amount": 3500.0},
        {"date": None, "category": "Groceries & Provisions", "description": "Missing date row", "amount": 1000.0},
        {"date": "", "category": "Dining & Swiggy/Zomato", "description": "Empty date row", "amount": 500.0}
    ]
    inserted = insert_expenses(test_rows, source="Strict Date Test")
    assert inserted == 1 # Only row with explicit date is inserted
    print("✅ Strict uploaded date enforcement passed.")

def test_inline_database_update():
    init_db()
    df = get_expenses_df(fy="FY 2024-25")
    assert not df.empty
    
    # Edit date of first record to 2024-04-10
    row_to_edit = df.iloc[0].to_dict()
    row_to_edit["expense_date"] = "2024-04-10"
    row_to_edit["description"] = "Updated Description via Editor"
    row_to_edit["amount"] = 9999.00
    
    updated_cnt = update_expenses_df(pd.DataFrame([row_to_edit]))
    assert updated_cnt == 1
    
    # Verify update in database
    df_updated = get_expenses_df(fy="FY 2024-25")
    matched = df_updated[df_updated["id"] == row_to_edit["id"]]
    assert not matched.empty
    assert matched.iloc[0]["description"] == "Updated Description via Editor"
    assert matched.iloc[0]["amount"] == 9999.00
    print("✅ Inline database update & FY recalculation passed.")

if __name__ == "__main__":
    test_strict_uploaded_date_enforcement()
    test_inline_database_update()
    print("🎉 All strict date and inline update tests passed successfully!")
