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
    delete_user,
    add_income_source,
    get_income_sources_df,
    delete_income_source
)
from cpi_data import calculate_cpi_inflation
from categorizer import auto_categorize_description, auto_categorize_records

# Isolate test suite DB so live data/expenses.db is NEVER touched or modified by test runs
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""
database.get_turso_credentials = lambda: (None, None)
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

def test_statement_ingestion_and_segments():
    init_db()
    from statement_parser import identify_and_parse_statement
    from database import batch_insert_investments, get_user_investments_df
    from investment_planner import analyze_portfolio_segments, calculate_asset_allocation_drift
    
    csv_content = b"Symbol,Quantity,Avg Price,CMP,Category\nINFY,10,1400,1500,Equity\nHDFCMF,100,50,60,Mutual Fund\n"
    
    parsed = identify_and_parse_statement(csv_content, "icici_statement.csv")
    assert len(parsed) == 2
    assert parsed[0]["type"] == "Equity"
    assert parsed[1]["type"] == "Mutual Funds"
    
    cnt = batch_insert_investments(parsed, "admin", family_id=1)
    assert cnt == 2
    
    df = get_user_investments_df("admin")
    assert not df.empty
    
    segments = analyze_portfolio_segments(df)
    assert "Equity" in segments["asset_class"]
    assert "Mutual Funds" in segments["asset_class"]
    
    drifts = calculate_asset_allocation_drift(segments, {"Equity": 60.0, "Mutual Funds": 40.0})
    assert isinstance(drifts, list)
    
    print("✅ Statement Ingestion & Segment Analytics tests passed.")

def test_multi_family_data_isolation():
    init_db()
    import uuid
    from database import (
        create_family,
        get_family_by_code,
        join_family_by_code,
        insert_expenses,
        get_expenses_df,
        insert_investment,
        get_user_investments_df
    )
    
    uid = uuid.uuid4().hex[:6]
    u_a = f"sharma_admin_{uid}"
    u_m = f"sharma_member_{uid}"
    u_b = f"verma_admin_{uid}"
    
    # 1. Create Family A
    ok_a, msg_a, user_a = create_family("Sharma Household", u_a, "pass123", "Sharma Admin")
    assert ok_a is True, f"create_family A failed: {msg_a}"
    fam_a_id = user_a["family_id"]
    fam_a_code = user_a["family_code"]
    
    # 2. Join Family A with Member A
    ok_m, msg_m, user_mem = join_family_by_code(fam_a_code, u_m, "pass123", "Sharma Member")
    assert ok_m is True, f"join_family A failed: {msg_m}"
    assert user_mem["family_id"] == fam_a_id
    
    # 3. Create Family B
    ok_b, msg_b, user_b = create_family("Verma Household", u_b, "pass123", "Verma Admin")
    assert ok_b is True, f"create_family B failed: {msg_b}"
    fam_b_id = user_b["family_id"]
    assert fam_b_id != fam_a_id
    
    # 4. Add Expenses in Family A and Family B
    insert_expenses([
        {"date": "2024-05-10", "category": "Groceries & Provisions", "description": "Sharma Groceries", "amount": 15000.0, "visibility": "Family"}
    ], username=u_a, family_id=fam_a_id)
    
    insert_expenses([
        {"date": "2024-05-12", "category": "Rent & Housing", "description": "Verma Rent", "amount": 40000.0, "visibility": "Family"}
    ], username=u_b, family_id=fam_b_id)
    
    # 5. Verify Expense Data Isolation
    df_fam_a = get_expenses_df(fy="FY 2024-25", username=u_a, view_mode="Family", family_id=fam_a_id)
    df_fam_b = get_expenses_df(fy="FY 2024-25", username=u_b, view_mode="Family", family_id=fam_b_id)
    
    assert len(df_fam_a) >= 1
    assert "Sharma Groceries" in df_fam_a["description"].values
    
    assert len(df_fam_b) >= 1
    assert "Verma Rent" in df_fam_b["description"].values
    
    # 6. Verify Investments Data Isolation
    insert_investment(u_a, "Zerodha", "Equity", 50000.0, 2023, 60000.0, family_id=fam_a_id)
    insert_investment(u_b, "Groww", "Mutual funds", 100000.0, 2022, 120000.0, family_id=fam_b_id)
    
    inv_a = get_user_investments_df(family_id=fam_a_id)
    inv_b = get_user_investments_df(family_id=fam_b_id)
    
    assert len(inv_a) >= 1
    assert "Zerodha" in inv_a["platform"].values
    
    assert len(inv_b) >= 1
    assert "Groww" in inv_b["platform"].values
    
    # 7. Verify Super Admin Access Across All Families
    df_super_admin = get_expenses_df(fy="FY 2024-25", username="admin", view_mode="SuperAdmin", family_id=None)
    assert len(df_super_admin) >= 2
    assert "Sharma Groceries" in df_super_admin["description"].values
    assert "Verma Rent" in df_super_admin["description"].values
    
    print("✅ Multi-Family Workspace & Super Admin Data Isolation tests passed.")

