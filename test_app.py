import os
import tempfile
import datetime
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import database
from config import get_indian_fy, get_indian_quarter, get_indian_half_year, format_inr, format_inr_short
from database import (
    init_db,
    insert_expenses,
    get_expenses_df,
    delete_month_expenses,
    delete_expense,
    update_expenses_df,
    authenticate_user,
    create_user,
    update_user_password,
    update_user_role,
    get_all_users,
    delete_user
)
from cpi_data import calculate_cpi_inflation
from categorizer import auto_categorize_description, auto_categorize_records

# Isolate test suite DB so live data/expenses.db is NEVER touched or modified by test runs
temp_db = tempfile.NamedTemporaryFile(suffix="_test.db", delete=False)
database.DB_PATH = temp_db.name
temp_db.close()

def test_strict_uploaded_date_enforcement():
    init_db()
    test_rows = [
        {"date": "2024-11-15", "category": "Shopping & Apparel", "description": "Explicit date row", "amount": 3500.0},
        {"date": None, "category": "Groceries & Provisions", "description": "Missing date row", "amount": 1000.0},
        {"date": "", "category": "Dining & Swiggy/Zomato", "description": "Empty date row", "amount": 500.0}
    ]
    inserted = insert_expenses(test_rows, source="Strict Date Test")
    assert inserted == 1
    print("✅ Strict uploaded date enforcement passed.")

def test_user_auth_and_management():
    init_db()
    delete_user("rahul")
    # Test default admin login
    admin = authenticate_user("admin", "admin1234")
    assert admin is not None
    assert admin["role"] == "Admin"
    
    # Test wrong password
    assert authenticate_user("admin", "wrongpwd") is None
    
    # Create new user
    ok, msg = create_user("rahul", "rahul123", "Rahul Sharma", "Member")
    assert ok
    rahul = authenticate_user("rahul", "rahul123")
    assert rahul is not None
    assert rahul["role"] == "Member"
    
    # Update password
    ok_pwd, _ = update_user_password("rahul", "newpwd456")
    assert ok_pwd
    assert authenticate_user("rahul", "newpwd456") is not None
    
    print("✅ User authentication & user management tests passed.")

def test_private_vs_family_visibility_scoping():
    init_db()
    # Add family expense and private expense for admin
    insert_expenses([
        {"date": "2025-05-10", "category": "Groceries & Provisions", "description": "Shared Family Groceries", "amount": 4000.0, "visibility": "Family"}
    ], source="Test", username="admin", visibility="Family")
    
    insert_expenses([
        {"date": "2025-05-12", "category": "Shopping & Apparel", "description": "Admin Secret Gift", "amount": 1500.0, "visibility": "Private"}
    ], source="Test", username="admin", visibility="Private")

    insert_expenses([
        {"date": "2025-05-15", "category": "Shopping & Apparel", "description": "Rahul Private Item", "amount": 2200.0, "visibility": "Private"}
    ], source="Test", username="rahul", visibility="Private")
    
    # Admin Family View (sees Family items + own items)
    df_admin_family = get_expenses_df(username="admin", view_mode="Family")
    descriptions_admin_fam = df_admin_family["description"].tolist() if not df_admin_family.empty else []
    assert "Shared Family Groceries" in descriptions_admin_fam
    assert "Rahul Private Item" not in descriptions_admin_fam
    
    # Admin Private View (sees only Admin Private items)
    df_admin_priv = get_expenses_df(username="admin", view_mode="Private")
    descriptions_admin_priv = df_admin_priv["description"].tolist() if not df_admin_priv.empty else []
    assert "Admin Secret Gift" in descriptions_admin_priv
    assert "Shared Family Groceries" not in descriptions_admin_priv
    
    # Rahul Private View (sees only Rahul Private items)
    df_rahul_priv = get_expenses_df(username="rahul", view_mode="Private")
    descriptions_rahul_priv = df_rahul_priv["description"].tolist() if not df_rahul_priv.empty else []
    assert "Rahul Private Item" in descriptions_rahul_priv
    assert "Admin Secret Gift" not in descriptions_rahul_priv

    print("✅ Private vs. Family visibility scoping tests passed.")

def test_inline_database_update():
    init_db()
    df = get_expenses_df(fy="FY 2024-25")
    assert not df.empty
    
    row_to_edit = df.iloc[0].to_dict()
    row_to_edit["expense_date"] = "2024-04-10"
    row_to_edit["description"] = "Updated Description via Editor"
    row_to_edit["amount"] = 9999.00
    
    updated_cnt = update_expenses_df(pd.DataFrame([row_to_edit]))
    assert updated_cnt == 1
    
    df_updated = get_expenses_df(fy="FY 2024-25")
    matched = df_updated[df_updated["id"] == row_to_edit["id"]]
    assert not matched.empty
    assert matched.iloc[0]["description"] == "Updated Description via Editor"
    assert matched.iloc[0]["amount"] == 9999.00
    print("✅ Inline database update & FY recalculation passed.")

