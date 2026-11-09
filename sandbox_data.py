import pandas as pd
import datetime
from config import get_indian_fy, get_indian_quarter, get_indian_half_year

def mock_success(*args, **kwargs):
    return True

def sandbox_get_expenses_df(fy=None, category=None, username=None, view_mode="Personal", family_id=None, transaction_type="Expense"):
    # Return mock expenses matching the real schema
    data = [
        {"id": 1, "date": "2026-08-01", "expense_date": "2026-08-01", "category": "Rent",      "description": "Monthly Rent",   "amount": 25000, "visibility": "Personal", "source_note": "", "username": username or "sandbox_user", "transaction_type": "Expense"},
        {"id": 2, "date": "2026-08-05", "expense_date": "2026-08-05", "category": "Groceries", "description": "Supermarket",     "amount": 8000,  "visibility": "Personal", "source_note": "", "username": username or "sandbox_user", "transaction_type": "Expense"},
        {"id": 3, "date": "2026-08-10", "expense_date": "2026-08-10", "category": "Utilities", "description": "Electricity",     "amount": 2000,  "visibility": "Personal", "source_note": "", "username": username or "sandbox_user", "transaction_type": "Expense"},
        {"id": 4, "date": "2026-08-15", "expense_date": "2026-08-15", "category": "Dining Out","description": "Restaurant",      "amount": 3000,  "visibility": "Personal", "source_note": "", "username": username or "sandbox_user", "transaction_type": "Expense"},
    ]
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['expense_date'] = pd.to_datetime(df['expense_date'])
    df['financial_year'] = df['expense_date'].apply(lambda dt: get_indian_fy(dt.date()))
    df['quarter'] = df['expense_date'].apply(lambda dt: get_indian_quarter(dt.date()))
    df['half_year'] = df['expense_date'].apply(lambda dt: get_indian_half_year(dt.date()))
    df['Month_Year'] = df['expense_date'].dt.strftime('%b %Y')
    df['Month_Key'] = df['expense_date'].dt.strftime('%Y-%m')
    df['Year'] = df['expense_date'].dt.year
    return df

def sandbox_get_user_investments_df(username, view_mode="Personal", family_id=None):
    data = [
        {"id": 1, "investment_name": "Nifty 50 Index", "broker_name": "Zerodha", "asset_class": "Equity", "amount_invested": 50000,  "maturity_date": None,         "current_value": 55000,  "is_pledged": 0, "is_tax_saving": 0, "notes": "", "visibility": "Personal", "source_note": "", "username": username},
        {"id": 2, "investment_name": "Fixed Deposit",   "broker_name": "SBI",     "asset_class": "Debt",   "amount_invested": 100000, "maturity_date": "2028-01-01", "current_value": 105000, "is_pledged": 0, "is_tax_saving": 0, "notes": "", "visibility": "Personal", "source_note": "", "username": username},
    ]
    df = pd.DataFrame(data)
    df['absolute_return']   = df['current_value'] - df['amount_invested']
    df['percentage_return'] = (df['absolute_return'] / df['amount_invested']) * 100
    df['is_pledged']    = df['is_pledged'].astype(bool)
    df['is_tax_saving'] = df['is_tax_saving'].astype(bool)
    return df

def sandbox_get_budget_status(fy=None, username=None, view_mode="Personal", family_id=None):
    # Returns a single DataFrame matching the real get_budget_status() schema.
    # Real columns used in app.py: category, Actual_Spent, Annual_Budget, Utilization_%
    budget_data = [
        {"category": "Groceries", "Annual_Budget": 120000, "Actual_Spent": 96000, "Utilization_%": 80.0},
        {"category": "Dining Out","Annual_Budget": 24000,  "Actual_Spent": 36000, "Utilization_%": 150.0},
        {"category": "Utilities", "Annual_Budget": 36000,  "Actual_Spent": 24000, "Utilization_%": 66.7},
        {"category": "Rent",      "Annual_Budget": 300000, "Actual_Spent": 300000,"Utilization_%": 100.0},
    ]
    return pd.DataFrame(budget_data)
