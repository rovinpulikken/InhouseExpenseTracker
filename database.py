import os
import sqlite3
import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from config import get_indian_fy, get_indian_quarter, EXPENSE_CATEGORIES

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "expenses.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Expenses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date DATE NOT NULL,
            financial_year TEXT NOT NULL,
            quarter TEXT NOT NULL,
            half_year TEXT DEFAULT 'H1',
            category TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            source_note TEXT DEFAULT 'Manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if half_year column exists (for existing DB migration)
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in cursor.fetchall()]
    if "half_year" not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN half_year TEXT DEFAULT 'H1'")
    
    # Budgets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            financial_year TEXT NOT NULL,
            category TEXT NOT NULL,
            monthly_limit REAL DEFAULT 0.0,
            annual_limit REAL DEFAULT 0.0,
            UNIQUE(financial_year, category)
        )
    """)
    
    conn.commit()
    conn.close()

def insert_expenses(expense_rows: List[Dict[str, Any]], source: str = "OCR Scanner") -> int:
    """
    Inserts a list of expense dicts: [{'date': 'YYYY-MM-DD', 'category': '...', 'description': '...', 'amount': 123.45}]
    """
    from config import get_indian_half_year
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    
    for row in expense_rows:
        raw_date = row.get("date")
        if raw_date is None or pd.isna(raw_date) or str(raw_date).strip() == "":
            # STRICT RULE: Skip rows without an explicit date from uploaded data
            continue
            
        try:
            if isinstance(raw_date, (datetime.date, datetime.datetime)):
                dt = raw_date.date() if isinstance(raw_date, datetime.datetime) else raw_date
            else:
                dt = pd.to_datetime(str(raw_date)).date()
        except Exception:
            # Skip if uploaded date is invalid
            continue
            
        fy = get_indian_fy(dt)
        q_code, _ = get_indian_quarter(dt)
        h_code, _ = get_indian_half_year(dt)
        cat = row.get("category", "Miscellaneous")
        desc = row.get("description", "")
        
        # Robust Amount Parsing & Null / NaN Protection
        raw_amt = row.get("amount")
        if raw_amt is None or pd.isna(raw_amt):
            continue
            
        try:
            if isinstance(raw_amt, str):
                raw_amt = raw_amt.replace("₹", "").replace("Rs", "").replace("INR", "").replace(",", "").strip()
            amt = float(raw_amt)
            import math
            if math.isnan(amt) or math.isinf(amt) or amt <= 0:
                continue
        except (ValueError, TypeError):
            continue
            
        cursor.execute("""
            INSERT INTO expenses (expense_date, financial_year, quarter, half_year, category, description, amount, source_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (dt.isoformat(), fy, q_code, h_code, cat, str(desc), amt, source))
        count += 1
        
    conn.commit()
    conn.close()
    return count

def get_expenses_df(fy: Optional[str] = None, category: Optional[str] = None) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
    if category and category != "All Categories":
        query += " AND category = ?"
        params.append(category)
        
    query += " ORDER BY expense_date DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not df.empty and "expense_date" in df.columns:
        df["expense_date"] = pd.to_datetime(df["expense_date"])
        df["Month_Year"] = df["expense_date"].dt.strftime("%b %Y")
        df["Year"] = df["expense_date"].dt.year
    return df

def get_all_financial_years() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT financial_year FROM expenses ORDER BY financial_year DESC")
    fys = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    current_fy = get_indian_fy(datetime.date.today())
    if current_fy not in fys:
        fys.insert(0, current_fy)
    return fys

def get_category_breakdown(fy: Optional[str] = None) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT category, SUM(amount) as Total_Amount, COUNT(*) as Transaction_Count, AVG(amount) as Avg_Amount
        FROM expenses
        WHERE 1=1
    """
    params = []
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY category ORDER BY Total_Amount DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_monthly_trend_df(fy: Optional[str] = None) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT strftime('%Y-%m', expense_date) as YearMonth, financial_year, category, SUM(amount) as Monthly_Total
        FROM expenses
        WHERE 1=1
    """
    params = []
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY YearMonth, category ORDER BY YearMonth ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_quarterly_trend_df(fy: Optional[str] = None) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT financial_year, quarter, category, SUM(amount) as Quarterly_Total
        FROM expenses
        WHERE 1=1
    """
    params = []
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY financial_year, quarter, category ORDER BY financial_year ASC, quarter ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_surge_categories(fy: str) -> pd.DataFrame:
    """
    Identifies categories with recent surge comparing current month/quarter vs historical category average.
    """
    df = get_expenses_df(fy=fy)
    if df.empty:
        return pd.DataFrame()
        
    category_summary = df.groupby("category")["amount"].agg(
        Total="sum",
        Count="count",
        Avg_Txn="mean",
        Max_Txn="max"
    ).reset_index()
    
    # Calculate recent month total vs earlier months
    latest_month = df["Month_Year"].iloc[0] if not df.empty else None
    
    recent_month_df = df[df["Month_Year"] == latest_month].groupby("category")["amount"].sum().reset_index()
    recent_month_df.rename(columns={"amount": "Latest_Month_Spend"}, inplace=True)
    
    prev_months_df = df[df["Month_Year"] != latest_month].groupby("category")["amount"].mean().reset_index()
    prev_months_df.rename(columns={"amount": "Hist_Monthly_Avg"}, inplace=True)
    
    merged = pd.merge(category_summary, recent_month_df, on="category", how="left").fillna(0)
    merged = pd.merge(merged, prev_months_df, on="category", how="left").fillna(0)
    
    merged["Surge_%"] = 0.0
    mask = merged["Hist_Monthly_Avg"] > 0
    merged.loc[mask, "Surge_%"] = ((merged.loc[mask, "Latest_Month_Spend"] - merged.loc[mask, "Hist_Monthly_Avg"]) / merged.loc[mask, "Hist_Monthly_Avg"]) * 100
    
    merged = merged.sort_values(by="Surge_%", ascending=False)
    return merged

def set_category_budget(fy: str, category: str, monthly_limit: float, annual_limit: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO budgets (financial_year, category, monthly_limit, annual_limit)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(financial_year, category) DO UPDATE SET
            monthly_limit = excluded.monthly_limit,
            annual_limit = excluded.annual_limit
    """, (fy, category, monthly_limit, annual_limit))
    conn.commit()
    conn.close()

