import sys
import os
import io
import datetime

# Ensure repository root is on sys.path for Streamlit Cloud deployment
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as io_plotly
import streamlit as st

from categorizer import (
    auto_categorize_description,
    apply_ml_auto_categorization,
    MLCategorizer,
    generate_ai_spend_rationalization
)
from investment_planner import (
    calculate_investment_plan,
    generate_ai_wealth_advice,
    generate_ai_portfolio_suggestions,
    analyze_portfolio_segments,
    calculate_asset_allocation_drift,
    generate_ai_segment_advisory
)
import statement_parser
import live_market_tracker
from config import (
    EXPENSE_CATEGORIES,
    get_indian_fy,
    get_indian_quarter,
    get_indian_half_year,
    format_inr,
    format_inr_short,
    format_month_label
)
from database import (
    init_db,
    insert_expenses,
    get_expenses_df,
    get_all_financial_years,
    get_category_breakdown,
    get_monthly_trend_df,
    get_quarterly_trend_df,
    get_surge_categories,
    get_period_surge_analytics,
    set_category_budget,
    batch_set_category_budgets,
    get_suggested_budgets,
    get_budget_status,
    delete_expense,
    delete_month_expenses,
    update_expenses_df,
    delete_multiple_expenses,
    seed_sample_data_if_empty,
    get_cumulative_metrics,
    authenticate_user,
    create_user,
    update_user_password,
    update_user_role,
    get_all_users,
    delete_user,
    get_db_type,
    insert_investment,
    get_user_investments_df,
    update_investments_df,
    delete_investment,
    delete_all_investments,
    batch_insert_investments,
    create_family,
    get_family_by_code,
    join_family_by_code,
    get_all_families
)
from cpi_data import (
    get_cpi_df,
    calculate_cpi_inflation,
    calculate_personal_inflation_rate,
    CPI_CATEGORY_INFLATION
)
from categorizer import auto_categorize_description, auto_categorize_records

# Page Config
st.set_page_config(
    page_title="Indian FY Expense Tracker & Inflation Analyzer",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="auto"
)

