import os
import io
import datetime
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as io_plotly
import streamlit as st

from categorizer import (
    auto_categorize_description,
    apply_ml_auto_categorization,
    MLCategorizer
)
from config import (
    EXPENSE_CATEGORIES,
    get_indian_fy,
    get_indian_quarter,
    get_indian_half_year,
    format_inr,
    format_inr_short
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
    set_category_budget,
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
    get_db_type
)
from cpi_data import (
    get_cpi_df,
    calculate_cpi_inflation,
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
    <div style="max-width: 480px; margin: 30px auto; padding: 30px; border-radius: 12px; background-color: #1e293b; border: 1px solid #334155; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">
        <h2 style="color: #38bdf8; margin-bottom: 6px;">🔐 In-House Expense Tracker</h2>
        <p style="color: #94a3b8; font-size: 0.95rem;">Sign in to access your Private & Household Expenses</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
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
                    
        st.caption("🔒 Authorized household access only. Contact your administrator if you need access.")

else:
    # ----------------------------------------------------
    # LOGGED IN USER & SIDEBAR SETUP
    # ----------------------------------------------------
    current_user = st.session_state["user"]

    st.sidebar.image("https://img.icons8.com/isometric/100/rupee.png", width=64)
    st.sidebar.title("📌 Navigation & Settings")

    role_color = "#38bdf8" if current_user["role"] == "Admin" else "#34d399"
    st.sidebar.markdown(f"""
    <div style="background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid {role_color}; margin-bottom: 12px;">
        <div style="font-weight: 600; color: #f8fafc;">👤 {current_user['full_name']}</div>
        <div style="font-size: 0.8rem; color: #94a3b8;">@{current_user['username']} • <span style="color: {role_color}; font-weight: 600;">{current_user['role']}</span></div>
    </div>
    """, unsafe_allow_html=True)

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

    all_fys = get_all_financial_years(username=current_user["username"], view_mode=view_mode)
    selected_fy = st.sidebar.selectbox("📅 Select Financial Year", ["All FYs"] + all_fys, index=1 if len(all_fys) > 1 else 0)

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

    df_fy = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
    total_spent = df_fy["amount"].sum() if not df_fy.empty else 0.0
    total_txns = len(df_fy) if not df_fy.empty else 0
    num_months = df_fy["Month_Year"].nunique() if not df_fy.empty and "Month_Year" in df_fy.columns else 1
    num_months = max(1, num_months)
    avg_monthly_spent = total_spent / num_months if not df_fy.empty else 0.0

    cat_breakdown = get_category_breakdown(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
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
    def import_from_excel_or_csv(file, username: str = "admin", visibility: str = "Family") -> tuple:
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
            count = insert_expenses(records, source=f"Import ({file.name})", username=username, visibility=visibility)
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
        "🎯 Budgeting & Targets",
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
                        cnt = insert_expenses(categorized_rows, source="Excel Grid (Auto-Categorized)", username=current_user["username"], visibility=entry_vis)
                        st.success(f"🎉 Successfully auto-categorized and saved {cnt} expense entries!")
                        st.rerun()
                    else:
                        st.warning("Please enter at least one row with an amount greater than 0.")
                        
            with col_btn2:
                if st.button("💾 Save As Is (No Auto-Categorize)", use_container_width=True):
                    valid_rows = [r for r in grid_edited.to_dict("records") if float(r.get("amount", 0.0)) > 0]
                    if valid_rows:
                        cnt = insert_expenses(valid_rows, source="Excel Grid Editor", username=current_user["username"], visibility=entry_vis)
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
                uploaded_excel = st.file_uploader("Choose Excel or CSV File", type=["xlsx", "xls", "csv"], key="excel_uploader")
                if uploaded_excel:
                    if st.button("🚀 Import & Auto-Categorize File", type="primary", use_container_width=True):
                        cnt, msg = import_from_excel_or_csv(uploaded_excel, username=current_user["username"], visibility=upload_vis)
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
                    }], source="Quick Manual Entry", username=current_user["username"], visibility=q_vis)
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
                    months_available = all_df["Month_Year"].unique().tolist()
                    selected_month = st.selectbox("Select Month", months_available)
                    filtered_df = all_df[all_df["Month_Year"] == selected_month]
                    period_title = f"Itemized Expenses for {selected_month}"
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
                    available_m = expenses_df_all["Month_Year"].unique().tolist()
                    del_month_target = st.selectbox("Select Month to Wipe", available_m, key="bulk_del_m")
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
        st.subheader("📈 Indian CPI Inflation & Purchasing Power Analytics")
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

    # ----------------------------------------------------
    # TAB 6: EXPENSE SURGE DETECTOR
    # ----------------------------------------------------
    with tab_surge:
        st.subheader(f"🚨 Expense Surge & Spike Detector ({selected_fy})")
        st.write("Identifies categories where your spending is spiking above trailing averages or exceeding the inflation baseline.")
        
        surge_df = get_surge_categories(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
        
        if surge_df.empty:
            st.warning("Insufficient transaction data to compute surge detection.")
        else:
            st.markdown("#### Expense Surge Radar")
            st.dataframe(
                surge_df[["category", "Latest_Month_Spend", "Hist_Monthly_Avg", "Surge_%", "Total", "Count"]],
                column_config={
                    "category": st.column_config.TextColumn("Category"),
                    "Latest_Month_Spend": st.column_config.NumberColumn("Recent Spend (₹)", format="₹ %.2f"),
                    "Hist_Monthly_Avg": st.column_config.NumberColumn("Hist Monthly Avg (₹)", format="₹ %.2f"),
                    "Surge_%": st.column_config.NumberColumn("Spike / Surge %", format="%.1f %%"),
                    "Total": st.column_config.NumberColumn("FY Total (₹)", format="₹ %.2f"),
                    "Count": st.column_config.NumberColumn("Entries")
                },
                use_container_width=True,
                hide_index=True
            )

    # ----------------------------------------------------
    # TAB 7: BUDGETING & TARGETS
    # ----------------------------------------------------
    with tab_budget:
        st.subheader(f"🎯 Budgeting & Target Allocation ({selected_fy})")
        st.write("Set monthly or annual budget caps for each category to keep expenses under control.")
        
        with st.expander("⚙️ Set / Edit Category Budget Cap"):
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            with b_col1:
                budget_cat = st.selectbox("Category", EXPENSE_CATEGORIES)
            with b_col2:
                m_limit = st.number_input("Monthly Limit (₹)", min_value=0.0, value=15000.0, step=1000.0)
            with b_col3:
                a_limit = st.number_input("Annual Limit (₹)", min_value=0.0, value=m_limit * 12, step=5000.0)
            with b_col4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Save Budget Target", type="primary", use_container_width=True):
                    set_category_budget(selected_fy if selected_fy != "All FYs" else all_fys[0], budget_cat, m_limit, a_limit)
                    st.success(f"Saved budget target for {budget_cat}!")
                    st.rerun()

        budget_status = get_budget_status(selected_fy if selected_fy != "All FYs" else all_fys[0], username=current_user["username"], view_mode=view_mode)
        
        st.markdown("#### Budget Performance Dashboard")
        for idx, row in budget_status.iterrows():
            cat = row["category"]
            spent = row["Actual_Spent"]
            budget = row["Annual_Budget"]
            util = row["Utilization_%"]
            
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

    # ----------------------------------------------------
    # TAB 8: DATABASE LOG, EDIT & EXPORT
    # ----------------------------------------------------
    with tab_data:
        st.subheader("📝 Interactive Database Log, Edit & Delete Manager")
        st.caption("Double-click any cell to edit dates, categories, descriptions, or amounts directly. Click **Save All Edits** to update database.")
        
        expenses_table = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
        
        if not expenses_table.empty:
            # Fetch all historical labeled records for Machine Learning training
            all_hist_df = get_expenses_df(fy=None, username=None, view_mode="All")
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
                
            edited_db = st.data_editor(
                expenses_table[["id", "expense_date", "category", "description", "amount", "financial_year", "quarter", "half_year", "visibility", "username", "source_note"]],
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
                st.download_button(
                    label="📥 Export Full Records to CSV",
                    data=csv_data,
                    file_name=f"expenses_{selected_fy.replace(' ', '_')}.csv",
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
            st.subheader("👑 Administrator & User Access Control")
            st.caption("Manage user accounts, assign roles, change credentials, and verify Turso cloud database connection.")
            
            st.markdown("---")
            
            # Section 1: Register New User
            st.markdown("### ➕ Register New Household User / Family Member")
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
                    ok, msg = create_user(c_user, c_pwd, c_name, c_role)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
            st.markdown("---")
            
            # Section 2: User Directory & Access Management
            st.markdown("### 👥 Active Users Directory & Access Management")
            users_list = get_all_users()
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
