import os
import sqlite3
import datetime
import hashlib
import secrets
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from config import get_indian_fy, get_indian_quarter, EXPENSE_CATEGORIES

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "expenses.db")

class LibSQLCursorWrapper:
    def __init__(self, client):
        self.client = client
        self._rows = []
        self._idx = 0
        self.description = None
        self.lastrowid = None

    def execute(self, sql, params=()):
        if isinstance(params, (tuple, set)):
            params = list(params)
        res = self.client.execute(sql, params)
        if hasattr(res, 'columns') and res.columns:
            self.description = [(col, None, None, None, None, None, None) for col in res.columns]
        else:
            self.description = None
        if hasattr(res, 'rows'):
            self._rows = [r._tuple if hasattr(r, '_tuple') else (tuple(r) if isinstance(r, (list, tuple)) else r) for r in res.rows]
        else:
            self._rows = []
        self._idx = 0
        if hasattr(res, 'last_insert_rowid'):
            self.lastrowid = res.last_insert_rowid
        return self

    def fetchall(self):
        rows = self._rows[self._idx:]
        self._idx = len(self._rows)
        return rows

    def fetchone(self):
        if self._idx < len(self._rows):
            r = self._rows[self._idx]
            self._idx += 1
            return r
        return None

    def fetchmany(self, size=1):
        rows = self._rows[self._idx:self._idx+size]
        self._idx += len(rows)
        return rows

    def close(self):
        pass

    def executemany(self, sql, seq_of_params=()):
        for params in seq_of_params:
            self.execute(sql, params)
        return self

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

class LibSQLConnectionWrapper:
    def __init__(self, client):
        self.client = client
        self.row_factory = None

    def cursor(self):
        return LibSQLCursorWrapper(self.client)

    def execute(self, sql, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        pass

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass

def get_turso_credentials() -> Tuple[Optional[str], Optional[str]]:
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        try:
            import streamlit as st
            if not url:
                url = st.secrets.get("TURSO_DATABASE_URL")
            if not token:
                token = st.secrets.get("TURSO_AUTH_TOKEN")
        except Exception:
            pass
    if url and ("your-db-name" in url or "your-turso" in url):
        url = None
    if token and ("your-turso" in token or "your-auth-token" in token):
        token = None
    return url, token

def get_db_type() -> str:
    turso_url, turso_token = get_turso_credentials()
    if turso_url and turso_token:
        try:
            import libsql_experimental
            return "Turso Cloud Database"
        except (ImportError, ModuleNotFoundError):
            try:
                import libsql_client
                return "Turso Cloud Database (libsql-client)"
            except (ImportError, ModuleNotFoundError):
                return "Local SQLite Database (Turso driver missing)"
    return "Local SQLite Database"

def get_connection():
    turso_url, turso_token = get_turso_credentials()
    
    if turso_url and turso_token:
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(database=turso_url, auth_token=turso_token)
            return conn
        except (ImportError, ModuleNotFoundError, Exception) as e:
            try:
                import libsql_client
                http_url = turso_url.replace("libsql://", "https://") if turso_url.startswith("libsql://") else turso_url
                client = libsql_client.create_client_sync(url=http_url, auth_token=turso_token)
                return LibSQLConnectionWrapper(client)
            except Exception as e2:
                print(f"Turso connection fallback to SQLite: {e} / {e2}")
            
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------------------------------
# PASSWORD HASHING HELPERS
# ----------------------------------------------------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${key.hex()}"

def verify_password(stored_password_hash: str, password_attempt: str) -> bool:
    try:
        if not stored_password_hash or "$" not in stored_password_hash:
            return False
        salt, key_hex = stored_password_hash.split("$", 1)
        attempt_key = hashlib.pbkdf2_hmac('sha256', password_attempt.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return secrets.compare_digest(key_hex, attempt_key)
    except Exception:
        return False

# ----------------------------------------------------
# DB INITIALIZATION & MIGRATIONS
# ----------------------------------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'Member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
            username TEXT DEFAULT 'admin',
            visibility TEXT DEFAULT 'Family',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check for column migrations on expenses table
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in cursor.fetchall()]
    if "half_year" not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN half_year TEXT DEFAULT 'H1'")
    if "username" not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN username TEXT DEFAULT 'admin'")
    if "visibility" not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN visibility TEXT DEFAULT 'Family'")
    
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
    
    # Seed default admin if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    user_cnt = cursor.fetchone()[0]
    if user_cnt == 0:
        admin_hash = hash_password("admin1234")
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ("admin", admin_hash, "Administrator", "Admin"))
        
    conn.commit()
    conn.close()

