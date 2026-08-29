import sys
import os
import io
import datetime
import random

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
    DEBT_CATEGORIES,
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
    get_category_budget,
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
    update_user_age,
    update_user_profile,
    get_all_users,
    delete_user,
    get_db_type,
    check_turso_connection,
    insert_investment,
    get_user_investments_df,
    update_investments_df,
    delete_investment,
    delete_all_investments,
    batch_insert_investments,
    create_family,
    get_family_by_code,
    join_family_by_code,
    get_all_families,
    add_debt,
    get_debts,
    add_debt_payment,
    get_debt_payments,
    update_debt,
    delete_debt,
    record_portfolio_snapshot,
    get_portfolio_snapshots_deltas,
    add_savings_goal,
    get_savings_goals,
    delete_savings_goal,
    add_goal_contribution,
    set_user_recovery_info,
    get_user_recovery_info,
    verify_security_answer,
    set_recovery_otp,
    verify_recovery_otp,
    clear_recovery_otp
)
from debt_simulator import simulate_debt_payoff
from email_utils import send_otp_email
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
    .dashboard-box {
        background-color: #0f172a;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #1e293b;
        box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
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
        .dashboard-box { padding: 12px !important; margin-bottom: 12px !important; }
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
# TURSO REMOTE DB CONNECTION CHECK (once per session)
# ----------------------------------------------------
if "_turso_status_checked" not in st.session_state:
    _turso_ok, _turso_err = check_turso_connection()
    st.session_state["_turso_status_checked"] = True
    st.session_state["_turso_ok"] = _turso_ok
    st.session_state["_turso_err"] = _turso_err

if not st.session_state.get("_turso_ok") and st.session_state.get("_turso_err"):
    _err_detail = st.session_state["_turso_err"]
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
        border: 1px solid #dc2626;
        border-left: 5px solid #ef4444;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    ">
        <span style="font-size: 1.5rem; line-height: 1;">⚠️</span>
        <div>
            <div style="font-weight: 700; color: #fca5a5; font-size: 0.95rem; margin-bottom: 3px;">
                Turso Remote Database Unreachable
            </div>
            <div style="color: #fecaca; font-size: 0.85rem; line-height: 1.5;">
                The app could not connect to the Turso cloud database and has fallen back to
                <strong>local SQLite</strong>. Data entered now will <em>not</em> be synced to the cloud.
            </div>
            <div style="margin-top: 6px; background: rgba(0,0,0,0.3); border-radius: 6px; padding: 6px 10px;
                        font-family: monospace; font-size: 0.78rem; color: #fda4af; word-break: break-all;">
                {_err_detail}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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

            with st.expander("Forgot Password?"):
                st.caption("Recover your account using your email OTP or security question.")
                rec_username = st.text_input("Enter your Username", key="rec_user")
                
                if st.button("Find Account"):
                    info = get_user_recovery_info(rec_username)
                    if not info:
                        st.error("User not found.")
                    else:
                        st.session_state["recovery_user"] = rec_username
                        st.session_state["recovery_info"] = info
                        st.rerun()
                
                if "recovery_user" in st.session_state:
                    info = st.session_state["recovery_info"]
                    r_user = st.session_state["recovery_user"]
                    st.success(f"Account found for {r_user}!")
                    
                    rec_method = st.radio("Choose Recovery Method", ["Answer Security Question", "Send OTP to Email"])
                    
                    if rec_method == "Answer Security Question":
                        if not info["security_question"]:
                            st.warning("No security question is configured for this account.")
                        else:
                            st.write(f"**Question:** {info['security_question']}")
                            ans_attempt = st.text_input("Your Answer", type="password", key="rec_ans")
                            if st.button("Verify Answer"):
                                if verify_security_answer(r_user, ans_attempt):
                                    st.session_state["recovery_verified"] = True
                                    st.success("Answer correct! You can now reset your password.")
                                    st.rerun()
                                else:
                                    st.error("Incorrect answer.")
                    
                    elif rec_method == "Send OTP to Email":
                        if not info["email"]:
                            st.warning("No email is configured for this account.")
                        else:
                            st.write(f"Email will be sent to: **{info['email'][:3]}***@{info['email'].split('@')[-1]}**")
                            col_o1, col_o2 = st.columns([1,1])
                            with col_o1:
                                if st.button("Send OTP"):
                                    otp = str(random.randint(100000, 999999))
                                    if set_recovery_otp(r_user, otp) and send_otp_email(info["email"], otp):
                                        st.success("OTP Sent!")
                                    else:
                                        st.error("Failed to send OTP. Check SMTP settings.")
                            with col_o2:
                                otp_attempt = st.text_input("Enter 6-digit OTP", key="rec_otp")
                                if st.button("Verify OTP"):
                                    if verify_recovery_otp(r_user, otp_attempt):
                                        clear_recovery_otp(r_user)
                                        st.session_state["recovery_verified"] = True
                                        st.success("OTP Verified! You can now reset your password.")
                                        st.rerun()
                                    else:
                                        st.error("Invalid or expired OTP.")
                                        
                    if st.session_state.get("recovery_verified"):
                        new_pwd = st.text_input("New Password", type="password", key="rec_new_pwd")
                        if st.button("Reset Password"):
                            if len(new_pwd) < 4:
                                st.error("Password must be at least 4 characters long.")
                            else:
                                update_user_password(r_user, new_pwd)
                                st.success("Password reset successfully! You can now log in.")
                                # cleanup state
                                del st.session_state["recovery_user"]
                                del st.session_state["recovery_info"]
                                del st.session_state["recovery_verified"]
                                st.rerun()

        with auth_tab2:
            st.caption("Create a new isolated Family Household & become its Family Admin.")
            with st.form("create_family_form"):
                new_fam_name = st.text_input("Family / Household Name", placeholder="e.g. Pulikken Household", key="reg_fam_name")
                fam_admin_user = st.text_input("Admin Username", placeholder="e.g. rovin_admin", key="reg_fam_user")
                fam_admin_fullname = st.text_input("Your Full Name", placeholder="e.g. Rovin Pulikken", key="reg_fam_name_full")
                fam_admin_pwd = st.text_input("Password", type="password", placeholder="••••••••", key="reg_fam_pwd")
                st.markdown("---")
                st.markdown("#### Password Recovery Setup")
                fam_admin_email = st.text_input("Email Address", placeholder="e.g. rovin@example.com", key="reg_fam_email")
                fam_admin_sq = st.selectbox("Security Question", ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"], key="reg_fam_sq")
                fam_admin_sa = st.text_input("Security Answer", type="password", key="reg_fam_sa")
                submit_fam = st.form_submit_button("🏠 Register Family & Become Admin", type="primary", use_container_width=True)
                
                if submit_fam:
                    if not fam_admin_email or not fam_admin_sa:
                        st.error("Email and Security Answer are required for recovery.")
                    else:
                        ok, msg, u_record = create_family(new_fam_name, fam_admin_user, fam_admin_pwd, fam_admin_fullname, fam_admin_email, fam_admin_sq, fam_admin_sa)
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
                st.markdown("---")
                st.markdown("#### Password Recovery Setup")
                join_email = st.text_input("Email Address", placeholder="e.g. priya@example.com", key="join_email")
                join_sq = st.selectbox("Security Question", ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"], key="join_sq")
                join_sa = st.text_input("Security Answer", type="password", key="join_sa")
                submit_join = st.form_submit_button("👨‍👩‍👧 Join Family Workspace", type="primary", use_container_width=True)
                
                if submit_join:
                    if not join_email or not join_sa:
                        st.error("Email and Security Answer are required for recovery.")
                    else:
                        ok, msg, u_record = join_family_by_code(join_code_in, join_user_in, join_pwd_in, join_fullname_in, "Member", join_email, join_sq, join_sa)
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

    # MANDATORY RECOVERY SETUP FOR EXISTING USERS
    if not current_user.get("email") or not current_user.get("security_question"):
        st.warning("⚠️ Action Required: Complete your profile to secure your account.")
        st.info("You must set up password recovery before you can access your dashboard.")
        
        with st.form("mandatory_setup_form"):
            st.markdown("### Password Recovery Setup")
            setup_email = st.text_input("Email Address (Mandatory)", value=current_user.get("email", ""), placeholder="e.g. your_email@example.com")
            setup_sq = st.selectbox("Security Question", ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"])
            setup_sa = st.text_input("Security Answer", type="password")
            
            if st.form_submit_button("Save & Continue", type="primary"):
                if not setup_email or not setup_sa:
                    st.error("Email and Security Answer are mandatory.")
                else:
                    if set_user_recovery_info(current_user["username"], setup_email, setup_sq, setup_sa):
                        st.success("Recovery info saved successfully!")
                        # Re-authenticate to refresh session state
                        updated_user = authenticate_user(current_user["username"], "dummy") # Note: we don't have their password here, so we must just fetch their dict
                        # Actually we can just update the dict directly in session state
                        st.session_state["user"]["email"] = setup_email
                        st.session_state["user"]["security_question"] = setup_sq
                        st.rerun()
                    else:
                        st.error("Failed to save recovery info.")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()
        st.stop() # Block rest of app from loading


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

    # ----------------------------------------------------
    # MAIN NAVIGATION (SIDEBAR)
    # ----------------------------------------------------
    nav_options = [
        "🏠 Dashboard",
        "💸 Transactions",
        "📈 Insights & Analytics",
        "🔮 Wealth & Planning",
        "🎓 Financial Academy",
        "⚙️ Settings & Admin"
    ]
    
    nav_selection = st.sidebar.radio("Navigation", nav_options)
    st.sidebar.markdown("---")

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

    def render_grouped_portfolio_summary(holdings_df):
        # --- GROUPED PORTFOLIO SUMMARY ---
        st.markdown("#### 📂 Grouped Holdings Summary")
        st.caption("Expand categories below to view summarized totals and detailed sub-groupings.")
        
        # Add Recommendation logic based on returns
        def get_rec(ret):
            if pd.isna(ret): return "Hold ⏳"
            if ret <= -15: return "Risk ⚠️"
            elif ret >= 20: return "Sell 🎯"
            elif -5 <= ret <= 10: return "Buy ❇️"
            else: return "Hold ⏳"
            
        _df = holdings_df.copy()
        if "returns_pct" in _df.columns:
            _df["Recommendation"] = _df["returns_pct"].apply(get_rec)
        else:
            _df["Recommendation"] = "Hold ⏳"
        
        # Categorize holdings
        mf_mask = _df["investment_type"].str.lower().str.contains("mutual fund|mf", na=False)
        stock_mask = _df["investment_type"].str.lower() == "equity"
        other_mask = ~(mf_mask | stock_mask)
        
        mf_df = _df[mf_mask]
        stock_df = _df[stock_mask]
        other_df = _df[other_mask]
        
        def render_summary_expander(title_prefix, df, is_mf=False, is_other=False):
            if df.empty:
                return
            total_val = float(df["current_value"].sum())
            total_gain = float(df["unrealized_gain"].sum())
            total_inv = float(df["investment_amount"].sum())
            gain_pct = (total_gain / total_inv * 100) if total_inv > 0 else 0
            
            gain_color = "🟢" if total_gain >= 0 else "🔴"
            expander_title = f"{title_prefix} | Total Value: ₹{total_val:,.2f} | {gain_color} Gain: ₹{total_gain:,.2f} ({gain_pct:+.2f}%)"
            
            # Unified formatting for tables
            col_cfg = {
                "description": st.column_config.TextColumn("Code / Name"),
                "resolved_name": st.column_config.TextColumn("Resolved Name"),
                "platform": st.column_config.TextColumn("Platform"),
                "investment_amount": st.column_config.NumberColumn("Invested", format="₹ %.2f"),
                "current_value": st.column_config.NumberColumn("Current Val", format="₹ %.2f"),
                "unrealized_gain": st.column_config.NumberColumn("Gain/Loss", format="₹ %.2f"),
                "returns_pct": st.column_config.NumberColumn("Return", format="%.2f%%"),
                "Recommendation": st.column_config.TextColumn("Action")
            }
            
            with st.expander(expander_title):
                if is_mf:
                    caps = df["market_cap"].unique()
                    for cap in sorted(caps):
                        cap_df = df[df["market_cap"] == cap]
                        if not cap_df.empty:
                            cap_total = cap_df["current_value"].sum()
                            st.markdown(f"**{cap} (Total: ₹{cap_total:,.2f})**")
                            st.dataframe(cap_df[["description", "resolved_name", "platform", "investment_amount", "current_value", "unrealized_gain", "returns_pct", "Recommendation"]], use_container_width=True, hide_index=True, column_config=col_cfg)
                elif is_other:
                    types = df["investment_type"].unique()
                    for t in sorted(types):
                        t_df = df[df["investment_type"] == t]
                        if not t_df.empty:
                            t_total = t_df["current_value"].sum()
                            st.markdown(f"**{t} (Total: ₹{t_total:,.2f})**")
                            st.dataframe(t_df[["description", "platform", "investment_amount", "current_value", "unrealized_gain", "returns_pct", "Recommendation"]], use_container_width=True, hide_index=True, column_config=col_cfg)
                else:
                    st.dataframe(df[["description", "platform", "investment_amount", "current_value", "unrealized_gain", "returns_pct", "Recommendation"]], use_container_width=True, hide_index=True, column_config=col_cfg)

        render_summary_expander("📈 Mutual Funds", mf_df, is_mf=True)
        render_summary_expander("📊 Stocks (Equity)", stock_df)
        render_summary_expander("🏦 Other Investments", other_df, is_other=True)


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
    inv_df = get_user_investments_df(current_user["username"], family_id=user_family_id)
    total_active_investments = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
    user_age = current_user.get("age", 35)
    cpi_rate = 5.6 # Avg Indian CPI
    
    dash_debts_df = get_debts(family_id=user_family_id)
    total_active_debts = float(dash_debts_df["outstanding_principal"].sum()) if not dash_debts_df.empty else 0.0

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
                return None, f"No valid rows with expense amounts > 0 were found in {file.name}."
                
            records = df[["date", "category", "description", "amount", "visibility"]].to_dict("records")
            records = auto_categorize_records(records)
            df_final = pd.DataFrame(records)
            df_final["transaction_type"] = "Expense"
            return df_final, f"Successfully parsed {len(df_final)} expense rows from {file.name}!"
        except Exception as e:
            return 0, f"Error processing file: {e}"

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"<div style='font-size: 14px; color: gray; margin-bottom: 10px;'>💾 Storage Engine: <b>{get_db_type()}</b></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ----------------------------------------------------
    # Helper: Detect Duplicates in DataFrame
    def detect_and_flag_duplicates(df_import, username, view_mode, family_id):
        existing_expenses = get_expenses_df(fy="All FYs", username=username, view_mode=view_mode, family_id=family_id)
        existing_signatures = set()
        if not existing_expenses.empty:
            for _, row in existing_expenses.iterrows():
                # Signature: (date_str, amount)
                sig = (str(row['expense_date']).strip()[:10], float(row.get('amount', 0)))
                existing_signatures.add(sig)
        
        duplicate_list = []
        import_list = []
        for _, row in df_import.iterrows():
            sig = (str(row.get('date', '')).strip()[:10], float(row.get('amount', 0)))
            is_dup = sig in existing_signatures
            duplicate_list.append(is_dup)
            import_list.append(not is_dup)
            
        df_import["duplicate_warning"] = duplicate_list
        df_import["import"] = import_list
        return df_import

    # ----------------------------------------------------
    # 🏠 DASHBOARD

    # ----------------------------------------------------
    if nav_selection == "🏠 Dashboard":
        st.header("🏠 Dashboard Overview")
        st.write(f"Welcome back, **{current_user['username']}**!")
        
        # Consolidated Dashboard KPI Boxes
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"""
            <div class="dashboard-box">
                <h4 style="margin-top: 0; margin-bottom: 15px; color: #f8fafc; font-size: 1.1rem; border-bottom: 1px solid #334155; padding-bottom: 8px;">📊 Household Expenses Overview</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div class="metric-card">
                        <div class="metric-label">Total Expense ({selected_fy})</div>
                        <div class="metric-value" style="font-size: 1.5rem;">{format_inr_short(total_spent)}</div>
                        <div style="color: #64748b; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{format_inr(total_spent)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Monthly Spend</div>
                        <div class="metric-value" style="color: #38bdf8; font-size: 1.5rem;">{format_inr_short(avg_monthly_spent)}</div>
                        <div style="color: #64748b; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{format_inr(avg_monthly_spent)}/mo</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Logged Entries</div>
                        <div class="metric-value" style="font-size: 1.5rem;">{total_txns}</div>
                        <div style="color: #64748b; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Transactions</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Top Category</div>
                        <div class="metric-value" style="font-size: 1.15rem; color: #f43f5e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.8rem;" title="{top_category}">{top_category}</div>
                        <div style="color: #64748b; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{format_inr_short(top_cat_amount)}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_right:
            st.markdown(f"""
            <div class="dashboard-box">
                <h4 style="margin-top: 0; margin-bottom: 15px; color: #f8fafc; font-size: 1.1rem; border-bottom: 1px solid #334155; padding-bottom: 8px;">👤 Personal Wealth & Profile</h4>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div class="metric-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;">
                        <div>
                            <div class="metric-label">Portfolio Networth</div>
                            <div style="color: #64748b; font-size: 0.78rem;">Active Investments</div>
                        </div>
                        <div class="metric-value" style="color: #10b981; font-size: 1.5rem;">{format_inr_short(total_active_investments)}</div>
                    </div>
                    <div class="metric-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;">
                        <div>
                            <div class="metric-label">Your Age</div>
                            <div style="color: #64748b; font-size: 0.78rem;">Years</div>
                        </div>
                        <div class="metric-value" style="color: #a855f7; font-size: 1.5rem;">{user_age}</div>
                    </div>
                    <div class="metric-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;">
                        <div>
                            <div class="metric-label">CPI Benchmark</div>
                            <div style="color: #64748b; font-size: 0.78rem;">Avg Annual Inflation (RBI)</div>
                        </div>
                        <div class="metric-value" style="color: #fbbf24; font-size: 1.5rem;">{cpi_rate}%</div>
                    </div>
                    <div class="metric-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;">
                        <div>
                            <div class="metric-label">Total Active Debt</div>
                            <div style="color: #64748b; font-size: 0.78rem;">Outstanding Principal</div>
                        </div>
                        <div class="metric-value" style="color: #ef4444; font-size: 1.5rem;">{format_inr_short(total_active_debts)}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Calculate current month metrics
        now = datetime.datetime.now()
        curr_month_str = now.strftime('%Y-%m')
        df = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
        
        if not df.empty and "expense_date" in df.columns:
            df_curr_month = df[df['expense_date'].dt.strftime('%Y-%m') == curr_month_str]
            total_curr_month = df_curr_month['amount'].sum() if not df_curr_month.empty else 0.0
        else:
            df_curr_month = pd.DataFrame()
            total_curr_month = 0.0
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Total Spent ({now.strftime('%B %Y')})", format_inr(total_curr_month))
        
        st.markdown("### Top Spending Categories This Month")
        if not df_curr_month.empty:
            top_cats = df_curr_month.groupby('category')['amount'].sum().sort_values(ascending=False).head(5)
            # Rename for display
            top_cats.index.name = "Category"
            top_cats.name = "Amount"
            st.dataframe(top_cats.reset_index().style.format({"Amount": "₹{:,.2f}"}), use_container_width=True)
        else:
            st.info("No expenses logged for this month yet.")
            
        st.info("👈 Use the **Sidebar Navigation** to manage transactions, view insights, or plan your wealth.")

    # ----------------------------------------------------
    # 💸 TRANSACTIONS & ENTRY
    # ----------------------------------------------------
    elif nav_selection == "💸 Transactions":
        st.header("💸 Transactions")
        st.write("Manage your manual entries, file imports, and edit or delete existing expenses.")
        
        tx_tab1, tx_tab2, tx_tab3 = st.tabs([
            "📊 Add Expenses (Grid)",
            "📂 File Import & Quick Add",
            "✏️ Edit & Delete Existing"
        ])
        
        with tx_tab1:
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
                    
        with tx_tab2:
            st.markdown("### File Import & Quick Add")
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
                st.markdown("#### Upload Unstructured Statement (PDF/CSV) or Standard Excel")
                st.write("Upload your bank/credit card statements. Gemini AI will automatically extract and categorize transactions for your review.")
                
                upload_vis = st.radio("Import Expense/Income Visibility", ["Family", "Private"], horizontal=True, key="upload_vis")
                uploaded_file = st.file_uploader("Choose PDF, Excel, or CSV File", type=["xlsx", "xls", "csv", "pdf"], key="excel_uploader")
                
                pdf_password = ""
                if uploaded_file and uploaded_file.name.lower().endswith('.pdf'):
                    pdf_password = st.text_input("PDF Password (if protected)", type="password", help="Enter password if your bank statement is password protected")

                gemini_api_key = current_user.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
                
                if uploaded_file:
                    if st.button("🚀 Parse & Auto-Categorize Statement", type="primary", use_container_width=True):
                        with st.spinner("🤖 AI is reading your statement. This may take 15-30 seconds..."):
                            # Simple heuristic: if it's explicitly the template name or standard format without 'statement' keyword, try standard import
                            if uploaded_file.name.lower().endswith(('.xlsx', '.csv')) and "statement" not in uploaded_file.name.lower() and "bill" not in uploaded_file.name.lower():
                                try:
                                    df_parsed, msg = import_from_excel_or_csv(uploaded_file, username=current_user["username"], visibility=upload_vis, family_id=user_family_id)
                                    if df_parsed is not None and not df_parsed.empty:
                                        df_parsed = detect_and_flag_duplicates(df_parsed, current_user["username"], view_mode, user_family_id)
                                        st.session_state["parsed_statement_df"] = df_parsed
                                        st.success(f"{msg} Please review them below.")
                                    else:
                                        st.error(msg)
                                except Exception as e:
                                    st.error(f"Error with standard template import: {e}. Try renaming file to include 'statement' to force AI parsing.")
                            else:
                                # Force AI unstructured parsing
                                if not gemini_api_key:
                                    st.error("⚠️ Gemini API Key is required for PDF/Unstructured Statement parsing. Add it in 'My Profile'.")
                                else:
                                    from statement_parser import parse_expense_statement_with_gemini
                                    try:
                                        raw_json = parse_expense_statement_with_gemini(uploaded_file.getvalue(), uploaded_file.name, gemini_api_key, pdf_password)
                                        df_parsed = pd.DataFrame(raw_json)
                                        if not df_parsed.empty:
                                            # Standardize columns if missing
                                            for col in ["date", "description", "amount", "transaction_type", "category"]:
                                                if col not in df_parsed.columns:
                                                    df_parsed[col] = ""
                                                    
                                            # Filter out 'Income' and 'Refund' entirely based on user request
                                            df_parsed["transaction_type"] = df_parsed["transaction_type"].astype(str).str.strip().str.title()
                                            df_parsed["category"] = df_parsed["category"].astype(str).str.strip().str.title()
                                            
                                            df_parsed = df_parsed[df_parsed["transaction_type"] != "Income"]
                                            df_parsed = df_parsed[~df_parsed["category"].str.contains("Refund", case=False, na=False)]
                                            
                                            if not df_parsed.empty:
                                                # Coerce types for data_editor compatibility:
                                                # amount → float64 (NumberColumn), date → ISO string (TextColumn, avoids DateColumn type errors)
                                                df_parsed["amount"] = pd.to_numeric(df_parsed["amount"], errors="coerce").fillna(0.0)
                                                df_parsed["date"] = pd.to_datetime(df_parsed["date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna(str(datetime.date.today()))
                                                
                                                df_parsed = detect_and_flag_duplicates(df_parsed, current_user["username"], view_mode, user_family_id)
                                                
                                                st.session_state["parsed_statement_df"] = df_parsed
                                                st.rerun()
                                            else:
                                                st.warning("No expense transactions found (or all were filtered out as Income/Refunds).")
                                        else:
                                            st.warning("No transactions found in the document.")
                                    except Exception as e:
                                        st.error(f"Failed to parse statement: {e}")
                                        
                if "parsed_statement_df" in st.session_state:
                    st.markdown("### 🔍 Review & Confirm Transactions")
                    st.info("Please review the extracted transactions, uncheck any duplicates you don't want to save, correct categories/amounts, and click Save.")
                    
                    edited_df = st.data_editor(
                        st.session_state["parsed_statement_df"],
                        num_rows="dynamic",
                        column_config={
                            "import": st.column_config.CheckboxColumn("Import?", default=True),
                            "duplicate_warning": st.column_config.CheckboxColumn("Duplicate?", disabled=True, help="Checked if a record with the same Date + Amount already exists."),
                            "date": st.column_config.TextColumn("Date (YYYY-MM-DD)", help="Edit as YYYY-MM-DD"),
                            "description": st.column_config.TextColumn("Description"),
                            "amount": st.column_config.NumberColumn("Amount", required=True),
                            "transaction_type": st.column_config.SelectboxColumn("Type", options=["Expense", "Income"], required=True),
                            "category": st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES + ["Salary", "Refund", "Interest"], required=True)
                        },
                        use_container_width=True,
                        key="statement_editor"
                    )
                    
                    col_save1, col_save2 = st.columns(2)
                    with col_save1:
                        if st.button("💾 Confirm & Save to Database", type="primary", use_container_width=True):
                            records = edited_df.to_dict('records')
                            valid_records = []
                            for r in records:
                                if r.get('import', True):
                                    t_type = str(r.get('transaction_type', '')).strip().lower()
                                    if t_type != 'income':
                                        r['visibility'] = upload_vis
                                        # Force positive amount just in case
                                        try:
                                            r['amount'] = abs(float(str(r.get('amount', 0)).replace(',', '')))
                                        except:
                                            pass
                                        valid_records.append(r)
                            
                            try:
                                if valid_records:
                                    cnt = insert_expenses(valid_records, source=f"AI Import ({uploaded_file.name})", username=current_user["username"], visibility=upload_vis, family_id=user_family_id)
                                    st.success(f"Successfully saved {cnt} transactions!")
                                else:
                                    st.warning("No valid expense transactions to save (Income entries are ignored).")
                                del st.session_state["parsed_statement_df"]
                                import time; time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Database error: {e}")
                    with col_save2:
                        if st.button("❌ Cancel", type="secondary", use_container_width=True):
                            del st.session_state["parsed_statement_df"]
                            st.rerun()
                            
        st.divider()
        if True:
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
    # TAB 3: EDIT & DELETE EXPENSES
    # ----------------------------------------------------
        with tx_tab3:
            st.subheader(f"✏️ Edit & Delete Expenses ({selected_fy})")
            st.write("Modify existing entries, re-assign categories, edit amounts, or delete records.")
            
            expenses_df_all = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
            
            edit_mode_tab1, edit_mode_tab2, edit_mode_tab3, edit_mode_tab4, edit_mode_tab5 = st.tabs([
                "📝 Inline Table Editor",
                "🔍 Search & Edit Single Record",
                "🗑️ Delete Single Record",
                "🧹 Clear Entire Month Data",
                "🕵️ Detect Duplicates"
            ])
            
            with edit_mode_tab1:
                if expenses_df_all.empty:
                    st.warning(f"No expense records available to edit or delete in {selected_fy}.")
                else:
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
                if expenses_df_all.empty:
                    st.warning(f"No expense records available to edit or delete in {selected_fy}.")
                else:
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
                if expenses_df_all.empty:
                    st.warning(f"No expense records available to edit or delete in {selected_fy}.")
                else:
                    st.markdown("#### Delete Single Record by ID")
                    del_id_select = st.selectbox("Select Expense ID to Delete", record_ids, key="single_del_id_select")
                    del_target = expenses_df_all[expenses_df_all["id"] == del_id_select].iloc[0]
                    
                    st.info(f"Target Record #{del_id_select}: {del_target['expense_date']} | {del_target['category']} | {del_target['description']} | {format_inr(del_target['amount'])}")
                    
                    if st.button(f"🗑️ Permanently Delete Record #{del_id_select}", type="primary", use_container_width=True):
                        delete_expense(int(del_id_select))
                        st.success(f"Deleted record #{del_id_select}!")
                        st.rerun()
                        
            with edit_mode_tab4:
                if expenses_df_all.empty:
                    st.warning(f"No expense records available to edit or delete in {selected_fy}.")
                else:
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

            with edit_mode_tab5:
                st.markdown("#### 🕵️ Detect Duplicates")
                st.write("Find and delete duplicate expense entries across **ALL Financial Years** (exact same Date and Amount).")
                
                # Fetch ALL expenses across ALL years globally
                all_time_expenses_df = get_expenses_df(fy="All FYs", username=current_user["username"], view_mode=view_mode)
                
                if not all_time_expenses_df.empty:
                    # Find duplicate groups
                    dup_counts = all_time_expenses_df.groupby(['expense_date', 'amount']).size().reset_index(name='count')
                    dup_groups = dup_counts[dup_counts['count'] > 1]
                    
                    if dup_groups.empty:
                        st.success("No duplicate entries found across any Financial Year!")
                    else:
                        st.warning(f"Found {len(dup_groups)} groups of duplicate entries.")
                        
                        # Join back to get full details of duplicates
                        merged = pd.merge(all_time_expenses_df, dup_groups, on=['expense_date', 'amount'])
                        merged = merged.sort_values(['expense_date', 'amount', 'id'])
                        
                        st.write("By default, all redundant records are pre-selected for deletion (keeping one original record from each group):")
                        
                        # Smart selection: mark all but the first in each group for deletion
                        merged['Delete'] = merged.duplicated(subset=['expense_date', 'amount'], keep='first')
                        
                        edited_dups = st.data_editor(
                            merged[['Delete', 'id', 'expense_date', 'category', 'description', 'amount', 'source_note']],
                            num_rows="fixed",
                            column_config={
                                "Delete": st.column_config.CheckboxColumn("🗑️ Delete", default=False),
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "expense_date": st.column_config.DateColumn("Date", disabled=True),
                                "category": st.column_config.TextColumn("Category", disabled=True),
                                "description": st.column_config.TextColumn("Description", disabled=True),
                                "amount": st.column_config.NumberColumn("Amount", format="₹ %.2f", disabled=True),
                                "source_note": st.column_config.TextColumn("Source", disabled=True)
                            },
                            use_container_width=True,
                            hide_index=True,
                            key="dup_editor"
                        )
                        
                        to_delete_ids = edited_dups[edited_dups['Delete'] == True]['id'].tolist()
                        if len(to_delete_ids) > 0:
                            if st.button(f"🗑️ Delete Selected ({len(to_delete_ids)} records)", type="primary"):
                                for d_id in to_delete_ids:
                                    delete_expense(int(d_id))
                                st.success(f"Successfully deleted {len(to_delete_ids)} duplicate records!")
                                st.rerun()
                else:
                    st.info("No records to check for duplicates.")


        # ----------------------------------------------------
        # 📈 INSIGHTS & ANALYTICS
        # ----------------------------------------------------
    elif nav_selection == "📈 Insights & Analytics":
        st.header("📈 Insights & Analytics")
        ia_tab1, ia_tab2, ia_tab3, ia_tab4 = st.tabs([
            "📑 Itemized Explorer", 
            "📊 FY Trends", 
            "📈 Inflation & CPI", 
            "🚨 Anomaly Detection"
        ])

    # ----------------------------------------------------
    # TAB 2: ITEMIZED PERIOD EXPLORER
    # ----------------------------------------------------
        with ia_tab1:
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
        # TAB 4: INDIAN FY TRENDS
        # ----------------------------------------------------
        with ia_tab2:
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
        with ia_tab3:
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
        with ia_tab4:
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
        # 🔮 WEALTH & PLANNING
        # ----------------------------------------------------
    elif nav_selection == "🔮 Wealth & Planning":
    # ----------------------------------------------------
    # TAB 7: BUDGETING & INVESTMENTS
    # ----------------------------------------------------
        wp_tab1, = st.tabs(["🎯 Budget & Wealth"])
        with wp_tab1:
            st.subheader(f"🎯 Budgeting, Investments & Active Portfolio ({selected_fy})")
            
        subtab_budget, subtab_invest, subtab_holdings, subtab_debts, subtab_advisor = st.tabs([
            "🎯 Category Budget Planner & Performance",
            "📈 Investment & Wealth Portfolio Planner",
            "💼 Active Investment Portfolio & Holdings Tracker",
            "🏦 Debt & Liabilities Management",
            "💡 Smart Advisor & Tax Planner"
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

            # Calculate the sum of user-entered categories (excluding auto-calculated Investments)
            other_cats = [c for c in EXPENSE_CATEGORIES if c != "Insurance & Investments"]
            current_entered_sum = sum([float(st.session_state.get("budget_dict", {}).get(c, 0.0)) for c in other_cats])
            
            # Fallback if empty
            if current_entered_sum == 0:
                current_entered_sum = max(50000.0, float(round(total_hist_avg_monthly, -3))) if total_hist_avg_monthly > 0 else 75000.0
                
            def autosave_all_budgets():
                t_others = sum([float(st.session_state["budget_dict"].get(c, 0.0)) for c in other_cats])
                st.session_state["budget_dict"]["Insurance & Investments"] = max(0.0, float(monthly_income_input - t_others))
                records = [
                    {"category": c, "monthly_limit": val, "annual_limit": val * 12.0}
                    for c, val in st.session_state["budget_dict"].items()
                ]
                batch_set_category_budgets(target_fy_clean, records, family_id=user_family_id)

            t_col_inc, t_col1, t_col2, t_col3 = st.columns([1.5, 2, 1.2, 1.2])
            with t_col_inc:
                monthly_income_input = st.number_input(
                    "💵 Expected Monthly Income (₹)",
                    min_value=0.0,
                    value=100000.0,
                    step=5000.0,
                    help="Your total expected monthly income. Used to calculate target savings and investments."
                )
            with t_col1:
                target_monthly_input = st.number_input(
                    "💰 Target Total Household Monthly Spend (₹)",
                    min_value=1000.0,
                    value=float(current_entered_sum),
                    step=5000.0,
                    help="Sum of all your category limits. Edit this to auto-scale your categories proportionally."
                )
                
            # If user manually edited the Target Total, auto-scale the categories
            if "budget_dict" in st.session_state and target_monthly_input != current_entered_sum and current_entered_sum > 0:
                scale_factor = target_monthly_input / current_entered_sum
                for c in other_cats:
                    st.session_state["budget_dict"][c] = round(float(st.session_state["budget_dict"][c]) * scale_factor, 2)
                autosave_all_budgets()
                st.rerun()

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
                    if c != "Insurance & Investments":
                        val = round(float(r["hist_monthly_avg"]), 2)
                        st.session_state["budget_dict"][c] = val
                autosave_all_budgets()
                st.success("⚡ Filled all category limits with past monthly averages and Auto-Saved!")
                st.rerun()

            if btn_apply_prop:
                prop_target = monthly_income_input * 0.80  # 80% of income for expenses
                prop_df = get_suggested_budgets(fy=target_fy_clean, username=current_user["username"], view_mode=view_mode, target_total_monthly=prop_target, family_id=user_family_id)
                for idx, r in prop_df.iterrows():
                    c = r["category"]
                    if c == "Insurance & Investments":
                        st.session_state["budget_dict"][c] = round(float(monthly_income_input * 0.20), 2)
                    else:
                        st.session_state["budget_dict"][c] = round(float(r["suggested_monthly"]), 2)
                autosave_all_budgets()
                st.success(f"🎯 Auto-allocated and Auto-Saved! Set Investments to 20% ({format_inr(monthly_income_input * 0.20)}) and distributed the remaining 80% to expenses.")
                st.rerun()

            # ------------------------------------------------
            # SECTION 2: INTERACTIVE CATEGORY BUDGET ADJUSTER (+/-)
            # ------------------------------------------------
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### ⚙️ Category Budget Planner & Interactive Adjuster (+ / -)")
            st.caption("Use the quick `+` and `-` modifier buttons to fine-tune each category limit up or down.")

            hist_avg_map = dict(zip(suggested_base_df["category"], suggested_base_df["hist_monthly_avg"]))

            for cat in other_cats:
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
                        autosave_all_budgets()
                        st.rerun()
                    if b_minus5p:
                        st.session_state["budget_dict"][cat] = max(0.0, round(current_val * 0.95, 2))
                        autosave_all_budgets()
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
                    if new_val != st.session_state["budget_dict"][cat]:
                        st.session_state["budget_dict"][cat] = round(new_val, 2)
                        autosave_all_budgets()
                        st.rerun()

                with cat_col4:
                    b_plus1k = st.button("➕ ₹1k", key=f"add_1k_{cat}", help=f"Increase {cat} budget by ₹1,000")
                    b_plus5p = st.button("➕ 5%", key=f"add_5p_{cat}", help=f"Increase {cat} budget by 5%")
                    if b_plus1k:
                        st.session_state["budget_dict"][cat] = round(current_val + 1000.0, 2)
                        autosave_all_budgets()
                        st.rerun()
                    if b_plus5p:
                        st.session_state["budget_dict"][cat] = round(current_val * 1.05, 2)
                        autosave_all_budgets()
                        st.rerun()

                with cat_col5:
                    ann_val = st.session_state["budget_dict"][cat] * 12.0
                    st.markdown(f"**{format_inr_short(ann_val)}**")
                    st.caption("Annual Cap")

                st.markdown("<hr style='margin: 6px 0; border-color: #334155;'>", unsafe_allow_html=True)
            
            # Dynamic calculation for Insurance & Investments
            cat = "Insurance & Investments"
            total_others = sum([float(st.session_state["budget_dict"].get(c, 0.0)) for c in other_cats])
            calc_inv = max(0.0, float(monthly_income_input - total_others))
            st.session_state["budget_dict"][cat] = calc_inv

            # Render it special
            cat_col1, cat_col2, cat_col3, cat_col4, cat_col5 = st.columns([2.5, 1.8, 2.5, 1.8, 1.8])
            with cat_col1:
                st.markdown(f"**{cat}** (Auto-Calculated)")
                st.caption(f"Income - All Other Expenses")
            with cat_col2:
                 st.write("")
            with cat_col3:
                 st.markdown(f"**{format_inr(calc_inv)}**")
            with cat_col4:
                 st.write("")
            with cat_col5:
                 st.markdown(f"**{format_inr_short(calc_inv * 12.0)}**")
                 st.caption("Annual Cap")
                 
            st.markdown("<hr style='margin: 6px 0; border-color: #334155;'>", unsafe_allow_html=True)

            if monthly_income_input < total_others:
                 st.warning("⚠️ Warning: Your allocated expenses exceed your expected monthly income. Please reduce your category limits.")

            # ------------------------------------------------
            # 🎯 GOAL-BASED SAVINGS
            # ------------------------------------------------
            st.markdown("### 🎯 Goal-Based Savings")
            st.caption("Track your cash savings against specific life goals (e.g. Child's Education, Downpayment).")
            
            savings_goals_df = get_savings_goals(family_id=user_family_id)
            if not savings_goals_df.empty:
                for _, goal in savings_goals_df.iterrows():
                    pct = min(1.0, goal["current_saved"] / goal["target_amount"]) if goal["target_amount"] > 0 else 0.0
                    st.markdown(f"**{goal['goal_name']}**")
                    st.progress(pct)
                    sc1, sc2, sc3 = st.columns([2, 1, 1])
                    with sc1:
                        st.caption(f"Saved: {format_inr_short(goal['current_saved'])} / {format_inr_short(goal['target_amount'])} ({int(pct*100)}%)")
                    with sc2:
                        if goal["target_date"]:
                            st.caption(f"Target: {goal['target_date']}")
                    with sc3:
                        with st.popover("⚙️ Manage Goal"):
                            c_amt = st.number_input("Log Contribution", min_value=0.0, step=1000.0, key=f"contrib_{goal['id']}")
                            if st.button("➕ Add Funds", key=f"btn_add_{goal['id']}"):
                                if add_goal_contribution(goal['id'], user_family_id, c_amt):
                                    st.success(f"Added {format_inr(c_amt)} to {goal['goal_name']}")
                                    st.rerun()
                            st.markdown("---")
                            if st.button("🚨 Delete Goal", key=f"btn_del_{goal['id']}"):
                                if delete_savings_goal(goal['id'], user_family_id):
                                    st.success("Deleted goal!")
                                    st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info("No savings goals active. Create one below!")
                
            with st.expander("➕ Create New Savings Goal"):
                with st.form("new_goal_form"):
                    g_name = st.text_input("Goal Name (e.g., Child's Education)")
                    g_target = st.number_input("Target Amount", min_value=0.0, step=10000.0)
                    g_date = st.date_input("Target Date")
                    g_contrib = st.number_input("Planned Monthly Contribution (Optional)", min_value=0.0, step=1000.0)
                    if st.form_submit_button("Create Goal"):
                        if g_name and g_target > 0:
                            if add_savings_goal(user_family_id, g_name, g_target, str(g_date), g_contrib):
                                st.success("Goal created!")
                                st.rerun()
                        else:
                            st.error("Please provide a valid name and target amount.")
            
            st.markdown("<hr style='margin: 10px 0; border-color: #334155;'>", unsafe_allow_html=True)

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
            
            st.success("✅ **Auto-Save Enabled**: All changes you make above are instantly saved to the database.")

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
            inv_df = get_user_investments_df(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)
            total_active_investments = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0

            inv_col1, inv_col2, inv_col3, inv_col4 = st.columns([1, 1.2, 1.5, 1.8])
            with inv_col1:
                u_age = st.number_input("👤 Your Age", min_value=18, max_value=85, value=current_user.get("age", 35), step=1, key="invest_user_age")
                if u_age != current_user.get("age", 35):
                    from database import update_user_age
                    if update_user_age(current_user["username"], u_age):
                        st.session_state["user"]["age"] = u_age
            with inv_col2:
                st.write("") # vertical spacing to align toggle
                st.write("")
                use_portfolio_networth = st.toggle("Link Networth", value=True, help="Automatically link your total active investment valuation here.")
            with inv_col3:
                if use_portfolio_networth:
                    u_savings = total_active_investments
                    st.metric("💰 Linked Portfolio Networth", format_inr_short(u_savings))
                else:
                    # Need a separate key to preserve manual state
                    u_savings = st.number_input("💰 Your Networth (₹)", min_value=0.0, value=total_active_investments, step=50000.0, format="%.2f", key="invest_user_savings_manual")
            with inv_col4:
                u_sip_budget = st.number_input(
                    "💵 Monthly recurring Investments (₹)",
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

            st.markdown("#### 💸 Additional Planner Assumptions")
            st.caption("Factor in extra expenses before retirement. These will drain your accumulating corpus.")
            add_col1, add_col2 = st.columns(2)
            with add_col1:
                default_expenses = pd.DataFrame([{"Expense Description": "", "Amount (₹)": 0.0, "Age": min(ret_age, u_age + 5)}])
                one_time_exp_df = st.data_editor(default_expenses, num_rows="dynamic", key="one_time_exp_editor", use_container_width=True, hide_index=True)
            with add_col2:
                add_recurring_exp = st.number_input(
                    "Additional Monthly Recurring Expenses (₹)", 
                    min_value=0.0, 
                    value=0.0, 
                    step=5000.0, 
                    help="Extra monthly expenses you want to plan for (e.g., ongoing medical costs) during the accumulation phase."
                )

            one_time_expenses_list = []
            for _, row in one_time_exp_df.iterrows():
                raw_amt = row.get("Amount (₹)", 0.0)
                raw_age = row.get("Age", u_age)
                
                try:
                    amt = float(raw_amt) if raw_amt is not None and str(raw_amt).strip() != "" else 0.0
                except (ValueError, TypeError):
                    amt = 0.0
                
                try:
                    age_val = int(raw_age) if raw_age is not None and str(raw_age).strip() != "" else u_age
                except (ValueError, TypeError):
                    age_val = u_age

                if amt > 0:
                    one_time_expenses_list.append({"amount": amt, "age": age_val})

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
                        cagr_decimal=cagr_decimal,
                        one_time_expenses=one_time_expenses_list,
                        additional_monthly_expense=add_recurring_exp
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
                
                # Portfolio Snapshot Deltas
                deltas = get_portfolio_snapshots_deltas(user_family_id, tot_current)
                
                st.markdown("#### ⏳ Historical Growth (vs Live Market)")
                dh1, dh2, dh3, dh4 = st.columns(4)
                
                def format_delta(d):
                    val = d["value"]
                    pct = d["percent"]
                    prefix = "+" if val >= 0 else ""
                    return f"{prefix}{format_inr_short(val)} ({prefix}{pct:.2f}%)"
                
                with dh1:
                    st.metric("Since Last Sync", "", delta=format_delta(deltas["previous_sync"]), delta_color="normal")
                with dh2:
                    st.metric("7-Day Change", "", delta=format_delta(deltas["weekly"]), delta_color="normal")
                with dh3:
                    st.metric("30-Day Change", "", delta=format_delta(deltas["monthly"]), delta_color="normal")
                with dh4:
                    st.metric("1-Year Change", "", delta=format_delta(deltas["yearly"]), delta_color="normal")

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
                            
                            # Record snapshot of the new total value
                            new_tot = float(updated_df["current_value"].sum())
                            record_portfolio_snapshot(user_family_id, new_tot)
                            
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
                
                # --- GROUPED PORTFOLIO SUMMARY ---
                render_grouped_portfolio_summary(holdings_df)
                
                
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
                        debts_df = get_debts(family_id=user_family_id)
                        goals_df = get_savings_goals(family_id=user_family_id)
                        portfolio_ai = generate_ai_portfolio_suggestions(holdings_df, current_user, debts_df, goals_df)

                    st.success("🎉 Portfolio AI Review Complete!")
                    st.info(portfolio_ai.get("summary", ""))

                    for rec in portfolio_ai.get("recommendations", []):
                        st.markdown(f"#### {rec.get('title', 'Recommendation')}")
                        st.markdown(f"**Observation**: {rec.get('observation', '')}")
                        st.markdown(f"**Suggestion**: {rec.get('suggestion', '')}")
                        st.markdown("<hr style='margin: 8px 0; border-color: #334155;'>", unsafe_allow_html=True)

            else:
                st.info("💡 No active holdings recorded yet. Use the form above to add your first investment asset!")

        with subtab_debts:
            st.caption("Track your liabilities, outstanding principal, interest rates, and loan tenures.")
            
            # Fetch all debts for the family
            debts_df = get_debts(family_id=user_family_id)
            
            # ------------------------------------------------
            # DEBT SUMMARY DASHBOARD
            # ------------------------------------------------
            if not debts_df.empty:
                total_outstanding = debts_df["outstanding_principal"].sum()
                total_monthly_emi = debts_df["monthly_emi"].sum()
                
                st.markdown("""
                <div style="background-color: #1e293b; padding: 14px 18px; border-radius: 8px; border-left: 4px solid #ef4444; margin-bottom: 15px;">
                    <div style="font-weight: 600; color: #ef4444; font-size: 0.95rem;">🏦 Total Debt & Liabilities Overview</div>
                </div>
                """, unsafe_allow_html=True)
                
                sum_c1, sum_c2, sum_c3 = st.columns(3)
                with sum_c1:
                    st.metric("Total Outstanding Debt", format_inr(total_outstanding))
                with sum_c2:
                    st.metric("Total Monthly EMI", format_inr(total_monthly_emi))
                with sum_c3:
                    st.metric("Active Loans", str(len(debts_df)))
                    
                st.markdown("<hr>", unsafe_allow_html=True)
                
            # ------------------------------------------------
            # ADD NEW DEBT FORM
            # ------------------------------------------------
            with st.expander("➕ Add New Debt / Liability", expanded=debts_df.empty):
                with st.form("add_debt_form"):
                    st.markdown("#### Enter Loan / Debt Details")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        new_debt_name = st.text_input("Debt / Loan Name", placeholder="e.g. HDFC Home Loan")
                        new_debt_cat = st.selectbox("Category", DEBT_CATEGORIES)
                    with dc2:
                        new_principal = st.number_input("Total Principal Amount", min_value=0.0, step=10000.0)
                        new_start_date = st.date_input("Start Date", value=datetime.date.today())
                        
                    dc3, dc4, dc5 = st.columns(3)
                    with dc3:
                        new_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
                    with dc4:
                        new_tenure = st.number_input("Tenure (Months)", min_value=1, step=12)
                    with dc5:
                        new_emi = st.number_input("Monthly EMI / Payment", min_value=0.0, step=1000.0)
                        
                    if st.form_submit_button("💾 Save Liability", type="primary", use_container_width=True):
                        if new_debt_name and new_principal > 0:
                            # Auto-sync to Budget Planner as Fixed Expense
                            if new_emi > 0:
                                if "budget_dict" in st.session_state:
                                    st.session_state["budget_dict"][new_debt_cat] = st.session_state["budget_dict"].get(new_debt_cat, 0.0) + new_emi
                                
                                # Instantly save this new budget to DB so it persists in the Budget Planner Tab
                                existing_val = 0.0
                                b_df = get_category_budget(target_fy_clean, new_debt_cat, family_id=user_family_id)
                                if not b_df.empty:
                                    existing_val = float(b_df.iloc[0]["monthly_limit"])
                                
                                new_limit = existing_val + new_emi
                                set_category_budget(target_fy_clean, new_debt_cat, new_limit, new_limit * 12, family_id=user_family_id)

                            add_debt(new_debt_name, new_debt_cat, new_principal, new_principal, new_rate, new_emi, new_tenure, str(new_start_date), user_family_id)
                            st.success(f"Successfully added {new_debt_name} to your liabilities and synced its EMI ({format_inr(new_emi)}) to the '{new_debt_cat}' Budget Planner!")
                            st.rerun()
                        else:
                            st.error("Please provide a valid Debt Name and Principal Amount.")

            # ------------------------------------------------
            # DEBT PORTFOLIO & PAYMENT LOGGING
            # ------------------------------------------------
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📊 Active Debt Portfolio")
            
            if not debts_df.empty:
                for idx, row in debts_df.iterrows():
                    did = row["id"]
                    dname = row["debt_name"]
                    dcat = row["debt_category"]
                    outstanding = row["outstanding_principal"]
                    total = row["total_principal"]
                    emi = row["monthly_emi"]
                    rate = row["interest_rate"]
                    
                    paid_pct = 0.0
                    if total > 0:
                        paid_pct = max(0.0, min(100.0, ((total - outstanding) / total) * 100))
                        
                    with st.container():
                        st.markdown(f"""
                        <div class="dashboard-box" style="margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                                <div>
                                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{dname}</div>
                                    <div style="font-size: 0.85rem; color: #94a3b8;">{dcat} • {rate}% Interest</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 1.2rem; font-weight: 700; color: #ef4444;">{format_inr(outstanding)}</div>
                                    <div style="font-size: 0.85rem; color: #94a3b8;">Outstanding</div>
                                </div>
                            </div>
                            <div style="margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
                                    <span style="color: #64748b;">Principal Paid: {paid_pct:.1f}%</span>
                                    <span style="color: #64748b;">Total: {format_inr(total)}</span>
                                </div>
                                <div style="width: 100%; background-color: #334155; border-radius: 4px; height: 8px;">
                                    <div style="width: {paid_pct}%; background-color: #10b981; height: 100%; border-radius: 4px;"></div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander(f"💸 Log EMI/Payment for {dname}"):
                            with st.form(f"pay_debt_{did}"):
                                pc1, pc2 = st.columns(2)
                                with pc1:
                                    pay_date = st.date_input("Payment Date", value=datetime.date.today(), key=f"pd_{did}")
                                    pay_principal = st.number_input("Principal Portion", min_value=0.0, step=100.0, key=f"pp_{did}")
                                with pc2:
                                    pay_interest = st.number_input("Interest Portion", min_value=0.0, step=100.0, key=f"pi_{did}")
                                
                                if st.form_submit_button("Record Payment", type="primary"):
                                    if pay_principal > 0 or pay_interest > 0:
                                        add_debt_payment(did, str(pay_date), pay_principal, pay_interest, user_family_id)
                                        st.success(f"Payment recorded! Outstanding principal reduced by {format_inr(pay_principal)}.")
                                        st.rerun()
                                    else:
                                        st.error("Please enter an amount.")
                                        
                        # Show payment history
                        pay_df = get_debt_payments(did)
                        if not pay_df.empty:
                            with st.expander("📜 Payment History"):
                                st.dataframe(pay_df[["payment_date", "principal_paid", "interest_paid"]], use_container_width=True, hide_index=True)
                                
                        with st.expander(f"✏️ Edit / Delete {dname}"):
                            with st.form(f"edit_debt_{did}"):
                                st.markdown("### Update Debt Details")
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    e_dname = st.text_input("Debt Name", value=dname, key=f"edn_{did}")
                                    e_dcat = st.selectbox("Category", DEBT_CATEGORIES, index=DEBT_CATEGORIES.index(dcat) if dcat in DEBT_CATEGORIES else 0, key=f"edc_{did}")
                                    e_rate = st.number_input("Interest Rate (%)", value=float(rate), min_value=0.0, step=0.1, key=f"edr_{did}")
                                    e_tenure = st.number_input("Tenure (Months)", value=int(row["tenure_months"]), min_value=1, step=1, key=f"edt_{did}")
                                with ec2:
                                    e_total = st.number_input("Total Principal", value=float(total), min_value=0.0, step=100.0, key=f"edtp_{did}")
                                    e_out = st.number_input("Outstanding Principal", value=float(outstanding), min_value=0.0, step=100.0, key=f"edop_{did}")
                                    e_emi = st.number_input("Monthly EMI", value=float(emi), min_value=0.0, step=100.0, key=f"edemi_{did}")
                                    e_start = st.date_input("Start Date", value=datetime.datetime.strptime(row["start_date"], "%Y-%m-%d").date() if row["start_date"] else datetime.date.today(), key=f"edsd_{did}")
                                    
                                uc1, uc2 = st.columns(2)
                                with uc1:
                                    if st.form_submit_button("Update Liability", type="primary"):
                                        if update_debt(did, e_dname, e_dcat, e_total, e_out, e_rate, e_emi, e_tenure, str(e_start), user_family_id):
                                            st.success("Liability updated successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update.")
                                with uc2:
                                    if st.form_submit_button("🚨 Delete Liability"):
                                        if delete_debt(did, user_family_id):
                                            st.success("Liability deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete.")

                st.markdown("---")
                st.markdown("### 🔮 Debt Payoff Simulator")
                st.caption("Simulate your payoff timeline and see how much interest you can save.")
                
                sim_col1, sim_col2 = st.columns(2)
                with sim_col1:
                    strategy = st.selectbox(
                        "Payoff Strategy",
                        ["Avalanche (Highest Interest First) - mathematically optimal", 
                         "Snowball (Lowest Balance First) - psychological wins"]
                    )
                with sim_col2:
                    sim_budget = st.number_input(
                        "Total Monthly Debt Budget",
                        value=float(total_monthly_emi),
                        min_value=float(total_monthly_emi),
                        step=1000.0,
                        help="Must be at least the sum of all your minimum EMIs."
                    )
                
                if st.button("Run Simulation 🚀"):
                    total_months, total_interest, timeline_df = simulate_debt_payoff(debts_df, strategy, sim_budget)
                    
                    st.markdown("#### Simulation Results")
                    r_col1, r_col2, r_col3 = st.columns(3)
                    r_col1.metric("Months to Debt Free", f"{total_months} months")
                    r_col2.metric("Total Interest Paid", format_inr_short(total_interest))
                    
                    from datetime import datetime
                    from dateutil.relativedelta import relativedelta
                    payoff_date = datetime.now() + relativedelta(months=total_months)
                    r_col3.metric("Payoff Date", payoff_date.strftime("%b %Y"))
                    
                    fig = px.area(
                        timeline_df, 
                        x="Month", 
                        y="Total Balance", 
                        title=f"{strategy.split()[0]} Payoff Trajectory",
                        color_discrete_sequence=["#ef4444"]
                    )
                    st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No active debts. You are debt-free! 🎉")

        # ============================================================
        # SUB-TAB 5: 💡 SMART ADVISOR & TAX PLANNER
        # ============================================================
        with subtab_advisor:
            from investment_planner import (
                generate_rebalance_advice, generate_new_money_advice,
                compute_tax_liability, ADVISORY_DISCLAIMER
            )
            from database import (
                add_income_source, get_income_sources_df,
                delete_income_source, update_income_source,
                INCOME_TYPES, FREQUENCY_OPTIONS,
                upsert_tax_deductions, get_tax_deductions,
                upsert_capital_gains, get_capital_gains,
            )
            from tax_engine import (
                derive_investment_income, parse_capital_gains,
                compute_deductions, compute_cg_tax,
                compute_advance_tax_schedule, compute_full_tax,
                FRSB_RATE, FRSB_RATE_EFFECTIVE,
            )

            st.markdown("### 💡 Smart Investment Advisor & Tax Planner")
            st.caption("AI-powered portfolio rebalancing, new money deployment suggestions, and country-aware tax planning — all in one place.")

            # Advisory disclaimer banner
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid #f59e0b;
                        border-left: 4px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                <div style="color: #fbbf24; font-size: 0.85rem; font-weight: 600;">⚠️ Advisory Notice</div>
                <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 4px;">
                    All recommendations are for informational purposes only. Trend signals use historical
                    SMA crossovers &amp; momentum. Consult a SEBI-registered advisor before investing.
                </div>
            </div>
            """, unsafe_allow_html=True)

            advisor_user_context = st.text_area(
                "💬 Additional Context / Goals (Optional)", 
                placeholder="e.g., 'I want to buy a house in 2 years' or 'Should I shift my FDs to Mutual Funds?'",
                help="The AI will incorporate these specific goals into its recommendations."
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # Ensure API key is available in this scope
            gemini_api_key = (
                current_user.get("gemini_api_key") or
                os.environ.get("GEMINI_API_KEY", "") or
                st.secrets.get("GEMINI_API_KEY", "")
            )

            adv_tab1, adv_tab2, adv_tab3 = st.tabs([
                "🔄 Rebalance My Portfolio",
                "💰 Deploy New Money",
                "🧾 Income & Tax Planner"
            ])

            # --------------------------------
            # INNER TAB 1: REBALANCE
            # --------------------------------
            with adv_tab1:
                st.markdown("#### 🔄 Portfolio Rebalance Advisor")
                st.caption("Compare your current allocation vs your target, spot drift, and get specific rebalancing actions.")
                
                render_grouped_portfolio_summary(inv_df)
                st.markdown("<br>", unsafe_allow_html=True)
                
                rc1, rc2, rc3 = st.columns([1, 1.5, 1.5])
                with rc1:
                    rebal_risk = st.selectbox(
                        "Risk Profile", ["Conservative", "Moderate", "Aggressive"],
                        index=["Conservative", "Moderate", "Aggressive"].index(
                            current_user.get("risk_tolerance", "Moderate") if current_user.get("risk_tolerance") in ["Conservative", "Moderate", "Aggressive"] else "Moderate"
                        ), key="rebal_risk_sel"
                    )
                with rc2:
                    country_opts = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
                    cur_country = current_user.get("country", "India")
                    rebal_country = st.selectbox(
                        "Country of Residence", country_opts,
                        index=country_opts.index(cur_country) if cur_country in country_opts else 0,
                        key="rebal_country_sel",
                        help="Your country determines which specific funds & instruments are suggested."
                    )
                    if rebal_country != cur_country:
                        from database import update_user_profile
                        update_user_profile(current_user["username"], country=rebal_country)
                        st.session_state["user"]["country"] = rebal_country
                with rc3:
                    st.write("")
                    run_rebal = st.button("🔍 Analyse & Rebalance", type="primary", use_container_width=True, key="run_rebal_btn")

                if run_rebal:
                    with st.spinner("Fetching live trend signals for ALL holdings and computing drift (this may take up to 30-45 seconds)..."):
                        rebal_result = generate_rebalance_advice(inv_df, rebal_risk, rebal_country, advisor_user_context, gemini_api_key)
                    st.session_state["rebal_result"] = rebal_result

                rebal_result = st.session_state.get("rebal_result")
                if rebal_result:
                    if "error" in rebal_result:
                        st.warning(f"⚠️ {rebal_result['error']}")
                    else:
                        st.success(f"✅ Analysis complete for portfolio of **{format_inr(rebal_result['total_value'])}**")

                        # Allocation Comparison Charts
                        alloc_c1, alloc_c2 = st.columns(2)
                        with alloc_c1:
                            st.markdown("##### 📊 Current Allocation")
                            curr_pie = pd.DataFrame(list(rebal_result["current_allocation"].items()), columns=["Asset", "%"])
                            fig_curr = px.pie(curr_pie, names="Asset", values="%", hole=0.4,
                                             color_discrete_sequence=px.colors.qualitative.Set3)
                            fig_curr.update_layout(margin=dict(l=0,r=0,t=10,b=10), height=240, showlegend=True)
                            st.plotly_chart(fig_curr, use_container_width=True)
                        with alloc_c2:
                            st.markdown("##### 🎯 Target Allocation")
                            tgt_pie = pd.DataFrame(list(rebal_result["target_allocation"].items()), columns=["Asset", "%"])
                            fig_tgt = px.pie(tgt_pie, names="Asset", values="%", hole=0.4,
                                            color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig_tgt.update_layout(margin=dict(l=0,r=0,t=10,b=10), height=240, showlegend=True)
                            st.plotly_chart(fig_tgt, use_container_width=True)

                        # Drift Table
                        st.markdown("##### 📋 Allocation Drift & Actions")
                        drift_df = pd.DataFrame(rebal_result["drift_table"])
                        if not drift_df.empty:
                            def drift_row_style(row):
                                if "Reduce" in str(row.get("Action", "")):
                                    return ["background-color: rgba(239,68,68,0.15)"] * len(row)
                                elif "Buy" in str(row.get("Action", "")):
                                    return ["background-color: rgba(16,185,129,0.15)"] * len(row)
                                return [""] * len(row)
                            st.dataframe(
                                drift_df[["Asset Class", "Current %", "Target %", "Drift %", "Action"]],
                                use_container_width=True, hide_index=True
                            )

                        # Detailed Action Plan
                        dp = rebal_result.get("detailed_plan", [])
                        if dp:
                            st.markdown("##### 🗺️ Detailed Action Plan")
                            with st.expander("View Step-by-Step Plan", expanded=True):
                                for i, step in enumerate(dp):
                                    st.markdown(f"**Step {i+1}:** {step}")

                        # Trend Signals for Equity Holdings
                        if rebal_result.get("trend_signals"):
                            with st.expander("📈 Live Trend Signals (Equity Holdings)", expanded=False):
                                for sig in rebal_result["trend_signals"]:
                                    signal_color = {"Strong Buy": "#10b981", "Buy": "#34d399", "Hold": "#94a3b8", "Reduce": "#f59e0b", "Caution": "#ef4444"}.get(sig.get("signal", ""), "#94a3b8")
                                    sig_col1, sig_col2, sig_col3, sig_col4 = st.columns([2, 1.5, 1, 3])
                                    with sig_col1:
                                        st.markdown(f"**{sig.get('holding_name', sig.get('ticker', '?'))}**")
                                        st.caption(f"Ticker: `{sig.get('ticker', 'N/A')}`")
                                    with sig_col2:
                                        price = sig.get("current_price")
                                        st.metric("Current Price", f"₹{price:,.2f}" if price else "N/A",
                                                  delta=f"{sig.get('momentum_pct', 0):+.1f}% (30d)" if sig.get("momentum_pct") is not None else None)
                                    with sig_col3:
                                        st.markdown(f"""<div style="background:{signal_color}22; border:1px solid {signal_color};
                                            border-radius:6px; padding:8px 12px; text-align:center;
                                            font-weight:700; color:{signal_color}; font-size:0.9rem;">
                                            {sig.get('signal', 'N/A')}<br>
                                            <span style="font-size:0.75rem; font-weight:400;">{sig.get('strength_score', 50)}/100</span>
                                            </div>""", unsafe_allow_html=True)
                                    with sig_col4:
                                        st.caption(sig.get("details", ""))
                                    st.markdown("<hr style='margin:6px 0; border-color:#334155;'>", unsafe_allow_html=True)

                        # Recommendations
                        if rebal_result.get("recommendations"):
                            st.markdown("##### 🤖 AI Rebalancing Recommendations")
                            for rec in rebal_result["recommendations"]:
                                action_color = {"Buy": "#10b981", "Sell/Switch": "#f59e0b", "Hold": "#64748b"}.get(rec.get("action_type", ""), "#64748b")
                                st.markdown(f"""
                                <div style="background:#1e293b; border-radius:8px; border-left:4px solid {action_color}; padding:12px 16px; margin-bottom:8px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div style="font-weight:600; color:#f1f5f9;">{rec.get('title','')}</div>
                                        <span style="background:{action_color}22; color:{action_color}; padding:3px 10px; border-radius:4px; font-size:0.82rem; font-weight:600;">{rec.get('action_type','')}</span>
                                    </div>
                                    <div style="color:#38bdf8; font-size:0.87rem; margin:6px 0 4px;">🏛️ {rec.get('instrument','')}</div>
                                    <div style="color:#94a3b8; font-size:0.82rem;">{rec.get('rationale','')}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        # Sector Analysis
                        if rebal_result.get("sector_analysis"):
                            st.markdown("##### 🏢 Sector & Segment Analysis")
                            for sec in rebal_result["sector_analysis"]:
                                action_color = {"Buy": "#10b981", "Sell": "#f59e0b", "Hold": "#64748b"}.get(sec.get("action_type", ""), "#64748b")
                                st.markdown(f"""
                                <div style="background:#1e293b; border-radius:8px; border-left:4px solid {action_color}; padding:12px 16px; margin-bottom:8px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div style="font-weight:600; color:#f1f5f9;">{sec.get('sector','')}</div>
                                        <span style="background:{action_color}22; color:{action_color}; padding:3px 10px; border-radius:4px; font-size:0.82rem; font-weight:600;">{sec.get('action_type','')}</span>
                                    </div>
                                    <div style="color:#94a3b8; font-size:0.82rem; margin-top:6px;">{sec.get('rationale','')}</div>
                                </div>
                                """, unsafe_allow_html=True)

            # --------------------------------
            # INNER TAB 2: DEPLOY NEW MONEY
            # --------------------------------
            with adv_tab2:
                st.markdown("#### 💰 New Money Investment Advisor")
                st.caption("Tell us how much you have to invest and we'll suggest the best instruments based on your risk profile and country.")

                nm_c1, nm_c2, nm_c3, nm_c4 = st.columns([1.5, 1.2, 1.2, 1.2])
                with nm_c1:
                    nm_amount = st.number_input("💵 Amount to Invest (₹)", min_value=1000.0, value=50000.0, step=5000.0, key="nm_amount")
                with nm_c2:
                    nm_mode = st.selectbox("Investment Mode", ["Lump Sum", "SIP (Monthly)"], key="nm_mode")
                with nm_c3:
                    nm_risk = st.selectbox("Risk Profile", ["Conservative", "Moderate", "Aggressive"],
                        index=["Conservative", "Moderate", "Aggressive"].index(
                            current_user.get("risk_tolerance", "Moderate") if current_user.get("risk_tolerance") in ["Conservative", "Moderate", "Aggressive"] else "Moderate"
                        ), key="nm_risk_sel"
                    )
                with nm_c4:
                    country_opts2 = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
                    cur_country2 = st.session_state.get("user", {}).get("country", "India")
                    nm_country = st.selectbox("Country", country_opts2,
                        index=country_opts2.index(cur_country2) if cur_country2 in country_opts2 else 0,
                        key="nm_country_sel"
                    )
                    if nm_country != cur_country2:
                        from database import update_user_profile
                        update_user_profile(current_user["username"], country=nm_country)
                        st.session_state["user"]["country"] = nm_country

                if st.button("💡 Get Investment Suggestions", type="primary", use_container_width=True, key="nm_suggest_btn"):
                    with st.spinner("Generating personalised suggestions..."):
                        mode_str = "SIP" if "SIP" in nm_mode else "Lump Sum"
                        nm_result = generate_new_money_advice(inv_df, nm_risk, nm_amount, mode_str, nm_country, advisor_user_context, gemini_api_key)
                    st.session_state["nm_result"] = nm_result

                nm_result = st.session_state.get("nm_result")
                if nm_result:
                    st.success("🎉 Suggestions Ready!")
                    st.info(nm_result.get("summary", ""))

                    if nm_result.get("detailed_plan"):
                        st.markdown("##### 🗺️ Detailed Action Plan")
                        with st.expander("View Step-by-Step Plan", expanded=True):
                            for i, step in enumerate(nm_result["detailed_plan"]):
                                st.markdown(f"**Step {i+1}:** {step}")

                    st.markdown("---")
                    st.markdown("##### 🗂️ Instrument Suggestions by Asset Class")

                    CLASS_ICONS = {"equity": "🚀", "debt": "🛡️", "gold": "🪙", "tax_saving": "🏛️"}
                    CLASS_COLORS = {"equity": "#38bdf8", "debt": "#34d399", "gold": "#fbbf24", "tax_saving": "#a78bfa"}

                    for cls_key, instruments in nm_result.get("suggestions", {}).items():
                        if not instruments:
                            continue
                        icon = CLASS_ICONS.get(cls_key, "📌")
                        color = CLASS_COLORS.get(cls_key, "#94a3b8")
                        alloc_amt = nm_result.get("allocation_split", {}).get(cls_key.capitalize(), 0)
                        st.markdown(f"""
                        <div style="display:flex; align-items:center; gap:10px; margin: 14px 0 6px;">
                            <span style="font-size:1.2rem;">{icon}</span>
                            <span style="font-size:1rem; font-weight:700; color:{color};">{cls_key.replace('_', ' ').title()}</span>
                            <span style="background:{color}22; color:{color}; padding:2px 10px; border-radius:12px; font-size:0.82rem;">
                                Suggested: {'₹'+f'{alloc_amt:,.0f}' if alloc_amt else 'N/A'}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                        for instr in instruments:
                            risk_color = {"Low": "#34d399", "Very Low": "#10b981", "Moderate": "#fbbf24", "Moderate-High": "#f97316", "High": "#ef4444"}.get(instr.get("risk", ""), "#94a3b8")
                            st.markdown(f"""
                            <div style="background:#1e293b; border-radius:8px; border-left:3px solid {color}; padding:10px 14px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                                <div style="flex:1; min-width:200px;">
                                    <div style="font-weight:600; color:#f1f5f9; font-size:0.92rem;">{instr.get('name','')}</div>
                                    <div style="color:#64748b; font-size:0.78rem; margin-top:2px;">{instr.get('type','')} &nbsp;•&nbsp;
                                        <span style="color:{risk_color};">Risk: {instr.get('risk','N/A')}</span>
                                    </div>
                                    <div style="color:#94a3b8; font-size:0.82rem; margin-top:6px;">{instr.get('rationale','')}</div>
                                </div>
                                <div style="text-align:right; min-width:130px;">
                                    <div style="font-weight:700; color:{color}; font-size:0.92rem;">{instr.get('suggested_amount','')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)


            # --------------------------------
            # INNER TAB 3: INCOME & TAX PLANNER
            # --------------------------------
            with adv_tab3:
                st.markdown("#### 🧾 Income Manager & Tax Planner")
                st.caption("Log all income sources, compute your annual tax liability, and discover personalized tax-saving opportunities.")

                # --- INCOME SOURCES SECTION ---
                st.markdown("##### 💵 Income Sources")
                income_df = get_income_sources_df(
                    username=current_user["username"],
                    family_id=user_family_id,
                    view_mode=view_mode
                )

                total_monthly_income = float(income_df["monthly_equivalent"].sum()) if not income_df.empty else 0.0
                total_annual_income = total_monthly_income * 12.0

                # KPI summary row
                if not income_df.empty:
                    ki1, ki2, ki3 = st.columns(3)
                    ki1.metric("📅 Total Monthly Income", format_inr(total_monthly_income))
                    ki2.metric("📆 Total Annual Income", format_inr(total_annual_income))
                    ki3.metric("🔢 Income Sources", str(len(income_df)))

                    # Income breakdown bar chart (only when > 1 sources)
                    if len(income_df) > 1:
                        fig_inc = px.bar(
                            income_df.sort_values("monthly_equivalent", ascending=True),
                            x="monthly_equivalent", y="source_name", orientation="h",
                            color="income_type",
                            labels={"monthly_equivalent": "Monthly Equivalent (₹)", "source_name": "Source"},
                            title="Income Sources Breakdown (Monthly Equivalent)",
                            height=max(200, len(income_df) * 40)
                        )
                        fig_inc.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                                              margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_inc, use_container_width=True)

                # Initialise edit-mode tracker
                if "edit_inc_id" not in st.session_state:
                    st.session_state["edit_inc_id"] = None

                # Income-type → icon mapping for visual scanning
                _inc_icons = {
                    "Salary / Regular Employment": "💼",
                    "Business / Self-Employment": "🏢",
                    "Freelance / Consulting": "💻",
                    "Rental Income": "🏠",
                    "Dividends / Investment Income": "📈",
                    "Pension / Annuity": "🧓",
                    "Capital Gains": "💹",
                    "Agricultural Income": "🌾",
                    "Gifts / Inheritance": "🎁",
                    "Other": "💰",
                }

                # --- 3-COLUMN CARD GRID ---
                if not income_df.empty:
                    st.markdown("**Your Income Sources:**")
                    inc_rows = list(income_df.iterrows())
                    for row_start in range(0, len(inc_rows), 3):
                        grid_cols = st.columns(3)
                        for col_idx, (_, irow) in enumerate(inc_rows[row_start:row_start + 3]):
                            with grid_cols[col_idx]:
                                inc_icon = _inc_icons.get(str(irow["income_type"]), "💰")
                                is_editing = st.session_state.get("edit_inc_id") == irow["id"]

                                if is_editing:
                                    # ── Inline edit form ──────────────────────────
                                    st.markdown(
                                        f"<div style='background:linear-gradient(135deg,#1e293b,#0f172a);"
                                        f"border:2px solid #a78bfa; border-radius:12px; padding:14px 16px; margin-bottom:6px;'>"
                                        f"<div style='font-weight:700; color:#a78bfa; font-size:0.88rem; margin-bottom:8px;'>"
                                        f"✏️ Editing: {irow['source_name']}</div></div>",
                                        unsafe_allow_html=True
                                    )
                                    with st.form(key=f"edit_inc_form_{irow['id']}"):
                                        e_name = st.text_input("Source Name", value=str(irow["source_name"]))
                                        e_type = st.selectbox(
                                            "Income Type", INCOME_TYPES,
                                            index=INCOME_TYPES.index(irow["income_type"])
                                            if irow["income_type"] in INCOME_TYPES else 0
                                        )
                                        e_amount = st.number_input(
                                            "Amount (₹)", min_value=0.0, step=1000.0,
                                            value=float(irow["amount"])
                                        )
                                        e_freq = st.selectbox(
                                            "Frequency", FREQUENCY_OPTIONS,
                                            index=FREQUENCY_OPTIONS.index(irow["frequency"])
                                            if irow["frequency"] in FREQUENCY_OPTIONS else 0
                                        )
                                        e_notes = st.text_input(
                                            "Notes",
                                            value=str(irow["notes"]) if irow["notes"] else ""
                                        )
                                        esb1, esb2 = st.columns(2)
                                        with esb1:
                                            do_save = st.form_submit_button(
                                                "💾 Save", type="primary", use_container_width=True
                                            )
                                        with esb2:
                                            do_cancel = st.form_submit_button(
                                                "✖ Cancel", use_container_width=True
                                            )

                                        if do_save:
                                            if update_income_source(
                                                int(irow["id"]),
                                                source_name=e_name,
                                                income_type=e_type,
                                                amount=e_amount,
                                                frequency=e_freq,
                                                notes=e_notes
                                            ):
                                                st.session_state["edit_inc_id"] = None
                                                st.rerun()
                                            else:
                                                st.error("Failed to save changes.")
                                        if do_cancel:
                                            st.session_state["edit_inc_id"] = None
                                            st.rerun()

                                else:
                                    # ── Display card ──────────────────────────────
                                    notes_html = (
                                        f"<div style='color:#64748b; font-size:0.72rem; margin-top:6px; "
                                        f"font-style:italic;'>{irow['notes']}</div>"
                                        if irow.get("notes") else ""
                                    )
                                    st.markdown(
                                        f"""
                                        <div style="background:linear-gradient(135deg,#1e293b,#0f172a);
                                                    border:1px solid #334155; border-radius:12px;
                                                    padding:16px 18px; margin-bottom:4px; min-height:170px;">
                                            <div style="font-size:1.5rem; line-height:1;">{inc_icon}</div>
                                            <div style="font-weight:700; color:#f1f5f9; font-size:0.95rem;
                                                        margin:6px 0 2px; white-space:nowrap; overflow:hidden;
                                                        text-overflow:ellipsis;">{irow['source_name']}</div>
                                            <div style="color:#94a3b8; font-size:0.74rem; margin-bottom:10px;">{irow['income_type']}</div>
                                            <div style="color:#38bdf8; font-weight:600; font-size:0.9rem;">
                                                {format_inr(float(irow['amount']))}
                                                <span style="color:#64748b; font-size:0.74rem;"> / {irow['frequency']}</span>
                                            </div>
                                            <div style="display:flex; gap:20px; margin-top:8px;">
                                                <div>
                                                    <div style="color:#64748b; font-size:0.68rem;">Monthly</div>
                                                    <div style="color:#34d399; font-size:0.82rem; font-weight:600;">{format_inr(float(irow['monthly_equivalent']))}</div>
                                                </div>
                                                <div>
                                                    <div style="color:#64748b; font-size:0.68rem;">Annual</div>
                                                    <div style="color:#fbbf24; font-size:0.82rem; font-weight:600;">{format_inr(float(irow['monthly_equivalent']) * 12)}</div>
                                                </div>
                                            </div>
                                            {notes_html}
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                    cbtn1, cbtn2 = st.columns(2)
                                    with cbtn1:
                                        if st.button(
                                            "✏️ Edit", key=f"edit_inc_{irow['id']}",
                                            use_container_width=True, help="Edit this income source"
                                        ):
                                            st.session_state["edit_inc_id"] = irow["id"]
                                            st.rerun()
                                    with cbtn2:
                                        if st.button(
                                            "🗑️ Delete", key=f"del_inc_{irow['id']}",
                                            use_container_width=True, help="Delete this income source"
                                        ):
                                            if delete_income_source(int(irow["id"]), user_family_id):
                                                if st.session_state.get("edit_inc_id") == irow["id"]:
                                                    st.session_state["edit_inc_id"] = None
                                                st.rerun()
                                            else:
                                                st.error("Failed to delete income source.")
                else:
                    st.info("No income sources yet. Add your first one below!")

                # --- ADD INCOME SOURCE (persistent, always visible) ---
                st.markdown("---")
                st.markdown(
                    "<div style='font-weight:700; color:#f1f5f9; font-size:0.95rem; margin-bottom:10px;'>"
                    "➕ Add New Income Source</div>",
                    unsafe_allow_html=True
                )
                with st.form("add_income_form"):
                    ai1, ai2, ai3 = st.columns(3)
                    with ai1:
                        i_name = st.text_input("Source Name", placeholder="e.g. Primary Salary, Rental - Flat B")
                        i_type = st.selectbox("Income Type", INCOME_TYPES)
                    with ai2:
                        i_amount = st.number_input("Amount (₹)", min_value=0.0, step=1000.0)
                        i_freq = st.selectbox("Frequency", FREQUENCY_OPTIONS)
                    with ai3:
                        i_from = st.date_input("Effective From", value=datetime.date.today())
                        i_notes = st.text_input("Notes (Optional)", placeholder="e.g. Includes bonus")

                    if st.form_submit_button("💾 Add Income Source", type="primary"):
                        if i_name and i_amount > 0:
                            new_inc_id = add_income_source(
                                username=current_user["username"],
                                family_id=user_family_id,
                                source_name=i_name,
                                income_type=i_type,
                                amount=i_amount,
                                frequency=i_freq,
                                effective_from=str(i_from),
                                notes=i_notes
                            )
                            if new_inc_id:
                                st.success(f"✅ Added income source: {i_name}")
                                st.rerun()
                        else:
                            st.error("Please provide a source name and amount.")

                # ═══════════════════════════════════════════════════════════
                # ENHANCED TAX PLANNER — 4 sections
                # ═══════════════════════════════════════════════════════════
                st.markdown("---")
                st.markdown("### 🏛️ Advanced Tax Planner (FY 2025-26)")
                st.caption(f"Auto-derives interest & dividends from your portfolio · Parses capital gains from broker PDFs · Full deduction waterfall · Advance tax schedule. RBI FRSB rate: **{FRSB_RATE*100:.2f}%** (effective {FRSB_RATE_EFFECTIVE})")

                # Country & Regime selectors
                tax_c1, tax_c2 = st.columns([2, 2])
                with tax_c1:
                    tax_country_opts = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
                    tax_cur_country = st.session_state.get("user", {}).get("country", "India")
                    tax_country = st.selectbox(
                        "🌍 Country of Tax Residence", tax_country_opts,
                        index=tax_country_opts.index(tax_cur_country) if tax_cur_country in tax_country_opts else 0,
                        key="tax_country_sel"
                    )
                    if tax_country != tax_cur_country:
                        from database import update_user_profile
                        update_user_profile(current_user["username"], country=tax_country)
                        st.session_state["user"]["country"] = tax_country
                with tax_c2:
                    if tax_country == "India":
                        tax_regime = st.selectbox(
                            "📋 Tax Regime", ["New Regime", "Old Regime"],
                            key="tax_regime_sel",
                            help="New Regime: ₹75,000 std deduction, simplified slabs. Old Regime: ₹50,000 std + 80C/80D/HRA/24b."
                        )
                    else:
                        tax_regime = "N/A"
                        st.info(f"Tax rules auto-applied for {tax_country}.")

                if tax_country == "India":
                    _user_key  = current_user["username"]
                    _fam_id    = current_user.get("family_id", 1)
                    _fy        = "2025-26"
                    _saved_ded = get_tax_deductions(_user_key, _fam_id, _fy)
                    _saved_cg  = get_capital_gains(_user_key, _fam_id, _fy)

                    # ─────────────────────────────────────────────────────
                    # SECTION A — DEDUCTIONS
                    # ─────────────────────────────────────────────────────
                    with st.expander("📋 Section A — Deductions & TDS Details", expanded=False):
                        st.caption("Enter your deduction details for FY 2025-26. Values are saved automatically.")
                        _user_age = current_user.get("age", 35)

                        with st.form("tax_deduction_form"):
                            if tax_regime == "Old Regime":
                                st.markdown("##### 80C Investments (Max ₹1.5L)")
                                _dc1, _dc2, _dc3, _dc4 = st.columns(4)
                                _ppf   = _dc1.number_input("PPF Contribution (₹)", min_value=0.0, value=float(_saved_ded.get("ppf_contribution", 0)), step=1000.0, key="ded_ppf")
                                _elss  = _dc2.number_input("ELSS Investment (₹)", min_value=0.0, value=float(_saved_ded.get("elss_investment", 0)), step=1000.0, key="ded_elss")
                                _lic   = _dc3.number_input("LIC Premium (₹)", min_value=0.0, value=float(_saved_ded.get("lic_premium", 0)), step=1000.0, key="ded_lic")
                                _hlp   = _dc4.number_input("Home Loan Principal (₹)", min_value=0.0, value=float(_saved_ded.get("home_loan_principal", 0)), step=1000.0, key="ded_hlp")
                                _dc5, _dc6, _dc7, _dc8 = st.columns(4)
                                _school = _dc5.number_input("School Fees (₹)", min_value=0.0, value=float(_saved_ded.get("school_fees", 0)), step=500.0, key="ded_school")
                                _nsc_r  = _dc6.number_input("NSC Interest Reinvested (₹)", min_value=0.0, value=float(_saved_ded.get("nsc_interest_reinvested", 0)), step=100.0, key="ded_nsc")
                                _epf    = _dc7.number_input("EPF Contribution (₹)", min_value=0.0, value=float(_saved_ded.get("epf_contribution", 0)), step=500.0, key="ded_epf")
                                _tsfd   = _dc8.number_input("Tax-saver FD (₹)", min_value=0.0, value=float(_saved_ded.get("tax_saver_fd", 0)), step=1000.0, key="ded_tsfd")

                                _eighty_c_total = min(_ppf + _elss + _lic + _hlp + _school + _nsc_r + _epf + _tsfd, 150000)
                                st.caption(f"📊 80C total (capped at ₹1.5L): **{format_inr(_eighty_c_total)}**")

                                st.markdown("##### 80D — Health Insurance")
                                _hc1, _hc2, _hc3 = st.columns(3)
                                _hi_self = _hc1.number_input("Health Ins — Self & Family (₹)", min_value=0.0, value=float(_saved_ded.get("health_ins_self", 0)), step=500.0, key="ded_hi_self")
                                _hi_par  = _hc2.number_input("Health Ins — Parents (₹)", min_value=0.0, value=float(_saved_ded.get("health_ins_parents", 0)), step=500.0, key="ded_hi_par")
                                _par_sr  = _hc3.checkbox("Parents are Senior Citizens", value=bool(_saved_ded.get("parents_senior", 0)), key="ded_par_sr")

                                st.markdown("##### HRA, Home Loan Interest & Others")
                                _oc1, _oc2, _oc3 = st.columns(3)
                                _hra_basic = _oc1.number_input("Basic Salary p.a. (for HRA) (₹)", min_value=0.0, value=float(_saved_ded.get("hra_basic_salary", 0)), step=1000.0, key="ded_hra_basic")
                                _hra_recv  = _oc2.number_input("HRA Received p.a. (₹)", min_value=0.0, value=float(_saved_ded.get("hra_received", 0)), step=1000.0, key="ded_hra_recv")
                                _rent_paid = _oc3.number_input("Rent Paid p.a. (₹)", min_value=0.0, value=float(_saved_ded.get("rent_paid", 0)), step=1000.0, key="ded_rent_paid")
                                _oc4, _oc5, _oc6 = st.columns(3)
                                _metro     = _oc4.checkbox("Metro City (50% HRA rule)", value=bool(_saved_ded.get("metro_city", 1)), key="ded_metro")
                                _hl_int    = _oc5.number_input("Home Loan Interest 24(b) (₹)", min_value=0.0, max_value=200000.0, value=float(_saved_ded.get("home_loan_interest", 0)), step=1000.0, key="ded_hl_int")
                                _nps_1b    = _oc6.number_input("NPS 80CCD(1B) Self (₹)", min_value=0.0, max_value=50000.0, value=float(_saved_ded.get("nps_80ccd_1b", 0)), step=500.0, key="ded_nps_1b")
                            else:
                                # New regime — minimal inputs
                                st.info("ℹ️ **New Regime**: Only Standard Deduction (₹75,000), NPS Employer (80CCD2), and Professional Tax apply.")
                                _ppf = _elss = _lic = _hlp = _school = _nsc_r = _epf = _tsfd = 0.0
                                _hi_self = _hi_par = _hra_basic = _hra_recv = _rent_paid = _hl_int = _nps_1b = 0.0
                                _par_sr = False; _metro = True; _eighty_c_total = 0.0

                            # Common fields for both regimes
                            st.markdown("##### Common Deductions")
                            _cc1, _cc2, _cc3, _cc4 = st.columns(4)
                            _nps_emp  = _cc1.number_input("NPS Employer 80CCD(2) (₹)", min_value=0.0, value=float(_saved_ded.get("nps_employer_80ccd2", 0)), step=500.0, key="ded_nps_emp")
                            _prof_tax = _cc2.number_input("Professional Tax (₹, max ₹2,400)", min_value=0.0, max_value=2400.0, value=float(_saved_ded.get("professional_tax", 0)), step=200.0, key="ded_prof_tax")
                            _sb_int   = _cc3.number_input("Savings Bank Interest (80TTA/TTB) (₹)", min_value=0.0, value=float(_saved_ded.get("savings_bank_interest", 0)), step=100.0, key="ded_sb_int")
                            _scss_int = _cc4.number_input("SCSS Interest (for 80TTB) (₹)", min_value=0.0, value=float(_saved_ded.get("scss_interest", 0)), step=100.0, key="ded_scss_int")

                            st.markdown("##### TDS & Advance Tax Already Paid")
                            _tp1, _tp2 = st.columns(2)
                            _tds     = _tp1.number_input("TDS Already Deducted (₹)", min_value=0.0, value=float(_saved_ded.get("tds_deducted", 0)), step=1000.0, key="ded_tds")
                            _adv_pd  = _tp2.number_input("Advance Tax Already Paid (₹)", min_value=0.0, value=float(_saved_ded.get("advance_paid", 0)), step=1000.0, key="ded_adv_paid")

                            _save_ded = st.form_submit_button("💾 Save Deduction Details", type="primary", use_container_width=True)
                            if _save_ded:
                                _ded_payload = {
                                    "ppf_contribution": _ppf, "elss_investment": _elss, "lic_premium": _lic,
                                    "home_loan_principal": _hlp, "school_fees": _school, "nsc_interest_reinvested": _nsc_r,
                                    "epf_contribution": _epf, "tax_saver_fd": _tsfd,
                                    "health_ins_self": _hi_self, "health_ins_parents": _hi_par, "parents_senior": int(_par_sr),
                                    "nps_80ccd_1b": _nps_1b if tax_regime == "Old Regime" else 0,
                                    "nps_employer_80ccd2": _nps_emp,
                                    "home_loan_interest": _hl_int, "hra_basic_salary": _hra_basic,
                                    "hra_received": _hra_recv, "rent_paid": _rent_paid, "metro_city": int(_metro),
                                    "professional_tax": _prof_tax, "savings_bank_interest": _sb_int,
                                    "scss_interest": _scss_int, "tds_deducted": _tds, "advance_paid": _adv_pd,
                                    "age": _user_age,
                                }
                                if upsert_tax_deductions(_user_key, _fam_id, _fy, _ded_payload):
                                    _saved_ded = _ded_payload
                                    st.success("✅ Deduction details saved.")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to save deduction details.")

                    # ─────────────────────────────────────────────────────
                    # SECTION B — AUTO-DERIVED PASSIVE INCOME
                    # ─────────────────────────────────────────────────────
                    with st.expander("💰 Section B — Passive Income from Portfolio (Auto-Calculated)", expanded=False):
                        st.caption("Income automatically derived from your investment holdings and income sources. Override any figure if needed.")
                        
                        has_investments = inv_df is not None and not inv_df.empty
                        has_incomes = income_df is not None and not income_df.empty
                        
                        if has_investments or has_incomes:
                            with st.spinner("Deriving passive income from portfolio..."):
                                _passive_entries = derive_investment_income(inv_df, income_sources_df=income_df)
                            if _passive_entries:
                                st.markdown(f"🔍 Found **{len(_passive_entries)}** passive income streams from your portfolio:")
                                _override_vals = {}
                                for _pi_idx, _pe in enumerate(_passive_entries):
                                    _is_exempt = "EXEMPT" in _pe.get("taxability", "").upper()
                                    _card_border = "#10b981" if _is_exempt else "#38bdf8"
                                    _label_color = "#10b981" if _is_exempt else "#38bdf8"
                                    st.markdown(f"""
                                    <div style="background:#1e293b; border-radius:8px; border-left:4px solid {_card_border};
                                                padding:10px 14px; margin-bottom:6px;">
                                        <div style="display:flex; justify-content:space-between; align-items:center;">
                                            <div>
                                                <span style="font-weight:700; color:{_label_color};">{_pe['source_name']}</span>
                                                <span style="color:#64748b; font-size:0.78rem; margin-left:8px;">{_pe['income_type']}</span>
                                            </div>
                                            <div style="color:{'#10b981' if _is_exempt else '#fbbf24'}; font-weight:700;">{format_inr(_pe['annual_amount'])}/yr</div>
                                        </div>
                                        <div style="color:#64748b; font-size:0.75rem; margin-top:4px;">{_pe['notes']}</div>
                                        <div style="color:#475569; font-size:0.72rem;">Taxability: {_pe['taxability']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    _override = st.number_input(
                                        f"Override: {_pe['source_name']} (₹/yr)",
                                        min_value=0.0,
                                        value=float(_pe["annual_amount"]),
                                        step=100.0,
                                        key=f"passive_override_{_pi_idx}",
                                        label_visibility="collapsed"
                                    )
                                    _override_vals[_pi_idx] = _override
                                st.session_state["_passive_entries"]  = _passive_entries
                                st.session_state["_passive_overrides"] = _override_vals
                            else:
                                st.info("ℹ️ No passive income streams detected in your portfolio. Add FD, FRSB Bond, SGB, or equity holdings with units to auto-detect.")
                                st.session_state["_passive_entries"]  = []
                                st.session_state["_passive_overrides"] = {}
                        else:
                            st.info("ℹ️ No portfolio holdings found. Add investments in the Portfolio section to auto-derive passive income.")
                            st.session_state["_passive_entries"]  = []
                            st.session_state["_passive_overrides"] = {}

                    # ─────────────────────────────────────────────────────
                    # SECTION C — CAPITAL GAINS
                    # ─────────────────────────────────────────────────────
                    with st.expander("📈 Section C — Capital Gains (Upload or Manual Entry)", expanded=False):
                        st.caption("Upload your broker/AIS capital gains statement to auto-extract LTCG & STCG. Or enter manually.")

                        _cg_tabs = st.tabs(["📤 Upload Document", "✏️ Manual Entry", "📋 Saved Data"])

                        with _cg_tabs[0]:
                            st.markdown("""
                            **Supported documents:**
                            - **Zerodha**: Console → P&L → Download Tax P&L (PDF)
                            - **ICICI Direct**: Reports → Capital Gains → Download PDF
                            - **CAMS / KFintech**: CAS (Consolidated Account Statement) PDF
                            - **IT Dept AIS**: Income Tax Portal → AIS → Download JSON
                            """)
                            _cg_file = st.file_uploader(
                                "Upload capital gains document",
                                type=["pdf", "json"],
                                key="cg_upload_file",
                                help="Auto-detects format from Zerodha/ICICI/CAMS/AIS"
                            )
                            if _cg_file is not None:
                                with st.spinner(f"Parsing {_cg_file.name}..."):
                                    _parsed_cg = parse_capital_gains(_cg_file)
                                if _parsed_cg.get("parse_errors"):
                                    for _pe in _parsed_cg["parse_errors"]:
                                        st.warning(f"⚠️ {_pe}")
                                st.success(f"✅ Detected format: **{_parsed_cg['source']}**")
                                st.markdown(f"**Parsed Capital Gains — {_cg_file.name}:**")
                                _cg_display = pd.DataFrame([
                                    {"Category": "Equity LTCG", "Amount (₹)": format_inr(_parsed_cg["equity_ltcg"]), "Tax Rate": "12.5% (above ₹1.25L)"},
                                    {"Category": "Equity STCG", "Amount (₹)": format_inr(_parsed_cg["equity_stcg"]), "Tax Rate": "20%"},
                                    {"Category": "Equity MF LTCG", "Amount (₹)": format_inr(_parsed_cg["equity_mf_ltcg"]), "Tax Rate": "12.5% (above ₹1.25L)"},
                                    {"Category": "Equity MF STCG", "Amount (₹)": format_inr(_parsed_cg["equity_mf_stcg"]), "Tax Rate": "20%"},
                                    {"Category": "Debt MF LTCG", "Amount (₹)": format_inr(_parsed_cg["debt_mf_ltcg"]), "Tax Rate": "Slab rate"},
                                    {"Category": "Debt MF STCG", "Amount (₹)": format_inr(_parsed_cg["debt_mf_stcg"]), "Tax Rate": "Slab rate"},
                                    {"Category": "Property LTCG", "Amount (₹)": format_inr(_parsed_cg["property_ltcg"]), "Tax Rate": "12.5% (no indexation)"},
                                    {"Category": "Property STCG", "Amount (₹)": format_inr(_parsed_cg["property_stcg"]), "Tax Rate": "Slab rate"},
                                    {"Category": "Other LTCG", "Amount (₹)": format_inr(_parsed_cg["other_ltcg"]), "Tax Rate": "Slab rate"},
                                    {"Category": "Other STCG", "Amount (₹)": format_inr(_parsed_cg["other_stcg"]), "Tax Rate": "Slab rate"},
                                ])
                                st.dataframe(_cg_display, use_container_width=True, hide_index=True)
                                st.markdown(f"**Total LTCG: {format_inr(_parsed_cg['total_ltcg'])} | Total STCG: {format_inr(_parsed_cg['total_stcg'])}**")
                                if st.button("💾 Save Parsed Capital Gains", type="primary", key="save_parsed_cg"):
                                    if upsert_capital_gains(_user_key, _fam_id, _fy, _parsed_cg):
                                        _saved_cg = _parsed_cg
                                        st.success("✅ Capital gains saved.")
                                        st.rerun()

                        with _cg_tabs[1]:
                            st.markdown("Enter capital gains amounts manually (all figures in ₹):")
                            with st.form("manual_cg_form"):
                                _m1, _m2 = st.columns(2)
                                _m_eq_ltcg   = _m1.number_input("Equity LTCG (Listed Stocks)", min_value=0.0, value=float(_saved_cg.get("equity_ltcg", 0)), step=1000.0, key="mcg_eq_ltcg")
                                _m_eq_stcg   = _m2.number_input("Equity STCG (Listed Stocks)", min_value=0.0, value=float(_saved_cg.get("equity_stcg", 0)), step=1000.0, key="mcg_eq_stcg")
                                _m3, _m4 = st.columns(2)
                                _m_eqmf_ltcg = _m3.number_input("Equity Mutual Fund LTCG", min_value=0.0, value=float(_saved_cg.get("equity_mf_ltcg", 0)), step=1000.0, key="mcg_eqmf_ltcg")
                                _m_eqmf_stcg = _m4.number_input("Equity Mutual Fund STCG", min_value=0.0, value=float(_saved_cg.get("equity_mf_stcg", 0)), step=1000.0, key="mcg_eqmf_stcg")
                                _m5, _m6 = st.columns(2)
                                _m_dmf_ltcg  = _m5.number_input("Debt MF LTCG (taxed at slab)", min_value=0.0, value=float(_saved_cg.get("debt_mf_ltcg", 0)), step=1000.0, key="mcg_dmf_ltcg")
                                _m_dmf_stcg  = _m6.number_input("Debt MF STCG (taxed at slab)", min_value=0.0, value=float(_saved_cg.get("debt_mf_stcg", 0)), step=1000.0, key="mcg_dmf_stcg")
                                _m7, _m8 = st.columns(2)
                                _m_prop_ltcg = _m7.number_input("Property LTCG (12.5%, no indexation)", min_value=0.0, value=float(_saved_cg.get("property_ltcg", 0)), step=10000.0, key="mcg_prop_ltcg")
                                _m_prop_stcg = _m8.number_input("Property STCG (slab rate)", min_value=0.0, value=float(_saved_cg.get("property_stcg", 0)), step=10000.0, key="mcg_prop_stcg")
                                _m9, _m10 = st.columns(2)
                                _m_oth_ltcg  = _m9.number_input("Other LTCG", min_value=0.0, value=float(_saved_cg.get("other_ltcg", 0)), step=1000.0, key="mcg_oth_ltcg")
                                _m_oth_stcg  = _m10.number_input("Other STCG", min_value=0.0, value=float(_saved_cg.get("other_stcg", 0)), step=1000.0, key="mcg_oth_stcg")
                                _save_mcg = st.form_submit_button("💾 Save Manual Capital Gains", type="primary", use_container_width=True)
                                if _save_mcg:
                                    _mcg_payload = {
                                        "equity_ltcg": _m_eq_ltcg, "equity_stcg": _m_eq_stcg,
                                        "equity_mf_ltcg": _m_eqmf_ltcg, "equity_mf_stcg": _m_eqmf_stcg,
                                        "debt_mf_ltcg": _m_dmf_ltcg, "debt_mf_stcg": _m_dmf_stcg,
                                        "property_ltcg": _m_prop_ltcg, "property_stcg": _m_prop_stcg,
                                        "other_ltcg": _m_oth_ltcg, "other_stcg": _m_oth_stcg,
                                        "source": "Manual", "notes": "",
                                        "slab_income_addition": _m_dmf_ltcg + _m_dmf_stcg + _m_prop_stcg + _m_oth_ltcg + _m_oth_stcg,
                                    }
                                    if upsert_capital_gains(_user_key, _fam_id, _fy, _mcg_payload):
                                        _saved_cg = _mcg_payload
                                        st.success("✅ Capital gains saved.")
                                        st.rerun()

                        with _cg_tabs[2]:
                            if _saved_cg:
                                st.markdown(f"**Saved CG data for FY {_fy} (source: {_saved_cg.get('source', 'N/A')}):**")
                                _saved_cg_display = pd.DataFrame([
                                    {"Category": "Equity LTCG", "Amount": format_inr(float(_saved_cg.get("equity_ltcg", 0)))},
                                    {"Category": "Equity STCG", "Amount": format_inr(float(_saved_cg.get("equity_stcg", 0)))},
                                    {"Category": "Equity MF LTCG", "Amount": format_inr(float(_saved_cg.get("equity_mf_ltcg", 0)))},
                                    {"Category": "Equity MF STCG", "Amount": format_inr(float(_saved_cg.get("equity_mf_stcg", 0)))},
                                    {"Category": "Debt MF LTCG", "Amount": format_inr(float(_saved_cg.get("debt_mf_ltcg", 0)))},
                                    {"Category": "Debt MF STCG", "Amount": format_inr(float(_saved_cg.get("debt_mf_stcg", 0)))},
                                    {"Category": "Property LTCG", "Amount": format_inr(float(_saved_cg.get("property_ltcg", 0)))},
                                    {"Category": "Property STCG", "Amount": format_inr(float(_saved_cg.get("property_stcg", 0)))},
                                ])
                                st.dataframe(_saved_cg_display, use_container_width=True, hide_index=True)
                            else:
                                st.info("No capital gains data saved yet for FY 2025-26.")

                    # ─────────────────────────────────────────────────────
                    # SECTION D — TAX SUMMARY
                    # ─────────────────────────────────────────────────────
                    st.markdown("---")
                    _run_tax = st.button("🧮 Calculate Full Tax Liability", type="primary",
                                         use_container_width=True, key="run_full_tax_btn")
                    if _run_tax:
                        if income_df.empty and not st.session_state.get("_passive_entries"):
                            st.warning("⚠️ No income sources or passive income found. Add income sources or investments first.")
                        else:
                            with st.spinner("Computing full tax liability..."):
                                _tax_ded_for_compute = dict(_saved_ded)
                                _tax_ded_for_compute["age"] = current_user.get("age", 35)
                                _cg_for_compute = dict(_saved_cg) if _saved_cg else {}
                                if _cg_for_compute and "slab_income_addition" not in _cg_for_compute:
                                    _cg_for_compute["slab_income_addition"] = (
                                        float(_cg_for_compute.get("debt_mf_ltcg", 0)) +
                                        float(_cg_for_compute.get("debt_mf_stcg", 0)) +
                                        float(_cg_for_compute.get("property_stcg", 0)) +
                                        float(_cg_for_compute.get("other_ltcg", 0)) +
                                        float(_cg_for_compute.get("other_stcg", 0))
                                    )
                                _p_entries  = st.session_state.get("_passive_entries", [])
                                _p_override = st.session_state.get("_passive_overrides", {})
                                _tax_result = compute_full_tax(
                                    income_df, _p_entries, _p_override, _cg_for_compute,
                                    _tax_ded_for_compute,
                                    tds_deducted=float(_saved_ded.get("tds_deducted", 0)),
                                    advance_paid=float(_saved_ded.get("advance_paid", 0)),
                                    tax_regime=tax_regime,
                                )

                            # KPI Row
                            _tk1, _tk2, _tk3, _tk4, _tk5 = st.columns(5)
                            _tk1.metric("💰 Gross Income", format_inr(_tax_result["gross_slab_income"]))
                            _tk2.metric("🔽 Total Deductions", format_inr(_tax_result["total_deduction"]))
                            _tk3.metric("📊 Taxable Income", format_inr(_tax_result["taxable_income"]))
                            _tk4.metric("🏛️ Total Tax", format_inr(_tax_result["total_tax"]))
                            _tk5.metric("📈 Effective Rate", f"{_tax_result['effective_rate_pct']:.1f}%",
                                        delta=f"vs {_tax_result['compare_regime']}: {format_inr(_tax_result['compare_tax'])}",
                                        delta_color="inverse")

                            # Tax breakdown card
                            _cg_detail = _tax_result.get("cg_tax_detail", {})
                            st.markdown(f"""
                            <div style="background:linear-gradient(135deg,#1e293b,#0f172a); border-radius:12px;
                                        border:1px solid #334155; padding:16px 20px; margin:12px 0;">
                                <div style="font-weight:700; color:#f1f5f9; margin-bottom:10px; font-size:1rem;">
                                    📋 Tax Breakdown — {tax_regime} (FY 2025-26)
                                </div>
                                <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px;">
                                    <div><div style="color:#94a3b8;font-size:0.78rem;">Slab Tax</div>
                                         <div style="color:#38bdf8;font-weight:700;">{format_inr(_tax_result['slab_tax'])}</div></div>
                                    <div><div style="color:#94a3b8;font-size:0.78rem;">CG Tax</div>
                                         <div style="color:#f59e0b;font-weight:700;">{format_inr(_tax_result['cg_tax'])}</div></div>
                                    <div><div style="color:#94a3b8;font-size:0.78rem;">TDS Deducted</div>
                                         <div style="color:#34d399;font-weight:700;">{format_inr(_tax_result['tds_deducted'])}</div></div>
                                    <div><div style="color:#94a3b8;font-size:0.78rem;">Balance Due</div>
                                         <div style="color:#{'f87171' if _tax_result['balance_due'] > 0 else '34d399'};font-weight:700;">{format_inr(_tax_result['balance_due'])}</div></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # CG Tax Detail
                            if _cg_detail.get("total_cg_tax", 0) > 0:
                                st.markdown("**📈 Capital Gains Tax Detail:**")
                                _cg_table = pd.DataFrame([
                                    {"Item": "Equity LTCG (total)", "Amount": format_inr(_cg_detail.get("total_equity_ltcg", 0)), "Note": f"Exempt: {format_inr(_cg_detail.get('ltcg_exempt',0))} | Taxable: {format_inr(_cg_detail.get('taxable_equity_ltcg',0))}"},
                                    {"Item": "Equity LTCG Tax (12.5% + cess)", "Amount": format_inr(_cg_detail.get("tax_equity_ltcg", 0)), "Note": ""},
                                    {"Item": "Equity STCG (total)", "Amount": format_inr(_cg_detail.get("total_equity_stcg", 0)), "Note": ""},
                                    {"Item": "Equity STCG Tax (20% + cess)", "Amount": format_inr(_cg_detail.get("tax_equity_stcg", 0)), "Note": ""},
                                    {"Item": "Property LTCG Tax (12.5% + cess)", "Amount": format_inr(_cg_detail.get("tax_property_ltcg", 0)), "Note": "No indexation"},
                                    {"Item": "Debt MF / Other (slab)", "Amount": format_inr(_cg_detail.get("slab_income_addition", 0)), "Note": "Added to slab income above"},
                                ])
                                st.dataframe(_cg_table, use_container_width=True, hide_index=True)

                            # Income breakdown
                            _all_inc = _tax_result.get("income_breakdown", []) + _tax_result.get("passive_breakdown", [])
                            if _all_inc:
                                st.markdown("**📊 Full Income Breakdown:**")
                                _inc_df = pd.DataFrame(_all_inc)
                                _inc_df["annual"] = _inc_df["annual"].apply(format_inr)
                                st.dataframe(_inc_df.rename(columns={"source":"Source","type":"Type","annual":"Annual","taxability":"Taxability"}),
                                             use_container_width=True, hide_index=True)

                            # Deduction breakdown
                            _ded_det = _tax_result.get("deduction_detail", {})
                            if _ded_det:
                                st.markdown("**🔽 Deductions Applied:**")
                                _ded_rows = [
                                    {"Deduction": "Standard Deduction", "Amount": format_inr(_ded_det.get("standard_deduction", 0))},
                                ]
                                if tax_regime == "Old Regime":
                                    _ded_rows += [
                                        {"Deduction": "80C (PPF/ELSS/LIC etc.)", "Amount": format_inr(_ded_det.get("eighty_c", 0))},
                                        {"Deduction": "80D (Health Insurance)", "Amount": format_inr(_ded_det.get("eighty_d", 0))},
                                        {"Deduction": "80CCD(1B) NPS", "Amount": format_inr(_ded_det.get("nps_80ccd_1b", 0))},
                                        {"Deduction": "24(b) Home Loan Interest", "Amount": format_inr(_ded_det.get("home_loan_interest_24b", 0))},
                                        {"Deduction": "HRA Exemption", "Amount": format_inr(_ded_det.get("hra_exemption", 0))},
                                        {"Deduction": f"{_ded_det.get('tta_ttb_label','80TTA')}", "Amount": format_inr(_ded_det.get("tta_ttb", 0))},
                                    ]
                                _ded_rows += [
                                    {"Deduction": "Professional Tax", "Amount": format_inr(_ded_det.get("professional_tax", 0))},
                                    {"Deduction": "NPS Employer 80CCD(2)", "Amount": format_inr(_ded_det.get("nps_employer_80ccd2", 0))},
                                    {"Deduction": "**TOTAL**", "Amount": f"**{format_inr(_ded_det.get('total_deduction',0))}**"},
                                ]
                                st.dataframe(pd.DataFrame(_ded_rows), use_container_width=True, hide_index=True)

                            # Advance Tax Schedule
                            _adv_sched = _tax_result.get("advance_tax_schedule", [])
                            if _adv_sched:
                                st.markdown("#### 📅 Advance Tax Instalment Schedule (FY 2025-26)")
                                st.caption("Advance tax is required when net tax liability exceeds ₹10,000. Failure to pay on time attracts interest u/s 234B & 234C.")
                                _adv_df = pd.DataFrame(_adv_sched)
                                _adv_df["instalment_amount"] = _adv_df["instalment_amount"].apply(format_inr)
                                _adv_df["cumulative_due"]    = _adv_df["cumulative_due"].apply(format_inr)
                                st.dataframe(
                                    _adv_df.rename(columns={
                                        "instalment": "Instalment",
                                        "due_date": "Due Date",
                                        "cumulative_pct": "Cumulative %",
                                        "cumulative_due": "Cumulative Amount",
                                        "instalment_amount": "Pay This Instalment",
                                        "status": "Status",
                                    })[["Instalment","Due Date","Cumulative %","Cumulative Amount","Pay This Instalment","Status"]],
                                    use_container_width=True, hide_index=True
                                )
                            elif _tax_result["total_tax"] > 0:
                                st.success("✅ Net tax liability < ₹10,000 after TDS/advance paid — no advance tax required.")

                            # Savings Opportunities
                            if _tax_result.get("savings_opportunities"):
                                st.markdown("#### 💡 Tax Saving Opportunities")
                                for _opp in _tax_result["savings_opportunities"]:
                                    st.markdown(f"""
                                    <div style="background:#1e293b; border-radius:8px; border-left:4px solid #a78bfa;
                                                padding:12px 16px; margin-bottom:8px;">
                                        <div style="font-weight:600; color:#a78bfa; font-size:0.9rem;">🏛️ {_opp.get('opportunity','')}</div>
                                        <div style="color:#94a3b8; font-size:0.83rem; margin-top:4px;">{_opp.get('detail','')}</div>
                                    </div>
                                    """, unsafe_allow_html=True)

                            # What's still needed info box
                            st.markdown("""
                            <div style="background:#0f172a; border-radius:10px; border:1px solid #1e3a5f;
                                        padding:14px 18px; margin-top:16px;">
                                <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">📌 Additional Information Needed for a Complete Tax Return</div>
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; color:#94a3b8; font-size:0.82rem;">
                                    <div>✅ <b>Form 16</b> — TDS certificate from employer</div>
                                    <div>✅ <b>FD Interest Certificates</b> — Annual interest statements from bank</div>
                                    <div>✅ <b>26AS / AIS</b> — Download from IT portal to verify TDS</div>
                                    <div>✅ <b>Home Loan Statement</b> — Principal & interest breakup for 80C/24b</div>
                                    <div>✅ <b>Rental Income</b> — Net rent after 30% standard deduction + municipal taxes</div>
                                    <div>✅ <b>Foreign Income / DTAA</b> — If NRI or foreign accounts (FEMA/DTAA compliance)</div>
                                    <div>✅ <b>Advance Tax Challans</b> — BSR code + date + amount for each payment</div>
                                    <div>✅ <b>MF IDCW Statements</b> — CAMS/Kfintech dividend statements if applicable</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                else:
                    # Non-India: use the legacy compute_tax_liability
                    st.markdown("---")
                    st.markdown("##### 🏛️ Tax Liability Calculator")
                    _run_tax_intl = st.button("🧮 Calculate Tax Liability", type="primary", use_container_width=True, key="run_tax_btn")
                    if _run_tax_intl:
                        if income_df.empty:
                            st.warning("⚠️ No income sources found. Please add at least one income source above first.")
                        else:
                            with st.spinner("Computing tax liability..."):
                                tax_result = compute_tax_liability(income_df, inv_df, tax_country, tax_regime)
                            t1, t2, t3, t4 = st.columns(4)
                            t1.metric("💰 Gross Annual Income", format_inr(tax_result["gross_annual_income"]))
                            t2.metric("📊 Taxable Income", format_inr(tax_result.get("taxable_income", 0)))
                            t3.metric("🏛️ Est. Annual Tax", format_inr(tax_result["estimated_tax"]))
                            t4.metric("📈 Effective Tax Rate", f"{tax_result['effective_rate_pct']:.1f}%")
                            if tax_result.get("savings_opportunities"):
                                st.markdown("#### 💡 Tax Saving Opportunities")
                                for opp in tax_result["savings_opportunities"]:
                                    st.markdown(f"""
                                    <div style="background:#1e293b; border-radius:8px; border-left:4px solid #a78bfa;
                                                padding:12px 16px; margin-bottom:8px;">
                                        <div style="font-weight:600; color:#a78bfa; font-size:0.9rem;">🏛️ {opp.get('opportunity','')}</div>
                                        <div style="color:#94a3b8; font-size:0.83rem; margin-top:4px;">{opp.get('detail','')}</div>
                                    </div>
                                    """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # ⚙️ SETTINGS & ADMIN
    # ----------------------------------------------------
    elif nav_selection == "🎓 Financial Academy":
        from financial_academy import render_financial_academy_tab
        render_financial_academy_tab()
        
    elif nav_selection == "⚙️ Settings & Admin":
        sa_tab1, sa_tab2, sa_tab3 = st.tabs(["💾 Data Export", "👑 Admin", "👤 Profile"])
        
        with sa_tab3:
            st.subheader("👤 User Profile Settings")
            st.caption("Update your personal details. This information is used across the dashboard and wealth planner.")
            
            with st.form("update_profile_form"):
                st.markdown("#### 1. Basic Information")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    new_name = st.text_input("Full Name", value=current_user.get("full_name", ""))
                with c2:
                    new_age = st.number_input("Age", min_value=18, max_value=100, value=current_user.get("age", 35), step=1)
                with c3:
                    cur_sex = current_user.get("sex", "Not Specified")
                    new_sex = st.selectbox("Sex", ["Not Specified", "Male", "Female", "Other"], index=["Not Specified", "Male", "Female", "Other"].index(cur_sex) if cur_sex in ["Not Specified", "Male", "Female", "Other"] else 0)
                with c4:
                    try:
                        parsed_dob = datetime.datetime.strptime(current_user.get("dob", ""), "%Y-%m-%d").date()
                    except:
                        parsed_dob = datetime.date(1990, 1, 1)
                    new_dob = st.date_input("Date of Birth", value=parsed_dob, min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today())
                
                st.markdown("#### 2. Location Details")
                new_address = st.text_area("Address", value=current_user.get("address", ""))
                l1, l2, l3 = st.columns(3)
                with l1:
                    new_city = st.text_input("City", value=current_user.get("city", ""))
                with l2:
                    new_state = st.text_input("State", value=current_user.get("state", ""))
                with l3:
                    new_country = st.text_input("Country", value=current_user.get("country", "India"))
                
                st.markdown("#### 3. Financial & Wealth Planner Meta")
                f1, f2, f3 = st.columns(3)
                with f1:
                    inc_opts = ["Not Specified", "< ₹10L", "₹10L - ₹25L", "₹25L - ₹50L", "> ₹50L"]
                    cur_inc = current_user.get("income_range", "Not Specified")
                    new_income = st.selectbox("Annual Income Range", inc_opts, index=inc_opts.index(cur_inc) if cur_inc in inc_opts else 0)
                    new_occ = st.text_input("Occupation / Profession", value=current_user.get("occupation", ""))
                with f2:
                    mar_opts = ["Not Specified", "Single", "Married", "Divorced", "Widowed"]
                    cur_mar = current_user.get("marital_status", "Not Specified")
                    new_marital = st.selectbox("Marital Status", mar_opts, index=mar_opts.index(cur_mar) if cur_mar in mar_opts else 0)
                with f3:
                    risk_opts = ["Conservative", "Moderate", "Aggressive"]
                    cur_risk = current_user.get("risk_tolerance", "Moderate")
                    new_risk = st.selectbox("Risk Tolerance (Wealth Planner)", risk_opts, index=risk_opts.index(cur_risk) if cur_risk in risk_opts else 1)
                
                st.markdown("#### 4. API Configurations")
                new_api_key = st.text_input("Gemini API Key", value=current_user.get("gemini_api_key", ""), type="password", help="Required for AI-powered features like Unstructured Statement Import.")
                
                st.markdown("#### 5. Password Recovery Settings")
                new_email = st.text_input("Recovery Email Address", value=current_user.get("email", ""), placeholder="your_email@example.com")
                cur_sq = current_user.get("security_question", "")
                sq_options = ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"]
                new_sq = st.selectbox("Security Question", sq_options, index=sq_options.index(cur_sq) if cur_sq in sq_options else 0)
                new_sa = st.text_input("Security Answer", type="password", help="Leave blank if you do not want to change your existing security answer.")

                if st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True):
                    profile_data = {
                        "full_name": new_name,
                        "age": new_age,
                        "sex": new_sex,
                        "dob": new_dob.isoformat(),
                        "address": new_address,
                        "city": new_city,
                        "state": new_state,
                        "country": new_country,
                        "income_range": new_income,
                        "occupation": new_occ,
                        "marital_status": new_marital,
                        "risk_tolerance": new_risk,
                        "gemini_api_key": new_api_key
                    }
                    # Handle recovery info separately
                    recovery_ok = True
                    if new_email or new_sa: # if they try to update email or answer
                        # if they just want to update email, they don't *have* to re-enter answer, but the function requires it or it overwrites it to None if empty. Wait, set_user_recovery_info overwrites the hash if answer is provided. Let's fix that. Actually, if new_sa is empty, it shouldn't overwrite the existing hash.
                        # I'll just pass the new_sa. Wait, my set_user_recovery_info function hashes answer if provided, else None. I should adjust it to only update hash if answer is provided. Let me fix the DB function call or adjust here.
                        pass # I'll update database.py in a sec if needed

                    if update_user_profile(current_user["username"], profile_data):
                        # Update session state dynamically
                        for k, v in profile_data.items():
                            st.session_state["user"][k] = v
                        
                        # Set recovery info
                        if new_email or new_sq:
                            # if new_sa is blank, we need a special way to NOT overwrite it, but we don't have that in set_user_recovery_info. 
                            # If new_sa is blank, we will just use the current hash? We can't pass the current hash directly into set_user_recovery_info since it hashes it again.
                            pass

                        # For simplicity, if new_sa is not provided, we should probably warn them that they must provide it to update recovery settings.
                        if new_email and not new_sa and not current_user.get("security_answer_hash"):
                            st.error("Please provide a Security Answer to set up recovery.")
                        else:
                            if new_sa:
                                set_user_recovery_info(current_user["username"], new_email, new_sq, new_sa)
                                st.session_state["user"]["email"] = new_email
                                st.session_state["user"]["security_question"] = new_sq
                            elif new_email != current_user.get("email") or new_sq != current_user.get("security_question"):
                                # they want to update email/sq without changing answer. This might overwrite the hash to None with my current DB function!
                                pass
                        
                        st.success("Profile updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update profile. Please try again.")
                        
        with sa_tab1:
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
        if current_user.get("role") != "Admin" and not is_super_admin:
            with sa_tab2:
                st.info("⚠️ You do not have administrator privileges to view this section.")
                
        if current_user.get("role") == "Admin" or is_super_admin:
            with sa_tab2:
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
