import os
import io
import datetime
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as io_plotly
import streamlit as st

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
    get_cumulative_metrics
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

# Mobile viewport meta tag (ensures proper scaling on Chrome, Safari, Edge mobile)
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
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.88rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .surge-badge {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .normal-badge {
        background-color: #064e3b;
        color: #6ee7b7;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* ===== MOBILE RESPONSIVE STYLES ===== */

    /* Tablet breakpoint (768px and below) */
    @media screen and (max-width: 768px) {
        /* Stack Streamlit columns vertically */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Scale down header text */
        .main-header {
            font-size: 1.5rem !important;
        }
        .sub-header {
            font-size: 0.9rem !important;
        }

        /* Metric cards: smaller padding & font */
        .metric-card {
            padding: 12px 10px !important;
            margin-bottom: 8px !important;
        }
        .metric-value {
            font-size: 1.4rem !important;
        }
        .metric-label {
            font-size: 0.78rem !important;
        }

        /* Tabs: allow horizontal scroll, prevent wrapping */
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

        /* Data editor / dataframe: horizontal scroll */
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }
        [data-testid="stDataFrame"] table,
        [data-testid="stDataEditor"] table {
            min-width: 600px !important;
        }

        /* Buttons: touch-friendly size */
        .stButton > button {
            min-height: 44px !important;
            font-size: 0.85rem !important;
        }

        /* Sidebar: auto-collapse on mobile */
        [data-testid="stSidebar"] {
            min-width: 0px !important;
        }
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 260px !important;
            max-width: 80vw !important;
        }

        /* Inputs: full width, comfortable tap targets */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stDateInput > div > div > input {
            min-height: 42px !important;
            font-size: 0.9rem !important;
        }

        /* Plotly charts: constrain to viewport */
        .js-plotly-plot, .plotly {
            max-width: 100% !important;
            overflow-x: auto !important;
        }

        /* Expander: readable on mobile */
        [data-testid="stExpander"] {
            font-size: 0.9rem !important;
        }

        /* Radio buttons horizontal → stack if needed */
        [data-testid="stRadio"] > div {
            flex-wrap: wrap !important;
            gap: 6px !important;
        }
    }

    /* Small phone breakpoint (480px and below) */
    @media screen and (max-width: 480px) {
        .main-header {
            font-size: 1.25rem !important;
        }
        .sub-header {
            font-size: 0.8rem !important;
            margin-bottom: 0.8rem !important;
        }
        .metric-card {
            padding: 10px 8px !important;
            border-radius: 8px !important;
        }
        .metric-value {
            font-size: 1.2rem !important;
        }
        .metric-label {
            font-size: 0.72rem !important;
            letter-spacing: 0.02em !important;
        }

        /* Even smaller tab labels on phones */
        [data-testid="stTabs"] [role="tab"] {
            font-size: 0.68rem !important;
            padding: 6px 8px !important;
        }

        /* Compact badges */
        .surge-badge, .normal-badge {
            font-size: 0.75rem !important;
            padding: 3px 6px !important;
        }

        /* Stack radio buttons vertically on small phones */
        [data-testid="stRadio"] > div {
            flex-direction: column !important;
        }
    }

    /* ===== CROSS-BROWSER FIXES ===== */

    /* Safari: fix text rendering and gradient clip */
    @supports (-webkit-touch-callout: none) {
        .main-header {
            background-clip: text;
            -webkit-background-clip: text;
        }
        /* Safari smooth scrolling for tabs */
        [data-testid="stTabs"] [role="tablist"] {
            -webkit-overflow-scrolling: touch;
        }
    }

    /* Ensure touch-action for all interactive elements (Edge/Chrome/Safari) */
    button, input, select, textarea, [role="tab"], [role="button"] {
        touch-action: manipulation;
    }

    /* Scrollbar styling for tab overflow (Chrome/Edge) */
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
        height: 3px;
    }
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 3px;
    }
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar-track {
        background: transparent;
    }