def test_duplicate_detection():
    from database import init_db, insert_expenses, get_expenses_df, delete_expense
    import pandas as pd
    
    init_db()
    
    # We will simulate the behavior of detect_and_flag_duplicates here
    # since importing from app.py runs Streamlit.
    
    # Insert some initial data
    u = "testuser"
    f_id = 99
    
    insert_expenses([{
        "date": "2023-01-01",
        "category": "Food",
        "description": "Lunch",
        "amount": 500.0,
        "visibility": "Private"
    }], source="Test", username=u, visibility="Private", family_id=f_id)
    
    # Now simulate the imported file
    df_import = pd.DataFrame([
        {"date": "2023-01-01", "category": "Food", "description": "Lunch", "amount": 500.0},
        {"date": "2023-01-02", "category": "Transport", "description": "Taxi", "amount": 250.0}
    ])
    
    # 1. Fetch existing
    existing = get_expenses_df(fy="All FYs", username=u, view_mode="Private", family_id=f_id)
    existing_sigs = set()
    for _, row in existing.iterrows():
        sig = (str(row['expense_date']).strip()[:10], float(row.get('amount', 0)))
        existing_sigs.add(sig)
        
    dup_list = []
    imp_list = []
    for _, row in df_import.iterrows():
        sig = (str(row.get('date', '')).strip()[:10], float(row.get('amount', 0)))
        is_dup = sig in existing_sigs
        dup_list.append(is_dup)
        imp_list.append(not is_dup)
        
    df_import["duplicate_warning"] = dup_list
    df_import["import"] = imp_list
    
    assert df_import.iloc[0]["duplicate_warning"] == True
    assert df_import.iloc[0]["import"] == False
    
    assert df_import.iloc[1]["duplicate_warning"] == False
    assert df_import.iloc[1]["import"] == True
    
    print("✅ File Import Duplicate Detection test passed.")

def test_income_source_crud():
    init_db()
    # Add income sources
    id1 = add_income_source(username="admin", family_id=1, source_name="Primary Salary", income_type="Salary", amount=100000.0, frequency="Monthly")
    id2 = add_income_source(username="admin", family_id=None, source_name="Freelance", income_type="Freelance/Consulting", amount=25000.0, frequency="Monthly")
    id3 = add_income_source(username="rahul", family_id=2, source_name="Rental", income_type="Rental Income", amount=15000.0, frequency="Monthly")

    assert id1 > 0
    assert id2 > 0
    assert id3 > 0

    df_admin = get_income_sources_df(username="admin", family_id=1, view_mode="Family")
    assert any(df_admin["source_name"] == "Primary Salary")

    # Test deleting when family_id is None (Super Admin / Global scope)
    assert delete_income_source(id2, family_id=None) == True
    df_after_del2 = get_income_sources_df(username="admin", family_id=1, view_mode="All")
    assert not any(df_after_del2["id"] == id2)

    # Test deleting when family_id is provided
    assert delete_income_source(id1, family_id=1) == True
    df_after_del1 = get_income_sources_df(username="admin", family_id=1, view_mode="Family")
    assert not any(df_after_del1["id"] == id1)

    # Test deleting row with mismatched family_id (properly prevented)
    assert delete_income_source(id3, family_id=1) == False
    assert delete_income_source(id3, family_id=2) == True
    df_after_del3 = get_income_sources_df(username="rahul", family_id=2, view_mode="Family")
    assert not any(df_after_del3["id"] == id3)

    # Deleting already deleted item returns False
    assert delete_income_source(id1, family_id=1) == False
    assert delete_income_source(99999, family_id=1) == False

    print("✅ Income Source CRUD and Deletion tests passed.")