def get_budget_status(fy: str) -> pd.DataFrame:
    conn = get_connection()
    b_df = pd.read_sql_query("SELECT category, monthly_limit, annual_limit FROM budgets WHERE financial_year = ?", conn, params=[fy])
    conn.close()
    
    e_df = get_category_breakdown(fy=fy)
    
    # Merge categories
    cat_df = pd.DataFrame({"category": EXPENSE_CATEGORIES})
    merged = pd.merge(cat_df, b_df, on="category", how="left").fillna(0.0)
    merged = pd.merge(merged, e_df[["category", "Total_Amount"]], on="category", how="left").fillna(0.0)
    merged.rename(columns={"Total_Amount": "Actual_Spent"}, inplace=True)
    
    merged["Annual_Budget"] = merged["annual_limit"]
    merged.loc[merged["Annual_Budget"] == 0, "Annual_Budget"] = merged["monthly_limit"] * 12
    
    merged["Remaining"] = merged["Annual_Budget"] - merged["Actual_Spent"]
    merged["Utilization_%"] = 0.0
    mask = merged["Annual_Budget"] > 0
    merged.loc[mask, "Utilization_%"] = (merged.loc[mask, "Actual_Spent"] / merged.loc[mask, "Annual_Budget"]) * 100
    
    return merged