# ----------------------------------------------------
# USER AUTHENTICATION & MANAGEMENT
# ----------------------------------------------------
def authenticate_user(username: str, password_attempt: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?", (username.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    user_dict = dict(row) if isinstance(row, sqlite3.Row) else {
        "id": row[0], "username": row[1], "password_hash": row[2], "full_name": row[3], "role": row[4]
    }
    
    if verify_password(user_dict["password_hash"], password_attempt):
        return {
            "id": user_dict["id"],
            "username": user_dict["username"],
            "full_name": user_dict["full_name"],
            "role": user_dict["role"]
        }
    return None

def create_user(username: str, password: str, full_name: str, role: str = "Member") -> Tuple[bool, str]:
    username_clean = username.strip().lower()
    if not username_clean:
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username_clean,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False, f"User '{username_clean}' already exists."
        
    pwd_hash = hash_password(password)
    cursor.execute("""
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, ?)
    """, (username_clean, pwd_hash, full_name.strip(), role))
    conn.commit()
    conn.close()
    return True, f"User '{username_clean}' created successfully!"

def update_user_password(username: str, new_password: str) -> Tuple[bool, str]:
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters long."
        
    conn = get_connection()
    cursor = conn.cursor()
    pwd_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (pwd_hash, username.strip().lower()))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if updated:
        return True, "Password updated successfully!"
    return False, "User not found."

def update_user_role(username: str, new_role: str) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username.strip().lower()))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if updated:
        return True, f"Role for '{username}' updated to '{new_role}'."
    return False, "User not found."

def get_all_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY username ASC")
    rows = cursor.fetchall()
    conn.close()
    users = []
    for r in rows:
        if isinstance(r, sqlite3.Row):
            users.append(dict(r))
        else:
            users.append({"id": r[0], "username": r[1], "full_name": r[2], "role": r[3], "created_at": r[4]})
    return users

def delete_user(username: str) -> Tuple[bool, str]:
    if username.strip().lower() == "admin":
        return False, "Default admin account cannot be deleted."
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username.strip().lower(),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if deleted:
        return True, f"User '{username}' deleted successfully."
    return False, "User not found."

# ----------------------------------------------------
# EXPENSE MANAGEMENT & DATA ACCESS
# ----------------------------------------------------
def _build_visibility_clause(username: Optional[str] = None, view_mode: str = "Family") -> Tuple[str, List[Any]]:
    """
    Constructs SQL clause based on view mode:
    - 'Family': (visibility = 'Family' OR username = current_user)
    - 'Private': (username = current_user AND visibility = 'Private')
    - 'All': (visibility = 'Family' OR username = current_user)
    """
    user_clean = (username or "admin").strip().lower()
    
    if view_mode == "Private":
        return " AND (username = ? AND visibility = 'Private')", [user_clean]
    elif view_mode == "Family":
        return " AND (visibility = 'Family' OR username = ? OR username IS NULL)", [user_clean]
    else: # All Accessible
        return " AND (visibility = 'Family' OR username = ? OR username IS NULL)", [user_clean]

def insert_expenses(
    expense_rows: List[Dict[str, Any]], 
    source: str = "Manual",
    username: str = "admin",
    visibility: str = "Family"
) -> int:
    from config import get_indian_half_year
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    user_clean = username.strip().lower()
    
    for row in expense_rows:
        raw_date = row.get("date")
        if raw_date is None or pd.isna(raw_date) or str(raw_date).strip() == "":
            continue
            
        try:
            if isinstance(raw_date, (datetime.date, datetime.datetime)):
                dt = raw_date.date() if isinstance(raw_date, datetime.datetime) else raw_date
            else:
                dt = pd.to_datetime(str(raw_date), dayfirst=True, format="mixed").date()
        except Exception:
            continue
            
        fy = get_indian_fy(dt)
        q_code, _ = get_indian_quarter(dt)
        h_code, _ = get_indian_half_year(dt)
        cat = row.get("category", "Miscellaneous")
        desc = row.get("description", "")
        row_vis = row.get("visibility", visibility)
        
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
            INSERT INTO expenses (expense_date, financial_year, quarter, half_year, category, description, amount, source_note, username, visibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dt.isoformat(), fy, q_code, h_code, cat, str(desc), amt, source, user_clean, row_vis))
        count += 1
        
    conn.commit()
    conn.close()
    return count