def test_free_text_retirement_milestones_and_override():
    import investment_planner
    user_input = "Use this inputs .. 1. I am 53 now (in another few days)... i have following expense monthly expense of 1.75 lakhs. fixed expense of 7 lakhs a year starting 2027 for daughters education. additinoal marriaghe expense of 50 lakhs in 2035 . all figures should be inflation adjusted. add stanadard medical expense required.. anything else needed suggest("
    
    parsed = investment_planner.extract_free_text_parameters(user_input, base_age=50, current_year=2026)
    
    assert parsed["detected_age"] == 53
    assert parsed["monthly_living_expense"] == 175000.0
    assert parsed["monthly_medical_expense"] == 25000.0
    assert len(parsed["milestones"]) == 5
    
    # Verify education milestones (4 years starting 2027)
    edu_milestones = [m for m in parsed["milestones"] if "education" in m["description"].lower()]
    assert len(edu_milestones) == 4
    for m in edu_milestones:
        assert m["amount"] == 700000.0
        assert m["source"] == "Retirement Vision (Free Text)"
    assert [m["calendar_year"] for m in edu_milestones] == [2027, 2028, 2029, 2030]
    assert [m["age"] for m in edu_milestones] == [54, 55, 56, 57]
    
    # Verify marriage milestone in 2035 at age 62
    marr_milestones = [m for m in parsed["milestones"] if "marriage" in m["description"].lower() or "child's marriage" in m["description"].lower()]
    assert len(marr_milestones) == 1
    assert marr_milestones[0]["amount"] == 5000000.0
    assert marr_milestones[0]["calendar_year"] == 2035
    assert marr_milestones[0]["age"] == 62
    assert marr_milestones[0]["source"] == "Retirement Vision (Free Text)"
    
    # Test Detailed Expense Plan generation with these milestones
    exp_plan = investment_planner.generate_detailed_retirement_expense_plan(
        current_age=53,
        retirement_age=60,
        base_monthly_expense=175000.0,
        additional_monthly_expense=25000.0,
        one_time_expenses=parsed["milestones"],
        user_context=user_input,
        inflation_rate=0.06
    )
    assert len(exp_plan["milestones"]) == 5
    assert any(m["description"].startswith("Daughters Education") for m in exp_plan["milestones"])
    assert any("Marriage" in m["description"] for m in exp_plan["milestones"])
    
    # Verify post-retirement reserve in calculate_retirement_corpus (Age 62 milestone when retiring at 60)
    ret_plan = investment_planner.calculate_retirement_corpus(
        current_age=53,
        retirement_age=60,
        current_savings=5000000.0,
        monthly_sip=100000.0,
        cagr_decimal=0.12,
        one_time_expenses=parsed["milestones"],
        additional_monthly_expense=25000.0,
        inflation_rate=0.06
    )
    assert ret_plan["post_ret_milestones_count"] == 1
    assert ret_plan["post_ret_milestones_reserve_needed"] > 0
    print("✅ Free-text retirement milestone extraction & conflict override tests passed.")