def delete_expense(expense_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def seed_sample_data_if_empty():
    """Seeds realistic sample data for Indian Financial Year testing if database is empty."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM expenses")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        return
        
    sample_records = [
        # FY 2024-25 Data
        {"date": "2024-04-05", "category": "Groceries & Provisions", "description": "Monthly D-Mart provisions", "amount": 12500.00},
        {"date": "2024-04-10", "category": "Utilities (Electricity/Water/Gas)", "description": "Electricity & Gas Bill", "amount": 3400.00},
        {"date": "2024-04-15", "category": "Rent & Housing", "description": "Flat House Rent", "amount": 28000.00},
        {"date": "2024-04-20", "category": "Dining & Swiggy/Zomato", "description": "Weekend family dining", "amount": 4200.00},
        {"date": "2024-04-25", "category": "Transportation & Fuel", "description": "Car petrol refilling", "amount": 6500.00},
        
        {"date": "2024-05-02", "category": "Groceries & Provisions", "description": "Monthly ration & snacks", "amount": 13200.00},
        {"date": "2024-05-12", "category": "Healthcare & Medicines", "description": "Apollo pharmacy medicines", "amount": 4800.00},
        {"date": "2024-05-18", "category": "Domestic Help & Services", "description": "Maid & Cook salary", "amount": 9500.00},
        {"date": "2024-05-28", "category": "Shopping & Apparel", "description": "Summer clothing purchase", "amount": 8400.00},
        
        {"date": "2024-06-04", "category": "Groceries & Provisions", "description": "Vegetables & groceries", "amount": 14100.00},
        {"date": "2024-06-15", "category": "Rent & Housing", "description": "Flat Rent", "amount": 28000.00},
        {"date": "2024-06-22", "category": "Utilities (Electricity/Water/Gas)", "description": "Summer AC electricity bill", "amount": 6200.00},
        
        {"date": "2024-07-05", "category": "Education & Books", "description": "School tuition fees Q2", "amount": 35000.00},
        {"date": "2024-07-14", "category": "Groceries & Provisions", "description": "Groceries & dry fruits", "amount": 13800.00},
        {"date": "2024-07-28", "category": "Transportation & Fuel", "description": "Fuel & auto servicing", "amount": 7800.00},

        {"date": "2024-10-15", "category": "Shopping & Apparel", "description": "Diwali festival shopping", "amount": 24500.00},
        {"date": "2024-10-22", "category": "Groceries & Provisions", "description": "Sweets & festival provisions", "amount": 18500.00},
        {"date": "2024-10-29", "category": "Dining & Swiggy/Zomato", "description": "Diwali family celebration", "amount": 8900.00},

        # FY 2025-26 Data
        {"date": "2025-04-05", "category": "Groceries & Provisions", "description": "Monthly Provisions", "amount": 14800.00},
        {"date": "2025-04-12", "category": "Rent & Housing", "description": "Flat Rent (Revised)", "amount": 30000.00},
        {"date": "2025-04-18", "category": "Utilities (Electricity/Water/Gas)", "description": "Electricity bill", "amount": 4100.00},
        {"date": "2025-05-10", "category": "Healthcare & Medicines", "description": "Annual health checkups", "amount": 12000.00},
        {"date": "2025-05-20", "category": "Groceries & Provisions", "description": "Groceries & mangoes", "amount": 16500.00},
        {"date": "2025-06-15", "category": "Utilities (Electricity/Water/Gas)", "description": "AC Electricity peak bill", "amount": 7800.00},
        {"date": "2025-07-02", "category": "Transportation & Fuel", "description": "Fuel expenses", "amount": 8200.00}
    ]
    
    insert_expenses(sample_records, source="Sample Seeder")

def get_cumulative_metrics(fy: Optional[str] = None) -> Dict[str, float]:
    """
    Calculates YTD, QTD, H1, and H2 cumulative totals for a given Financial Year.
    """
    df = get_expenses_df(fy=fy)
    if df.empty:
        return {"YTD": 0.0, "QTD": 0.0, "H1": 0.0, "H2": 0.0}
        
    ytd_total = float(df["amount"].sum())
    
    # H1 & H2 Totals
    h1_total = float(df[df["half_year"] == "H1"]["amount"].sum()) if "half_year" in df.columns else 0.0
    h2_total = float(df[df["half_year"] == "H2"]["amount"].sum()) if "half_year" in df.columns else 0.0
    
    # QTD Total (Current Quarter)
    today = datetime.date.today()
    curr_q, _ = get_indian_quarter(today)
    qtd_total = float(df[df["quarter"] == curr_q]["amount"].sum())
    
    return {
        "YTD": ytd_total,
        "QTD": qtd_total,
        "H1": h1_total,
        "H2": h2_total
    }

def delete_month_expenses(month_year_label: str) -> int:
    """
    Deletes all expense entries matching a month label e.g., 'May 2025' or '2025-05'.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        dt = datetime.datetime.strptime(month_year_label, "%b %Y")
        ym = dt.strftime("%Y-%m")
    except Exception:
        ym = month_year_label
        
    cursor.execute("""
        DELETE FROM expenses 
        WHERE strftime('%Y-%m', expense_date) = ? 
           OR expense_date LIKE ?
    """, (ym, f"{ym}%"))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def update_expenses_df(updated_df: pd.DataFrame) -> int:
    """
    Persists inline edits (dates, categories, descriptions, amounts) made in the database editor table.
    Re-calculates FY, quarter, and half-year strictly from the edited date.
    """
    from config import get_indian_half_year
    conn = get_connection()
    cursor = conn.cursor()
    updated_count = 0
    
    for _, row in updated_df.iterrows():
        exp_id = row.get("id")
        if not exp_id or pd.isna(exp_id):
            continue
            
        raw_date = row.get("expense_date") or row.get("date")
        if raw_date is None or pd.isna(raw_date):
            continue
            
        try:
            if isinstance(raw_date, (datetime.date, datetime.datetime)):
                dt = raw_date.date() if isinstance(raw_date, datetime.datetime) else raw_date
            else:
                dt = pd.to_datetime(str(raw_date)).date()
        except Exception:
            continue
            
        fy = get_indian_fy(dt)
        q_code, _ = get_indian_quarter(dt)
        h_code, _ = get_indian_half_year(dt)
        cat = row.get("category", "Miscellaneous")
        desc = str(row.get("description", ""))
        
        try:
            amt = float(row.get("amount", 0.0))
        except (ValueError, TypeError):
            continue
            
        cursor.execute("""
            UPDATE expenses
            SET expense_date = ?,
                financial_year = ?,
                quarter = ?,
                half_year = ?,
                category = ?,
                description = ?,
                amount = ?
            WHERE id = ?
        """, (dt.isoformat(), fy, q_code, h_code, cat, desc, amt, int(exp_id)))
        updated_count += 1
        
    conn.commit()
    conn.close()
    return updated_count

def delete_multiple_expenses(id_list: List[int]) -> int:
    if not id_list:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(id_list))
    cursor.execute(f"DELETE FROM expenses WHERE id IN ({placeholders})", id_list)
    cnt = cursor.rowcount
    conn.commit()
    conn.close()
    return cnt