def get_expenses_df(
    fy: Optional[str] = None, 
    category: Optional[str] = None,
    username: Optional[str] = None,
    view_mode: str = "Family"
) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    
    vis_clause, vis_params = _build_visibility_clause(username, view_mode)
    query += vis_clause
    params.extend(vis_params)
    
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

def get_all_financial_years(username: Optional[str] = None, view_mode: str = "Family") -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT financial_year FROM expenses WHERE 1=1"
    vis_clause, vis_params = _build_visibility_clause(username, view_mode)
    query += vis_clause + " ORDER BY financial_year DESC"
    cursor.execute(query, vis_params)
    fys = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    current_fy = get_indian_fy(datetime.date.today())
    if current_fy not in fys:
        fys.insert(0, current_fy)
    return fys

def get_category_breakdown(fy: Optional[str] = None, username: Optional[str] = None, view_mode: str = "Family") -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT category, SUM(amount) as Total_Amount, COUNT(*) as Transaction_Count, AVG(amount) as Avg_Amount
        FROM expenses
        WHERE 1=1
    """
    params = []
    vis_clause, vis_params = _build_visibility_clause(username, view_mode)
    query += vis_clause
    params.extend(vis_params)
    
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY category ORDER BY Total_Amount DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_monthly_trend_df(fy: Optional[str] = None, username: Optional[str] = None, view_mode: str = "Family") -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT strftime('%Y-%m', expense_date) as YearMonth, financial_year, category, SUM(amount) as Monthly_Total
        FROM expenses
        WHERE 1=1
    """
    params = []
    vis_clause, vis_params = _build_visibility_clause(username, view_mode)
    query += vis_clause
    params.extend(vis_params)
    
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY YearMonth, category ORDER BY YearMonth ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_quarterly_trend_df(fy: Optional[str] = None, username: Optional[str] = None, view_mode: str = "Family") -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT financial_year, quarter, category, SUM(amount) as Quarterly_Total
        FROM expenses
        WHERE 1=1
    """
    params = []
    vis_clause, vis_params = _build_visibility_clause(username, view_mode)
    query += vis_clause
    params.extend(vis_params)
    
    if fy and fy != "All FYs":
        query += " AND financial_year = ?"
        params.append(fy)
        
    query += " GROUP BY financial_year, quarter, category ORDER BY financial_year ASC, quarter ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_period_surge_analytics(
    timeframe_type: str = "Month-wise",
    selected_period: Optional[str] = None,
    fy: Optional[str] = None,
    username: Optional[str] = None,
    view_mode: str = "Family"
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Computes period spend vs historical baseline average per category for any timeframe:
    - timeframe_type: 'Month-wise', 'Quarter-wise', 'Half Year-wise', 'Financial Year'
    - selected_period: e.g. '2024-05', 'Q1', 'H1', 'FY 2024-25'
    Returns (surge_df, available_periods_list).
    """
    all_df = get_expenses_df(fy=None, username=username, view_mode=view_mode)
    if all_df.empty:
        return pd.DataFrame(), []

    all_df["expense_date"] = pd.to_datetime(all_df["expense_date"])
    all_df["Month_Year"] = all_df["expense_date"].dt.strftime("%Y-%m")

    # Determine grouping column based on timeframe_type
    if timeframe_type == "Month-wise":
        period_col = "Month_Year"
    elif timeframe_type == "Quarter-wise":
        period_col = "quarter"
    elif timeframe_type == "Half Year-wise":
        period_col = "half_year"
    else:
        period_col = "financial_year"

    # Filter by FY if specified and not 'All FYs'
    filtered_df = all_df.copy()
    if fy and fy != "All FYs":
        filtered_df = filtered_df[filtered_df["financial_year"] == fy]

    if filtered_df.empty:
        return pd.DataFrame(), []

    available_periods = sorted(filtered_df[period_col].dropna().unique().tolist(), reverse=True)
    if not available_periods:
        return pd.DataFrame(), []

    target_period = selected_period if (selected_period and selected_period in available_periods) else available_periods[0]

    # Selected period dataframe
    period_df = filtered_df[filtered_df[period_col] == target_period]
    period_cat_spend = period_df.groupby("category")["amount"].sum().reset_index()
    period_cat_spend.rename(columns={"amount": "Period_Spend"}, inplace=True)

    # Historical baseline average per category
    period_summary = filtered_df.groupby([period_col, "category"])["amount"].sum().reset_index()
    hist_baseline = period_summary[period_summary[period_col] != target_period].groupby("category")["amount"].mean().reset_index()
    if hist_baseline.empty:
        hist_baseline = period_summary.groupby("category")["amount"].mean().reset_index()
    hist_baseline.rename(columns={"amount": "Baseline_Avg"}, inplace=True)

    # Master Category DataFrame
    cat_df = pd.DataFrame({"category": EXPENSE_CATEGORIES})
    merged = pd.merge(cat_df, period_cat_spend, on="category", how="left").fillna(0.0)
    merged = pd.merge(merged, hist_baseline, on="category", how="left").fillna(0.0)

    merged["Period_Spend"] = merged["Period_Spend"].astype(float)
    merged["Baseline_Avg"] = merged["Baseline_Avg"].astype(float)
    merged["Surge_Amount"] = (merged["Period_Spend"] - merged["Baseline_Avg"]).astype(float)

    baseline_s = merged["Baseline_Avg"]
    surge_pct = ((merged["Period_Spend"] - baseline_s) / baseline_s) * 100.0
    merged["Surge_%"] = surge_pct.where(baseline_s > 0, 0.0).astype(float)

    # Anomaly Flag: Surge >= 15% AND Surge Amount > 500
    merged["Is_Anomaly"] = (merged["Surge_%"] >= 15.0) & (merged["Surge_Amount"] > 500.0)

    # Sort by Surge_% descending
    merged = merged.sort_values(by="Surge_%", ascending=False).reset_index(drop=True)

    return merged, available_periods