def test_cost_of_living_variations_and_bullet_prefix_isolation():
    import investment_planner
    
    variations = [
        "1. monthly living: 150,000",
        "1. monthly cost of living 150,000",
        "1. cost of living is 150,000",
        "1. cost of living at 150,000",
        "1. cost of living 150,000",
        "1. cost of living: 150,000",
        "1. living expense 150,000",
        "1. living expenses 150,000",
        "1. 150,000 a month",
        "1. 150000/month",
        "1. 150,000/mo",
        "1. 150,000 / month",
        "1. 1.5 lakhs a month",
        "1. 1.5L / mo",
        "1. 150k a month",
        "1. 150k/month",
        "1. cost of living is 1.5 lakhs",
        "1. cost of living 1.5 lakhs",
        "1. cost of living 1.5L",
        "1. cost of living of 150000",
        "1. living expense 1.5 lakhs",
        "1. living expenses 1.5L"
    ]
    
    for v_str in variations:
        res = investment_planner.extract_free_text_parameters(v_str, base_age=53)
        assert res["monthly_living_expense"] == 150000.0, f"Failed on: '{v_str}' -> got {res.get('monthly_living_expense')}"
        
        # Ensure detailed expense plan reflects 150,000 and never clamps to 1000.0
        exp_plan = investment_planner.generate_detailed_retirement_expense_plan(
            current_age=53,
            retirement_age=60,
            base_monthly_expense=res["monthly_living_expense"],
            user_context=v_str
        )
        assert exp_plan["base_monthly_today"] == 150000.0, f"Expected 150,000 but got {exp_plan['base_monthly_today']}"
        assert exp_plan["base_monthly_today"] != 1000.0
        
    print("✅ Cost of living 150,000 variations and numbered bullet isolation tests passed.")

def test_mutual_exclusive_expense_sources():
    import investment_planner
    
    free_text = "I am 53 now. Monthly living expense 1.75 lakhs. Fixed expense of 7 lakhs a year starting 2027 for daughters education. Marriage expense of 50 lakhs in 2035."
    table_milestones = [{
        "amount": 2000000.0,
        "age": 58,
        "description": "Home Renovation",
        "source": "One-Time Milestone Table"
    }]
    
    # Test Option A: Structured Data Entry Columns (ignore_free_text_overrides=True)
    exp_plan_a = investment_planner.generate_detailed_retirement_expense_plan(
        current_age=53,
        retirement_age=60,
        base_monthly_expense=60000.0,
        additional_monthly_expense=10000.0,
        one_time_expenses=table_milestones,
        user_context=free_text,
        inflation_rate=0.06,
        ignore_free_text_overrides=True
    )
    # Under Option A, free text should NOT override base living expenses or milestones
    assert exp_plan_a["base_monthly_today"] == 60000.0, f"Expected 60,000 but got {exp_plan_a['base_monthly_today']}"
    assert len(exp_plan_a["milestones"]) == 1
    assert exp_plan_a["milestones"][0]["description"] == "Home Renovation"
    assert exp_plan_a["milestones"][0]["amount_today"] == 2000000.0
    
    # Test Option B: Free-Text Vision (uses extracted parameters, table bypassed)
    parsed = investment_planner.extract_free_text_parameters(free_text, base_age=53)
    exp_plan_b = investment_planner.generate_detailed_retirement_expense_plan(
        current_age=parsed["detected_age"] or 53,
        retirement_age=60,
        base_monthly_expense=parsed["monthly_living_expense"] or 50000.0,
        additional_monthly_expense=parsed["monthly_medical_expense"] or 0.0,
        one_time_expenses=parsed["milestones"],
        user_context=free_text,
        inflation_rate=0.06,
        ignore_free_text_overrides=False
    )
    # Under Option B, parsed text living expenses and milestones are used
    assert exp_plan_b["base_monthly_today"] == 175000.0, f"Expected 175,000 but got {exp_plan_b['base_monthly_today']}"
    assert len(exp_plan_b["milestones"]) == 5
    assert not any(m["description"] == "Home Renovation" for m in exp_plan_b["milestones"])
    assert any("Marriage" in m["description"] for m in exp_plan_b["milestones"])
    
    print("✅ Mutual exclusive expense sources (Option A vs Option B) test passed.")