def test_ml_auto_categorization():
    init_db()
    from categorizer import MLCategorizer, apply_ml_auto_categorization
    
    historical_samples = [
        {"description": "swiggy biryani dinner", "category": "Dining & Swiggy/Zomato"},
        {"description": "nandini milk 1L", "category": "Milk & Dairy"},
        {"description": "bescom power electricity bill", "category": "Utilities (Electricity/Water/Gas)"},
        {"description": "apollo medicine tablets", "category": "Healthcare & Medicines"}
    ]
    
    model = MLCategorizer()
    trained_count = model.train(historical_samples)
    assert trained_count == 4
    
    cat1, conf1, m1 = model.predict("swiggy food order")
    assert cat1 == "Dining & Swiggy/Zomato"
    
    cat2, conf2, m2 = model.predict("nandini milk packet")
    assert cat2 == "Milk & Dairy"
    
    test_df = pd.DataFrame([
        {"id": 9991, "description": "swiggy food order", "category": "Miscellaneous"},
        {"id": 9992, "description": "bescom electricity payment", "category": ""}
    ])
    
    updated_df, mod_cnt, t_cnt = apply_ml_auto_categorization(test_df, historical_samples, overwrite_all=False)
    assert mod_cnt == 2
    assert updated_df.iloc[0]["category"] == "Dining & Swiggy/Zomato"
    assert updated_df.iloc[1]["category"] == "Utilities (Electricity/Water/Gas)"
    
    print("✅ Machine Learning Auto-Categorization tests passed.")

def test_period_surge_analytics():
    init_db()
    from database import get_period_surge_analytics
    from categorizer import generate_ai_spend_rationalization
    
    surge_df, periods = get_period_surge_analytics(timeframe_type="Month-wise", selected_period=None, fy="FY 2024-25")
    assert not surge_df.empty
    assert "Period_Spend" in surge_df.columns
    assert "Baseline_Avg" in surge_df.columns
    assert "Surge_%" in surge_df.columns
    assert "Is_Anomaly" in surge_df.columns
    
    ai_advice = generate_ai_spend_rationalization(surge_df, timeframe_label="Month 2024-05")
    assert "summary" in ai_advice
    assert "recommendations" in ai_advice
    assert "total_potential_savings" in ai_advice
    
    print("✅ Period Surge Analytics & AI Spend Rationalization tests passed.")

def test_smart_suggested_budgets():
    init_db()
    from database import get_suggested_budgets, batch_set_category_budgets
    
    s_df = get_suggested_budgets(fy="FY 2024-25", target_total_monthly=90000.0)
    assert not s_df.empty
    assert "suggested_monthly" in s_df.columns
    assert "hist_monthly_avg" in s_df.columns
    
    recs = [
        {"category": "Groceries & Provisions", "monthly_limit": 25000.0, "annual_limit": 300000.0},
        {"category": "Utilities (Electricity/Water/Gas)", "monthly_limit": 8000.0, "annual_limit": 96000.0}
    ]
    cnt = batch_set_category_budgets("FY 2024-25", recs)
    assert cnt == 2
    print("✅ Smart Suggested Budgets & Batch Update tests passed.")

def test_investment_planner():
    from investment_planner import calculate_investment_plan, generate_ai_wealth_advice
    
    plan = calculate_investment_plan(age=30, current_savings=600000.0, monthly_investment_budget=25000.0, monthly_expenses=40000.0)
    assert plan["equity_pct"] == 80.0
    assert plan["investable_sip_monthly"] > 0
    assert 20 in plan["projections"]
    assert plan["projections"][20]["total_future_value"] > plan["projections"][20]["total_invested"]
    
    advice = generate_ai_wealth_advice(plan)
    assert "summary" in advice
    assert "key_takeaways" in advice
    print("✅ Investment & Wealth Portfolio Planner tests passed.")

def test_active_holdings_tracker():
    init_db()
    from database import insert_investment, get_user_investments_df, update_investments_df, delete_investment
    from investment_planner import generate_ai_portfolio_suggestions
    
    inv_id1 = insert_investment("admin", "Zerodha", "Equity (Stocks)", 100000.0, 2022, 140000.0)
    inv_id2 = insert_investment("admin", "SBI", "EPF", 200000.0, 2021, 230000.0)
    
    df = get_user_investments_df("admin")
    assert not df.empty
    assert len(df) >= 2
    assert "unrealized_gain" in df.columns
    assert "returns_pct" in df.columns
    
    df.loc[df["id"] == inv_id1, "current_value"] = 150000.0
    upd_cnt = update_investments_df(df)
    assert upd_cnt >= 1
    
    ai_suggestions = generate_ai_portfolio_suggestions(df)
    assert "summary" in ai_suggestions
    assert "recommendations" in ai_suggestions
    
    del_ok = delete_investment(inv_id1)
    assert del_ok is True
    print("✅ Active Investment Portfolio & Holdings Tracker tests passed.")

if __name__ == "__main__":
    try:
        test_strict_uploaded_date_enforcement()
        test_user_auth_and_management()
        test_private_vs_family_visibility_scoping()
        test_inline_database_update()
        test_ml_auto_categorization()
        test_period_surge_analytics()
        test_smart_suggested_budgets()
        test_investment_planner()
        test_active_holdings_tracker()
        print("🎉 All test suite assertions passed successfully!")
    finally:
        if os.path.exists(database.DB_PATH):
            os.unlink(database.DB_PATH)