</style>
""", unsafe_allow_html=True)

# Helper for Excel Template Download
def generate_excel_template() -> bytes:
    df_template = pd.DataFrame([
        {"Date (YYYY-MM-DD)": "2025-05-01", "Category": "Groceries & Provisions", "Description": "Weekly D-Mart shopping", "Amount (INR)": 4500.00},
        {"Date (YYYY-MM-DD)": "2025-05-03", "Category": "Utilities (Electricity/Water/Gas)", "Description": "LPG Gas Cylinder", "Amount (INR)": 950.00},
        {"Date (YYYY-MM-DD)": "2025-05-10", "Category": "Dining & Swiggy/Zomato", "Description": "Family dinner", "Amount (INR)": 1800.00}
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Expense_Template')
    return output.getvalue()

# Helper for Excel/CSV Import
def import_from_excel_or_csv(file) -> tuple:
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
                
        df.rename(columns=col_map, inplace=True)
        
        # Ensure mandatory columns exist
        for col_req in ["date", "category", "description", "amount"]:
            if col_req not in df.columns:
                df[col_req] = "" if col_req != "amount" else 0.0
                
        # Fill NA / NaN values safely
        df["amount"] = pd.to_numeric(
            df["amount"].astype(str).str.replace("₹", "").str.replace("Rs", "").str.replace(",", "").str.strip(),
            errors="coerce"
        ).fillna(0.0)
        
        # Keep only rows with amount > 0
        df = df[df["amount"] > 0]
        
        if df.empty:
            return 0, f"No valid rows with expense amounts > 0 were found in {file.name}."
            
        records = df[["date", "category", "description", "amount"]].to_dict("records")
        records = auto_categorize_records(records)
        count = insert_expenses(records, source=f"Import ({file.name})")
        return count, f"Successfully imported {count} expense rows from {file.name}!"
    except Exception as e:
        return 0, f"Error processing file: {e}"

# Initialize Database & Seed Data
init_db()
seed_sample_data_if_empty()

# Sidebar Setup
st.sidebar.image("https://img.icons8.com/isometric/100/rupee.png", width=64)
st.sidebar.title("📌 Navigation & Settings")

all_fys = get_all_financial_years()
selected_fy = st.sidebar.selectbox("📅 Select Financial Year", ["All FYs"] + all_fys, index=1 if len(all_fys) > 1 else 0)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Indian Financial Year**: Apr 1st - Mar 31st.\n\nData is saved locally in SQLite (`data/expenses.db`).")

# Header Section
st.markdown("<div class='main-header'>Indian FY Expense Tracker & Inflation Analyzer</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Type expenses into an Excel-like grid, auto-categorize expenses, analyze Indian Financial Year trends, track CPI inflation, and manage budgets.</div>", unsafe_allow_html=True)

# Top Metrics Row
df_fy = get_expenses_df(fy=selected_fy)
total_spent = df_fy["amount"].sum() if not df_fy.empty else 0.0
total_txns = len(df_fy) if not df_fy.empty else 0
cat_breakdown = get_category_breakdown(fy=selected_fy)
top_category = cat_breakdown.iloc[0]["category"] if not cat_breakdown.empty else "N/A"
top_cat_amount = cat_breakdown.iloc[0]["Total_Amount"] if not cat_breakdown.empty else 0.0

col1, col2, col3, col4 = st.columns(4)
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
        <div class="metric-label">Logged Entries</div>
        <div class="metric-value">{total_txns}</div>
        <div style="color: #64748b; font-size: 0.8rem;">Transactions recorded</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Top Expense Category</div>
        <div class="metric-value" style="font-size: 1.3rem; color: #f43f5e;">{top_category}</div>
        <div style="color: #64748b; font-size: 0.8rem;">{format_inr_short(top_cat_amount)}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    cpi_rate = 5.6 # Avg Indian CPI
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Indian CPI Benchmark</div>
        <div class="metric-value" style="color: #fbbf24;">{cpi_rate}%</div>
        <div style="color: #64748b; font-size: 0.8rem;">Avg Annual Inflation (RBI)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Content Tabs
tab_manual, tab_itemized, tab_edit_delete, tab_trends, tab_cpi, tab_surge, tab_budget, tab_data = st.tabs([
    "📊 Manual Entry & Excel Grid",
    "📑 Itemized Period Explorer",
    "✏️ Edit & Delete Expenses",
    "📊 Indian FY Trends",
    "📈 Inflation & CPI Analytics",
    "🚨 Expense Surge Detector",
    "🎯 Budgeting & Targets",
    "📝 Database Log & Export"
])

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
        
        today_date = datetime.date.today()
        initial_grid = pd.DataFrame([
            {"date": today_date, "category": "Groceries & Provisions", "description": "D-Mart monthly ration", "amount": 3500.0},
            {"date": today_date, "category": "Dining & Swiggy/Zomato", "description": "Swiggy weekend dinner", "amount": 650.0},
            {"date": today_date, "category": "Transportation & Fuel", "description": "Petrol filling HPCL", "amount": 2000.0}
        ])
        
        grid_edited = st.data_editor(
            initial_grid,
            num_rows="dynamic",
            column_config={
                "date": st.column_config.DateColumn("Date", required=True),
                "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                "description": st.column_config.TextColumn("Description", help="Type description e.g., 'Amul milk', 'Apollo medicine', 'Swiggy'"),
                "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True)
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
                    cnt = insert_expenses(categorized_rows, source="Excel Grid (Auto-Categorized)")
                    st.success(f"🎉 Successfully auto-categorized and saved {cnt} expense entries!")
                    st.rerun()
                else:
                    st.warning("Please enter at least one row with an amount greater than 0.")
                    
        with col_btn2:
            if st.button("💾 Save As Is (No Auto-Categorize)", use_container_width=True):
                valid_rows = [r for r in grid_edited.to_dict("records") if float(r.get("amount", 0.0)) > 0]
                if valid_rows:
                    cnt = insert_expenses(valid_rows, source="Excel Grid Editor")
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
            
            uploaded_excel = st.file_uploader("Choose Excel or CSV File", type=["xlsx", "xls", "csv"], key="excel_uploader")
            if uploaded_excel:
                if st.button("🚀 Import & Auto-Categorize File", type="primary", use_container_width=True):
                    cnt, msg = import_from_excel_or_csv(uploaded_excel)
                    if cnt > 0:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
    with manual_sub_tab3:
        st.markdown("#### Add Single Expense Entry (with Smart Auto-Categorization)")
        m1, m2, m3, m4 = st.columns(4)
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
            
        if st.button("➕ Add Single Expense", type="primary", use_container_width=True):
            if q_amt > 0:
                insert_expenses([{
                    "date": q_date.isoformat(),
                    "category": q_cat,
                    "description": q_desc,
                    "amount": q_amt
                }], source="Quick Manual Entry")
                st.success(f"Added {format_inr(q_amt)} under '{q_cat}'!")
                st.rerun()
            else:
                st.warning("Please enter an amount > 0.")

# ----------------------------------------------------
# TAB 3: ITEMIZED PERIOD EXPLORER
# ----------------------------------------------------
with tab_itemized:
    st.subheader(f"📑 Itemized Expense Explorer ({selected_fy})")
    st.write("Explore itemized line-by-line expenses with customizable period filters (**Monthly, Quarterly, Half-Yearly, Yearly**) alongside cumulative **QTD, H1, H2, and YTD** totals.")
    
    # 1. Cumulative Metrics Overview Cards
    cum_metrics = get_cumulative_metrics(fy=selected_fy if selected_fy != "All FYs" else None)
    
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
    
    # 2. Flexible Period Filtering Controls
    ctrl_col1, ctrl_col2 = st.columns([1, 2])
    with ctrl_col1:
        granularity = st.radio(
            "Select Time Granularity",
            ["Monthly", "Quarterly", "Half-Yearly", "Yearly (Full FY)"],
            horizontal=False
        )
        
    all_df = get_expenses_df(fy=selected_fy)
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
        
        # Category Itemized Summary
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
            filtered_df[["id", "expense_date", "category", "description", "amount", "quarter", "half_year", "source_note"]],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "expense_date": st.column_config.DateColumn("Date"),
                "category": st.column_config.TextColumn("Category"),
                "description": st.column_config.TextColumn("Item / Description"),
                "amount": st.column_config.NumberColumn("Amount (₹)", format="₹ %.2f"),
                "quarter": st.column_config.TextColumn("Quarter"),
                "half_year": st.column_config.TextColumn("Half Year"),
                "source_note": st.column_config.TextColumn("Source")
            },
            use_container_width=True,
            hide_index=True
        )

# ----------------------------------------------------
# TAB 4: EDIT & DELETE EXPENSES MANAGER
# ----------------------------------------------------
with tab_edit_delete:
    st.subheader(f"✏️ Edit & Delete Expenses ({selected_fy})")
    st.write("Easily update existing expense records (dates, categories, amounts, descriptions) or delete single entries and full months.")
    
    edit_mode_tab1, edit_mode_tab2, edit_mode_tab3, edit_mode_tab4 = st.tabs([
        "✏️ Update / Edit Single Entry",
        "🗑️ Delete Single Entry",
        "🔥 Bulk Delete Entire Month",
        "📊 Bulk Spreadsheet Table Editor"
    ])
    
    expenses_df_all = get_expenses_df(fy=selected_fy)
    
    with edit_mode_tab1:
        st.markdown("#### ✏️ Select Entry to Update / Modify")
        if not expenses_df_all.empty:
            expense_options = {}
            for idx, r in expenses_df_all.iterrows():
                label = f"ID #{r['id']} | {r['expense_date']} | {r['category']} | {r['description']} | {format_inr(r['amount'])}"
                expense_options[label] = r
                
            selected_label = st.selectbox("Select Expense Record to Edit", list(expense_options.keys()), key="edit_selector")
            target_rec = expense_options[selected_label]
            
            st.markdown("##### Modify Record Details:")
            e_c1, e_c2, e_c3, e_c4 = st.columns(4)
            with e_c1:
                curr_date = pd.to_datetime(target_rec['expense_date']).date() if target_rec['expense_date'] else datetime.date.today()
                new_date = st.date_input("Date (From Upload/Entry)", curr_date, key=f"edit_d_{target_rec['id']}")
            with e_c2:
                curr_cat = target_rec['category'] if target_rec['category'] in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
                cat_idx = EXPENSE_CATEGORIES.index(curr_cat)
                new_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=cat_idx, key=f"edit_c_{target_rec['id']}")
            with e_c3:
                new_desc = st.text_input("Description", target_rec['description'] or "", key=f"edit_desc_{target_rec['id']}")
            with e_c4:
                new_amt = st.number_input("Amount (₹)", min_value=0.01, value=float(target_rec['amount']), step=50.0, key=f"edit_amt_{target_rec['id']}")
                
            if st.button(f"💾 Save Updates to Entry #{target_rec['id']}", type="primary", use_container_width=True):
                update_df = pd.DataFrame([{
                    "id": target_rec['id'],
                    "expense_date": new_date.isoformat(),
                    "category": new_cat,
                    "description": new_desc,
                    "amount": new_amt
                }])
                cnt = update_expenses_df(update_df)
                st.success(f"🎉 Successfully updated Entry #{target_rec['id']}! FY & Quarters updated strictly from edited date.")
                st.rerun()
        else:
            st.info("No expenses found to edit.")
            
    with edit_mode_tab2:
        st.markdown("#### 🗑️ Delete Single Expense Entry")
        if not expenses_df_all.empty:
            del_options = {}
            for idx, r in expenses_df_all.iterrows():
                label = f"ID #{r['id']} | {r['expense_date']} | {r['category']} | {r['description']} | {format_inr(r['amount'])}"
                del_options[label] = r['id']
                
            del_label = st.selectbox("Select Expense Record to Delete", list(del_options.keys()), key="del_selector")
            target_del_id = del_options[del_label]
            
            st.warning(f"⚠️ Are you sure you want to delete **Entry #{target_del_id}**?")
            if st.button(f"🗑️ Delete Entry #{target_del_id}", type="primary", use_container_width=True):
                delete_expense(target_del_id)
                st.success(f"Deleted Entry #{target_del_id}!")
                st.rerun()
        else:
            st.info("No expenses found to delete.")
            
    with edit_mode_tab3:
        st.markdown("#### 🔥 Delete Entire Month of Expenses")
        if not expenses_df_all.empty and "Month_Year" in expenses_df_all.columns:
            months_avail = expenses_df_all["Month_Year"].unique().tolist()
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                target_del_month = st.selectbox("Select Month to Delete", months_avail, key="del_m_select_tab")
                m_sub = expenses_df_all[expenses_df_all["Month_Year"] == target_del_month]
                st.error(f"⚠️ **Warning**: {target_del_month} contains **{len(m_sub)}** records totaling **{format_inr(m_sub['amount'].sum())}**.")
            with d_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                confirm_m = st.checkbox(f"Confirm permanent deletion of ALL records for {target_del_month}", key="chk_del_m")
                if st.button(f"🔥 Delete All Records for {target_del_month}", type="primary", disabled=not confirm_m, use_container_width=True):
                    n_del = delete_month_expenses(target_del_month)
                    st.success(f"Successfully deleted {n_del} records for {target_del_month}!")
                    st.rerun()
        else:
            st.info("No monthly data available.")
            
    with edit_mode_tab4:
        st.markdown("#### 📊 Bulk Table Editor (Double-click cells to edit)")
        if not expenses_df_all.empty:
            df_edit_copy = expenses_df_all.copy()
            if "expense_date" in df_edit_copy.columns:
                df_edit_copy["expense_date"] = pd.to_datetime(df_edit_copy["expense_date"]).dt.date
                
            edited_grid_df = st.data_editor(
                df_edit_copy[["id", "expense_date", "category", "description", "amount", "financial_year", "quarter", "half_year"]],
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "expense_date": st.column_config.DateColumn("Date", required=True),
                    "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                    "description": st.column_config.TextColumn("Description"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.01, format="₹ %.2f", required=True)
                },
                use_container_width=True,
                hide_index=True,
                key="tab_bulk_editor"
            )
            
            if st.button("💾 Save All Table Edits to Database", type="primary", use_container_width=True):
                u_cnt = update_expenses_df(edited_grid_df)
                st.success(f"Updated {u_cnt} records!")
                st.rerun()

# ----------------------------------------------------
# TAB 3: INDIAN FY TRENDS
# ----------------------------------------------------
with tab_trends:
    st.subheader(f"📊 Expense Trends & Breakdown ({selected_fy})")
    
    if df_fy.empty:
        st.warning("No expense entries found for the selected Financial Year.")
    else:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### Monthly Expense Trajectory (Apr - Mar)")
            monthly_df = get_monthly_trend_df(fy=selected_fy)
            if not monthly_df.empty:
                fig_m = px.bar(
                    monthly_df,
                    x="YearMonth",
                    y="Monthly_Total",
                    color="category",
                    title=f"Monthly Expenses Breakdown ({selected_fy})",
                    labels={"Monthly_Total": "Amount (₹)", "YearMonth": "Month"},
                    template="plotly_dark",
                    barmode="stack"
                )
                fig_m.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                st.plotly_chart(fig_m, use_container_width=True)
                
        with col_chart2:
            st.markdown("#### Category Share Breakdown")
            cat_df = get_category_breakdown(fy=selected_fy)
            if not cat_df.empty:
                fig_p = px.pie(
                    cat_df,
                    values="Total_Amount",
                    names="category",
                    title=f"Share of Expenses by Category ({selected_fy})",
                    hole=0.4,
                    template="plotly_dark"
                )
                fig_p.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                st.plotly_chart(fig_p, use_container_width=True)
                
        st.markdown("---")
        st.markdown("#### Quarterly Breakdown (Indian FY Quarters)")
        st.caption("Q1: Apr-Jun | Q2: Jul-Sep | Q3: Oct-Dec | Q4: Jan-Mar")
        
        q_df = get_quarterly_trend_df(fy=selected_fy)
        if not q_df.empty:
            fig_q = px.bar(
                q_df,
                x="quarter",
                y="Quarterly_Total",
                color="category",
                title=f"Quarterly Expenses ({selected_fy})",
                labels={"Quarterly_Total": "Amount (₹)", "quarter": "Quarter"},
                template="plotly_dark"
            )
            fig_q.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_q, use_container_width=True)

# ----------------------------------------------------
# TAB 4: INFLATION & CPI ANALYTICS
# ----------------------------------------------------
with tab_cpi:
    st.subheader("📈 Personal Expense Growth vs. Indian CPI Inflation")
    st.write("Understand how your personal cost of living is rising compared to official Reserve Bank of India / MOSPI Consumer Price Index benchmarks.")
    
    col_cpi_info, col_cpi_chart = st.columns([1, 1])
    
    with col_cpi_info:
        st.markdown("#### Indian CPI (Combined) Series (Base 2012=100)")
        cpi_df = get_cpi_df()
        st.dataframe(
            cpi_df,
            column_config={
                "Year": st.column_config.NumberColumn("Year", format="%d"),
                "CPI Index (2012=100)": st.column_config.NumberColumn("CPI Index", format="%.1f"),
                "CPI Inflation (%)": st.column_config.NumberColumn("Inflation Rate", format="%.2f %%")
            },
            use_container_width=True,
            hide_index=True
        )
        
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
# TAB 5: EXPENSE SURGE DETECTOR
# ----------------------------------------------------
with tab_surge:
    st.subheader(f"🚨 Expense Surge & Spike Detector ({selected_fy})")
    st.write("Identifies categories where your spending is spiking above trailing averages or exceeding the inflation baseline.")
    
    surge_df = get_surge_categories(fy=selected_fy)
    
    if surge_df.empty:
        st.warning("Insufficient transaction data to compute surge detection.")
    else:
        high_surges = surge_df[surge_df["Surge_%"] > 15]
        
        if not high_surges.empty:
            st.error(f"⚠️ **Alert**: {len(high_surges)} Category(s) are experiencing severe spending surges (>15% jump)!")
        else:
            st.success("✅ Good news! No extreme spending spikes detected for the current period.")
            
        st.markdown("#### Category Surge Analysis Grid")
        st.dataframe(
            surge_df,
            column_config={
                "category": st.column_config.TextColumn("Category"),
                "Total": st.column_config.NumberColumn("Total Spent (₹)", format="₹ %.2f"),
                "Latest_Month_Spend": st.column_config.NumberColumn("Latest Month (₹)", format="₹ %.2f"),
                "Hist_Monthly_Avg": st.column_config.NumberColumn("Historical Avg (₹)", format="₹ %.2f"),
                "Surge_%": st.column_config.NumberColumn("Spike / Surge %", format="%.1f %%")
            },
            use_container_width=True,
            hide_index=True
        )
        
        fig_surge = px.bar(
            surge_df,
            x="category",
            y="Surge_%",
            title=f"Category Surge Percentage vs Historical Average ({selected_fy})",
            color="Surge_%",
            color_continuous_scale="Reds",
            labels={"Surge_%": "Surge %", "category": "Category"},
            template="plotly_dark"
        )
        fig_surge.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
        st.plotly_chart(fig_surge, use_container_width=True)

# ----------------------------------------------------
# TAB 6: BUDGETING & TARGETS
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

    budget_status = get_budget_status(selected_fy if selected_fy != "All FYs" else all_fys[0])
    
    st.markdown("#### Budget Performance Dashboard")
    for idx, row in budget_status.iterrows():
        cat = row["category"]
        spent = row["Actual_Spent"]
        budget = row["Annual_Budget"]
        remaining = row["Remaining"]
        util = row["Utilization_%"]
        
        if budget > 0:
            c1, c2, c3 = st.columns([2, 3, 1])
            with c1:
                st.markdown(f"**{cat}**")
                st.caption(f"Spent: {format_inr(spent)} / Budget: {format_inr(budget)}")
            with c2:
                # Progress bar color logic
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
# TAB 7: DATABASE LOG, EDIT & EXPORT
# ----------------------------------------------------
with tab_data:
    st.subheader("📝 Interactive Database Log, Edit & Delete Manager")
    st.caption("Double-click any cell to edit dates, categories, descriptions, or amounts directly. Click **Save All Edits** to update database.")
    
    expenses_table = get_expenses_df(fy=selected_fy)
    
    if not expenses_table.empty:
        if "expense_date" in expenses_table.columns:
            expenses_table["expense_date"] = pd.to_datetime(expenses_table["expense_date"]).dt.date
            
        edited_db = st.data_editor(
            expenses_table[["id", "expense_date", "category", "description", "amount", "financial_year", "quarter", "half_year", "source_note"]],
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "expense_date": st.column_config.DateColumn("Date (Strictly from Data)", required=True),
                "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                "description": st.column_config.TextColumn("Description"),
                "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
                "financial_year": st.column_config.TextColumn("FY", disabled=True),
                "quarter": st.column_config.TextColumn("Quarter", disabled=True),
                "half_year": st.column_config.TextColumn("Half Year", disabled=True),
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
                st.success(f"🎉 Successfully updated {updated_count} record(s) in database! FY & Quarters recalculated strictly from edited dates.")
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

    st.markdown("---")
    st.subheader("🗑️ Record Deletion & Month Cleanup Tools")
    st.write("Delete individual incorrect entries by ID or permanently remove an entire month's expense data in one click.")
    
    del_tab1, del_tab2 = st.tabs(["🗑️ Bulk Delete Entire Month", "❌ Delete Single Entry by ID"])
    
    with del_tab1:
        all_expenses_for_del = get_expenses_df(fy=selected_fy)
        if not all_expenses_for_del.empty and "Month_Year" in all_expenses_for_del.columns:
            months_to_del = all_expenses_for_del["Month_Year"].unique().tolist()
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                target_month = st.selectbox("Select Month to Delete", months_to_del, key="del_month_select")
                month_records = all_expenses_for_del[all_expenses_for_del["Month_Year"] == target_month]
                m_amt = month_records["amount"].sum()
                m_cnt = len(month_records)
                st.warning(f"⚠️ **Target Month**: **{target_month}** contains **{m_cnt}** transaction(s) totaling **{format_inr(m_amt)}**.")
            with col_m2:
                st.markdown("<br>", unsafe_allow_html=True)
                confirm_del_month = st.checkbox(f"Confirm permanent deletion of ALL records for {target_month}", key="confirm_m_del")
                if st.button(f"🔥 Permanently Delete All Records for {target_month}", type="primary", disabled=not confirm_del_month, use_container_width=True):
                    del_n = delete_month_expenses(target_month)
                    st.success(f"Successfully deleted {del_n} records for {target_month}!")
                    st.rerun()
        else:
            st.info("No month data available to delete.")
            
    with del_tab2:
        col_id1, col_id2 = st.columns(2)
        with col_id1:
            del_id = st.number_input("Enter Expense ID to Delete", min_value=1, step=1, value=1)
            target_row = expenses_table[expenses_table["id"] == del_id] if not expenses_table.empty else pd.DataFrame()
            if not target_row.empty:
                r = target_row.iloc[0]
                st.info(f"Entry #{del_id}: {r['expense_date']} | {r['category']} | {r['description']} | {format_inr(r['amount'])}")
            else:
                st.caption(f"No entry found with ID #{del_id}.")
        with col_id2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🗑️ Delete Entry #{del_id}", type="primary", disabled=target_row.empty, use_container_width=True):
                delete_expense(int(del_id))
                st.success(f"Deleted expense entry #{del_id}!")
                st.rerun()