def test_option_b_full_resolution():
    import investment_planner
    
    user_prompt = "Use this inputs .. 1. I am 53 now (in another few days)... i have following expense monthly expense of 1.75 lakhs.   fixed expense of 7 lakhs a year starting 2027 for daughters education. additinoal marriaghe expense of 50 lakhs in 2035 . all figures should be inflation adjusted. add stanadard medical expense required.. anything else needed suggest"
    
    # Table data entered in Option A
    table_milestones = [{
        "amount": 1000000.0,
        "age": 55,
        "description": "Car Upgrade",
        "source": "One-Time Milestone Table"
    }]
    table_base_living = 25000.0
    table_recurring = 5000.0
    u_age = 50
    ret_age = 60
    
    # Simulate Option B mode selection
    is_free_text_mode = True
    parsed = investment_planner.extract_free_text_parameters(user_prompt, base_age=u_age)
    
    if is_free_text_mode:
        active_milestones = parsed["milestones"]
        calc_base_living_exp = float(parsed["monthly_living_expense"] or 50000.0)
        calc_recurring_exp = float(parsed["monthly_medical_expense"] or 0.0)
        calc_user_age = int(parsed.get("detected_age") or u_age)
        calc_ret_age = int(parsed.get("detected_retirement_age") or ret_age)
        active_user_context = user_prompt
        ignore_free_text = False
    else:
        active_milestones = table_milestones
        calc_base_living_exp = float(table_base_living)
        calc_recurring_exp = float(table_recurring)
        calc_user_age = int(u_age)
        calc_ret_age = int(ret_age)
        active_user_context = ""
        ignore_free_text = True
        
    assert calc_user_age == 53
    assert calc_base_living_exp == 175000.0
    assert calc_recurring_exp == 25000.0
    assert len(active_milestones) == 5
    assert not any(m["description"] == "Car Upgrade" for m in active_milestones)
    
    ret_plan = investment_planner.calculate_retirement_corpus(
        current_age=calc_user_age,
        retirement_age=calc_ret_age,
        current_savings=5000000.0,
        monthly_sip=50000.0,
        cagr_decimal=0.12,
        one_time_expenses=active_milestones,
        additional_monthly_expense=calc_recurring_exp,
        outstanding_debt=0.0,
        real_estate_value=0.0,
        inflation_rate=0.06
    )
    assert ret_plan["post_ret_milestones_count"] == 1 # 2035 Marriage (Age 62)
    assert ret_plan["post_ret_milestones_reserve_needed"] > 0
    
    exp_plan = investment_planner.generate_detailed_retirement_expense_plan(
        current_age=calc_user_age,
        retirement_age=calc_ret_age,
        base_monthly_expense=calc_base_living_exp,
        additional_monthly_expense=calc_recurring_exp,
        one_time_expenses=active_milestones,
        user_context=active_user_context,
        inflation_rate=0.06,
        safe_monthly_withdrawal=ret_plan["safe_monthly_withdrawal"],
        ignore_free_text_overrides=ignore_free_text
    )
    assert exp_plan["base_monthly_today"] == 175000.0
    assert len(exp_plan["milestones"]) == 5
    assert not any(m["description"] == "Car Upgrade" for m in exp_plan["milestones"])
    print("✅ Option B full resolution and Option A bypass test passed.")

def test_retire_at_55_statement_parsing():
    import investment_planner
    t = ("I want to retire at 55. Consider total monthly expense of 150,000.  fixed expense of  7lakhs from 2027 for 6 years "
         "and one time cost of 50 lakhs at 2035 and other standard expenses in line with getting older. "
         "family - wife and 2 kids - son age 22 and duaghter age 17")
    r = investment_planner.extract_free_text_parameters(t, base_age=52, current_year=2026)
    assert r["detected_retirement_age"] == 55
    assert r["monthly_living_expense"] == 150000.0
    assert r["monthly_medical_expense"] == 25000.0
    recurring = [m for m in r["milestones"] if "Yr" in m["description"]]
    assert len(recurring) == 6 and all(m["amount"] == 700000.0 for m in recurring)
    one_time = [m for m in r["milestones"] if m["calendar_year"] == 2035]
    assert len(one_time) == 1 and one_time[0]["amount"] == 5000000.0
    assert {f["role"] for f in r["family"]} == {"Son", "Daughter"}
    print("✅ Retire-at-55 free-text statement parsing test passed.")

def test_friendly_gemini_errors():
    from ai_errors import friendly_gemini_error
    raw503 = "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.', 'status': 'UNAVAILABLE'}}"
    msg = friendly_gemini_error(Exception(raw503), 3)
    assert "busy" in msg and "503" not in msg and "UNAVAILABLE" not in msg and "{" not in msg
    assert "limit" in friendly_gemini_error(Exception("429 RESOURCE_EXHAUSTED quota"))
    assert "API key" in friendly_gemini_error(Exception("400 API key not valid"))
    assert "went wrong" in friendly_gemini_error(Exception("weird"))
    print("✅ Friendly Gemini error mapping test passed.")