# Mobile viewport meta tag
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
""", unsafe_allow_html=True)

# Custom Styling (Desktop + Mobile Responsive)
st.markdown("""
<style>
    /* Dark Theme Accent Styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-label {
        font-size: 0.88rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .surge-badge {
        background-color: #9f1239;
        color: #fecdd3;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .normal-badge {
        background-color: #065f46;
        color: #a7f3d0;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* Mobile responsive styles */
    @media screen and (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        .main-header { font-size: 1.5rem !important; }
        .sub-header { font-size: 0.9rem !important; }
        .metric-card { padding: 12px 10px !important; margin-bottom: 8px !important; }
        .metric-value { font-size: 1.4rem !important; }
        .metric-label { font-size: 0.78rem !important; }
        [data-testid="stTabs"] [role="tablist"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: thin;
            flex-wrap: nowrap !important;
            gap: 2px !important;
        }
        [data-testid="stTabs"] [role="tab"] {
            font-size: 0.75rem !important;
            padding: 8px 10px !important;
            white-space: nowrap !important;
            min-width: fit-content !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database & Seed Data
init_db()
seed_sample_data_if_empty()

# ----------------------------------------------------
# USER AUTHENTICATION SCREEN
# ----------------------------------------------------
if "user" not in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="max-width: 540px; margin: 20px auto; padding: 24px; border-radius: 12px; background-color: #1e293b; border: 1px solid #334155; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">
        <h2 style="color: #38bdf8; margin-bottom: 4px;">🔐 In-House Expense Tracker</h2>
        <p style="color: #94a3b8; font-size: 0.95rem;">Multi-Family Expense Tracking, Wealth Planning & AI Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2.4, 1])
    with col_l2:
        auth_tab1, auth_tab2, auth_tab3 = st.tabs([
            "🔑 Sign In",
            "🏠 Register New Family",
            "👨‍👩‍👧 Join Existing Family"
        ])
        
        with auth_tab1:
            with st.form("login_form"):
                login_user = st.text_input("Username", placeholder="e.g. admin", key="login_username").strip()
                login_pwd = st.text_input("Password", type="password", placeholder="••••••••", key="login_pwd")
                submit_login = st.form_submit_button("🚀 Sign In to Expense Tracker", type="primary", use_container_width=True)
                
                if submit_login:
                    user_record = authenticate_user(login_user, login_pwd)
                    if user_record:
                        st.session_state["user"] = user_record
                        st.session_state["view_mode"] = "Family"
                        st.success(f"Welcome back, {user_record['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with auth_tab2:
            st.caption("Create a new isolated Family Household & become its Family Admin.")
            with st.form("create_family_form"):
                new_fam_name = st.text_input("Family / Household Name", placeholder="e.g. Pulikken Household", key="reg_fam_name")
                fam_admin_user = st.text_input("Admin Username", placeholder="e.g. rovin_admin", key="reg_fam_user")
                fam_admin_fullname = st.text_input("Your Full Name", placeholder="e.g. Rovin Pulikken", key="reg_fam_name_full")
                fam_admin_pwd = st.text_input("Password", type="password", placeholder="••••••••", key="reg_fam_pwd")
                submit_fam = st.form_submit_button("🏠 Register Family & Become Admin", type="primary", use_container_width=True)
                
                if submit_fam:
                    ok, msg, u_record = create_family(new_fam_name, fam_admin_user, fam_admin_pwd, fam_admin_fullname)
                    if ok and u_record:
                        st.session_state["user"] = u_record
                        st.session_state["view_mode"] = "Family"
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with auth_tab3:
            st.caption("Join an existing Family using your Family Admin's unique Join Code.")
            with st.form("join_family_form"):
                join_code_in = st.text_input("Family Join Code", placeholder="e.g. FAM-PULIKKEN-92A1", key="join_fam_code").strip()
                join_user_in = st.text_input("Desired Username", placeholder="e.g. priya", key="join_user_name").strip()
                join_fullname_in = st.text_input("Your Full Name", placeholder="e.g. Priya Pulikken", key="join_full_name")
                join_pwd_in = st.text_input("Password", type="password", placeholder="••••••••", key="join_user_pwd")
                submit_join = st.form_submit_button("👨‍👩‍👧 Join Family Workspace", type="primary", use_container_width=True)
                
                if submit_join:
                    ok, msg, u_record = join_family_by_code(join_code_in, join_user_in, join_pwd_in, join_fullname_in, role="Member")
                    if ok and u_record:
                        st.session_state["user"] = u_record
                        st.session_state["view_mode"] = "Family"
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

else:
    # ----------------------------------------------------
    # LOGGED IN USER & SIDEBAR SETUP
    # ----------------------------------------------------
    current_user = st.session_state["user"]
    user_family_id = current_user.get("family_id", 1)
    user_family_name = current_user.get("family_name", "Primary Household")
    user_family_code = current_user.get("family_code", "PRIMARY-1001")

    st.sidebar.image("https://img.icons8.com/isometric/100/rupee.png", width=64)
    st.sidebar.title("📌 Navigation & Settings")

    is_super_admin = (current_user["username"] == "admin" or current_user.get("role") == "Super Admin")

    role_color = "#e11d48" if is_super_admin else ("#38bdf8" if current_user["role"] == "Admin" else "#34d399")
    role_label = "Super Admin 👑" if is_super_admin else current_user["role"]

    st.sidebar.markdown(f"""
    <div style="background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid {role_color}; margin-bottom: 12px;">
        <div style="font-weight: 700; color: #38bdf8; font-size: 0.85rem; text-transform: uppercase;">🏠 {user_family_name}</div>
        <div style="font-weight: 600; color: #f8fafc; font-size: 0.95rem;">👤 {current_user['full_name']}</div>
        <div style="font-size: 0.8rem; color: #94a3b8;">@{current_user['username']} • <span style="color: {role_color}; font-weight: 600;">{role_label}</span></div>
        <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Code: <code>{user_family_code}</code></div>
    </div>
    """, unsafe_allow_html=True)

    if is_super_admin:
        all_fams = get_all_families()
        fam_options = ["🌐 Entire Database (All Families)"] + [f"{f['family_name']} ({f['family_code']})" for f in all_fams]
        selected_fam_scope = st.sidebar.selectbox(
            "🏛️ Family Scope (Super Admin)",
            fam_options,
            index=0,
            help="Super Admin has access to view/export the entire database across all families, or filter by a specific family."
        )
        if "Entire Database" in selected_fam_scope:
            user_family_id = None
        else:
            selected_code = selected_fam_scope.split("(")[-1].replace(")", "").strip()
            matched_fam = next((f for f in all_fams if f["family_code"] == selected_code), None)
            user_family_id = matched_fam["id"] if matched_fam else None
    else:
        user_family_id = current_user.get("family_id", 1)

    view_mode_choice = st.sidebar.radio(
        "👁️ Expense View Mode",
        ["🏠 Family / Household View", "🔒 My Private View", "🌐 All Accessible"],
        index=0,
        help="Family Mode shows shared household expenses; Private Mode shows only your items."
    )

    if "Family" in view_mode_choice:
        view_mode = "Family"
    elif "Private" in view_mode_choice:
        view_mode = "Private"
    else:
        view_mode = "All"

    all_fys = get_all_financial_years(username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
    selected_fy = st.sidebar.selectbox("📅 Select Financial Year", ["All FYs"] + all_fys, index=1 if len(all_fys) > 1 else 0)

    # Sidebar Monthly Dropdown List Filter
    df_raw_for_months = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
    avail_months = sorted(df_raw_for_months["Month_Year"].unique().tolist(), reverse=True) if not df_raw_for_months.empty and "Month_Year" in df_raw_for_months.columns else []
    
    selected_month_filter = st.sidebar.selectbox(
        "🗓️ Select Month Filter",
        options=["All Months"] + avail_months,
        format_func=format_month_label,
        help="Filter dashboard metrics, trajectory charts, and itemized lists by a specific month."
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"💾 Storage Engine: **{get_db_type()}**")

    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ----------------------------------------------------
    # HEADER & TOP KPI ROW
    # ----------------------------------------------------
    st.markdown("<div class='main-header'>Indian FY Expense Tracker & Inflation Analyzer</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Manage household and private expenses, track CPI inflation, analyze Indian Financial Year trends, and set category budgets.</div>", unsafe_allow_html=True)

    df_fy = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
    if selected_month_filter != "All Months" and not df_fy.empty and "Month_Year" in df_fy.columns:
        df_fy = df_fy[df_fy["Month_Year"] == selected_month_filter]
    total_spent = df_fy["amount"].sum() if not df_fy.empty else 0.0
    total_txns = len(df_fy) if not df_fy.empty else 0
    num_months = df_fy["Month_Year"].nunique() if not df_fy.empty and "Month_Year" in df_fy.columns else 1
    num_months = max(1, num_months)
    avg_monthly_spent = total_spent / num_months if not df_fy.empty else 0.0

    cat_breakdown = get_category_breakdown(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
    top_category = cat_breakdown.iloc[0]["category"] if not cat_breakdown.empty else "N/A"
    top_cat_amount = cat_breakdown.iloc[0]["Total_Amount"] if not cat_breakdown.empty else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Expense ({selected_fy})</div>
            <div class="metric-value">{format_inr_short(total_spent)}</div>
            <div style="color: #64748b; font-size: 0.8rem;">{format_inr(total_spent)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Monthly Spend</div>
            <div class="metric-value" style="color: #38bdf8;">{format_inr_short(avg_monthly_spent)}</div>
            <div style="color: #64748b; font-size: 0.8rem;">{format_inr(avg_monthly_spent)} / month</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Logged Entries</div>
            <div class="metric-value">{total_txns}</div>
            <div style="color: #64748b; font-size: 0.8rem;">Transactions recorded</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Expense Category</div>
            <div class="metric-value" style="font-size: 1.3rem; color: #f43f5e;">{top_category}</div>
            <div style="color: #64748b; font-size: 0.8rem;">{format_inr_short(top_cat_amount)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        cpi_rate = 5.6 # Avg Indian CPI
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Indian CPI Benchmark</div>
            <div class="metric-value" style="color: #fbbf24;">{cpi_rate}%</div>
            <div style="color: #64748b; font-size: 0.8rem;">Avg Annual Inflation (RBI)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Helper for Excel Template Download
    def generate_excel_template() -> bytes:
        df_template = pd.DataFrame([
            {"Date (YYYY-MM-DD)": "2025-05-01", "Category": "Groceries & Provisions", "Description": "Weekly D-Mart shopping", "Amount (INR)": 4500.00, "Visibility": "Family"},
            {"Date (YYYY-MM-DD)": "2025-05-03", "Category": "Utilities (Electricity/Water/Gas)", "Description": "LPG Gas Cylinder", "Amount (INR)": 950.00, "Visibility": "Family"},
            {"Date (YYYY-MM-DD)": "2025-05-10", "Category": "Shopping & Apparel", "Description": "Personal clothing", "Amount (INR)": 1800.00, "Visibility": "Private"}
        ])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_template.to_excel(writer, index=False, sheet_name='Expense_Template')
        return output.getvalue()

    # Helper for Excel/CSV Import
    def import_from_excel_or_csv(file, username: str = "admin", visibility: str = "Family", family_id: int = 1) -> tuple:
        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            col_map = {}
            for col in df.columns:
                c_lower = str(col).lower().strip()
                if "date" in c_lower or "dt" in c_lower:
                    col_map[col] = "date"
                elif "cat" in c_lower or "group" in c_lower or "head" in c_lower:
                    col_map[col] = "category"
                elif "desc" in c_lower or "note" in c_lower or "item" in c_lower or "particular" in c_lower or "remark" in c_lower:
                    col_map[col] = "description"
                elif "amt" in c_lower or "amount" in c_lower or "price" in c_lower or "inr" in c_lower or "rupee" in c_lower or "cost" in c_lower or "val" in c_lower or "exp" in c_lower:
                    col_map[col] = "amount"
                elif "vis" in c_lower or "share" in c_lower or "mode" in c_lower:
                    col_map[col] = "visibility"
                    
            df.rename(columns=col_map, inplace=True)
            
            for col_req in ["date", "category", "description", "amount"]:
                if col_req not in df.columns:
                    df[col_req] = "" if col_req != "amount" else 0.0
                    
            if "visibility" not in df.columns:
                df["visibility"] = visibility
                
            df["amount"] = pd.to_numeric(
                df["amount"].astype(str).str.replace("₹", "").str.replace("Rs", "").str.replace(",", "").str.strip(),
                errors="coerce"
            ).fillna(0.0)
            
            df = df[df["amount"] > 0]
            if df.empty:
                return 0, f"No valid rows with expense amounts > 0 were found in {file.name}."
                
            records = df[["date", "category", "description", "amount", "visibility"]].to_dict("records")
            records = auto_categorize_records(records)
            count = insert_expenses(records, source=f"Import ({file.name})", username=username, visibility=visibility, family_id=family_id)
            return count, f"Successfully imported {count} expense rows from {file.name}!"
        except Exception as e:
            return 0, f"Error processing file: {e}"

    # ----------------------------------------------------
    # MAIN NAVIGATION TABS
    # ----------------------------------------------------
    tab_labels = [
        "📊 Manual Entry & Excel Grid",
        "📑 Itemized Period Explorer",
        "✏️ Edit & Delete Expenses",
        "📊 Indian FY Trends",
        "📈 Inflation & CPI Analytics",
        "🚨 Expense Surge Detector",
        "🎯 Budgeting & Investments",
        "📝 Database Log & Export"
    ]

    if current_user["role"] == "Admin":
        tab_labels.append("👑 Admin & User Management")

    tabs_list = st.tabs(tab_labels)
    tab_manual = tabs_list[0]
    tab_itemized = tabs_list[1]
    tab_edit_delete = tabs_list[2]
    tab_trends = tabs_list[3]
    tab_cpi = tabs_list[4]
    tab_surge = tabs_list[5]
    tab_budget = tabs_list[6]
    tab_data = tabs_list[7]
    tab_admin = tabs_list[8] if current_user["role"] == "Admin" else None

    # ----------------------------------------------------
    # TAB 1: MANUAL ENTRY & EXCEL GRID
    # ----------------------------------------------------
    with tab_manual:
        st.subheader("📝 Manual Data Entry & Excel Spreadsheet Tools")
        st.write("You can enter expenses directly using an Excel-like interactive table with **Auto-Categorization**, import existing Excel/CSV sheets, or add quick single entries.")
        
        manual_sub_tab1, manual_sub_tab2, manual_sub_tab3 = st.tabs([
            "📊 Excel-like Interactive Grid",
            "📂 Excel / CSV File Import",
            "⚡ Quick Single Entry Form"
        ])
        
        with manual_sub_tab1:
            st.markdown("#### Interactive Spreadsheet Grid (Auto-Categorizing)")
            st.caption("Type descriptions (e.g., 'Swiggy', 'D-Mart', 'Petrol', 'Electricity bill') and click **✨ Auto-Categorize & Save** below!")
            
            c_v1, c_v2 = st.columns([3, 1])
            with c_v2:
                entry_vis = st.selectbox("Default Sharing / Visibility", ["Family", "Private"], help="Family entries are shared with household; Private entries are visible only to you.", key="grid_vis")
                
            today_date = datetime.date.today()
            initial_grid = pd.DataFrame([
                {"date": today_date, "category": "Groceries & Provisions", "description": "D-Mart monthly ration", "amount": 3500.0, "visibility": entry_vis},
                {"date": today_date, "category": "Dining & Swiggy/Zomato", "description": "Swiggy weekend dinner", "amount": 650.0, "visibility": entry_vis},
                {"date": today_date, "category": "Transportation & Fuel", "description": "Petrol filling HPCL", "amount": 2000.0, "visibility": entry_vis}
            ])
            
            grid_edited = st.data_editor(
                initial_grid,
                num_rows="dynamic",
                column_config={
                    "date": st.column_config.DateColumn("Date", required=True),
                    "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                    "description": st.column_config.TextColumn("Description", help="Type description e.g., 'Amul milk', 'Apollo medicine', 'Swiggy'"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
                    "visibility": st.column_config.SelectboxColumn("Visibility", options=["Family", "Private"], required=True)
                },
                use_container_width=True,
                key="excel_grid_manual"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✨ Auto-Categorize & Save Grid to Database", type="primary", use_container_width=True):
                    valid_rows = [r for r in grid_edited.to_dict("records") if float(r.get("amount", 0.0)) > 0]
                    if valid_rows:
                        categorized_rows = auto_categorize_records(valid_rows)
                        cnt = insert_expenses(categorized_rows, source="Excel Grid (Auto-Categorized)", username=current_user["username"], visibility=entry_vis, family_id=user_family_id)
                        st.success(f"🎉 Successfully auto-categorized and saved {cnt} expense entries!")
                        st.rerun()
                    else:
                        st.warning("Please enter at least one row with an amount greater than 0.")
                        
            with col_btn2:
                if st.button("💾 Save As Is (No Auto-Categorize)", use_container_width=True):
                    valid_rows = [r for r in grid_edited.to_dict("records") if float(r.get("amount", 0.0)) > 0]
                    if valid_rows:
                        cnt = insert_expenses(valid_rows, source="Excel Grid Editor", username=current_user["username"], visibility=entry_vis, family_id=user_family_id)
                        st.success(f"Saved {cnt} entries!")
                        st.rerun()
                    else:
                        st.warning("Please enter at least one row with an amount > 0.")
                    
        with manual_sub_tab2:
            col_ex_left, col_ex_right = st.columns(2)
            
            with col_ex_left:
                st.markdown("#### Download Standard Excel Template")
                st.write("Download this pre-formatted `.xlsx` template to log expenses offline in Excel or Google Sheets.")
                
                excel_bytes = generate_excel_template()
                st.download_button(
                    label="📥 Download Excel Template (.xlsx)",
                    data=excel_bytes,
                    file_name="Expense_Tracker_Template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            with col_ex_right:
                st.markdown("#### Upload Completed Excel / CSV File")
                st.write("Upload your filled Excel (`.xlsx`, `.xls`) or `.csv` spreadsheet. Categories will be auto-classified if missing!")
                
                upload_vis = st.radio("Import Expense Visibility", ["Family", "Private"], horizontal=True, key="upload_vis")
                uploaded_excel = st.file_uploader("Choose Excel, CSV, or PDF File", type=["xlsx", "xls", "csv", "pdf"], key="excel_uploader")
                if uploaded_excel:
                    if st.button("🚀 Import & Auto-Categorize File", type="primary", use_container_width=True):
                        cnt, msg = import_from_excel_or_csv(uploaded_excel, username=current_user["username"], visibility=upload_vis, family_id=user_family_id)
                        if cnt > 0:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
        with manual_sub_tab3:
            st.markdown("#### Add Single Expense Entry (with Smart Auto-Categorization)")
            m1, m2, m3, m4, m5 = st.columns([1.5, 2, 2, 1.5, 1.5])
            with m1:
                q_date = st.date_input("Date", datetime.date.today(), key="q_date")
            with m2:
                q_desc = st.text_input("Description", placeholder="e.g. Swiggy biryani, Amul milk, D-Mart", key="q_desc")
            with m3:
                predicted_cat = auto_categorize_description(q_desc) if q_desc else EXPENSE_CATEGORIES[0]
                default_idx = EXPENSE_CATEGORIES.index(predicted_cat) if predicted_cat in EXPENSE_CATEGORIES else 0
                q_cat = st.selectbox("Category (Auto-Suggested)", EXPENSE_CATEGORIES, index=default_idx, key="q_cat")
            with m4:
                q_amt = st.number_input("Amount (₹)", min_value=0.0, value=500.0, step=100.0, key="q_amt")
            with m5:
                q_vis = st.selectbox("Sharing", ["Family", "Private"], key="q_vis")
                
            if st.button("➕ Add Single Expense", type="primary", use_container_width=True):
                if q_amt > 0:
                    insert_expenses([{
                        "date": q_date.isoformat(),
                        "category": q_cat,
                        "description": q_desc,
                        "amount": q_amt,
                        "visibility": q_vis
                    }], source="Quick Manual Entry", username=current_user["username"], visibility=q_vis, family_id=user_family_id)
                    st.success(f"Added {format_inr(q_amt)} under '{q_cat}'!")
                    st.rerun()
                else:
                    st.warning("Please enter an amount > 0.")

    # ----------------------------------------------------
    # TAB 2: ITEMIZED PERIOD EXPLORER
    # ----------------------------------------------------
    with tab_itemized:
        st.subheader(f"📑 Itemized Expense Explorer ({selected_fy})")
        st.write("Explore itemized line-by-line expenses with customizable period filters (**Monthly, Quarterly, Half-Yearly, Yearly**) alongside cumulative **QTD, H1, H2, and YTD** totals.")
        
        cum_metrics = get_cumulative_metrics(fy=selected_fy if selected_fy != "All FYs" else None, username=current_user["username"], view_mode=view_mode)
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">QTD Total (Quarter to Date)</div>
                <div class="metric-value" style="color:#38bdf8;">{format_inr_short(cum_metrics['QTD'])}</div>
                <div style="color:#64748b; font-size:0.8rem;">{format_inr(cum_metrics['QTD'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">H1 Total (Apr - Sep)</div>
                <div class="metric-value" style="color:#818cf8;">{format_inr_short(cum_metrics['H1'])}</div>
                <div style="color:#64748b; font-size:0.8rem;">{format_inr(cum_metrics['H1'])}</div>
            </div>
            """, unsafe_allow_html=True)

        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">H2 Total (Oct - Mar)</div>
                <div class="metric-value" style="color:#c084fc;">{format_inr_short(cum_metrics['H2'])}</div>
                <div style="color:#64748b; font-size:0.8rem;">{format_inr(cum_metrics['H2'])}</div>
            </div>
            """, unsafe_allow_html=True)

        with m_col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">YTD / Full FY Total</div>
                <div class="metric-value" style="color:#34d399;">{format_inr_short(cum_metrics['YTD'])}</div>
                <div style="color:#64748b; font-size:0.8rem;">{format_inr(cum_metrics['YTD'])}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        ctrl_col1, ctrl_col2 = st.columns([1, 2])
        with ctrl_col1:
            granularity = st.radio(
                "Select Time Granularity",
                ["Monthly", "Quarterly", "Half-Yearly", "Yearly (Full FY)"],
                horizontal=False
            )
            
        all_df = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
        filtered_df = pd.DataFrame()
        period_title = ""
        
        with ctrl_col2:
            if granularity == "Monthly":
                if not all_df.empty and "Month_Year" in all_df.columns:
                    months_available = sorted(all_df["Month_Year"].unique().tolist(), reverse=True)
                    selected_month = st.selectbox(
                        "Select Month",
                        options=["All Months in FY"] + months_available,
                        format_func=format_month_label
                    )
                    if selected_month != "All Months in FY":
                        filtered_df = all_df[all_df["Month_Year"] == selected_month]
                        period_title = f"Itemized Expenses for {format_month_label(selected_month)}"
                    else:
                        filtered_df = all_df
                        period_title = f"All Itemized Expenses for {selected_fy}"
                else:
                    st.info("No monthly transaction data available.")
                    
            elif granularity == "Quarterly":
                selected_q = st.selectbox("Select Quarter", ["Q1 (Apr - Jun)", "Q2 (Jul - Sep)", "Q3 (Oct - Dec)", "Q4 (Jan - Mar)"])
                q_code = selected_q.split()[0]
                filtered_df = all_df[all_df["quarter"] == q_code] if not all_df.empty else pd.DataFrame()
                period_title = f"Itemized Expenses for {selected_q} ({selected_fy})"
                
            elif granularity == "Half-Yearly":
                selected_h = st.selectbox("Select Half Year", ["H1 (Apr - Sep)", "H2 (Oct - Mar)"])
                h_code = selected_h.split()[0]
                filtered_df = all_df[all_df["half_year"] == h_code] if not all_df.empty and "half_year" in all_df.columns else pd.DataFrame()
                period_title = f"Itemized Expenses for {selected_h} ({selected_fy})"
                
            else: # Yearly
                filtered_df = all_df
                period_title = f"Full Year Itemized Expenses ({selected_fy})"
                
        st.markdown("---")
        st.markdown(f"### {period_title}")
        
        if filtered_df.empty:
            st.warning("No itemized expenses found for the selected period.")
        else:
            period_total_val = filtered_df["amount"].sum()
            st.info(f"💰 Total Itemized Expenses for **{period_title}**: **{format_inr(period_total_val)}** across **{len(filtered_df)}** transactions.")
            
            item_cat_summary = filtered_df.groupby("category")["amount"].agg(
                Itemized_Total="sum",
                Count="count"
            ).reset_index()
            
            item_cat_summary["Share_%"] = (item_cat_summary["Itemized_Total"] / period_total_val) * 100
            item_cat_summary = item_cat_summary.sort_values(by="Itemized_Total", ascending=False)
            
            st.markdown("#### 📊 Itemized Summary by Category")
            st.dataframe(
                item_cat_summary,
                column_config={
                    "category": st.column_config.TextColumn("Category"),
                    "Itemized_Total": st.column_config.NumberColumn("Itemized Total (₹)", format="₹ %.2f"),
                    "Count": st.column_config.NumberColumn("Entries"),
                    "Share_%": st.column_config.NumberColumn("Share of Period Total", format="%.1f %%")
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("#### 📋 Itemized Transactions Ledger")
            st.dataframe(
                filtered_df[["id", "expense_date", "category", "description", "amount", "quarter", "half_year", "visibility", "username", "source_note"]],
                column_config={
                    "id": st.column_config.NumberColumn("ID"),
                    "expense_date": st.column_config.DateColumn("Date"),
                    "category": st.column_config.TextColumn("Category"),
                    "description": st.column_config.TextColumn("Item / Description"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", format="₹ %.2f"),
                    "quarter": st.column_config.TextColumn("Quarter"),
                    "half_year": st.column_config.TextColumn("Half Year"),
                    "visibility": st.column_config.TextColumn("Sharing"),
                    "username": st.column_config.TextColumn("Logged By"),
                    "source_note": st.column_config.TextColumn("Source")
                },
                use_container_width=True,
                hide_index=True
            )

    # ----------------------------------------------------
    # TAB 3: EDIT & DELETE EXPENSES
    # ----------------------------------------------------
    with tab_edit_delete:
        st.subheader(f"✏️ Edit & Delete Expenses ({selected_fy})")
        st.write("Modify existing entries, re-assign categories, edit amounts, or delete records.")
        
        expenses_df_all = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
        
        if expenses_df_all.empty:
            st.warning("No expense records available to edit or delete.")
        else:
            edit_mode_tab1, edit_mode_tab2, edit_mode_tab3, edit_mode_tab4 = st.tabs([
                "📝 Inline Table Editor",
                "🔍 Search & Edit Single Record",
                "🗑️ Delete Single Record",
                "🧹 Clear Entire Month Data"
            ])
            
            with edit_mode_tab1:
                st.markdown("#### Interactive Database Table Editor")
                st.caption("Edit dates, categories, descriptions, or amounts directly in the grid. FY and Quarters recalculate automatically upon saving.")
                
                edited_df_inline = st.data_editor(
                    expenses_df_all[["id", "expense_date", "category", "description", "amount", "visibility", "source_note"]],
                    num_rows="dynamic",
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "expense_date": st.column_config.DateColumn("Date", required=True),
                        "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                        "description": st.column_config.TextColumn("Description"),
                        "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
                        "visibility": st.column_config.SelectboxColumn("Visibility", options=["Family", "Private"], required=True),
                        "source_note": st.column_config.TextColumn("Source", disabled=True)
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="inline_editor_tab3"
                )
                
                if st.button("💾 Save All Edits to Database", type="primary", use_container_width=True):
                    updated_count = update_expenses_df(edited_df_inline)
                    st.success(f"🎉 Successfully updated {updated_count} record(s) in database!")
                    st.rerun()
                    
            with edit_mode_tab2:
                st.markdown("#### Select & Modify Single Record")
                record_ids = expenses_df_all["id"].tolist()
                selected_id = st.selectbox("Select Expense ID to Edit", record_ids, key="single_edit_id")
                
                target_record = expenses_df_all[expenses_df_all["id"] == selected_id].iloc[0]
                
                e_c1, e_c2, e_c3, e_c4, e_c5 = st.columns([1.5, 2, 2, 1.5, 1.5])
                with e_c1:
                    cur_dt = pd.to_datetime(target_record["expense_date"]).date() if not pd.isna(target_record["expense_date"]) else datetime.date.today()
                    new_dt = st.date_input("Date", cur_dt, key="single_new_dt")
                with e_c2:
                    cur_cat = target_record["category"] if target_record["category"] in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
                    new_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(cur_cat), key="single_new_cat")
                with e_c3:
                    new_desc = st.text_input("Description", value=str(target_record["description"]), key="single_new_desc")
                with e_c4:
                    new_amt = st.number_input("Amount (₹)", min_value=0.0, value=float(target_record["amount"]), step=100.0, key="single_new_amt")
                with e_c5:
                    cur_vis = target_record.get("visibility", "Family") if target_record.get("visibility") in ["Family", "Private"] else "Family"
                    new_vis = st.selectbox("Sharing", ["Family", "Private"], index=0 if cur_vis == "Family" else 1, key="single_new_vis")
                    
                if st.button(f"💾 Update Record #{selected_id}", type="primary", use_container_width=True):
                    single_df = pd.DataFrame([{
                        "id": selected_id,
                        "expense_date": new_dt.isoformat(),
                        "category": new_cat,
                        "description": new_desc,
                        "amount": new_amt,
                        "visibility": new_vis
                    }])
                    update_expenses_df(single_df)
                    st.success(f"Updated record #{selected_id}!")
                    st.rerun()
                    
            with edit_mode_tab3:
                st.markdown("#### Delete Single Record by ID")
                del_id_select = st.selectbox("Select Expense ID to Delete", record_ids, key="single_del_id_select")
                del_target = expenses_df_all[expenses_df_all["id"] == del_id_select].iloc[0]
                
                st.info(f"Target Record #{del_id_select}: {del_target['expense_date']} | {del_target['category']} | {del_target['description']} | {format_inr(del_target['amount'])}")
                
                if st.button(f"🗑️ Permanently Delete Record #{del_id_select}", type="primary", use_container_width=True):
                    delete_expense(int(del_id_select))
                    st.success(f"Deleted record #{del_id_select}!")
                    st.rerun()
                    
            with edit_mode_tab4:
                st.markdown("#### Bulk Delete Entire Month Data")
                if "Month_Year" in expenses_df_all.columns:
                    available_m = sorted(expenses_df_all["Month_Year"].unique().tolist(), reverse=True)
                    del_month_target = st.selectbox("Select Month to Wipe", available_m, format_func=format_month_label, key="bulk_del_m")
                    month_records = expenses_df_all[expenses_df_all["Month_Year"] == del_month_target]
                    m_sum = month_records["amount"].sum()
                    
                    st.warning(f"⚠️ Month **{del_month_target}** contains **{len(month_records)}** entries totaling **{format_inr(m_sum)}**.")
                    confirm_chk = st.checkbox(f"I confirm deletion of all entries for {del_month_target}", key="chk_bulk_del")
                    
                    if st.button(f"🔥 Wipe All Data for {del_month_target}", type="primary", disabled=not confirm_chk, use_container_width=True):
                        cnt_del = delete_month_expenses(del_month_target)
                        st.success(f"Deleted {cnt_del} records for {del_month_target}!")
                        st.rerun()

    # ----------------------------------------------------
    # TAB 4: INDIAN FY TRENDS
    # ----------------------------------------------------
    with tab_trends:
        st.subheader(f"📊 Indian Financial Year Trends ({selected_fy})")
        st.write("Visualizes monthly spending trajectories, quarterly spending distributions, and category breakdowns.")
        
        trend_df = get_monthly_trend_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
        
        if trend_df.empty:
            st.warning("No trend data available for the selected Financial Year.")
        else:
            st.markdown("#### Monthly Expense Trajectory (Apr - Mar)")
            fig_month = px.bar(
                trend_df,
                x="YearMonth",
                y="Monthly_Total",
                color="category",
                title=f"Monthly Expenses Breakdown ({selected_fy})",
                labels={"Monthly_Total": "Amount (₹)", "YearMonth": "Month"},
                template="plotly_dark"
            )
            fig_month.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_month, use_container_width=True)
            
            q_trend_df = get_quarterly_trend_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
            if not q_trend_df.empty:
                st.markdown("#### Quarterly Expenditure Distribution (Q1 - Q4)")
                fig_q = px.bar(
                    q_trend_df,
                    x="quarter",
                    y="Quarterly_Total",
                    color="category",
                    barmode="group",
                    title=f"Quarterly Expenses by Category ({selected_fy})",
                    labels={"Quarterly_Total": "Amount (₹)", "quarter": "Quarter"},
                    template="plotly_dark"
                )
                fig_q.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                st.plotly_chart(fig_q, use_container_width=True)

    # ----------------------------------------------------
    # TAB 5: INFLATION & CPI ANALYTICS
    # ----------------------------------------------------
    with tab_cpi:
        st.subheader("📈 Inflation & Purchasing Power Analytics")
        
        sub_tab_cpi, sub_tab_personal = st.tabs(["General CPI Analytics", "Personal Expense Predictor"])
        
        with sub_tab_cpi:
            st.write("Compares your category expense changes against official Reserve Bank of India (RBI) & Ministry of Statistics (MOSPI) CPI inflation benchmarks.")
            
            cpi_df = get_cpi_df()
            col_cpi_calc, col_cpi_chart = st.columns([1, 1])
            
            with col_cpi_calc:
                st.markdown("#### Purchasing Power Erosion Calculator")
                base_yr = st.number_input("Base Year", min_value=2018, max_value=2025, value=2020)
                curr_yr = st.number_input("Comparison Year", min_value=2019, max_value=2026, value=2025)
                sample_amt = st.number_input("Expense Amount in Base Year (₹)", value=10000.0, step=1000.0)
                
                cum_inf = calculate_cpi_inflation(base_yr, curr_yr)
                req_amt = sample_amt * (1 + (cum_inf / 100))
                
                st.info(f"💡 What cost **{format_inr(sample_amt)}** in {base_yr} requires **{format_inr(req_amt)}** in {curr_yr} just to keep pace with Indian CPI inflation (**+{cum_inf}%** total inflation).")

            with col_cpi_chart:
                st.markdown("#### Personal Expense Inflation vs. Indian CPI Curve")
                fig_cpi = px.line(
                    cpi_df,
                    x="Year",
                    y="CPI Inflation (%)",
                    markers=True,
                    title="Indian CPI Annual Inflation Rate (%)",
                    template="plotly_dark",
                    color_discrete_sequence=["#fbbf24"]
                )
                fig_cpi.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                st.plotly_chart(fig_cpi, use_container_width=True)

                st.markdown("#### Category-Specific Benchmark Inflation Rates")
                cat_cpi_list = []
                for cat, details in CPI_CATEGORY_INFLATION.items():
                    cat_cpi_list.append({
                        "Category": cat,
                        "CPI Group": details["cpi_group"],
                        "CPI Weight (%)": details["cpi_weight"],
                        "Avg Category Inflation (%)": details["avg_inflation"]
                    })
                st.dataframe(pd.DataFrame(cat_cpi_list), use_container_width=True, hide_index=True)

        with sub_tab_personal:
            st.markdown("### Predict Your Future Expenses")
            st.write("This tool calculates a **Personalized Inflation Rate** based on your exact historical spending habits. Instead of using the generic national CPI, it heavily weights the inflation of the categories you spend the most on.")
            
            # Fetch historical category breakdown
            hist_breakdown_df = get_category_breakdown(fy=None, username=current_user["username"] if view_mode == "Personal" else None, view_mode=view_mode, family_id=user_family_id)
            personal_rate = calculate_personal_inflation_rate(hist_breakdown_df)
            
            st.info(f"🔥 **Your Personalized Inflation Rate:** {personal_rate}% per year (Based on your historical category weightings)")
            
            col_pred_inputs, col_pred_chart = st.columns([1, 2])
            
            with col_pred_inputs:
                custom_inflation = st.number_input(
                    "Inflation Rate to Use (%)", 
                    value=float(personal_rate), 
                    step=0.5, 
                    format="%.2f", 
                    help="Defaults to your personalized historical inflation rate based on your category spend weightings, but you can override it here."
                )
                pred_base_year = st.number_input("Base Year", min_value=2020, max_value=2030, value=2024, key="pred_base")
                pred_target_year = st.number_input("Target Prediction Year", min_value=2025, max_value=2060, value=2034, key="pred_target")
                
                # Default baseline expense to the most recent FY if available, else 0
                default_expense = 1000000.0 # 10L default
                if not hist_breakdown_df.empty:
                    # Let's get the most recent FY data
                    fys = get_all_financial_years(username=current_user["username"] if view_mode == "Personal" else None, view_mode=view_mode, family_id=user_family_id)
                    if fys:
                        latest_fy = fys[0]
                        latest_fy_df = get_category_breakdown(fy=latest_fy, username=current_user["username"] if view_mode == "Personal" else None, view_mode=view_mode, family_id=user_family_id)
                        if not latest_fy_df.empty and 'Total_Amount' in latest_fy_df.columns:
                            default_expense = float(latest_fy_df['Total_Amount'].sum())
                
                baseline_expense = st.number_input("Base Year Annual Expense (₹)", value=default_expense, step=50000.0)
                
            with col_pred_chart:
                if pred_target_year <= pred_base_year:
                    st.warning("Target year must be greater than base year.")
                else:
                    # Generate projection data
                    proj_years = list(range(pred_base_year, pred_target_year + 1))
                    proj_expenses = [baseline_expense * ((1 + (custom_inflation / 100.0)) ** (y - pred_base_year)) for y in proj_years]
                    
                    proj_df = pd.DataFrame({
                        "Year": proj_years,
                        "Projected Annual Expense (₹)": proj_expenses
                    })
                    
                    fig_proj = px.bar(
                        proj_df, 
                        x="Year", 
                        y="Projected Annual Expense (₹)",
                        title=f"Expense Projection at {custom_inflation}% Inflation",
                        template="plotly_dark",
                        color_discrete_sequence=["#ef4444"]
                    )
                    fig_proj.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                    st.plotly_chart(fig_proj, use_container_width=True)
                    
                    final_amt = proj_expenses[-1]
                    st.success(f"By {pred_target_year}, you will need **{format_inr(final_amt)}** annually to maintain your current lifestyle.")

    # ----------------------------------------------------
    # TAB 6: EXPENSE SURGE DETECTOR & AI SAVINGS ADVISOR
    # ----------------------------------------------------
    with tab_surge:
        st.subheader("🚨 Expense Surge & Anomaly Detector")
        st.caption("Select a Month, Quarter, Half-Year, or Financial Year to pinpoint categories spiking above baseline averages and generate AI cost-savings advice.")

        s_col1, s_col2 = st.columns([1, 1])
        with s_col1:
            timeframe_type = st.selectbox(
                "📅 Select Timeframe Granularity",
                options=["Month-wise", "Quarter-wise", "Half Year-wise", "Financial Year"],
                key="surge_tf_type"
            )

        dummy_df, available_periods = get_period_surge_analytics(
            timeframe_type=timeframe_type,
            selected_period=None,
            fy=selected_fy,
            username=current_user["username"],
            view_mode=view_mode,
            family_id=user_family_id
        )

        with s_col2:
            if available_periods:
                fmt_fn = format_month_label if timeframe_type == "Month-wise" else (lambda x: str(x))
                selected_period = st.selectbox(
                    "🎯 Select Target Period",
                    options=available_periods,
                    format_func=fmt_fn,
                    key="surge_target_period"
                )
            else:
                selected_period = None
                st.info("No records available for the selected timeframe.")

        if selected_period:
            period_surge_df, _ = get_period_surge_analytics(
                timeframe_type=timeframe_type,
                selected_period=selected_period,
                fy=selected_fy,
                username=current_user["username"],
                view_mode=view_mode,
                family_id=user_family_id
            )

            if not period_surge_df.empty:
                # Key Metrics Cards
                active_spends = period_surge_df[period_surge_df["Period_Spend"] > 0]
                anomalies_df = period_surge_df[period_surge_df["Is_Anomaly"] == True]
                top_surging_cat = period_surge_df.iloc[0]["category"] if not period_surge_df.empty else "N/A"
                top_surge_pct = period_surge_df.iloc[0]["Surge_%"] if not period_surge_df.empty else 0.0
                total_excess = period_surge_df["Surge_Amount"].apply(lambda x: max(0.0, x)).sum()

                m_c1, m_c2, m_c3 = st.columns(3)
                with m_c1:
                    st.metric("🔥 Top Surging Category", top_surging_cat, f"+{top_surge_pct:.1f}%")
                with m_c2:
                    st.metric("💸 Total Excess Spend Over Baseline", format_inr(total_excess))
                with m_c3:
                    st.metric("⚠️ Detected Anomaly Spikes", f"{len(anomalies_df)} Categories")

                st.markdown("<br>", unsafe_allow_html=True)

                # Grouped Bar Chart: Selected Period Spend vs Baseline Average
                st.markdown(f"#### 📊 Category Spend vs Baseline Average ({selected_period})")
                chart_df = period_surge_df[period_surge_df["Period_Spend"] > 0].copy()
                if not chart_df.empty:
                    fig_surge = px.bar(
                        chart_df,
                        x="category",
                        y=["Period_Spend", "Baseline_Avg"],
                        barmode="group",
                        labels={"value": "Amount (₹)", "category": "Category", "variable": "Metric"},
                        color_discrete_map={"Period_Spend": "#ef4444", "Baseline_Avg": "#3b82f6"},
                        height=400
                    )
                    fig_surge.update_layout(
                        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=30, b=20)
                    )
                    st.plotly_chart(fig_surge, use_container_width=True)

                # Detailed Table
                st.markdown(f"#### 📝 Surge & Anomaly Analysis Table ({selected_period})")
                st.dataframe(
                    period_surge_df[["category", "Period_Spend", "Baseline_Avg", "Surge_Amount", "Surge_%", "Is_Anomaly"]],
                    column_config={
                        "category": st.column_config.TextColumn("Category"),
                        "Period_Spend": st.column_config.NumberColumn(f"Spend in {selected_period} (₹)", format="₹ %.2f"),
                        "Baseline_Avg": st.column_config.NumberColumn("Historical Baseline Avg (₹)", format="₹ %.2f"),
                        "Surge_Amount": st.column_config.NumberColumn("Excess / Surge (₹)", format="₹ %.2f"),
                        "Surge_%": st.column_config.NumberColumn("Spike %", format="%.1f %%"),
                        "Is_Anomaly": st.column_config.CheckboxColumn("Anomaly Tag")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("<hr>", unsafe_allow_html=True)

                # AI Spend Rationalization & Savings Advisor Section
                st.markdown(f"### 🤖 Gemini AI & ML Spend Rationalization Advisor ({selected_period})")
                st.caption("Generate actionable cost reduction strategies, root cause insights, and target savings tailored for your household.")

                if st.button("💡 Generate AI Cost Savings & Rationalization Strategy", type="primary", use_container_width=True):
                    with st.spinner("🤖 Analyzing spending patterns with Machine Learning & Gemini AI..."):
                        ai_advice = generate_ai_spend_rationalization(period_surge_df, timeframe_label=f"{timeframe_type} ({selected_period})")

                    st.success("🎉 AI Spend Rationalization Report Generated!")
                    st.info(ai_advice.get("summary", ""))

                    st.markdown(f"#### 💰 Potential Target Savings: **{ai_advice.get('total_potential_savings', '₹ 0')}**")

                    recs = ai_advice.get("recommendations", [])
                    if recs:
                        for idx, rec in enumerate(recs, 1):
                            with st.expander(f"💡 #{idx} {rec.get('category', 'Category')} — Estimated Savings: {rec.get('est_savings', '₹ 0')}", expanded=True):
                                st.markdown(f"**Issue Identified**: {rec.get('issue', '')}")
                                st.markdown(f"**Actionable Advice**: {rec.get('suggestion', '')}")
            else:
                st.info("No transaction data found for this period.")
        else:
            st.info("No period available to display surge analytics.")

    # ----------------------------------------------------
    # TAB 7: BUDGETING & INVESTMENTS
    # ----------------------------------------------------
    with tab_budget:
        st.subheader(f"🎯 Budgeting, Investments & Active Portfolio ({selected_fy})")
        
        subtab_budget, subtab_invest, subtab_holdings = st.tabs([
            "🎯 Category Budget Planner & Performance",
            "📈 Investment & Wealth Portfolio Planner",
            "💼 Active Investment Portfolio & Holdings Tracker"
        ])

        target_fy_clean = selected_fy if selected_fy != "All FYs" else (all_fys[0] if all_fys else "FY 2024-25")

        with subtab_budget:
            st.caption("Set category budget caps, auto-calculate target allocations based on historical monthly spending averages, and fine-tune limits using interactive + / - controls.")

            # ------------------------------------------------
            # SECTION 1: SMART SUGGESTED BUDGET ALLOCATOR
            # ------------------------------------------------
            st.markdown("""
            <div style="background-color: #1e293b; padding: 14px 18px; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 15px;">
                <div style="font-weight: 600; color: #10b981; font-size: 0.95rem;">💡 Smart Suggested Budget Calculator</div>
                <div style="color: #94a3b8; font-size: 0.85rem;">Specify your overall target household monthly spend, or fill limits with your past monthly spending averages.</div>
            </div>
            """, unsafe_allow_html=True)

            suggested_base_df = get_suggested_budgets(fy=target_fy_clean, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
            total_hist_avg_monthly = float(suggested_base_df["hist_monthly_avg"].sum())

            t_col1, t_col2, t_col3 = st.columns([2, 1.2, 1.2])
            with t_col1:
                target_monthly_input = st.number_input(
                    "💰 Target Total Household Monthly Spend (₹)",
                    min_value=1000.0,
                    value=max(50000.0, float(round(total_hist_avg_monthly, -3))) if total_hist_avg_monthly > 0 else 75000.0,
                    step=5000.0,
                    help="Set your total desired monthly expenditure ceiling across all categories."
                )

            with t_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_apply_hist = st.button(
                    "⚡ Fill Historical Averages",
                    type="secondary",
                    use_container_width=True,
                    help="Populate suggested budgets matching exact past monthly spending averages."
                )

            with t_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_apply_prop = st.button(
                    "🎯 Auto-Allocate Target Proportionally",
                    type="primary",
                    use_container_width=True,
                    help="Distribute your Target Total Spend across categories proportionally based on past spending ratios."
                )

            # Handle Preset Actions in session state
            if "budget_dict" not in st.session_state:
                st.session_state["budget_dict"] = {}
                for idx, r in suggested_base_df.iterrows():
                    c = r["category"]
                    m = float(r["monthly_limit"]) if float(r["monthly_limit"]) > 0 else float(r["suggested_monthly"])
                    st.session_state["budget_dict"][c] = m

            if btn_apply_hist:
                for idx, r in suggested_base_df.iterrows():
                    c = r["category"]
                    st.session_state["budget_dict"][c] = round(float(r["hist_monthly_avg"]), 2)
                st.success("⚡ Filled all category limits with past monthly averages!")
                st.rerun()

            if btn_apply_prop:
                prop_df = get_suggested_budgets(fy=target_fy_clean, username=current_user["username"], view_mode=view_mode, target_total_monthly=target_monthly_input, family_id=user_family_id)
                for idx, r in prop_df.iterrows():
                    c = r["category"]
                    st.session_state["budget_dict"][c] = round(float(r["suggested_monthly"]), 2)
                st.success(f"🎯 Proportions calculated and allocated matching ₹ {format_inr(target_monthly_input)} target!")
                st.rerun()

            # ------------------------------------------------
            # SECTION 2: INTERACTIVE CATEGORY BUDGET ADJUSTER (+/-)
            # ------------------------------------------------
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### ⚙️ Category Budget Planner & Interactive Adjuster (+ / -)")
            st.caption("Use the quick `+` and `-` modifier buttons to fine-tune each category limit up or down.")

            hist_avg_map = dict(zip(suggested_base_df["category"], suggested_base_df["hist_monthly_avg"]))

            for cat in EXPENSE_CATEGORIES:
                current_val = float(st.session_state["budget_dict"].get(cat, 10000.0))
                h_avg = float(hist_avg_map.get(cat, 0.0))

                cat_col1, cat_col2, cat_col3, cat_col4, cat_col5 = st.columns([2.5, 1.8, 2.5, 1.8, 1.8])

                with cat_col1:
                    st.markdown(f"**{cat}**")
                    st.caption(f"Hist Avg: {format_inr(h_avg)} / mo")

                with cat_col2:
                    b_minus1k = st.button("➖ ₹1k", key=f"sub_1k_{cat}", help=f"Decrease {cat} budget by ₹1,000")
                    b_minus5p = st.button("➖ 5%", key=f"sub_5p_{cat}", help=f"Decrease {cat} budget by 5%")
                    if b_minus1k:
                        st.session_state["budget_dict"][cat] = max(0.0, round(current_val - 1000.0, 2))
                        st.rerun()
                    if b_minus5p:
                        st.session_state["budget_dict"][cat] = max(0.0, round(current_val * 0.95, 2))
                        st.rerun()

                with cat_col3:
                    new_val = st.number_input(
                        f"Monthly Limit (₹)",
                        min_value=0.0,
                        value=float(st.session_state["budget_dict"].get(cat, 10000.0)),
                        step=500.0,
                        key=f"input_m_{cat}",
                        label_visibility="collapsed"
                    )
                    st.session_state["budget_dict"][cat] = round(new_val, 2)

                with cat_col4:
                    b_plus1k = st.button("➕ ₹1k", key=f"add_1k_{cat}", help=f"Increase {cat} budget by ₹1,000")
                    b_plus5p = st.button("➕ 5%", key=f"add_5p_{cat}", help=f"Increase {cat} budget by 5%")
                    if b_plus1k:
                        st.session_state["budget_dict"][cat] = round(current_val + 1000.0, 2)
                        st.rerun()
                    if b_plus5p:
                        st.session_state["budget_dict"][cat] = round(current_val * 1.05, 2)
                        st.rerun()

                with cat_col5:
                    ann_val = st.session_state["budget_dict"][cat] * 12.0
                    st.markdown(f"**{format_inr_short(ann_val)}**")
                    st.caption("Annual Cap")

                st.markdown("<hr style='margin: 6px 0; border-color: #334155;'>", unsafe_allow_html=True)

            # ------------------------------------------------
            # LIVE BUDGET SUMMARY BAR & SAVE BUTTON
            # ------------------------------------------------
            total_allocated_monthly = float(sum(st.session_state["budget_dict"].values()))
            diff_from_target = float(target_monthly_input - total_allocated_monthly)

            sum_c1, sum_c2, sum_c3 = st.columns(3)
            with sum_c1:
                st.metric("🎯 User Target Monthly Spend", format_inr(target_monthly_input))
            with sum_c2:
                st.metric("💵 Total Allocated Monthly Budget", format_inr(total_allocated_monthly), delta=f"{format_inr(diff_from_target)} Buffer" if diff_from_target >= 0 else f"-{format_inr(abs(diff_from_target))} Deficit", delta_color="normal" if diff_from_target >= 0 else "inverse")
            with sum_c3:
                st.metric("📅 Total Annual Budget Cap", format_inr(total_allocated_monthly * 12.0))

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("💾 Save All Configured Category Budgets to Database", type="primary", use_container_width=True):
                records_to_save = [
                    {"category": c, "monthly_limit": val, "annual_limit": val * 12.0}
                    for c, val in st.session_state["budget_dict"].items()
                ]
                saved_n = batch_set_category_budgets(target_fy_clean, records_to_save, family_id=user_family_id)
                st.success(f"🎉 Successfully saved **{saved_n}** category budget target(s) for **{target_fy_clean}**!")
                st.rerun()

            # ------------------------------------------------
            # SECTION 3: BUDGET PERFORMANCE & UTILIZATION DASHBOARD
            # ------------------------------------------------
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("#### 📊 Budget Performance & Utilization Dashboard")
            budget_status = get_budget_status(target_fy_clean, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)

            if not budget_status.empty:
                for idx, row in budget_status.iterrows():
                    cat = row["category"]
                    spent = float(row["Actual_Spent"])
                    budget = float(row["Annual_Budget"])
                    util = float(row["Utilization_%"])

                    if budget > 0:
                        c1, c2, c3 = st.columns([2, 3, 1])
                        with c1:
                            st.markdown(f"**{cat}**")
                            st.caption(f"Spent: {format_inr(spent)} / Budget: {format_inr(budget)}")
                        with c2:
                            progress_val = min(util / 100.0, 1.0)
                            st.progress(progress_val)
                        with c3:
                            if util > 100:
                                st.markdown("<span class='surge-badge'>OVER BUDGET</span>", unsafe_allow_html=True)
                            elif util > 80:
                                st.markdown("<span style='background:#78350f; color:#fde047; padding:4px 8px; border-radius:6px; font-weight:600; font-size:0.85rem;'>DANGER ZONE</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span class='normal-badge'>ON TRACK</span>", unsafe_allow_html=True)

        # ------------------------------------------------
        # SUB-TAB 2: INVESTMENT & WEALTH PORTFOLIO PLANNER
        # ------------------------------------------------
        with subtab_invest:
            st.markdown("### 📈 Investment & Wealth Portfolio Planner")
            st.caption("Takes your allocated Insurance & Investment budget, age, and current savings to construct a personalized asset allocation, monthly SIP breakdown, and 20-year compound wealth trajectory.")

            curr_insurance_invest_monthly = float(st.session_state.get("budget_dict", {}).get("Insurance & Investments", 20000.0))

            from database import get_user_investments_df
            inv_df = get_user_investments_df(username=current_user["username"], family_id=current_user.get("family_id", 1))
            total_active_investments = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0

            inv_col1, inv_col2, inv_col3 = st.columns([1, 1.2, 1.5])
            with inv_col1:
                u_age = st.number_input("👤 Your Age (Years)", min_value=18, max_value=85, value=35, step=1, key="invest_user_age")
            with inv_col2:
                use_portfolio_networth = st.toggle("Link Networth from Active Investments", value=True, help="Automatically link your total active investment valuation here.")
                if use_portfolio_networth:
                    u_savings = total_active_investments
                    st.metric("💰 Linked Portfolio Networth", f"₹ {u_savings:,.2f}")
                else:
                    # Need a separate key to preserve manual state
                    u_savings = st.number_input("💰 Your Networth (₹)", min_value=0.0, value=total_active_investments, step=50000.0, format="%.2f", key="invest_user_savings_manual")
            with inv_col3:
                u_sip_budget = st.number_input(
                    "💵 Monthly Insurance & Investment Budget (₹)",
                    min_value=1000.0,
                    value=max(5000.0, curr_insurance_invest_monthly),
                    step=1000.0,
                    format="%.2f",
                    key="invest_user_sip"
                )

            # Compute Investment Plan
            inv_plan = calculate_investment_plan(
                age=u_age,
                current_savings=u_savings,
                monthly_investment_budget=u_sip_budget,
                monthly_expenses=total_spent / max(1, num_months) if not df_fy.empty else 50000.0
            )

            # Key Investment Metrics
            im1, im2, im3, im4 = st.columns(4)
            with im1:
                st.metric("🚀 Equity Allocation", f"{inv_plan['equity_pct']:.0f}%", f"SIP: {format_inr(inv_plan['equity_sip'])}")
            with im2:
                st.metric("🛡️ Debt Allocation", f"{inv_plan['debt_pct']:.0f}%", f"SIP: {format_inr(inv_plan['debt_sip'])}")
            with im3:
                st.metric("🪙 Gold Allocation", f"{inv_plan['gold_pct']:.0f}%", f"SIP: {format_inr(inv_plan['gold_sip'])}")
            with im4:
                st.metric("📈 Expected Blended CAGR", f"~{inv_plan['blended_cagr_pct']}% / yr", "Indian Market Benchmark")

            st.markdown("<br>", unsafe_allow_html=True)

            # Asset Split Pie Chart & Monthly SIP Allocation Table
            ch_col1, ch_col2 = st.columns([1, 1])

            with ch_col1:
                st.markdown("#### 📊 Age-Adjusted Asset Class Split")
                pie_df = pd.DataFrame([
                    {"Asset": "Equity", "Allocation_%": inv_plan["equity_pct"]},
                    {"Asset": "Debt / Fixed Income", "Allocation_%": inv_plan["debt_pct"]},
                    {"Asset": "Gold / SGB", "Allocation_%": inv_plan["gold_pct"]}
                ])
                fig_asset = px.pie(
                    pie_df,
                    names="Asset",
                    values="Allocation_%",
                    color="Asset",
                    color_discrete_map={"Equity": "#38bdf8", "Debt / Fixed Income": "#34d399", "Gold / SGB": "#fbbf24"},
                    hole=0.4
                )
                fig_asset.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280)
                st.plotly_chart(fig_asset, use_container_width=True)

            with ch_col2:
                st.markdown("#### 📝 Recommended Monthly SIP Allocation")
                sip_df = pd.DataFrame(inv_plan["sip_instruments"])
                st.dataframe(
                    sip_df[["asset_class", "allocation_pct", "monthly_sip", "recommended_instruments"]],
                    column_config={
                        "asset_class": st.column_config.TextColumn("Asset Class"),
                        "allocation_pct": st.column_config.TextColumn("Weight"),
                        "monthly_sip": st.column_config.NumberColumn("Monthly SIP (₹)", format="₹ %.2f"),
                        "recommended_instruments": st.column_config.TextColumn("Suggested Vehicles")
                    },
                    use_container_width=True,
                    hide_index=True
                )

            # Wealth Compound Growth Trajectory Chart
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("#### 🚀 Wealth Compound Growth Trajectory (5 - 20 Years)")
            
            proj_data = []
            for yrs, p_data in inv_plan["projections"].items():
                proj_data.append({
                    "Horizon": f"{yrs} Years",
                    "Total Invested": p_data["total_invested"],
                    "Projected Future Corpus": p_data["total_future_value"],
                    "Wealth Compounding Gain": p_data["wealth_gain"]
                })
            
            proj_df = pd.DataFrame(proj_data)

            fig_proj = px.bar(
                proj_df,
                x="Horizon",
                y=["Total Invested", "Wealth Compounding Gain"],
                title="Compound Capital Growth Projection (12% Eq / 7% Debt / 8% Gold)",
                labels={"value": "Amount (₹)", "variable": "Component"},
                color_discrete_map={"Total Invested": "#64748b", "Wealth Compounding Gain": "#10b981"},
                barmode="stack",
                height=380
            )
            fig_proj.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_proj, use_container_width=True)

            # Emergency Reserve & Safety Shield Indicator
            st.markdown("#### 🏦 Emergency Reserve & Protection Status")
            em_status = inv_plan["emergency_status"]
            if em_status == "Sufficient":
                st.success(f"✅ **Emergency Buffer Healthy**: Your current savings of **{format_inr(u_savings)}** exceeds your recommended 6-month buffer of **{format_inr(inv_plan['req_emergency'])}**.")
            else:
                st.warning(f"⚠️ **Emergency Buffer Deficit**: Target 6-month buffer is **{format_inr(inv_plan['req_emergency'])}**. You have a deficit of **{format_inr(inv_plan['emergency_gap'])}**. Consider assigning initial savings to Liquid Funds before aggressive stock investments.")

            # Gemini AI Wealth & Milestone Strategy Advisor Card
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### 🤖 Gemini AI Wealth & Milestone Advisory")
            st.caption("Get personalized financial milestone recommendations and tax-efficient wealth management strategies.")

            if st.button("💡 Generate AI Wealth & Milestone Advisory", type="primary", use_container_width=True):
                with st.spinner("🤖 Analyzing portfolio allocation with Gemini AI..."):
                    wealth_advice = generate_ai_wealth_advice(inv_plan)

                st.success("🎉 AI Wealth Strategy Generated!")
                st.info(wealth_advice.get("summary", ""))

                for bullet in wealth_advice.get("key_takeaways", []):
                    st.markdown(f"- {bullet}")

            # ------------------------------------------------
            # RETIREMENT PLANNER SIMULATION
            # ------------------------------------------------
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### 🏖️ Retirement Planner Simulation")
            st.caption("Plan your retirement corpus dynamically. Leave 'Expected Returns' blank to automatically fetch historical average returns from global indices.")

            ret_col1, ret_col2 = st.columns(2)
            with ret_col1:
                ret_age = st.number_input("🎯 Desired Retirement Age", min_value=u_age + 1, max_value=100, value=max(60, u_age + 10), step=1)
                exp_return_str = st.text_input("📈 Expected Returns (CAGR %)", placeholder="e.g. 12.5 (Leave blank to use historical data)")
            
            with ret_col2:
                benchmark_index = st.selectbox(
                    "📊 Benchmark Index (If Expected Returns is blank)",
                    options=[
                        ("Nifty 50 (India)", "^NSEI"),
                        ("BSE Sensex (India)", "^BSESN"),
                        ("S&P 500 (US)", "^GSPC"),
                        ("NASDAQ Composite (US)", "^IXIC")
                    ],
                    format_func=lambda x: x[0]
                )
                hist_years = st.selectbox(
                    "📅 Historical Data Period",
                    options=[5, 10, 15, 20],
                    index=1,
                    format_func=lambda x: f"Last {x} Years"
                )

            if st.button("🔮 Calculate Retirement Corpus", type="primary", use_container_width=True):
                from investment_planner import fetch_index_historical_cagr, calculate_retirement_corpus, generate_ai_retirement_advisory
                
                with st.spinner("Calculating retirement projections..."):
                    if exp_return_str.strip():
                        try:
                            cagr_decimal = float(exp_return_str.strip()) / 100.0
                        except ValueError:
                            st.warning("Invalid Expected Returns. Falling back to 12%.")
                            cagr_decimal = 0.12
                    else:
                        st.info(f"Fetching {hist_years}-year historical returns for {benchmark_index[0]}...")
                        cagr_decimal = fetch_index_historical_cagr(benchmark_index[1], hist_years)
                        st.success(f"Historical {hist_years}-year CAGR for {benchmark_index[0]} is **{cagr_decimal*100:.2f}%**")

                    ret_plan = calculate_retirement_corpus(
                        current_age=u_age,
                        retirement_age=ret_age,
                        current_savings=u_savings,
                        monthly_sip=u_sip_budget,
                        cagr_decimal=cagr_decimal
                    )

                    r1, r2, r3 = st.columns(3)
                    r1.metric("💰 Projected Corpus", format_inr(ret_plan["total_future_value"]), f"+ {format_inr(ret_plan['wealth_gain'])} Gain")
                    r2.metric("💵 Total Invested", format_inr(ret_plan["total_invested"]))
                    r3.metric("🏝️ Safe Monthly Withdrawal (4%)", format_inr(ret_plan["safe_monthly_withdrawal"]))

                with st.spinner("🤖 Generating AI Retirement Strategy..."):
                    ret_advice = generate_ai_retirement_advisory(ret_plan, inv_df)
                    st.markdown("#### 🤖 AI Retirement Advisory")
                    st.info(ret_advice.get("summary", ""))
                    for item in ret_advice.get("key_takeaways", []):
                        st.markdown(f"- {item}")

        # ------------------------------------------------
        # SUB-TAB 3: ACTIVE INVESTMENT PORTFOLIO & HOLDINGS TRACKER
        # ------------------------------------------------
        with subtab_holdings:
            st.markdown("### 💼 Active Investment Portfolio & Holdings Tracker")
            st.caption("Track, aggregate, and analyze active investments across platforms. Upload Consolidated Account Statements (CAS) or track live market NAVs.")

            # --- CAS / Broker Statement Uploader ---
            st.markdown("#### 📤 Auto-Ingest from Broker Statements (GenAI Powered)")
            with st.expander("Upload ICICI Direct / Anand Rathi / Standard CAS / Any Format"):
                import os
                import pandas as pd
                
                template_df = pd.DataFrame({
                    "Stock Code / Name": ["HDFC Bank", "Nifty 50 Index Fund"],
                    "Platform / Broker": ["Zerodha", "ICICI Direct"],
                    "Asset Class": ["Equity", "Mutual Funds"],
                    "Invested Amount": [50000.0, 31575.0],
                    "Year Invested": [2022, 2023],
                    "Current Value": [51850.0, 33750.0],
                    "Units": [30.5, 150.25],
                    "Average Buy Price": [1639.34, 210.50],
                    "Market Cap": ["Large Cap", "Unknown"],
                    "Sector / Theme": ["Banking", "Index"]
                })
                csv_template = template_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Standard Statement Template",
                    data=csv_template,
                    file_name="investment_template.csv",
                    mime="text/csv",
                    help="Fill out this standard template for guaranteed 100% accurate parsing without needing Gemini AI."
                )
                
                default_api_key = current_user.get("gemini_api_key")
                if not default_api_key:
                    default_api_key = os.environ.get("GEMINI_API_KEY", "")
                if not default_api_key:
                    try:
                        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
                    except:
                        pass
                
                gemini_api_key = st.text_input("Gemini API Key (Optional for Universal Parsing)", value=default_api_key, type="password", key="stmt_api_key")
                if gemini_api_key and gemini_api_key != current_user.get("gemini_api_key"):
                    if st.button("💾 Save Key to Profile", key="save_api_key_btn"):
                        from database import update_user_gemini_key
                        if update_user_gemini_key(current_user["username"], gemini_api_key):
                            st.session_state["user"]["gemini_api_key"] = gemini_api_key
                            st.success("API Key saved securely to your profile!")
                            st.rerun()
                        else:
                            st.error("Failed to save API key.")
                
                uploaded_file = st.file_uploader("Upload CSV, Excel, PDF, or Image file", type=['csv', 'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'], key="stmt_upload")
                if uploaded_file and st.button("Parse and Import Statement", type="primary"):
                    with st.spinner("Parsing statement with Gemini AI (fallback to heuristics)..." if gemini_api_key else "Parsing statement using heuristics..."):
                        try:
                            parsed_data = statement_parser.identify_and_parse_statement(uploaded_file.getvalue(), uploaded_file.name, api_key=gemini_api_key)
                            if not parsed_data:
                                st.warning("Could not extract any valid holdings from this file. Ensure it's a supported format.")
                            else:
                                import amfi_lookup
                                for inv_dict in parsed_data:
                                    code_candidate = inv_dict.get("name_or_symbol") or inv_dict.get("platform")
                                    if code_candidate and str(code_candidate).strip().isdigit():
                                        resolved = amfi_lookup.resolve_amfi_code(code_candidate)
                                        if resolved:
                                            inv_dict["resolved_name"] = resolved["name"]
                                            inv_dict["sector_segment"] = resolved["category"]

                                from database import batch_insert_investments
                                count = batch_insert_investments(parsed_data, username=current_user["username"], family_id=user_family_id)
                                st.success(f"🎉 Successfully imported {count} holdings from {uploaded_file.name}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error parsing file: {e}")

            # Form to Add New Investment Entry
            st.markdown("#### ➕ Add New Manual Holding")
            
            PRESET_TYPES = [
                "Equity (Stocks)",
                "Mutual funds",
                "Structured funds",
                "EPF",
                "PPF",
                "KVP (Kisan Vikas Patra)",
                "NSC (National Savings Certificate)",
                "Fixed Deposits / Recurring Deposits",
                "Startup investments",
                "Gold / Sovereign Gold Bonds (SGB)",
                "Real Estate",
                "Other (Add Custom Type)"
            ]
            
            PRESET_PLATFORMS = [
                "Zerodha",
                "Groww",
                "SBI / SBI Mutual Fund",
                "Post Office",
                "Coin (Zerodha)",
                "Angel One",
                "Upstox",
                "ICICI Direct",
                "HDFC Securities",
                "IndMoney",
                "Direct / Primary Institution",
                "Other (Add Custom Platform)"
            ]

            add_col1, add_col2, add_col3, add_col4, add_col5 = st.columns([1.5, 1.5, 1.2, 1.0, 1.2])

            with add_col1:
                selected_plat = st.selectbox("Platform / Broker", PRESET_PLATFORMS, key="inv_plat_sel")
                if selected_plat == "Other (Add Custom Platform)":
                    final_plat = st.text_input("Specify Platform Name", value="Custom Broker", key="inv_plat_custom")
                else:
                    final_plat = selected_plat

            with add_col2:
                selected_type = st.selectbox("Investment Type", PRESET_TYPES, key="inv_type_sel")
                if selected_type == "Other (Add Custom Type)":
                    final_type = st.text_input("Specify Custom Category", value="Alternative Asset", key="inv_type_custom")
                else:
                    final_type = selected_type

            with add_col3:
                inv_desc_val = st.text_input("Stock Code / Name", value="HDFCBANK", key="inv_desc_input")

            with add_col4:
                inv_amt_val = st.number_input("Invested Amount (₹)", min_value=100.0, value=50000.0, step=5000.0, format="%.2f", key="inv_amt_input")

            with add_col5:
                curr_year = datetime.datetime.now().year
                inv_yr_val = st.number_input("Year Invested", min_value=1990, max_value=curr_year + 5, value=curr_year, step=1, key="inv_yr_input")
                curr_val_input = st.number_input("Current Value (₹)", min_value=0.0, value=inv_amt_val * 1.10, step=5000.0, format="%.2f", key="inv_curr_input")

            if st.button("➕ Add Investment Holding to Portfolio", type="primary", use_container_width=True):
                new_id = insert_investment(
                    username=current_user["username"],
                    platform=final_plat,
                    investment_type=final_type,
                    investment_amount=inv_amt_val,
                    year_invested=inv_yr_val,
                    current_value=curr_val_input,
                    family_id=user_family_id,
                    description=inv_desc_val
                )
                st.success(f"🎉 Successfully added holding **{inv_desc_val}** under **{final_plat}** with initial investment of **{format_inr(inv_amt_val)}**!")
                st.rerun()

            st.markdown("<hr>", unsafe_allow_html=True)

            # Retrieve User Holdings
            holdings_df = get_user_investments_df(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)

            if not holdings_df.empty:
                tot_invested = float(holdings_df["investment_amount"].sum())
                tot_current = float(holdings_df["current_value"].sum())
                tot_gain = tot_current - tot_invested
                tot_returns_pct = round((tot_gain / tot_invested) * 100.0, 2) if tot_invested > 0 else 0.0

                # Top Metrics
                hm1, hm2, hm3, hm4 = st.columns(4)
                with hm1:
                    st.metric("💰 Total Invested Capital", format_inr(tot_invested))
                with hm2:
                    st.metric("🏆 Current Portfolio Valuation", format_inr(tot_current))
                with hm3:
                    st.metric(
                        "📈 Capital Gain / Loss",
                        format_inr(tot_gain),
                        delta=f"{tot_returns_pct:.2f}% Total Gain" if tot_gain >= 0 else f"{tot_returns_pct:.2f}% Loss",
                        delta_color="normal" if tot_gain >= 0 else "inverse"
                    )
                with hm4:
                    st.metric("📊 Total Holdings Count", f"{len(holdings_df)} Active Assets")

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Live Market Refresh
                head_c1, head_c2 = st.columns([3, 1])
                with head_c1:
                    st.markdown("#### 📡 Real-Time Portfolio Tracking")
                with head_c2:
                    if st.button("🔄 Sync Live Prices (NAVs)", use_container_width=True):
                        with st.spinner("Fetching latest NAVs from AMFI & Market APIs..."):
                            updated_df = live_market_tracker.update_portfolio_live_prices(holdings_df.copy())
                            update_investments_df(updated_df)
                        st.success("✅ Portfolio synced with live market data!")
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

                # Multi-Segment Distribution Charts
                chart_c1, chart_c2, chart_c3 = st.columns(3)
                with chart_c1:
                    st.markdown("#### 🍩 Asset Type")
                    fig_type = px.pie(
                        holdings_df,
                        names="investment_type",
                        values="current_value",
                        hole=0.4
                    )
                    fig_type.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=280)
                    st.plotly_chart(fig_type, use_container_width=True)

                with chart_c2:
                    st.markdown("#### 🏗️ Market Cap")
                    fig_mc = px.pie(
                        holdings_df,
                        names="market_cap",
                        values="current_value",
                        hole=0.4
                    )
                    fig_mc.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=280)
                    st.plotly_chart(fig_mc, use_container_width=True)

                with chart_c3:
                    st.markdown("#### 🏛️ Platform / Broker")
                    fig_plat = px.bar(
                        holdings_df.groupby("platform", as_index=False)["current_value"].sum(),
                        x="platform",
                        y="current_value",
                        color="platform",
                        labels={"current_value": "Current Value (₹)", "platform": "Platform"}
                    )
                    fig_plat.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", margin=dict(l=10, r=10, t=10, b=10), height=280, showlegend=False)
                    st.plotly_chart(fig_plat, use_container_width=True)
                    
                st.markdown("<hr>", unsafe_allow_html=True)
                
                # Target Allocation & Rebalancing Drift
                st.markdown("#### ⚖️ Target Allocation & Rebalancing (Segment Drift)")
                st.caption("Compare your current portfolio segments against ideal target allocations to identify drift.")
                
                seg_analytics = analyze_portfolio_segments(holdings_df)
                
                target_allocs = {
                    "Equity": st.sidebar.slider("Target Equity %", 0, 100, 60, key="tgt_eq"),
                    "Mutual Funds": st.sidebar.slider("Target MF %", 0, 100, 20, key="tgt_mf"),
                    "Deposits": st.sidebar.slider("Target Debt/Deposits %", 0, 100, 20, key="tgt_debt")
                }
                
                drift_data = calculate_asset_allocation_drift(seg_analytics, target_allocs)
                if drift_data:
                    drift_df = pd.DataFrame(drift_data)
                    st.dataframe(drift_df, use_container_width=True)
                    
                    if st.button("🤖 Get AI Segment & Rebalancing Advice", type="primary"):
                        with st.spinner("Analyzing Segment Diversification & Drift..."):
                            adv = generate_ai_segment_advisory(seg_analytics, "Moderate (Growth)")
                        st.info(adv)
                        
                st.markdown("<hr>", unsafe_allow_html=True)
                
                with st.expander("🧹 Find & Remove Duplicate Holdings"):
                    st.caption("Scan your portfolio for exactly identical entries (same amount, platform, year, type, etc.)")
                    from database import find_duplicate_investments, delete_duplicate_investments
                    duplicates = find_duplicate_investments(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)
                    
                    if not duplicates:
                        st.success("No duplicate holdings found!")
                    else:
                        st.warning(f"Found {len(duplicates)} group(s) of identical investments.")
                        
                        duplicate_ids_to_delete = []
                        dup_display_list = []
                        
                        for group in duplicates:
                            # Keep the first, mark rest for deletion
                            original = group[0]
                            dups = group[1:]
                            duplicate_ids_to_delete.extend([d['id'] for d in dups])
                            
                            for d in dups:
                                dup_display_list.append({
                                    "Duplicate ID": d['id'],
                                    "Original ID": original['id'],
                                    "Platform": d['platform'],
                                    "Name/Desc": d['description'],
                                    "Invested": d['investment_amount']
                                })
                        
                        st.dataframe(pd.DataFrame(dup_display_list), use_container_width=True)
                        
                        if st.button(f"🗑️ Delete {len(duplicate_ids_to_delete)} Duplicate Entries", type="primary"):
                            del_count = delete_duplicate_investments(duplicate_ids_to_delete)
                            st.success(f"Successfully deleted {del_count} duplicate entries! Refreshing...")
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                # Interactive Data Editor & Deletion Manager
                st.markdown("#### ✏️ Edit or Manage Holdings")
                st.caption("You can update investment amounts, current values, platform, or investment types directly in the table below, then click Save.")

                # Asset Class Filter
                all_asset_types = sorted(holdings_df["investment_type"].unique().tolist())
                selected_asset_types = st.multiselect(
                    "🔍 Filter by Asset Class",
                    options=all_asset_types,
                    default=all_asset_types,
                    help="Select asset classes (e.g., Equity, Mutual Funds) to view and edit."
                )

                if selected_asset_types:
                    filtered_df = holdings_df[holdings_df["investment_type"].isin(selected_asset_types)]
                else:
                    filtered_df = holdings_df.head(0) # Show empty if nothing selected

                # Make sure resolved_name exists in columns if loading legacy data
                if "resolved_name" not in holdings_df.columns:
                    holdings_df["resolved_name"] = ""

                display_cols = ["id", "description", "resolved_name", "platform", "investment_type", "investment_amount", "year_invested", "current_value", "units", "avg_buy_price", "market_cap", "sector_segment", "unrealized_gain", "returns_pct"]
                
                edited_holdings = st.data_editor(
                    filtered_df[display_cols] if not filtered_df.empty else filtered_df,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "description": st.column_config.TextColumn("Stock Code / Name"),
                        "resolved_name": st.column_config.TextColumn("Resolved AMFI Name (Read-only)", disabled=True),
                        "platform": st.column_config.TextColumn("Platform / Broker"),
                        "investment_type": st.column_config.TextColumn("Asset Type"),
                        "investment_amount": st.column_config.NumberColumn("Invested (₹)", format="₹ %.2f"),
                        "year_invested": st.column_config.NumberColumn("Year"),
                        "current_value": st.column_config.NumberColumn("Current Val (₹)", format="₹ %.2f"),
                        "units": st.column_config.NumberColumn("Units", format="%.4f"),
                        "avg_buy_price": st.column_config.NumberColumn("Avg Price", format="₹ %.2f"),
                        "market_cap": st.column_config.SelectboxColumn("Market Cap", options=["Large Cap", "Mid Cap", "Small Cap", "Multi Cap", "Unknown"]),
                        "sector_segment": st.column_config.TextColumn("Sector / Theme"),
                        "unrealized_gain": st.column_config.NumberColumn("Gain/Loss (₹)", format="₹ %.2f", disabled=True),
                        "returns_pct": st.column_config.NumberColumn("Return %", format="%.2f %%", disabled=True)
                    },
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_holdings"
                )

                ed_c1, ed_c2 = st.columns([2, 1])
                with ed_c1:
                    if st.button("💾 Save Table Edits to Database", type="primary", use_container_width=True):
                        cnt_upd = update_investments_df(edited_holdings)
                        st.success(f"🎉 Updated {cnt_upd} holding entry/entries in database!")
                        st.rerun()

                with ed_c2:
                    del_id = st.number_input("Delete Holding ID", min_value=1, step=1, key="del_inv_id")
                    if st.button("🗑️ Delete Holding", type="secondary", use_container_width=True):
                        delete_investment(del_id)
                        st.success(f"Deleted holding ID {del_id}!")
                        st.rerun()

                    # Add an expander for deleting all holdings to prevent accidental deletion
                    with st.expander("🚨 Delete All Holdings"):
                        st.warning("This action cannot be undone. It will permanently delete all your holdings.")
                        if st.button("🗑️ Confirm Delete ALL", type="primary", use_container_width=True):
                            deleted_count = delete_all_investments(
                                username=current_user["username"] if view_mode != "Family" else None,
                                family_id=user_family_id
                            )
                            st.success(f"Successfully deleted all {deleted_count} holdings!")
                            st.rerun()

                # Gemini AI Portfolio Review & Suggestions Section
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("### 🤖 Gemini AI Portfolio Review & Suggestions")
                st.caption("Get automated AI portfolio analysis on asset concentration risk, platform diversification, tax efficiency, and rebalancing recommendations.")

                if st.button("🤖 Generate AI Portfolio Review & Suggestions", type="primary", use_container_width=True):
                    with st.spinner("🤖 Analyzing active investment portfolio with Gemini AI..."):
                        portfolio_ai = generate_ai_portfolio_suggestions(holdings_df)

                    st.success("🎉 Portfolio AI Review Complete!")
                    st.info(portfolio_ai.get("summary", ""))

                    for rec in portfolio_ai.get("recommendations", []):
                        st.markdown(f"#### {rec.get('title', 'Recommendation')}")
                        st.markdown(f"**Observation**: {rec.get('observation', '')}")
                        st.markdown(f"**Suggestion**: {rec.get('suggestion', '')}")
                        st.markdown("<hr style='margin: 8px 0; border-color: #334155;'>", unsafe_allow_html=True)

            else:
                st.info("💡 No active holdings recorded yet. Use the form above to add your first investment asset!")

    with tab_data:
        st.subheader("📝 Interactive Database Log, Edit & Delete Manager")
        if is_super_admin:
            st.caption("👑 **Super Admin View**: You have access to view, edit, and export records across the entire database or filter by family using the sidebar.")
        else:
            st.caption("Double-click any cell to edit dates, categories, descriptions, or amounts directly. Click **Save All Edits** to update database.")
        
        expenses_table = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
        
        if not expenses_table.empty:
            # Fetch all historical labeled records for Machine Learning training
            all_hist_df = get_expenses_df(fy=None, username=None, view_mode="All", family_id=user_family_id)
            hist_records = all_hist_df.to_dict("records") if not all_hist_df.empty else []
            
            # Machine Learning Model Status & Toolbar
            st.markdown("""
            <div style="background-color: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #38bdf8; margin-bottom: 15px;">
                <div style="font-weight: 600; color: #38bdf8; font-size: 0.95rem;">🤖 Machine Learning Auto-Categorization Toolbar</div>
                <div style="color: #94a3b8; font-size: 0.85rem;">Automatically categorize expenses based on past learned spending patterns & Indian merchant rules.</div>
            </div>
            """, unsafe_allow_html=True)
            
            ml_col1, ml_col2 = st.columns([1, 1])
            with ml_col1:
                if st.button("🤖 Auto-Categorize Uncategorized/Misc (ML)", type="secondary", use_container_width=True, help="Auto-fills Miscellaneous or blank categories using ML learnings from historical records."):
                    updated_df, mod_cnt, t_cnt = apply_ml_auto_categorization(expenses_table, hist_records, overwrite_all=False)
                    if mod_cnt > 0:
                        saved_n = update_expenses_df(updated_df)
                        st.success(f"🎉 ML Engine auto-categorized **{mod_cnt}** record(s) based on **{t_cnt}** learned historical patterns!")
                        st.rerun()
                    else:
                        st.info("ℹ️ All records in the current view are already categorized.")
                        
            with ml_col2:
                if st.button("⚡ Re-Categorize ALL Items with ML Learnings", type="secondary", use_container_width=True, help="Re-applies ML categorizer across ALL items based on latest database learnings."):
                    updated_df, mod_cnt, t_cnt = apply_ml_auto_categorization(expenses_table, hist_records, overwrite_all=True)
                    if mod_cnt > 0:
                        saved_n = update_expenses_df(updated_df)
                        st.success(f"⚡ ML Engine re-categorized **{mod_cnt}** item(s) using **{t_cnt}** learned patterns!")
                        st.rerun()
                    else:
                        st.info("ℹ️ All categories are already up-to-date with ML learnings.")
                        
            st.markdown("<br>", unsafe_allow_html=True)
            
            if "expense_date" in expenses_table.columns:
                expenses_table["expense_date"] = pd.to_datetime(expenses_table["expense_date"]).dt.date
                
            cols_to_show = ["id", "expense_date", "category", "description", "amount", "financial_year", "quarter", "half_year", "visibility", "username"]
            if "family_id" in expenses_table.columns and is_super_admin:
                cols_to_show.append("family_id")
            cols_to_show.append("source_note")

            edited_db = st.data_editor(
                expenses_table[cols_to_show],
                num_rows="dynamic",
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "expense_date": st.column_config.DateColumn("Date", required=True),
                    "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                    "description": st.column_config.TextColumn("Description"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
                    "financial_year": st.column_config.TextColumn("FY", disabled=True),
                    "quarter": st.column_config.TextColumn("Quarter", disabled=True),
                    "half_year": st.column_config.TextColumn("Half Year", disabled=True),
                    "visibility": st.column_config.SelectboxColumn("Sharing", options=["Family", "Private"], required=True),
                    "username": st.column_config.TextColumn("Logged By", disabled=True),
                    "family_id": st.column_config.NumberColumn("Family ID", disabled=True),
                    "source_note": st.column_config.TextColumn("Source", disabled=True)
                },
                use_container_width=True,
                hide_index=True,
                key="db_log_editor"
            )
            
            col_act1, col_act2 = st.columns([1, 1])
            with col_act1:
                if st.button("💾 Save All Database Edits & Updates", type="primary", use_container_width=True):
                    updated_count = update_expenses_df(edited_db)
                    st.success(f"🎉 Successfully updated {updated_count} record(s) in database!")
                    st.rerun()
                    
            with col_act2:
                csv_data = expenses_table.to_csv(index=False).encode('utf-8')
                export_label = "📥 Export Full Database to CSV" if (is_super_admin and user_family_id is None) else "📥 Export Family Log to CSV"
                file_name_label = f"Expenses_{'Full_Database' if (is_super_admin and user_family_id is None) else f'Family_{user_family_id}'}_{selected_fy.replace(' ', '_')}.csv"
                st.download_button(
                    label=export_label,
                    data=csv_data,
                    file_name=file_name_label,
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No records found in database.")

    # ----------------------------------------------------
    # TAB 9: ADMIN & USER MANAGEMENT (Admin Only)
    # ----------------------------------------------------
    if tab_admin:
        with tab_admin:
            st.subheader("👑 Administrator & Family Workspace Management")
            st.caption("Manage household user accounts, share family join codes, assign roles, and verify Turso cloud database connection.")
            
            st.markdown(f"""
            <div style="background-color: #1e293b; padding: 18px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px;">
                <h4 style="color: #38bdf8; margin-top: 0; margin-bottom: 6px;">🏠 Active Family Workspace: {user_family_name}</h4>
                <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 8px;">Family Join Code: <code style="font-size: 1.15rem; color: #fbbf24; background: #0f172a; padding: 4px 10px; border-radius: 4px; font-weight: 700;">{user_family_code}</code></p>
                <p style="color: #64748b; font-size: 0.82rem; margin-bottom: 0;">💡 Share this Join Code with your family members so they can join this household workspace when signing up.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Section 1: Register New User
            st.markdown("### ➕ Register New Household Member Account")
            with st.form("create_user_form"):
                c_col1, c_col2, c_col3, c_col4 = st.columns([2, 2, 2, 1.5])
                with c_col1:
                    c_user = st.text_input("Username", placeholder="e.g. spouse, rahul, priya").strip().lower()
                with c_col2:
                    c_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma").strip()
                with c_col3:
                    c_pwd = st.text_input("Initial Password", type="password", help="Minimum 4 characters")
                with c_col4:
                    c_role = st.selectbox("Role", ["Member", "Admin"], help="Admins can manage users; Members can log private & family expenses.")
                    
                if st.form_submit_button("🚀 Create User Account", type="primary", use_container_width=True):
                    ok, msg = create_user(c_user, c_pwd, c_name, c_role, family_id=user_family_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
            st.markdown("---")
            
            # Section 2: User Directory & Access Management
            st.markdown(f"### 👥 {user_family_name} Members & Directory")
            users_list = get_all_users(family_id=user_family_id)
            u_df = pd.DataFrame(users_list)
            st.dataframe(u_df, use_container_width=True, hide_index=True)
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown("##### 🎭 Update User Role")
                target_user_role = st.selectbox("Select User for Role Change", [u["username"] for u in users_list], key="admin_role_target")
                new_r = st.selectbox("Assign Role", ["Member", "Admin"], key="admin_role_select")
                if st.button("Update User Role", type="primary", use_container_width=True):
                    ok, msg = update_user_role(target_user_role, new_r)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
            with m_col2:
                st.markdown("##### 🗑️ Delete User Account")
                non_admin_users = [u["username"] for u in users_list if u["username"] != "admin"]
                if non_admin_users:
                    target_user_del = st.selectbox("Select User to Delete", non_admin_users, key="admin_del_target")
                    if st.button(f"🗑️ Delete User '{target_user_del}'", use_container_width=True):
                        ok, msg = delete_user(target_user_del)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.caption("No secondary users available to delete.")
                    
            st.markdown("---")
            
            # Section 3: Password Change & Turso Cloud Status
            sec_col1, sec_col2 = st.columns(2)
            with sec_col1:
                st.markdown("### 🔑 Change My Password")
                with st.form("pwd_change_form"):
                    new_p1 = st.text_input("New Password", type="password", help="Minimum 4 characters")
                    new_p2 = st.text_input("Confirm New Password", type="password")
                    if st.form_submit_button("💾 Update My Password", type="primary", use_container_width=True):
                        if new_p1 != new_p2:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg = update_user_password(current_user["username"], new_p1)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                                
            with sec_col2:
                st.markdown("### 🌐 Database Storage Engine Status")
                db_type = get_db_type()
                if "Turso" in db_type:
                    st.success("✅ **Connected to Turso Cloud Database!** Your expense records persist 24/7 in the cloud.")
                else:
                    st.info("💻 **Running on Local SQLite Database** (`data/expenses.db`).")
                    st.markdown("""
                    ##### How to connect to Turso Cloud Database:
                    1. Create a free database on [Turso.tech](https://turso.tech).
                    2. Copy your database URL (`libsql://...`) and Auth Token.
                    3. Add them to environment variables or `.streamlit/secrets.toml`:
                       ```toml
                       TURSO_DATABASE_URL = "libsql://your-db-name.turso.io"
                       TURSO_AUTH_TOKEN = "your-turso-auth-token"
                       ```
                    4. Restart Streamlit — your app will automatically connect to Turso Cloud!
                    """)