def get_surge_categories(fy: str, username: Optional[str] = None, view_mode: str = "Family") -> pd.DataFrame:
    df = get_expenses_df(fy=fy, username=username, view_mode=view_mode)
    if df.empty:
        return pd.DataFrame()
        
    category_summary = df.groupby("category")["amount"].agg(
        Total="sum", Count="count", Avg_Txn="mean", Max_Txn="max"
    ).reset_index()
    
    latest_month = df["Month_Year"].iloc[0] if not df.empty else None
    
    recent_month_df = df[df["Month_Year"] == latest_month].groupby("category")["amount"].sum().reset_index()
    recent_month_df.rename(columns={"amount": "Latest_Month_Spend"}, inplace=True)
    
    prev_months_df = df[df["Month_Year"] != latest_month].groupby("category")["amount"].mean().reset_index()
    prev_months_df.rename(columns={"amount": "Hist_Monthly_Avg"}, inplace=True)
    
    merged = pd.merge(category_summary, recent_month_df, on="category", how="left").fillna(0.0)
    merged = pd.merge(merged, prev_months_df, on="category", how="left").fillna(0.0)
    
    hist_avg = merged["Hist_Monthly_Avg"].astype(float)
    latest_spend = merged["Latest_Month_Spend"].astype(float)
    surge_series = ((latest_spend - hist_avg) / hist_avg) * 100.0
    merged["Surge_%"] = surge_series.where(hist_avg > 0, 0.0).astype(float)
    
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