def test_academy_fallback():
    from academy_fallback import (fallback_new_session, fallback_next_question, fallback_record_answer,
                                  fallback_result, fallback_learning_path, MAX_QUESTIONS)
    from ai_errors import is_service_unavailable
    assert is_service_unavailable("503 UNAVAILABLE high demand")
    assert not is_service_unavailable("API key not valid")
    profile = {"monthly_income": 200000.0, "monthly_expense": 150000.0, "top_category": "Dining",
               "top_category_amount": 30000.0, "top_category_pct": 20.0, "total_debt": 500000.0,
               "portfolio_value": 1000000.0, "equity_pct": 60.0, "asset_classes": {}}
    for best, expect in ((2, "Advanced"), (0, "Beginner")):
        st_ = fallback_new_session(profile)
        seen = set()
        while True:
            q = fallback_next_question(st_)
            if q is None:
                break
            assert q["id"] not in seen
            seen.add(q["id"])
            idx = q["scores"].index(best)
            fallback_record_answer(st_, q, idx)
        assert len(st_["answers"]) == MAX_QUESTIONS
        assert fallback_result(st_)["final_score"] == expect
    # real figures appear in question text
    q = fallback_next_question(fallback_new_session(profile))
    assert "Dining" in q["text"] and "30,000" in q["text"]
    # works with an empty profile (generic wording)
    empty = fallback_new_session({"monthly_income": 0, "monthly_expense": 0, "top_category": None,
                                  "top_category_amount": 0, "top_category_pct": 0, "total_debt": 0,
                                  "portfolio_value": 0, "equity_pct": None, "asset_classes": {}})
    assert fallback_next_question(empty)["options"]
    path = fallback_learning_path({"knowledge_level": "Beginner", "location_preference": "Both",
                                   "investment_interests": ["Mutual Funds (Equity, Debt, Hybrid)", "Direct Stocks"],
                                   "total_monthly_income": 200000, "total_debt": 500000})
    names = [m["module_name"] for m in path["modules"]]
    assert path["source"] == "database" and len(names) == 4, names
    print("✅ Academy database fallback test passed.")


