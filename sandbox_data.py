import pandas as pd
import datetime

def mock_success(*args, **kwargs):
    return True

def sandbox_get_expenses_df(fy=None, username=None, view_mode="Personal", family_id=None):
    # Return mock expenses
    data = [
        {"id": 1, "date": "2026-08-01", "expense_date": "2026-08-01", "category": "Rent", "description": "Monthly Rent", "amount": 25000, "visibility": "Personal", "source_note": "", "username": username or "sandbox_user"},
        {"id": 2, "date": "2026-08-05", "expense_date": "2026-08-05", "category": "Groceries", "description": "Supermarket", "amount": 8000, "visibility": "Personal", "source_note": "", "username": username or "sandbox_user"},
        {"id": 3, "date": "2026-08-10", "expense_date": "2026-08-10", "category": "Utilities", "description": "Electricity", "amount": 2000, "visibility": "Personal", "source_note": "", "username": username or "sandbox_user"},
        {"id": 4, "date": "2026-08-15", "expense_date": "2026-08-15", "category": "Dining Out", "description": "Restaurant", "amount": 3000, "visibility": "Personal", "source_note": "", "username": username or "sandbox_user"},
    ]
    df = pd.DataFrame(data)
    # add 'date' formatted just in case
    df['date'] = pd.to_datetime(df['date'])
    df['expense_date'] = pd.to_datetime(df['expense_date'])
    return df

def sandbox_get_user_investments_df(username, view_mode="Personal", family_id=None):
    data = [
        {"id": 1, "investment_name": "Nifty 50 Index", "broker_name": "Zerodha", "asset_class": "Equity", "amount_invested": 50000, "maturity_date": None, "current_value": 55000, "is_pledged": 0, "is_tax_saving": 0, "notes": "", "visibility": "Personal", "source_note": "", "username": username},
        {"id": 2, "investment_name": "Fixed Deposit", "broker_name": "SBI", "asset_class": "Debt", "amount_invested": 100000, "maturity_date": "2028-01-01", "current_value": 105000, "is_pledged": 0, "is_tax_saving": 0, "notes": "", "visibility": "Personal", "source_note": "", "username": username},
    ]
    df = pd.DataFrame(data)
    # compute returns
    df['absolute_return'] = df['current_value'] - df['amount_invested']
    df['percentage_return'] = (df['absolute_return'] / df['amount_invested']) * 100
    df['is_pledged'] = df['is_pledged'].astype(bool)
    df['is_tax_saving'] = df['is_tax_saving'].astype(bool)
    return df

def sandbox_get_budget_status(username, view_mode="Personal", family_id=None):
    # Returns (budget_df, unbudgeted_df)
    # We'll just return some mock data
    budget_data = [
        {"Category": "Groceries", "Budget": 10000, "Spent": 8000, "Remaining": 2000, "Status": "Under Budget", "Utilization": 80.0},
        {"Category": "Dining Out", "Budget": 2000, "Spent": 3000, "Remaining": -1000, "Status": "Over Budget", "Utilization": 150.0},
    ]
    unbudgeted_data = [
        {"Category": "Rent", "Spent": 25000},
        {"Category": "Utilities", "Spent": 2000}
    ]
    return pd.DataFrame(budget_data), pd.DataFrame(unbudgeted_data)