def get_budget_status(fy: str, username: Optional[str] = None, view_mode: str = "Family") -> pd.DataFrame:
    conn = get_connection()
    b_df = pd.read_sql_query("SELECT category, monthly_limit, annual_limit FROM budgets WHERE financial_year = ?", conn, params=[fy])
    conn.close()
    
    e_df = get_category_breakdown(fy=fy, username=username, view_mode=view_mode)
    
    cat_df = pd.DataFrame({"category": EXPENSE_CATEGORIES})
    merged = pd.merge(cat_df, b_df, on="category", how="left").fillna(0.0)
    
    if e_df.empty or "Total_Amount" not in e_df.columns:
        merged["Actual_Spent"] = 0.0
    else:
        merged = pd.merge(merged, e_df[["category", "Total_Amount"]], on="category", how="left").fillna(0.0)
        merged.rename(columns={"Total_Amount": "Actual_Spent"}, inplace=True)
    
    annual_limit = merged["annual_limit"].astype(float)
    monthly_limit = merged["monthly_limit"].astype(float)
    annual_budget = annual_limit.copy()
    annual_budget = annual_budget.where(annual_budget > 0, monthly_limit * 12.0)
    
    merged["Annual_Budget"] = annual_budget.astype(float)
    merged["Actual_Spent"] = merged["Actual_Spent"].astype(float)
    merged["Remaining"] = (merged["Annual_Budget"] - merged["Actual_Spent"]).astype(float)
    
    utilization_series = (merged["Actual_Spent"] / merged["Annual_Budget"]) * 100.0
    merged["Utilization_%"] = utilization_series.where(merged["Annual_Budget"] > 0, 0.0).astype(float)
    
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
        {"date": "2024-04-05", "category": "Groceries & Provisions", "description": "Monthly D-Mart provisions", "amount": 12500.00, "visibility": "Family"},
        {"date": "2024-04-10", "category": "Utilities (Electricity/Water/Gas)", "description": "Electricity & Gas Bill", "amount": 3400.00, "visibility": "Family"},
        {"date": "2024-04-15", "category": "Rent & Housing", "description": "Flat House Rent", "amount": 28000.00, "visibility": "Family"},
        {"date": "2024-04-20", "category": "Dining & Swiggy/Zomato", "description": "Weekend family dining", "amount": 4200.00, "visibility": "Family"},
        {"date": "2024-04-25", "category": "Transportation & Fuel", "description": "Car petrol refilling", "amount": 6500.00, "visibility": "Family"},
        {"date": "2024-05-02", "category": "Groceries & Provisions", "description": "Monthly ration & snacks", "amount": 13200.00, "visibility": "Family"},
        {"date": "2024-05-12", "category": "Healthcare & Medicines", "description": "Apollo pharmacy medicines", "amount": 4800.00, "visibility": "Family"},
        {"date": "2024-05-18", "category": "Domestic Help & Services", "description": "Maid & Cook salary", "amount": 9500.00, "visibility": "Family"},
        {"date": "2024-05-28", "category": "Shopping & Apparel", "description": "Summer clothing purchase", "amount": 8400.00, "visibility": "Private"},
        {"date": "2024-06-04", "category": "Groceries & Provisions", "description": "Vegetables & groceries", "amount": 14100.00, "visibility": "Family"},
        {"date": "2024-06-15", "category": "Rent & Housing", "description": "Flat Rent", "amount": 28000.00, "visibility": "Family"},
        {"date": "2024-06-22", "category": "Utilities (Electricity/Water/Gas)", "description": "Summer AC electricity bill", "amount": 6200.00, "visibility": "Family"},
        {"date": "2025-04-05", "category": "Groceries & Provisions", "description": "Monthly Provisions", "amount": 14800.00, "visibility": "Family"},
        {"date": "2025-04-12", "category": "Rent & Housing", "description": "Flat Rent (Revised)", "amount": 30000.00, "visibility": "Family"},
        {"date": "2025-05-10", "category": "Healthcare & Medicines", "description": "Annual health checkups", "amount": 12000.00, "visibility": "Family"},
        {"date": "2025-06-15", "category": "Utilities (Electricity/Water/Gas)", "description": "AC Electricity peak bill", "amount": 7800.00, "visibility": "Family"}
    ]
    
    insert_expenses(sample_records, source="Sample Seeder", username="admin", visibility="Family")

def get_cumulative_metrics(fy: Optional[str] = None, username: Optional[str] = None, view_mode: str = "Family") -> Dict[str, float]:
    df = get_expenses_df(fy=fy, username=username, view_mode=view_mode)
    if df.empty:
        return {"YTD": 0.0, "QTD": 0.0, "H1": 0.0, "H2": 0.0}
        
    ytd_total = float(df["amount"].sum())
    h1_total = float(df[df["half_year"] == "H1"]["amount"].sum()) if "half_year" in df.columns else 0.0
    h2_total = float(df[df["half_year"] == "H2"]["amount"].sum()) if "half_year" in df.columns else 0.0
    
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
                dt = pd.to_datetime(str(raw_date), dayfirst=True, format="mixed").date()
        except Exception:
            continue
            
        fy = get_indian_fy(dt)
        q_code, _ = get_indian_quarter(dt)
        h_code, _ = get_indian_half_year(dt)
        cat = row.get("category", "Miscellaneous")
        desc = str(row.get("description", ""))
        vis = str(row.get("visibility", "Family"))
        
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
                amount = ?,
                visibility = ?
            WHERE id = ?
        """, (dt.isoformat(), fy, q_code, h_code, cat, desc, amt, vis, int(exp_id)))
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