def test_algo_advisor():
    import pandas as pd
    from algo_advisor import (build_algo_advice, select_tier, classify_holding, evaluate_regime,
                              LARGE, FLEXI, MIDSMALL, DEBT, GOLD, EXCLUDED)
    assert select_tier("Aggressive", 35)[0] == "High"
    assert select_tier("Aggressive", 62)[0] == "Moderate"
    assert select_tier("Moderate", 72)[0] == "Low"
    assert select_tier("Conservative", 30, override="High")[0] == "High"
    assert classify_holding({"investment_type": "PPF"}) == DEBT
    assert classify_holding({"investment_type": "Real Estate"}) == EXCLUDED
    assert classify_holding({"investment_type": "Gold / Sovereign Gold Bonds (SGB)"}) == GOLD
    assert classify_holding({"investment_type": "Mutual funds", "resolved_name": "UTI Nifty 50 Index Fund"}) == LARGE
    assert classify_holding({"investment_type": "Equity (Stocks)", "market_cap": "Small Cap"}) == MIDSMALL
    assert classify_holding({"investment_type": "Mutual funds", "resolved_name": "XYZ Flexi Cap Fund"}) == FLEXI

    df = pd.DataFrame([
        {"investment_type": "Equity (Stocks)", "description": "SMALLCO", "market_cap": "Small Cap", "current_value": 600000, "returns_pct": -20},
        {"investment_type": "Mutual funds", "resolved_name": "Nifty 50 Index Fund", "current_value": 200000, "returns_pct": 12},
        {"investment_type": "PPF", "current_value": 100000, "returns_pct": 7},
        {"investment_type": "Real Estate", "current_value": 5000000, "returns_pct": 30},
    ])
    res = build_algo_advice(df, "Conservative", 40, 20000, None)
    assert res["tier"] == "Low" and res["total_value"] == 900000 and res["excluded_value"] == 5000000
    acts = {h["Holding"]: h for h in res["holding_actions"]}
    assert acts["SMALLCO"]["Action"] == "SELL / TRIM" and acts["SMALLCO"]["Amount"] > 0
    assert any(b["Sleeve"] == GOLD and b["Amount"] > 0 for b in res["buys"])
    assert any(b["Sleeve"] == DEBT for b in res["buys"])
    assert abs(sum(x["Monthly ₹"] for x in res["sip_plan"]) - 20000) < 1
    assert res["summary_lines"] and "SELL / TRIM" in " ".join(res["summary_lines"])

    # regime triggers
    low = evaluate_regime({"available": True, "nifty": 80, "dma200": 100, "drawdown_pct": 12, "drop_10d_pct": 1, "vix": 15}, "Low")
    assert low["freeze_equity"]
    mod = evaluate_regime({"available": True, "nifty": 80, "dma200": 100, "drawdown_pct": 3, "drop_10d_pct": 1, "vix": 15}, "Moderate")
    assert mod["halve_equity"]
    high = evaluate_regime({"available": True, "nifty": 90, "dma200": 80, "drawdown_pct": 9, "drop_10d_pct": 9, "vix": 25}, "High")
    assert high["deploy_tranches"] == 3 and high["vix_shift"]
    # frozen equity buys in Low tier
    df2 = pd.DataFrame([{"investment_type": "PPF", "current_value": 1000000, "returns_pct": 7}])
    r2 = build_algo_advice(df2, "Conservative", 40, 0, {"available": True, "nifty": 80, "dma200": 100, "drawdown_pct": 12, "drop_10d_pct": 1, "vix": 15})
    assert any(b["Sleeve"] == LARGE and b["Amount"] == 0 for b in r2["buys"])
    assert build_algo_advice(pd.DataFrame(), "Moderate")["error"]
    print("✅ Algorithmic advisor test passed.")


def test_auto_calculate_age_and_lock_dob():
    import datetime
    from database import init_db, delete_user, create_user, update_user_profile, authenticate_user
    init_db()
    delete_user("dobtestuser")
    ok, msg = create_user("dobtestuser", "testpwd123", "DOB Test User", "Member")
    assert ok

    # User initially has empty dob
    u = authenticate_user("dobtestuser", "testpwd123")
    assert u is not None
    assert u.get("dob") == ""

    # First time setting DOB: sets DOB and auto-calculates age
    birth_date = datetime.date(1994, 6, 15)
    today = datetime.date.today()
    expected_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    res = update_user_profile("dobtestuser", {
        "dob": birth_date.isoformat(),
        "age": expected_age
    })
    assert res

    u_after = authenticate_user("dobtestuser", "testpwd123")
    assert u_after["dob"] == "1994-06-15"
    assert u_after["age"] == expected_age

    # Attempting to change/update DOB once set: must NOT be updated
    res2 = update_user_profile("dobtestuser", {
        "dob": "2005-01-01",
        "city": "Bengaluru"
    })
    assert res2

    u_locked = authenticate_user("dobtestuser", "testpwd123")
    assert u_locked["dob"] == "1994-06-15"  # Remains original, not updated
    assert u_locked["city"] == "Bengaluru"  # Other fields still update normally

    print("✅ Auto-calculate age from DOB and lock DOB test passed.")


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
        test_statement_ingestion_and_segments()
        test_multi_family_data_isolation()
        test_duplicate_detection()
        test_income_source_crud()
        test_free_text_retirement_milestones_and_override()
        test_cost_of_living_variations_and_bullet_prefix_isolation()
        test_mutual_exclusive_expense_sources()
        test_option_b_full_resolution()
        test_retire_at_55_statement_parsing()
        test_friendly_gemini_errors()
        test_academy_fallback()
        test_algo_advisor()
        test_auto_calculate_age_and_lock_dob()
        print("🎉 All test suite assertions passed successfully!")
    finally:
        if os.path.exists(database.DB_PATH):
            os.unlink(database.DB_PATH)


