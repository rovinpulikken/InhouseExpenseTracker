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
    clear_recovery_otp,
    get_admin_gemini_api_key
)
from sandbox_data import (
    sandbox_get_expenses_df,
    sandbox_get_user_investments_df,
    sandbox_get_budget_status,
    mock_success
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
    page_title="FinCompass: Wealth Manager & AI Tax Planner",
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
    # ── Hero brand banner ─────────────────────────────────────────────────────
    import os as _os
    _hero_path = _os.path.join(_os.path.dirname(__file__), "assets", "brand_hero.jpg")
    if _os.path.exists(_hero_path):
        st.image(_hero_path, use_container_width=True)
    st.markdown("""
    <div style="max-width: 540px; margin: 20px auto; padding: 20px 24px 8px; border-radius: 12px;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                border: 1px solid #1d4ed8; text-align: center;
                box-shadow: 0 10px 40px -5px rgba(56,189,248,0.25);">
        <div style="font-size: 2rem; font-weight: 900;
                    background: linear-gradient(90deg, #38bdf8, #fbbf24);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                    margin-bottom: 4px;">🧭 FinCompass</div>
        <p style="color: #94a3b8; font-size: 0.9rem; margin: 0;">Smart Financial Hub &nbsp;·&nbsp; AI-Powered &nbsp;·&nbsp; 360° Wealth View</p>
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
                submit_login = st.form_submit_button("🚀 Sign In to FinCompass", type="primary", use_container_width=True)
                
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

    if st.session_state.get("is_sandbox_mode", False):
        global get_expenses_df, get_user_investments_df, get_budget_status, insert_expenses, insert_investment, update_investments_df, get_debts, get_portfolio_snapshots_deltas
        get_expenses_df = sandbox_get_expenses_df
        get_user_investments_df = sandbox_get_user_investments_df
        get_budget_status = sandbox_get_budget_status
        insert_expenses = mock_success
        insert_investment = mock_success
        update_investments_df = mock_success

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


    # ── Sidebar brand logo ────────────────────────────────────────────────────
    import os as _os
    _brand360 = _os.path.join(_os.path.dirname(__file__), "assets", "brand_360.jpg")
    if _os.path.exists(_brand360):
        st.sidebar.image(_brand360, use_container_width=True)
    else:
        st.sidebar.image("https://img.icons8.com/isometric/100/rupee.png", width=64)
    st.sidebar.markdown("""
    <div style='text-align:center; padding: 4px 0 10px;
                font-size: 1.1rem; font-weight: 800;
                background: linear-gradient(90deg, #38bdf8, #fbbf24);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
        🧭 FinCompass
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.caption("Smart Financial Hub")
    st.sidebar.markdown("---")

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
    st.markdown("<div class='main-header'>FinCompass: Smart Financial Hub</div>", unsafe_allow_html=True)
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
    # Global Sandbox Banner
    if st.session_state.get("is_sandbox_mode", False):
        st.error("🎮 **SANDBOX MODE ACTIVE**: Data is simulated. Your real financial data is safe and hidden.")

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
        # ── Slim branded header (no scroll) ──────────────────────────────────
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:10px;padding:8px 14px;
                    background:linear-gradient(90deg,#0f172a,#1e293b);
                    border-radius:8px;border-left:3px solid #38bdf8;margin-bottom:12px;'>
            <span style='font-size:1rem;'>🧭</span>
            <span style='font-size:1rem;font-weight:700;color:#38bdf8;'>FinCompass</span>
            <span style='color:#334155;'>|</span>
            <span style='color:#94a3b8;font-size:0.85rem;'>🏠 Dashboard &nbsp;·&nbsp; Welcome back, <strong style="color:#f8fafc;">{current_user['full_name']}</strong></span>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.get("is_sandbox_mode", False):
            st.info("🎯 **Sandbox Mission**: Review the simulated expenses below. Try changing the time filter to see how the dashboard updates.")
        
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
        # ── Live KPI strip ──────────────────────────────────────────────────────
        kpi_df = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
        this_month = datetime.date.today().strftime("%Y-%m")
        month_df   = kpi_df[kpi_df["expense_date"].astype(str).str.startswith(this_month)] if not kpi_df.empty else pd.DataFrame()
        last_added = kpi_df["expense_date"].max() if not kpi_df.empty else "—"

        st.markdown("""
        <style>
        .tx-kpi-row { display:flex; gap:16px; margin-bottom:18px; flex-wrap:wrap; }
        .tx-kpi-card {
            flex:1; min-width:160px;
            background: linear-gradient(135deg,#1e293b,#0f172a);
            border:1px solid #334155; border-radius:12px;
            padding:14px 18px; text-align:center;
        }
        .tx-kpi-label { color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:.05em; }
        .tx-kpi-value { color:#38bdf8; font-size:1.45rem; font-weight:700; margin-top:2px; }
        .tx-kpi-sub   { color:#475569; font-size:0.72rem; margin-top:2px; }
        </style>
        """, unsafe_allow_html=True)

        m_total  = month_df["amount"].sum()  if not month_df.empty else 0
        m_count  = len(month_df)             if not month_df.empty else 0
        fy_total = kpi_df["amount"].sum()    if not kpi_df.empty else 0
        fy_count = len(kpi_df)               if not kpi_df.empty else 0

        st.markdown(f"""
        <div class="tx-kpi-row">
          <div class="tx-kpi-card">
            <div class="tx-kpi-label">This Month</div>
            <div class="tx-kpi-value">{format_inr_short(m_total)}</div>
            <div class="tx-kpi-sub">{m_count} entries</div>
          </div>
          <div class="tx-kpi-card">
            <div class="tx-kpi-label">FY Total ({selected_fy})</div>
            <div class="tx-kpi-value">{format_inr_short(fy_total)}</div>
            <div class="tx-kpi-sub">{fy_count} entries</div>
          </div>
          <div class="tx-kpi-card">
            <div class="tx-kpi-label">Last Entry</div>
            <div class="tx-kpi-value" style="font-size:1rem;">{str(last_added)}</div>
            <div class="tx-kpi-sub">most recent date</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 4-tab layout ────────────────────────────────────────────────────────
        tx_tab_add, tx_tab_grid, tx_tab_import, tx_tab_manage = st.tabs([
            "➕ Add Entry",
            "📋 Bulk Entry Grid",
            "📤 Import Statement",
            "🗃️ Manage Records",
        ])

        # ────────────────────────────────────────────────────────────────────────
        # TAB 1 ─ Add Entry  (most common action, put first)
        # ────────────────────────────────────────────────────────────────────────
        with tx_tab_add:
            st.markdown("#### ➕ Quick Single-Expense Entry")
            st.caption("Type a description and we'll auto-suggest the category for you.")

            a1, a2, a3 = st.columns([1.2, 2.5, 1.3])
            with a1:
                q_date = st.date_input("Date", datetime.date.today(), key="q_date")
            with a2:
                q_desc = st.text_input("Description", placeholder="e.g. Swiggy biryani, Petrol, D-Mart ration", key="q_desc")
            with a3:
                q_vis = st.selectbox("Visibility", ["Family", "Private"], key="q_vis")

            b1, b2, b3 = st.columns([2.5, 1.5, 1])
            with b1:
                predicted_cat = auto_categorize_description(q_desc) if q_desc else EXPENSE_CATEGORIES[0]
                default_idx   = EXPENSE_CATEGORIES.index(predicted_cat) if predicted_cat in EXPENSE_CATEGORIES else 0
                q_cat = st.selectbox("Category  ✨ Auto-Suggested", EXPENSE_CATEGORIES, index=default_idx, key="q_cat")
            with b2:
                q_amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=100.0, key="q_amt", format="%.2f")
            with b3:
                st.markdown("<br>", unsafe_allow_html=True)
                add_clicked = st.button("➕ Add Expense", type="primary", use_container_width=True)

            if add_clicked:
                if q_amt > 0:
                    insert_expenses([{
                        "date":        q_date.isoformat(),
                        "category":    q_cat,
                        "description": q_desc,
                        "amount":      q_amt,
                        "visibility":  q_vis,
                    }], source="Quick Manual Entry", username=current_user["username"],
                       visibility=q_vis, family_id=user_family_id)
                    st.success(f"✅ Added {format_inr(q_amt)} under '{q_cat}'!")
                    st.rerun()
                else:
                    st.warning("Please enter an amount greater than ₹ 0.")

        # ────────────────────────────────────────────────────────────────────────
        # TAB 2 ─ Bulk Entry Grid
        # ────────────────────────────────────────────────────────────────────────
        with tx_tab_grid:
            st.markdown("#### 📋 Spreadsheet-Style Bulk Entry")
            st.caption("Add multiple rows at once. Click **✨ Auto-Categorize & Save** and Gemini will fill in the best category for each row.")

            g1, g2 = st.columns([3, 1])
            with g2:
                entry_vis = st.selectbox("Default Visibility", ["Family", "Private"],
                                         help="Family entries are shared; Private are visible only to you.",
                                         key="grid_vis")

            # Empty grid — no sample rows so user starts clean
            empty_grid = pd.DataFrame([
                {"date": datetime.date.today(), "category": EXPENSE_CATEGORIES[0],
                 "description": "", "amount": 0.0, "visibility": entry_vis},
            ])

            grid_edited = st.data_editor(
                empty_grid,
                num_rows="dynamic",
                column_config={
                    "date":        st.column_config.DateColumn("Date", required=True),
                    "category":    st.column_config.SelectboxColumn("Category", options=EXPENSE_CATEGORIES, required=True),
                    "description": st.column_config.TextColumn("Description",
                                    help="e.g. Amul milk, Apollo medicine, HPCL petrol"),
                    "amount":      st.column_config.NumberColumn("Amount (₹)", min_value=0.0,
                                    format="₹ %.2f", required=True),
                    "visibility":  st.column_config.SelectboxColumn("Visibility",
                                    options=["Family", "Private"], required=True),
                },
                use_container_width=True,
                key="excel_grid_manual",
            )

            gc1, gc2 = st.columns(2)
            with gc1:
                if st.button("✨ Auto-Categorize & Save", type="primary", use_container_width=True):
                    valid_rows = [r for r in grid_edited.to_dict("records")
                                  if float(r.get("amount", 0.0)) > 0]
                    if valid_rows:
                        categorized_rows = auto_categorize_records(valid_rows)
                        cnt = insert_expenses(categorized_rows, source="Bulk Grid (Auto-Categorized)",
                                              username=current_user["username"],
                                              visibility=entry_vis, family_id=user_family_id)
                        st.success(f"🎉 Auto-categorized and saved {cnt} entries!")
                        st.rerun()
                    else:
                        st.warning("Please add at least one row with an amount > 0.")
            with gc2:
                if st.button("💾 Save As-Is (No AI Categorize)", use_container_width=True):
                    valid_rows = [r for r in grid_edited.to_dict("records")
                                  if float(r.get("amount", 0.0)) > 0]
                    if valid_rows:
                        cnt = insert_expenses(valid_rows, source="Bulk Grid (Manual)",
                                              username=current_user["username"],
                                              visibility=entry_vis, family_id=user_family_id)
                        st.success(f"Saved {cnt} entries!")
                        st.rerun()
                    else:
                        st.warning("Please add at least one row with an amount > 0.")

        # ────────────────────────────────────────────────────────────────────────
        # TAB 3 ─ Import Statement
        # ────────────────────────────────────────────────────────────────────────
        with tx_tab_import:
            st.markdown("#### 📤 Import Bank / Credit-Card Statement")
            st.caption("Upload a PDF, Excel, or CSV. Gemini AI extracts and categorizes transactions automatically.")

            imp1, imp2 = st.columns([1, 2])
            with imp1:
                st.markdown("##### 📥 Download Template")
                st.write("Use our pre-formatted `.xlsx` template to log expenses offline.")
                excel_bytes = generate_excel_template()
                st.download_button(
                    label="📥 Download Excel Template",
                    data=excel_bytes,
                    file_name="FinCompass_Expense_Template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with imp2:
                st.markdown("##### 🤖 AI Statement Parser")
                upload_vis    = st.radio("Visibility for Imported Entries", ["Family", "Private"],
                                        horizontal=True, key="upload_vis")
                uploaded_file = st.file_uploader("Choose PDF, Excel, or CSV",
                                                 type=["xlsx", "xls", "csv", "pdf"],
                                                 key="excel_uploader")

                pdf_password = ""
                if uploaded_file and uploaded_file.name.lower().endswith(".pdf"):
                    pdf_password = st.text_input("PDF Password (if protected)", type="password",
                                                 help="Enter password if your bank statement is password-protected")

                gemini_api_key = (current_user.get("gemini_api_key")
                                  or get_admin_gemini_api_key()
                                  or os.environ.get("GEMINI_API_KEY", "")
                                  or st.secrets.get("GEMINI_API_KEY", ""))

                if uploaded_file:
                    if st.button("🚀 Parse & Auto-Categorize", type="primary", use_container_width=True):
                        with st.spinner("🤖 AI is reading your statement — this may take 15–30 s…"):
                            is_std = (uploaded_file.name.lower().endswith((".xlsx", ".csv"))
                                      and "statement" not in uploaded_file.name.lower()
                                      and "bill" not in uploaded_file.name.lower())
                            if is_std:
                                try:
                                    df_parsed, msg = import_from_excel_or_csv(
                                        uploaded_file, username=current_user["username"],
                                        visibility=upload_vis, family_id=user_family_id)
                                    if df_parsed is not None and not df_parsed.empty:
                                        df_parsed = detect_and_flag_duplicates(
                                            df_parsed, current_user["username"], view_mode, user_family_id)
                                        st.session_state["parsed_statement_df"] = df_parsed
                                        st.success(f"{msg} Review below.")
                                    else:
                                        st.error(msg)
                                except Exception as e:
                                    st.error(f"Template import error: {e}. Try renaming the file to include 'statement' to force AI parsing.")
                            else:
                                if not gemini_api_key:
                                    st.error("⚠️ A Gemini API Key is required for AI parsing. Add it in **My Profile**.")
                                else:
                                    from statement_parser import parse_expense_statement_with_gemini
                                    try:
                                        raw_json  = parse_expense_statement_with_gemini(
                                            uploaded_file.getvalue(), uploaded_file.name,
                                            gemini_api_key, pdf_password)
                                        df_parsed = pd.DataFrame(raw_json)
                                        if not df_parsed.empty:
                                            for col in ["date", "description", "amount", "transaction_type", "category"]:
                                                if col not in df_parsed.columns:
                                                    df_parsed[col] = ""
                                            df_parsed["transaction_type"] = df_parsed["transaction_type"].astype(str).str.strip().str.title()
                                            df_parsed["category"]         = df_parsed["category"].astype(str).str.strip().str.title()
                                            df_parsed = df_parsed[df_parsed["transaction_type"] != "Income"]
                                            df_parsed = df_parsed[~df_parsed["category"].str.contains("Refund", case=False, na=False)]

                                            if not df_parsed.empty:
                                                df_parsed["amount"] = pd.to_numeric(df_parsed["amount"], errors="coerce").fillna(0.0)
                                                df_parsed["date"]   = (pd.to_datetime(df_parsed["date"], errors="coerce")
                                                                        .dt.strftime("%Y-%m-%d")
                                                                        .fillna(str(datetime.date.today())))
                                                df_parsed = detect_and_flag_duplicates(
                                                    df_parsed, current_user["username"], view_mode, user_family_id)
                                                st.session_state["parsed_statement_df"] = df_parsed
                                                st.rerun()
                                            else:
                                                st.warning("No expense transactions found (all filtered as Income/Refunds).")
                                        else:
                                            st.warning("No transactions found in the document.")
                                    except Exception as e:
                                        st.error(f"Failed to parse statement: {e}")

            # Review table — shown outside the columns so it has full width
            if "parsed_statement_df" in st.session_state:
                st.markdown("---")
                st.markdown("### 🔍 Review & Confirm Extracted Transactions")
                st.info("Uncheck duplicates you don't want, correct categories/amounts, then click **Confirm & Save**.")

                edited_df = st.data_editor(
                    st.session_state["parsed_statement_df"],
                    num_rows="dynamic",
                    column_config={
                        "import":            st.column_config.CheckboxColumn("Import?", default=True),
                        "duplicate_warning": st.column_config.CheckboxColumn("Duplicate?", disabled=True,
                                             help="Checked if same Date + Amount already exists."),
                        "date":              st.column_config.TextColumn("Date (YYYY-MM-DD)"),
                        "description":       st.column_config.TextColumn("Description"),
                        "amount":            st.column_config.NumberColumn("Amount", required=True),
                        "transaction_type":  st.column_config.SelectboxColumn("Type",
                                             options=["Expense", "Income"], required=True),
                        "category":          st.column_config.SelectboxColumn("Category",
                                             options=EXPENSE_CATEGORIES + ["Salary", "Refund", "Interest"],
                                             required=True),
                    },
                    use_container_width=True,
                    key="statement_editor",
                )

                cs1, cs2 = st.columns(2)
                with cs1:
                    if st.button("💾 Confirm & Save to Database", type="primary", use_container_width=True):
                        valid_records = []
                        for r in edited_df.to_dict("records"):
                            if r.get("import", True) and str(r.get("transaction_type", "")).strip().lower() != "income":
                                r["visibility"] = upload_vis
                                try:
                                    r["amount"] = abs(float(str(r.get("amount", 0)).replace(",", "")))
                                except Exception:
                                    pass
                                valid_records.append(r)
                        try:
                            if valid_records:
                                cnt = insert_expenses(
                                    valid_records,
                                    source=f"AI Import ({uploaded_file.name})",
                                    username=current_user["username"],
                                    visibility=upload_vis,
                                    family_id=user_family_id,
                                )
                                st.success(f"✅ Saved {cnt} transactions!")
                            else:
                                st.warning("No valid expense transactions to save.")
                            del st.session_state["parsed_statement_df"]
                            import time; time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")
                with cs2:
                    if st.button("❌ Discard & Cancel", use_container_width=True):
                        del st.session_state["parsed_statement_df"]
                        st.rerun()

        # ────────────────────────────────────────────────────────────────────────
        # TAB 4 ─ Manage Records  (Edit / Delete / Duplicates — consolidated)
        # ────────────────────────────────────────────────────────────────────────
        with tx_tab_manage:
            st.markdown("#### 🗃️ Manage Existing Records")

            expenses_df_all = get_expenses_df(fy=selected_fy, username=current_user["username"],
                                               view_mode=view_mode)

            if expenses_df_all.empty:
                st.info(f"No expense records found for **{selected_fy}**. Add some entries first!")
            else:
                # ── Section 1: Inline table editor ──────────────────────────────
                with st.expander("📝 Edit All Records in Table (Inline Grid)", expanded=True):
                    st.caption("Edit dates, categories, descriptions, or amounts directly. Click **Save Changes** when done.")
                    edited_df_inline = st.data_editor(
                        expenses_df_all[["id", "expense_date", "category", "description",
                                          "amount", "visibility", "source_note"]],
                        num_rows="dynamic",
                        column_config={
                            "id":           st.column_config.NumberColumn("ID", disabled=True),
                            "expense_date": st.column_config.DateColumn("Date", required=True),
                            "category":     st.column_config.SelectboxColumn("Category",
                                            options=EXPENSE_CATEGORIES, required=True),
                            "description":  st.column_config.TextColumn("Description"),
                            "amount":       st.column_config.NumberColumn("Amount (₹)", min_value=0.0,
                                            format="₹ %.2f", required=True),
                            "visibility":   st.column_config.SelectboxColumn("Visibility",
                                            options=["Family", "Private"], required=True),
                            "source_note":  st.column_config.TextColumn("Source", disabled=True),
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="inline_editor_tab3",
                    )
                    if st.button("💾 Save Changes", type="primary", use_container_width=True):
                        updated_count = update_expenses_df(edited_df_inline)
                        st.success(f"🎉 Updated {updated_count} record(s)!")
                        st.rerun()

                # ── Section 2: Pick-a-record editor / deleter ────────────────────
                with st.expander("🔍 Find & Edit / Delete a Single Record"):
                    record_ids   = expenses_df_all["id"].tolist()
                    selected_id  = st.selectbox("Select Record by ID", record_ids, key="single_edit_id",
                                                format_func=lambda i: f"#{i} — "
                                                    f"{expenses_df_all.loc[expenses_df_all['id']==i, 'expense_date'].values[0]}  "
                                                    f"{expenses_df_all.loc[expenses_df_all['id']==i, 'description'].values[0]}  "
                                                    f"({format_inr(float(expenses_df_all.loc[expenses_df_all['id']==i, 'amount'].values[0]))})")
                    target_record = expenses_df_all[expenses_df_all["id"] == selected_id].iloc[0]

                    e1, e2, e3, e4, e5 = st.columns([1.2, 2, 2, 1.4, 1.2])
                    with e1:
                        cur_dt  = pd.to_datetime(target_record["expense_date"]).date() if not pd.isna(target_record["expense_date"]) else datetime.date.today()
                        new_dt  = st.date_input("Date", cur_dt, key="single_new_dt")
                    with e2:
                        cur_cat = target_record["category"] if target_record["category"] in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
                        new_cat = st.selectbox("Category", EXPENSE_CATEGORIES,
                                               index=EXPENSE_CATEGORIES.index(cur_cat), key="single_new_cat")
                    with e3:
                        new_desc = st.text_input("Description", value=str(target_record["description"]), key="single_new_desc")
                    with e4:
                        new_amt = st.number_input("Amount (₹)", min_value=0.0,
                                                   value=float(target_record["amount"]), step=100.0, key="single_new_amt")
                    with e5:
                        cur_vis = target_record.get("visibility", "Family")
                        new_vis = st.selectbox("Visibility", ["Family", "Private"],
                                               index=0 if cur_vis == "Family" else 1, key="single_new_vis")

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"💾 Update Record #{selected_id}", type="primary", use_container_width=True):
                            update_expenses_df(pd.DataFrame([{
                                "id": selected_id, "expense_date": new_dt.isoformat(),
                                "category": new_cat, "description": new_desc,
                                "amount": new_amt, "visibility": new_vis,
                            }]))
                            st.success(f"✅ Record #{selected_id} updated!")
                            st.rerun()
                    with btn_col2:
                        if st.button(f"🗑️ Delete Record #{selected_id}", type="secondary", use_container_width=True):
                            delete_expense(int(selected_id))
                            st.success(f"🗑️ Record #{selected_id} deleted.")
                            st.rerun()

                # ── Section 3: Duplicate detector ───────────────────────────────
                with st.expander("🕵️ Detect & Remove Duplicates"):
                    st.write("Scans **all Financial Years** for entries with the same Date + Amount.")
                    all_time_df = get_expenses_df(fy="All FYs", username=current_user["username"], view_mode=view_mode)
                    if not all_time_df.empty:
                        dup_counts = all_time_df.groupby(["expense_date", "amount"]).size().reset_index(name="count")
                        dup_groups = dup_counts[dup_counts["count"] > 1]
                        if dup_groups.empty:
                            st.success("✅ No duplicate entries found across any Financial Year!")
                        else:
                            st.warning(f"Found {len(dup_groups)} duplicate group(s).")
                            merged = pd.merge(all_time_df, dup_groups, on=["expense_date", "amount"])
                            merged = merged.sort_values(["expense_date", "amount", "id"])
                            merged["Delete"] = merged.duplicated(subset=["expense_date", "amount"], keep="first")
                            edited_dups = st.data_editor(
                                merged[["Delete", "id", "expense_date", "category", "description", "amount", "source_note"]],
                                num_rows="fixed",
                                column_config={
                                    "Delete":       st.column_config.CheckboxColumn("🗑️ Delete?"),
                                    "id":           st.column_config.NumberColumn("ID", disabled=True),
                                    "expense_date": st.column_config.DateColumn("Date", disabled=True),
                                    "category":     st.column_config.TextColumn("Category", disabled=True),
                                    "description":  st.column_config.TextColumn("Description", disabled=True),
                                    "amount":       st.column_config.NumberColumn("Amount", format="₹ %.2f", disabled=True),
                                    "source_note":  st.column_config.TextColumn("Source", disabled=True),
                                },
                                use_container_width=True, hide_index=True, key="dup_editor",
                            )
                            to_delete = edited_dups[edited_dups["Delete"] == True]["id"].tolist()
                            if to_delete:
                                if st.button(f"🗑️ Delete {len(to_delete)} Selected Duplicate(s)", type="primary"):
                                    for d_id in to_delete:
                                        delete_expense(int(d_id))
                                    st.success(f"Deleted {len(to_delete)} duplicate record(s).")
                                    st.rerun()
                    else:
                        st.info("No records to scan.")

                # ── Section 4: Danger Zone ───────────────────────────────────────
                with st.expander("⚠️ Danger Zone — Bulk Delete", expanded=False):
                    st.warning("**This cannot be undone.** This permanently removes all entries for a selected month.")
                    if "Month_Year" in expenses_df_all.columns:
                        available_m    = sorted(expenses_df_all["Month_Year"].unique().tolist(), reverse=True)
                        del_month_target = st.selectbox("Select Month to Wipe", available_m,
                                                         format_func=format_month_label, key="bulk_del_m")
                        month_records  = expenses_df_all[expenses_df_all["Month_Year"] == del_month_target]
                        m_sum          = month_records["amount"].sum()
                        st.error(f"Month **{del_month_target}** → **{len(month_records)} entries**, total **{format_inr(m_sum)}**.")
                        confirm_chk    = st.checkbox(f"✅ I confirm — delete ALL entries for {del_month_target}", key="chk_bulk_del")
                        if st.button(f"🔥 Wipe All Data for {del_month_target}",
                                     type="primary", disabled=not confirm_chk, use_container_width=True):
                            cnt_del = delete_month_expenses(del_month_target)
                            st.success(f"Deleted {cnt_del} records for {del_month_target}.")
                            st.rerun()




        # ----------------------------------------------------
        # 📈 INSIGHTS & ANALYTICS
        # ----------------------------------------------------
    elif nav_selection == "📈 Insights & Analytics":
        # ── Slim branded header ────────────────────────────────────────────────
        st.markdown("""
        <div style='display:flex;align-items:center;gap:10px;padding:8px 14px;
                    background:linear-gradient(90deg,#0f172a,#1e293b);
                    border-radius:8px;border-left:3px solid #818cf8;margin-bottom:12px;'>
            <span style='font-size:1rem;'>🧭</span>
            <span style='font-size:1rem;font-weight:700;color:#818cf8;'>FinCompass</span>
            <span style='color:#334155;'>|</span>
            <span style='color:#94a3b8;font-size:0.85rem;'>📈 Insights &amp; Analytics &nbsp;·&nbsp; AI-Powered &nbsp;·&nbsp; Spending Trends &nbsp;·&nbsp; Inflation Tracking</span>
        </div>
        """, unsafe_allow_html=True)

        # ── KPI Strip ───────────────────────────────────────────────────────────
        ia_all_df = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
        ia_this_month = datetime.date.today().strftime("%Y-%m")
        ia_month_df   = ia_all_df[ia_all_df["expense_date"].astype(str).str.startswith(ia_this_month)] if not ia_all_df.empty else pd.DataFrame()
        ia_m_total    = ia_month_df["amount"].sum() if not ia_month_df.empty else 0
        ia_fy_total   = ia_all_df["amount"].sum()   if not ia_all_df.empty else 0
        ia_top_cat    = ia_all_df.groupby("category")["amount"].sum().idxmax() if not ia_all_df.empty else "—"

        # Biggest spike category vs prior month
        ia_cur_mo_cat = ia_month_df.groupby("category")["amount"].sum() if not ia_month_df.empty else pd.Series(dtype=float)
        prior_month   = (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
        ia_prior_df   = ia_all_df[ia_all_df["expense_date"].astype(str).str.startswith(prior_month)] if not ia_all_df.empty else pd.DataFrame()
        ia_prior_cat  = ia_prior_df.groupby("category")["amount"].sum() if not ia_prior_df.empty else pd.Series(dtype=float)
        if not ia_cur_mo_cat.empty and not ia_prior_cat.empty:
            ia_delta      = (ia_cur_mo_cat - ia_prior_cat).dropna()
            ia_spike_cat  = ia_delta.idxmax() if not ia_delta.empty else "—"
            ia_spike_val  = ia_delta.max()    if not ia_delta.empty else 0
        else:
            ia_spike_cat, ia_spike_val = "—", 0

        st.markdown("""
        <style>
        .ia-kpi-row { display:flex; gap:14px; margin-bottom:20px; flex-wrap:wrap; }
        .ia-kpi-card {
            flex:1; min-width:150px;
            background:linear-gradient(135deg,#1e293b,#0f172a);
            border:1px solid #334155; border-radius:12px;
            padding:13px 16px; text-align:center;
        }
        .ia-kpi-label { color:#64748b; font-size:0.72rem; text-transform:uppercase; letter-spacing:.06em; }
        .ia-kpi-value { color:#38bdf8; font-size:1.35rem; font-weight:700; margin-top:3px; }
        .ia-kpi-sub   { color:#475569; font-size:0.7rem; margin-top:2px; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="ia-kpi-row">
          <div class="ia-kpi-card">
            <div class="ia-kpi-label">This Month's Spend</div>
            <div class="ia-kpi-value">{format_inr_short(ia_m_total)}</div>
            <div class="ia-kpi-sub">{ia_this_month}</div>
          </div>
          <div class="ia-kpi-card">
            <div class="ia-kpi-label">FY Total ({selected_fy})</div>
            <div class="ia-kpi-value">{format_inr_short(ia_fy_total)}</div>
            <div class="ia-kpi-sub">all categories</div>
          </div>
          <div class="ia-kpi-card">
            <div class="ia-kpi-label">Top Spending Category</div>
            <div class="ia-kpi-value" style="font-size:0.95rem;">{ia_top_cat}</div>
            <div class="ia-kpi-sub">this FY</div>
          </div>
          <div class="ia-kpi-card">
            <div class="ia-kpi-label">Biggest Spike vs Last Month</div>
            <div class="ia-kpi-value" style="font-size:0.95rem; color:#f87171;">{ia_spike_cat}</div>
            <div class="ia-kpi-sub">{format_inr_short(ia_spike_val)} over prior month</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 4-tab layout ────────────────────────────────────────────────────────
        ia_tab_overview, ia_tab_drill, ia_tab_anomaly, ia_tab_inflation = st.tabs([
            "📊 Spending Overview",
            "🔍 Drill Down",
            "🚨 Anomaly Alerts",
            "📉 Inflation Forecast",
        ])

        # ────────────────────────────────────────────────────────────────────────
        # TAB 1 ─ Spending Overview  (charts first — what users want to see)
        # ────────────────────────────────────────────────────────────────────────
        with ia_tab_overview:
            trend_df = get_monthly_trend_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)

            if trend_df.empty:
                st.info(f"No spending data yet for **{selected_fy}**. Add some transactions first!")
            else:
                ov1, ov2 = st.columns([3, 2])

                with ov1:
                    st.markdown("##### 📅 Monthly Spend by Category")
                    fig_month = px.bar(
                        trend_df, x="YearMonth", y="Monthly_Total", color="category",
                        labels={"Monthly_Total": "Amount (₹)", "YearMonth": "Month"},
                        template="plotly_dark",
                    )
                    fig_month.update_layout(
                        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                    font=dict(size=10)),
                        margin=dict(l=10, r=10, t=40, b=10),
                        title=None,
                    )
                    st.plotly_chart(fig_month, use_container_width=True)

                with ov2:
                    st.markdown("##### 🍩 Category Share (Full FY)")
                    cat_totals = ia_all_df.groupby("category")["amount"].sum().reset_index() if not ia_all_df.empty else pd.DataFrame()
                    if not cat_totals.empty:
                        fig_donut = px.pie(
                            cat_totals, values="amount", names="category",
                            hole=0.52, template="plotly_dark",
                            color_discrete_sequence=px.colors.qualitative.Pastel,
                        )
                        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                        fig_donut.update_layout(
                            paper_bgcolor="#1e293b",
                            showlegend=False,
                            margin=dict(l=10, r=10, t=10, b=10),
                        )
                        st.plotly_chart(fig_donut, use_container_width=True)

                st.markdown("---")
                st.markdown("##### 📊 Quarterly Breakdown")
                q_trend_df = get_quarterly_trend_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
                if not q_trend_df.empty:
                    fig_q = px.bar(
                        q_trend_df, x="quarter", y="Quarterly_Total", color="category",
                        barmode="group",
                        labels={"Quarterly_Total": "Amount (₹)", "quarter": "Quarter"},
                        template="plotly_dark",
                    )
                    fig_q.update_layout(
                        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                    font=dict(size=10)),
                        margin=dict(l=10, r=10, t=40, b=10),
                        title=None,
                    )
                    st.plotly_chart(fig_q, use_container_width=True)

        # ────────────────────────────────────────────────────────────────────────
        # TAB 2 ─ Drill Down  (Itemized Explorer — simplified controls)
        # ────────────────────────────────────────────────────────────────────────
        with ia_tab_drill:
            # ── Cumulative metric strip ──────────────────────────────────────────
            cum_metrics = get_cumulative_metrics(
                fy=selected_fy if selected_fy != "All FYs" else None,
                username=current_user["username"], view_mode=view_mode)

            dd1, dd2, dd3, dd4 = st.columns(4)
            for col, label, key, color in [
                (dd1, "QTD", "QTD", "#38bdf8"),
                (dd2, "H1  (Apr–Sep)", "H1", "#818cf8"),
                (dd3, "H2  (Oct–Mar)", "H2", "#c084fc"),
                (dd4, "YTD / Full FY", "YTD", "#34d399"),
            ]:
                with col:
                    col.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value" style="color:{color};">{format_inr_short(cum_metrics[key])}</div>
                        <div style="color:#64748b;font-size:0.78rem;">{format_inr(cum_metrics[key])}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Horizontal filter row ────────────────────────────────────────────
            fc1, fc2, fc3 = st.columns([1.4, 2, 1])
            with fc1:
                granularity = st.selectbox("Period", ["Monthly", "Quarterly", "Half-Yearly", "Full FY"], key="ia_gran")
            with fc3:
                search_term = st.text_input("🔍 Search description", placeholder="e.g. Swiggy", key="ia_search")

            all_df = get_expenses_df(fy=selected_fy, username=current_user["username"], view_mode=view_mode)
            filtered_df  = pd.DataFrame()
            period_title = ""

            with fc2:
                if granularity == "Monthly":
                    if not all_df.empty and "Month_Year" in all_df.columns:
                        months_available = sorted(all_df["Month_Year"].unique().tolist(), reverse=True)
                        sel_month = st.selectbox("Month", ["All"] + months_available, format_func=format_month_label, key="ia_month")
                        filtered_df  = all_df if sel_month == "All" else all_df[all_df["Month_Year"] == sel_month]
                        period_title = f"All Months — {selected_fy}" if sel_month == "All" else format_month_label(sel_month)
                    else:
                        st.info("No data yet.")
                elif granularity == "Quarterly":
                    sel_q       = st.selectbox("Quarter", ["Q1 (Apr–Jun)", "Q2 (Jul–Sep)", "Q3 (Oct–Dec)", "Q4 (Jan–Mar)"], key="ia_q")
                    q_code      = sel_q.split()[0]
                    filtered_df = all_df[all_df["quarter"] == q_code] if not all_df.empty else pd.DataFrame()
                    period_title = sel_q
                elif granularity == "Half-Yearly":
                    sel_h        = st.selectbox("Half Year", ["H1 (Apr–Sep)", "H2 (Oct–Mar)"], key="ia_h")
                    h_code       = sel_h.split()[0]
                    filtered_df  = all_df[all_df.get("half_year", pd.Series()) == h_code] if not all_df.empty and "half_year" in all_df.columns else pd.DataFrame()
                    period_title = sel_h
                else:
                    filtered_df  = all_df
                    period_title = f"Full FY — {selected_fy}"

            # Apply description search
            if search_term and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df["description"].astype(str).str.contains(search_term, case=False, na=False)]

            st.markdown("---")
            if filtered_df.empty:
                st.info("No transactions found for the selected filter.")
            else:
                period_total_val = filtered_df["amount"].sum()

                # Category summary bar chart + table side by side
                cs1, cs2 = st.columns([2, 3])
                with cs1:
                    st.markdown(f"**{period_title}** — {format_inr(period_total_val)} across {len(filtered_df)} entries")
                    item_cat_summary = (
                        filtered_df.groupby("category")["amount"]
                        .agg(Total="sum", Count="count").reset_index()
                    )
                    item_cat_summary["Share %"] = (item_cat_summary["Total"] / period_total_val * 100).round(1)
                    item_cat_summary = item_cat_summary.sort_values("Total", ascending=False)
                    st.dataframe(
                        item_cat_summary,
                        column_config={
                            "category": st.column_config.TextColumn("Category"),
                            "Total":    st.column_config.NumberColumn("Total (₹)", format="₹ %.2f"),
                            "Count":    st.column_config.NumberColumn("Entries"),
                            "Share %":  st.column_config.NumberColumn("Share", format="%.1f %%"),
                        },
                        use_container_width=True, hide_index=True,
                    )
                with cs2:
                    fig_dd = px.bar(
                        item_cat_summary, x="Total", y="category", orientation="h",
                        color="Share %", color_continuous_scale="Blues",
                        labels={"Total": "₹", "category": ""},
                        template="plotly_dark",
                    )
                    fig_dd.update_layout(
                        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                        coloraxis_showscale=False, yaxis=dict(autorange="reversed"),
                        margin=dict(l=10, r=10, t=10, b=10),
                    )
                    st.plotly_chart(fig_dd, use_container_width=True)

                st.markdown("##### 📋 Transaction Ledger")
                st.dataframe(
                    filtered_df[["expense_date", "category", "description", "amount", "visibility", "username"]].sort_values("expense_date", ascending=False),
                    column_config={
                        "expense_date": st.column_config.DateColumn("Date"),
                        "category":     st.column_config.TextColumn("Category"),
                        "description":  st.column_config.TextColumn("Description"),
                        "amount":       st.column_config.NumberColumn("Amount (₹)", format="₹ %.2f"),
                        "visibility":   st.column_config.TextColumn("Visibility"),
                        "username":     st.column_config.TextColumn("Logged By"),
                    },
                    use_container_width=True, hide_index=True,
                )

        # ────────────────────────────────────────────────────────────────────────
        # TAB 3 ─ Anomaly Alerts  (defaults to current month, AI button at top)
        # ────────────────────────────────────────────────────────────────────────
        with ia_tab_anomaly:
            st.markdown("#### 🚨 Expense Surge & Anomaly Detector")
            st.caption("Automatically compares your spending in any period against your historical baseline to flag unusual spikes.")

            an1, an2 = st.columns([1.4, 2])
            with an1:
                timeframe_type = st.selectbox(
                    "Granularity",
                    ["Month-wise", "Quarter-wise", "Half Year-wise", "Financial Year"],
                    key="surge_tf_type",
                )
            _, available_periods = get_period_surge_analytics(
                timeframe_type=timeframe_type, selected_period=None,
                fy=selected_fy, username=current_user["username"],
                view_mode=view_mode, family_id=user_family_id,
            )
            with an2:
                if available_periods:
                    fmt_fn = format_month_label if timeframe_type == "Month-wise" else str
                    # Default to most-recent period (index 0)
                    selected_period = st.selectbox(
                        "Period", available_periods, format_func=fmt_fn, key="surge_target_period",
                    )
                else:
                    selected_period = None
                    st.info("No records available for the selected timeframe.")

            if selected_period:
                period_surge_df, _ = get_period_surge_analytics(
                    timeframe_type=timeframe_type, selected_period=selected_period,
                    fy=selected_fy, username=current_user["username"],
                    view_mode=view_mode, family_id=user_family_id,
                )

                if not period_surge_df.empty:
                    anomalies_df    = period_surge_df[period_surge_df["Is_Anomaly"] == True]
                    top_surge_row   = period_surge_df.iloc[0]
                    top_surging_cat = top_surge_row["category"]
                    top_surge_pct   = top_surge_row["Surge_%"]
                    total_excess    = period_surge_df["Surge_Amount"].apply(lambda x: max(0.0, x)).sum()

                    # ── 3 metric cards ───────────────────────────────────────────
                    am1, am2, am3 = st.columns(3)
                    am1.metric("🔥 Top Surging Category", top_surging_cat, f"+{top_surge_pct:.1f}%")
                    am2.metric("💸 Excess Spend over Baseline", format_inr(total_excess))
                    am3.metric("⚠️ Anomaly Spikes Detected", f"{len(anomalies_df)} categories")

                    # ── AI button RIGHT AT THE TOP ───────────────────────────────
                    gemini_api_key_an = (current_user.get("gemini_api_key") or get_admin_gemini_api_key()
                                         or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", ""))
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🤖 Get AI Cost-Saving Advice for This Period", type="primary", use_container_width=True):
                        with st.spinner("🤖 Gemini AI is analyzing spending patterns…"):
                            ai_advice = generate_ai_spend_rationalization(
                                period_surge_df, timeframe_label=f"{timeframe_type} ({selected_period})")
                        st.success("🎉 AI Analysis Complete!")
                        st.info(ai_advice.get("summary", ""))
                        st.markdown(f"#### 💰 Potential Savings Target: **{ai_advice.get('total_potential_savings', '₹ 0')}**")
                        for idx, rec in enumerate(ai_advice.get("recommendations", []), 1):
                            with st.expander(f"💡 #{idx} {rec.get('category','—')} — Est. Savings: {rec.get('est_savings','₹ 0')}"):
                                st.markdown(f"**Issue:** {rec.get('issue','')}")
                                st.markdown(f"**Advice:** {rec.get('suggestion','')}")

                    st.markdown("---")

                    # ── Chart: Period vs Baseline ────────────────────────────────
                    chart_df = period_surge_df[period_surge_df["Period_Spend"] > 0].copy()
                    if not chart_df.empty:
                        st.markdown(f"##### 📊 Category Spend vs Baseline — {selected_period}")
                        fig_surge = px.bar(
                            chart_df, x="category", y=["Period_Spend", "Baseline_Avg"],
                            barmode="group",
                            labels={"value": "Amount (₹)", "category": "Category", "variable": ""},
                            color_discrete_map={"Period_Spend": "#ef4444", "Baseline_Avg": "#3b82f6"},
                            template="plotly_dark", height=380,
                        )
                        fig_surge.update_layout(
                            paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            margin=dict(l=10, r=10, t=30, b=10),
                        )
                        st.plotly_chart(fig_surge, use_container_width=True)

                    # ── Detailed anomaly table ───────────────────────────────────
                    st.markdown(f"##### 📝 Surge & Anomaly Table — {selected_period}")
                    st.dataframe(
                        period_surge_df[["category", "Period_Spend", "Baseline_Avg", "Surge_Amount", "Surge_%", "Is_Anomaly"]],
                        column_config={
                            "category":     st.column_config.TextColumn("Category"),
                            "Period_Spend": st.column_config.NumberColumn(f"Spend (₹)", format="₹ %.2f"),
                            "Baseline_Avg": st.column_config.NumberColumn("Baseline Avg (₹)", format="₹ %.2f"),
                            "Surge_Amount": st.column_config.NumberColumn("Excess (₹)", format="₹ %.2f"),
                            "Surge_%":      st.column_config.NumberColumn("Spike %", format="%.1f %%"),
                            "Is_Anomaly":   st.column_config.CheckboxColumn("Anomaly?"),
                        },
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("No transaction data found for this period.")
            else:
                st.info("Select a timeframe above to view anomaly analysis.")

        # ────────────────────────────────────────────────────────────────────────
        # TAB 4 ─ Inflation Forecast  (flattened — no nested sub-tabs)
        # ────────────────────────────────────────────────────────────────────────
        with ia_tab_inflation:
            st.markdown("#### 📉 Inflation & Purchasing Power")

            # ── Section 1: CPI chart + erosion calculator ────────────────────────
            inf1, inf2 = st.columns([1.4, 2])
            with inf1:
                st.markdown("##### Purchasing Power Erosion Calculator")
                st.caption("How much more do you need to spend today vs a past year?")
                base_yr    = st.number_input("Base Year",       min_value=2018, max_value=2025, value=2020, key="inf_base")
                curr_yr    = st.number_input("Comparison Year", min_value=2019, max_value=2026, value=2025, key="inf_curr")
                sample_amt = st.number_input("Amount in Base Year (₹)", value=10000.0, step=1000.0, key="inf_amt")
                cum_inf    = calculate_cpi_inflation(base_yr, curr_yr)
                req_amt    = sample_amt * (1 + cum_inf / 100)
                st.success(f"₹ {sample_amt:,.0f} in {base_yr} → **{format_inr(req_amt)}** in {curr_yr}  (+{cum_inf:.1f}% CPI inflation)")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### Category CPI Benchmarks")
                cat_cpi_list = [
                    {"Category": cat, "CPI Group": d["cpi_group"], "Avg Inflation %": d["avg_inflation"]}
                    for cat, d in CPI_CATEGORY_INFLATION.items()
                ]
                st.dataframe(pd.DataFrame(cat_cpi_list), use_container_width=True, hide_index=True)

            with inf2:
                st.markdown("##### Indian CPI Annual Rate (%)")
                cpi_df  = get_cpi_df()
                fig_cpi = px.line(
                    cpi_df, x="Year", y="CPI Inflation (%)", markers=True,
                    template="plotly_dark", color_discrete_sequence=["#fbbf24"],
                )
                fig_cpi.update_layout(
                    paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                    margin=dict(l=10, r=10, t=20, b=10), title=None,
                )
                st.plotly_chart(fig_cpi, use_container_width=True)

            st.markdown("---")

            # ── Section 2: Personal Expense Predictor ───────────────────────────
            st.markdown("##### 🔮 Predict Your Future Expenses")
            st.caption("Uses your personal spending category weightings to calculate a tailored inflation rate — not the generic national CPI.")

            hist_breakdown_df = get_category_breakdown(
                fy=None,
                username=current_user["username"] if view_mode == "Personal" else None,
                view_mode=view_mode, family_id=user_family_id,
            )
            personal_rate = calculate_personal_inflation_rate(hist_breakdown_df)

            pr1, pr2, pr3 = st.columns([1, 1, 1])
            with pr1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Your Personalised Inflation Rate</div>
                    <div class="metric-value" style="color:#f87171;">{personal_rate}%</div>
                    <div style="color:#64748b;font-size:0.78rem;">based on your category spending mix</div>
                </div>""", unsafe_allow_html=True)
            with pr2:
                custom_inflation = st.number_input("Override Inflation Rate (%)", value=float(personal_rate),
                                                    step=0.5, format="%.2f", key="pred_inf")
                pred_base_year   = st.number_input("Base Year",   min_value=2020, max_value=2030, value=2024, key="pred_base")
            with pr3:
                pred_target_year = st.number_input("Target Year", min_value=2025, max_value=2060, value=2034, key="pred_target")
                # Baseline expense
                default_expense = 1_000_000.0
                fys_list = get_all_financial_years(
                    username=current_user["username"] if view_mode == "Personal" else None,
                    view_mode=view_mode, family_id=user_family_id)
                if fys_list and not hist_breakdown_df.empty:
                    latest_fy_df = get_category_breakdown(
                        fy=fys_list[0],
                        username=current_user["username"] if view_mode == "Personal" else None,
                        view_mode=view_mode, family_id=user_family_id)
                    if not latest_fy_df.empty and "Total_Amount" in latest_fy_df.columns:
                        default_expense = float(latest_fy_df["Total_Amount"].sum())
                baseline_expense = st.number_input("Base Year Annual Spend (₹)", value=default_expense,
                                                    step=50000.0, key="pred_baseline")

            if pred_target_year > pred_base_year:
                proj_years    = list(range(pred_base_year, pred_target_year + 1))
                proj_expenses = [baseline_expense * ((1 + custom_inflation / 100.0) ** (y - pred_base_year)) for y in proj_years]
                proj_df       = pd.DataFrame({"Year": proj_years, "Projected Annual Spend (₹)": proj_expenses})
                fig_proj      = px.bar(
                    proj_df, x="Year", y="Projected Annual Spend (₹)",
                    template="plotly_dark", color_discrete_sequence=["#ef4444"],
                )
                fig_proj.update_layout(
                    paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                    margin=dict(l=10, r=10, t=20, b=10), title=None,
                )
                st.plotly_chart(fig_proj, use_container_width=True)
                st.success(f"By **{pred_target_year}** you'll need **{format_inr(proj_expenses[-1])}** annually to maintain your current lifestyle.")
            else:
                st.warning("Target year must be greater than base year.")

        # ----------------------------------------------------
        # 🔮 WEALTH & PLANNING
        # ----------------------------------------------------
    elif nav_selection == "🔮 Wealth & Planning":
        target_fy_clean = selected_fy if selected_fy != "All FYs" else (all_fys[0] if all_fys else "FY 2024-25")

        # ── Common data fetched once ─────────────────────────────────────────────
        from database import get_user_investments_df
        inv_df        = get_user_investments_df(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)
        debts_df_wp   = get_debts(family_id=user_family_id)
        goals_df_wp   = get_savings_goals(family_id=user_family_id)
        income_df_wp  = None  # lazy-loaded in Tax Planner tab

        tot_invested   = float(inv_df["investment_amount"].sum()) if not inv_df.empty else 0.0
        tot_portfolio  = float(inv_df["current_value"].sum())      if not inv_df.empty else 0.0
        tot_debt_wp    = float(debts_df_wp["outstanding_principal"].sum()) if not debts_df_wp.empty else 0.0
        net_worth      = tot_portfolio - tot_debt_wp

        # Monthly savings rate  (income from session / budget dict)
        _monthly_inc_wp = float(st.session_state.get("budget_dict", {}).get("__income__", 0.0)) or 100_000.0
        _monthly_exp_wp = float(total_spent / max(1, num_months)) if not df_fy.empty else 0.0
        savings_rate    = max(0.0, min(100.0, ((_monthly_inc_wp - _monthly_exp_wp) / max(1, _monthly_inc_wp)) * 100))

        # ── Net Worth KPI strip ──────────────────────────────────────────────────
        st.markdown("""
        <style>
        .wp-kpi-row  { display:flex; gap:14px; margin-bottom:20px; flex-wrap:wrap; }
        .wp-kpi-card {
            flex:1; min-width:155px;
            background:linear-gradient(135deg,#1e293b,#0f172a);
            border:1px solid #334155; border-radius:12px;
            padding:13px 16px; text-align:center;
        }
        .wp-kpi-label { color:#64748b; font-size:0.72rem; text-transform:uppercase; letter-spacing:.06em; }
        .wp-kpi-value { font-size:1.35rem; font-weight:700; margin-top:3px; }
        .wp-kpi-sub   { color:#475569; font-size:0.7rem; margin-top:2px; }
        </style>
        """, unsafe_allow_html=True)

        nw_color  = "#34d399" if net_worth >= 0 else "#f87171"
        sr_color  = "#34d399" if savings_rate >= 20 else ("#fbbf24" if savings_rate >= 10 else "#f87171")
        gain_color = "#34d399" if (tot_portfolio - tot_invested) >= 0 else "#f87171"

        st.markdown(f"""
        <div class="wp-kpi-row">
          <div class="wp-kpi-card">
            <div class="wp-kpi-label">Portfolio Value</div>
            <div class="wp-kpi-value" style="color:#38bdf8;">{format_inr_short(tot_portfolio)}</div>
            <div class="wp-kpi-sub">{format_inr_short(tot_invested)} invested · {len(inv_df) if not inv_df.empty else 0} holdings</div>
          </div>
          <div class="wp-kpi-card">
            <div class="wp-kpi-label">Unrealised Gain / Loss</div>
            <div class="wp-kpi-value" style="color:{gain_color};">{format_inr_short(tot_portfolio - tot_invested)}</div>
            <div class="wp-kpi-sub">{((tot_portfolio-tot_invested)/max(1,tot_invested)*100):.1f}% total return</div>
          </div>
          <div class="wp-kpi-card">
            <div class="wp-kpi-label">Total Outstanding Debt</div>
            <div class="wp-kpi-value" style="color:#f87171;">{format_inr_short(tot_debt_wp)}</div>
            <div class="wp-kpi-sub">{len(debts_df_wp) if not debts_df_wp.empty else 0} active loans</div>
          </div>
          <div class="wp-kpi-card">
            <div class="wp-kpi-label">Net Worth</div>
            <div class="wp-kpi-value" style="color:{nw_color};">{format_inr_short(net_worth)}</div>
            <div class="wp-kpi-sub">portfolio − debt</div>
          </div>
          <div class="wp-kpi-card">
            <div class="wp-kpi-label">Monthly Savings Rate</div>
            <div class="wp-kpi-value" style="color:{sr_color};">{savings_rate:.0f}%</div>
            <div class="wp-kpi-sub">of income saved/invested</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 5 flat tabs ──────────────────────────────────────────────────────────
        wp_tab_nw, wp_tab_budget, wp_tab_invest, wp_tab_debt, wp_tab_tax = st.tabs([
            "💰 Net Worth Overview",
            "🎯 Budget & Goals",
            "📈 Investments",
            "🏦 Debts & EMIs",
            "🧾 Tax Planner",
        ])

        # ════════════════════════════════════════════════════════════════════════
        # TAB 1 ─ NET WORTH OVERVIEW
        # ════════════════════════════════════════════════════════════════════════
        with wp_tab_nw:
            st.markdown("#### 💰 Your Financial Health at a Glance")

            nw1, nw2 = st.columns([3, 2])

            with nw1:
                # Net Worth waterfall / bar
                if not inv_df.empty or not debts_df_wp.empty:
                    nw_data = []
                    if not inv_df.empty:
                        for _, row in inv_df.groupby("investment_type")["current_value"].sum().items():
                            nw_data.append({"Component": _, "Value": row, "Type": "Asset"})
                    if not debts_df_wp.empty:
                        for _, row in debts_df_wp.iterrows():
                            nw_data.append({"Component": row["debt_name"], "Value": -float(row["outstanding_principal"]), "Type": "Liability"})
                    nw_df_chart = pd.DataFrame(nw_data)
                    fig_nw = px.bar(
                        nw_df_chart, x="Component", y="Value", color="Type",
                        color_discrete_map={"Asset": "#34d399", "Liability": "#f87171"},
                        template="plotly_dark", height=320,
                        labels={"Value": "₹", "Component": ""},
                    )
                    fig_nw.update_layout(
                        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                        margin=dict(l=10, r=10, t=30, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.markdown("##### Assets vs Liabilities Breakdown")
                    st.plotly_chart(fig_nw, use_container_width=True)
                else:
                    st.info("Add investments and debts to see your net worth breakdown.")

            with nw2:
                st.markdown("##### 📊 Portfolio Mix")
                if not inv_df.empty:
                    fig_mix = px.pie(
                        inv_df.groupby("investment_type")["current_value"].sum().reset_index(),
                        names="investment_type", values="current_value",
                        hole=0.5, template="plotly_dark",
                        color_discrete_sequence=px.colors.qualitative.Set3,
                    )
                    fig_mix.update_traces(textposition="inside", textinfo="percent+label")
                    fig_mix.update_layout(paper_bgcolor="#1e293b", showlegend=False, margin=dict(l=5,r=5,t=5,b=5), height=240)
                    st.plotly_chart(fig_mix, use_container_width=True)
                else:
                    st.info("No investments recorded yet.")

                # Savings goals progress mini-view
                if not goals_df_wp.empty:
                    st.markdown("##### 🎯 Goals Progress")
                    for _, g in goals_df_wp.iterrows():
                        pct = min(1.0, g["current_saved"] / g["target_amount"]) if g["target_amount"] > 0 else 0
                        st.caption(f"**{g['goal_name']}** — {int(pct*100)}%")
                        st.progress(pct)

            st.markdown("---")
            st.markdown("##### ⚡ Quick Actions")
            qa1, qa2, qa3 = st.columns(3)
            with qa1:
                st.markdown("""
                <div style="background:linear-gradient(135deg,#1e3a5f,#0f172a); border:1px solid #38bdf8;
                            border-radius:10px; padding:14px 16px; text-align:center; min-height:90px;">
                    <div style="font-size:1.5rem;">📈</div>
                    <div style="color:#38bdf8; font-weight:700; margin-top:4px; font-size:0.9rem;">Investments Tab</div>
                    <div style="color:#64748b; font-size:0.75rem; margin-top:3px;">Add holdings · Sync prices · Rebalance</div>
                </div>""", unsafe_allow_html=True)
            with qa2:
                st.markdown("""
                <div style="background:linear-gradient(135deg,#2d1b3f,#0f172a); border:1px solid #a78bfa;
                            border-radius:10px; padding:14px 16px; text-align:center; min-height:90px;">
                    <div style="font-size:1.5rem;">🧾</div>
                    <div style="color:#a78bfa; font-weight:700; margin-top:4px; font-size:0.9rem;">Tax Planner</div>
                    <div style="color:#64748b; font-size:0.75rem; margin-top:3px;">Compute tax · Upload capital gains</div>
                </div>""", unsafe_allow_html=True)
            with qa3:
                st.markdown("""
                <div style="background:linear-gradient(135deg,#1a2f1a,#0f172a); border:1px solid #34d399;
                            border-radius:10px; padding:14px 16px; text-align:center; min-height:90px;">
                    <div style="font-size:1.5rem;">🎯</div>
                    <div style="color:#34d399; font-weight:700; margin-top:4px; font-size:0.9rem;">Budget & Goals</div>
                    <div style="color:#64748b; font-size:0.75rem; margin-top:3px;">Set budgets · Track savings goals</div>
                </div>""", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════════
        # TAB 2 ─ BUDGET & GOALS
        # ════════════════════════════════════════════════════════════════════════
        with wp_tab_budget:
            st.caption("Set spending limits, auto-allocate based on income, and track your savings goals.")

            # ── Smart Budget Allocator ───────────────────────────────────────────
            st.markdown("""
            <div style="background-color:#1e293b; padding:14px 18px; border-radius:8px;
                        border-left:4px solid #10b981; margin-bottom:15px;">
                <div style="font-weight:600; color:#10b981; font-size:0.95rem;">💡 Smart Suggested Budget Calculator</div>
                <div style="color:#94a3b8; font-size:0.85rem;">Specify your monthly income and target spend, or fill with past averages.</div>
            </div>
            """, unsafe_allow_html=True)

            suggested_base_df = get_suggested_budgets(fy=target_fy_clean, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
            total_hist_avg_monthly = float(suggested_base_df["hist_monthly_avg"].sum())
            other_cats = [c for c in EXPENSE_CATEGORIES if c != "Insurance & Investments"]
            current_entered_sum = sum([float(st.session_state.get("budget_dict", {}).get(c, 0.0)) for c in other_cats])
            if current_entered_sum == 0:
                current_entered_sum = max(50000.0, float(round(total_hist_avg_monthly, -3))) if total_hist_avg_monthly > 0 else 75000.0

            def autosave_all_budgets():
                t_others = sum([float(st.session_state["budget_dict"].get(c, 0.0)) for c in other_cats])
                st.session_state["budget_dict"]["Insurance & Investments"] = max(0.0, float(monthly_income_input - t_others))
                records = [{"category": c, "monthly_limit": val, "annual_limit": val * 12.0}
                           for c, val in st.session_state["budget_dict"].items()]
                batch_set_category_budgets(target_fy_clean, records, family_id=user_family_id)

            t_col_inc, t_col1, t_col2, t_col3 = st.columns([1.5, 2, 1.2, 1.2])
            with t_col_inc:
                monthly_income_input = st.number_input("💵 Monthly Income (₹)", min_value=0.0, value=100000.0, step=5000.0)
            with t_col1:
                target_monthly_input = st.number_input("💰 Target Monthly Spend (₹)", min_value=1000.0, value=float(current_entered_sum), step=5000.0)
            if "budget_dict" in st.session_state and target_monthly_input != current_entered_sum and current_entered_sum > 0:
                scale_factor = target_monthly_input / current_entered_sum
                for c in other_cats:
                    st.session_state["budget_dict"][c] = round(float(st.session_state["budget_dict"][c]) * scale_factor, 2)
                autosave_all_budgets()
                st.rerun()
            with t_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("⚡ Fill Historical Avgs", type="secondary", use_container_width=True):
                    if "budget_dict" not in st.session_state:
                        st.session_state["budget_dict"] = {}
                    for idx, r in suggested_base_df.iterrows():
                        c = r["category"]
                        if c != "Insurance & Investments":
                            st.session_state["budget_dict"][c] = round(float(r["hist_monthly_avg"]), 2)
                    autosave_all_budgets()
                    st.success("⚡ Filled historical averages!")
                    st.rerun()
            with t_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🎯 Auto-Allocate 80/20", type="primary", use_container_width=True):
                    if "budget_dict" not in st.session_state:
                        st.session_state["budget_dict"] = {}
                    prop_target = monthly_income_input * 0.80
                    prop_df = get_suggested_budgets(fy=target_fy_clean, username=current_user["username"], view_mode=view_mode, target_total_monthly=prop_target, family_id=user_family_id)
                    for idx, r in prop_df.iterrows():
                        c = r["category"]
                        if c == "Insurance & Investments":
                            st.session_state["budget_dict"][c] = round(float(monthly_income_input * 0.20), 2)
                        else:
                            st.session_state["budget_dict"][c] = round(float(r["suggested_monthly"]), 2)
                    autosave_all_budgets()
                    st.success(f"🎯 80/20 allocated! Investments set to {format_inr(monthly_income_input * 0.20)}/mo.")
                    st.rerun()

            if "budget_dict" not in st.session_state:
                st.session_state["budget_dict"] = {}
                for idx, r in suggested_base_df.iterrows():
                    c = r["category"]
                    m = float(r["monthly_limit"]) if float(r["monthly_limit"]) > 0 else float(r["suggested_monthly"])
                    st.session_state["budget_dict"][c] = m

            # ── Category adjuster ────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### ⚙️ Category Budget Adjuster")
            hist_avg_map = dict(zip(suggested_base_df["category"], suggested_base_df["hist_monthly_avg"]))

            for cat in other_cats:
                current_val = float(st.session_state["budget_dict"].get(cat, 10000.0))
                h_avg = float(hist_avg_map.get(cat, 0.0))
                cat_col1, cat_col2, cat_col3, cat_col4, cat_col5 = st.columns([2.5, 1.8, 2.5, 1.8, 1.8])
                with cat_col1:
                    st.markdown(f"**{cat}**")
                    st.caption(f"Hist Avg: {format_inr(h_avg)} / mo")
                with cat_col2:
                    b_m1k = st.button("➖ ₹1k", key=f"sub_1k_{cat}")
                    b_m5p = st.button("➖ 5%", key=f"sub_5p_{cat}")
                    if b_m1k:
                        st.session_state["budget_dict"][cat] = max(0.0, round(current_val - 1000.0, 2))
                        autosave_all_budgets(); st.rerun()
                    if b_m5p:
                        st.session_state["budget_dict"][cat] = max(0.0, round(current_val * 0.95, 2))
                        autosave_all_budgets(); st.rerun()
                with cat_col3:
                    new_val = st.number_input(f"Monthly Limit (₹)", min_value=0.0, value=float(st.session_state["budget_dict"].get(cat, 10000.0)),
                                              step=500.0, key=f"input_m_{cat}", label_visibility="collapsed")
                    if new_val != st.session_state["budget_dict"][cat]:
                        st.session_state["budget_dict"][cat] = round(new_val, 2)
                        autosave_all_budgets(); st.rerun()
                with cat_col4:
                    b_p1k = st.button("➕ ₹1k", key=f"add_1k_{cat}")
                    b_p5p = st.button("➕ 5%", key=f"add_5p_{cat}")
                    if b_p1k:
                        st.session_state["budget_dict"][cat] = round(current_val + 1000.0, 2)
                        autosave_all_budgets(); st.rerun()
                    if b_p5p:
                        st.session_state["budget_dict"][cat] = round(current_val * 1.05, 2)
                        autosave_all_budgets(); st.rerun()
                with cat_col5:
                    st.markdown(f"**{format_inr_short(st.session_state['budget_dict'][cat] * 12.0)}**")
                    st.caption("Annual Cap")
                st.markdown("<hr style='margin:6px 0; border-color:#334155;'>", unsafe_allow_html=True)

            # Auto-calculated investments row
            cat = "Insurance & Investments"
            total_others = sum([float(st.session_state["budget_dict"].get(c, 0.0)) for c in other_cats])
            calc_inv = max(0.0, float(monthly_income_input - total_others))
            st.session_state["budget_dict"][cat] = calc_inv
            ic1, ic2, ic3, ic4, ic5 = st.columns([2.5, 1.8, 2.5, 1.8, 1.8])
            with ic1:
                st.markdown(f"**{cat}** *(Auto)*")
                st.caption("Income − All Other Expenses")
            with ic3: st.markdown(f"**{format_inr(calc_inv)}**")
            with ic5:
                st.markdown(f"**{format_inr_short(calc_inv * 12.0)}**")
                st.caption("Annual Cap")
            st.markdown("<hr style='margin:6px 0; border-color:#334155;'>", unsafe_allow_html=True)

            if monthly_income_input < total_others:
                st.warning("⚠️ Allocated expenses exceed monthly income. Reduce category limits.")

            # Budget summary strip
            total_alloc = float(sum(st.session_state["budget_dict"].values()))
            diff = float(target_monthly_input - total_alloc)
            bs1, bs2, bs3 = st.columns(3)
            bs1.metric("🎯 Target Monthly Spend", format_inr(target_monthly_input))
            bs2.metric("💵 Total Allocated", format_inr(total_alloc), delta=f"{format_inr(diff)} Buffer" if diff >= 0 else f"-{format_inr(abs(diff))} Deficit", delta_color="normal" if diff >= 0 else "inverse")
            bs3.metric("📅 Annual Budget Cap", format_inr(total_alloc * 12.0))
            st.success("✅ **Auto-Save On**: All budget changes are instantly saved.")

            # ── Budget Performance ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### 📊 Budget Performance & Utilisation")
            budget_status = get_budget_status(target_fy_clean, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
            if not budget_status.empty:
                for idx, row in budget_status.iterrows():
                    cat  = row["category"]
                    spent  = float(row["Actual_Spent"])
                    budget = float(row["Annual_Budget"])
                    util   = float(row["Utilization_%"])
                    if budget > 0:
                        c1, c2, c3 = st.columns([2, 3, 1])
                        with c1:
                            st.markdown(f"**{cat}**")
                            st.caption(f"Spent: {format_inr(spent)} / Budget: {format_inr(budget)}")
                        with c2:
                            st.progress(min(util / 100.0, 1.0))
                        with c3:
                            if util > 100:
                                st.markdown("<span class='surge-badge'>OVER</span>", unsafe_allow_html=True)
                            elif util > 80:
                                st.markdown("<span style='background:#78350f; color:#fde047; padding:4px 8px; border-radius:6px; font-weight:600; font-size:0.82rem;'>DANGER</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span class='normal-badge'>ON TRACK</span>", unsafe_allow_html=True)

            # ── Savings Goals ─────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### 🎯 Savings Goals")

            if not goals_df_wp.empty:
                # Show as 2-column card grid
                goal_rows = list(goals_df_wp.iterrows())
                for row_start in range(0, len(goal_rows), 2):
                    gcols = st.columns(2)
                    for col_idx, (_, goal) in enumerate(goal_rows[row_start:row_start + 2]):
                        with gcols[col_idx]:
                            pct = min(1.0, goal["current_saved"] / goal["target_amount"]) if goal["target_amount"] > 0 else 0.0
                            bar_color = "#10b981" if pct >= 0.75 else ("#fbbf24" if pct >= 0.4 else "#38bdf8")
                            st.markdown(f"""
                            <div style="background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155;
                                        border-radius:12px; padding:16px 18px; margin-bottom:10px;">
                                <div style="font-weight:700; color:#f1f5f9; font-size:0.95rem;">{goal['goal_name']}</div>
                                <div style="display:flex; justify-content:space-between; margin:8px 0 4px;">
                                    <span style="color:#34d399; font-weight:600;">{format_inr_short(goal['current_saved'])}</span>
                                    <span style="color:#64748b; font-size:0.82rem;">of {format_inr_short(goal['target_amount'])}</span>
                                </div>
                                <div style="width:100%; background:#334155; border-radius:4px; height:8px;">
                                    <div style="width:{pct*100:.1f}%; background:{bar_color}; height:100%; border-radius:4px;"></div>
                                </div>
                                <div style="color:#64748b; font-size:0.75rem; margin-top:6px;">{int(pct*100)}% complete{(' · Target: '+str(goal['target_date'])) if goal.get('target_date') else ''}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            with st.popover("⚙️ Manage"):
                                c_amt = st.number_input("Log Contribution", min_value=0.0, step=1000.0, key=f"contrib_{goal['id']}")
                                if st.button("➕ Add Funds", key=f"btn_add_{goal['id']}"):
                                    if add_goal_contribution(goal['id'], user_family_id, c_amt):
                                        st.success(f"Added {format_inr(c_amt)}!")
                                        st.rerun()
                                st.markdown("---")
                                if st.button("🚨 Delete Goal", key=f"btn_del_{goal['id']}"):
                                    if delete_savings_goal(goal['id'], user_family_id):
                                        st.success("Deleted!")
                                        st.rerun()
            else:
                st.info("No savings goals yet. Create one below!")

            with st.expander("➕ Create New Savings Goal"):
                with st.form("new_goal_form"):
                    g_name = st.text_input("Goal Name (e.g. Child's Education)")
                    g_target = st.number_input("Target Amount", min_value=0.0, step=10000.0)
                    g_date = st.date_input("Target Date")
                    g_contrib = st.number_input("Planned Monthly Contribution (Optional)", min_value=0.0, step=1000.0)
                    if st.form_submit_button("Create Goal"):
                        if g_name and g_target > 0:
                            if add_savings_goal(user_family_id, g_name, g_target, str(g_date), g_contrib):
                                st.success("Goal created!")
                                st.rerun()
                        else:
                            st.error("Please provide a name and target amount.")

        # ════════════════════════════════════════════════════════════════════════
        # TAB 3 ─ INVESTMENTS  (Holdings + SIP Planner + Rebalance + Deploy New Money)
        # ════════════════════════════════════════════════════════════════════════
        with wp_tab_invest:
            # ── Portfolio KPI strip ──────────────────────────────────────────────
            if not inv_df.empty:
                tot_gain_inv = tot_portfolio - tot_invested
                tot_ret_pct  = round((tot_gain_inv / tot_invested) * 100, 2) if tot_invested > 0 else 0.0
                pm1, pm2, pm3, pm4 = st.columns(4)
                pm1.metric("💰 Total Invested", format_inr(tot_invested))
                pm2.metric("🏆 Portfolio Value", format_inr(tot_portfolio))
                pm3.metric("📈 Gain / Loss", format_inr(tot_gain_inv), delta=f"{tot_ret_pct:.2f}%", delta_color="normal" if tot_gain_inv >= 0 else "inverse")
                pm4.metric("📊 Holdings", f"{len(inv_df)} assets")

                st.markdown("<br>", unsafe_allow_html=True)

                # Historical growth deltas
                deltas_inv = get_portfolio_snapshots_deltas(user_family_id, tot_portfolio)
                dh1, dh2, dh3, dh4 = st.columns(4)
                def _fmt_d(d):
                    v, p = d["value"], d["percent"]
                    return f"{'+' if v>=0 else ''}{format_inr_short(v)} ({'+' if v>=0 else ''}{p:.1f}%)"
                dh1.metric("Since Last Sync", "", delta=_fmt_d(deltas_inv["previous_sync"]), delta_color="normal")
                dh2.metric("7-Day Change", "", delta=_fmt_d(deltas_inv["weekly"]), delta_color="normal")
                dh3.metric("30-Day Change", "", delta=_fmt_d(deltas_inv["monthly"]), delta_color="normal")
                dh4.metric("1-Year Change", "", delta=_fmt_d(deltas_inv["yearly"]), delta_color="normal")

                # Quick-action buttons
                st.markdown("<br>", unsafe_allow_html=True)
                act1, act2, act3 = st.columns([1, 1, 2])
                with act1:
                    if st.button("🔄 Sync Live Prices", use_container_width=True):
                        with st.spinner("Fetching NAVs..."):
                            updated_df = live_market_tracker.update_portfolio_live_prices(inv_df.copy())
                            update_investments_df(updated_df)
                            record_portfolio_snapshot(user_family_id, float(updated_df["current_value"].sum()))
                        st.success("✅ Prices synced!"); st.rerun()

                # ── AI Portfolio Review at TOP ───────────────────────────────────
                with act2:
                    run_ai_review = st.button("🤖 AI Portfolio Review", type="primary", use_container_width=True)
                if run_ai_review:
                    with st.spinner("🤖 Gemini AI analyzing portfolio..."):
                        portfolio_ai = generate_ai_portfolio_suggestions(inv_df, current_user, debts_df_wp, goals_df_wp)
                    st.success("🎉 AI Review Complete!")
                    st.info(portfolio_ai.get("summary", ""))
                    for rec in portfolio_ai.get("recommendations", []):
                        with st.expander(f"**{rec.get('title', 'Recommendation')}**"):
                            st.markdown(f"**Observation**: {rec.get('observation', '')}")
                            st.markdown(f"**Suggestion**: {rec.get('suggestion', '')}")

            else:
                st.info("💡 No holdings yet. Add your first investment below.")

            st.markdown("---")

            # ── Add Holdings (collapsed by default if data exists) ───────────────
            with st.expander("➕ Add / Import Holdings", expanded=inv_df.empty):
                # CAS Uploader
                st.markdown("##### 📤 Import from Broker Statement (AI-Powered)")
                default_api_key = current_user.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
                template_df_inv = pd.DataFrame({
                    "Stock Code / Name": ["HDFC Bank", "Nifty 50 Index Fund"],
                    "Platform / Broker": ["Zerodha", "ICICI Direct"],
                    "Asset Class": ["Equity", "Mutual Funds"],
                    "Invested Amount": [50000.0, 31575.0],
                    "Year Invested": [2022, 2023],
                    "Current Value": [51850.0, 33750.0],
                    "Units": [30.5, 150.25],
                    "Average Buy Price": [1639.34, 210.50],
                    "Market Cap": ["Large Cap", "Unknown"],
                    "Sector / Theme": ["Banking", "Index"],
                })
                st.download_button("⬇️ Download Standard CSV Template", template_df_inv.to_csv(index=False).encode(), "investment_template.csv", "text/csv")
                uploaded_file_inv = st.file_uploader("Upload CSV, Excel, PDF or Image", type=["csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg"], key="stmt_upload")
                if uploaded_file_inv and st.button("Parse & Import", type="primary"):
                    with st.spinner("Parsing..."):
                        try:
                            parsed_data = statement_parser.identify_and_parse_statement(uploaded_file_inv.getvalue(), uploaded_file_inv.name, api_key=default_api_key)
                            if parsed_data:
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
                                st.success(f"🎉 Imported {count} holdings!")
                                st.rerun()
                            else:
                                st.warning("Could not extract holdings from this file.")
                        except Exception as e:
                            st.error(f"Parse error: {e}")

                st.markdown("##### ➕ Manual Entry")
                PRESET_TYPES = ["Equity (Stocks)", "Mutual funds", "Structured funds", "EPF", "PPF",
                                "KVP (Kisan Vikas Patra)", "NSC (National Savings Certificate)",
                                "Fixed Deposits / Recurring Deposits", "Startup investments",
                                "Gold / Sovereign Gold Bonds (SGB)", "Real Estate", "Other (Add Custom Type)"]
                PRESET_PLATFORMS = ["Zerodha", "Groww", "SBI / SBI Mutual Fund", "Post Office", "Coin (Zerodha)",
                                    "Angel One", "Upstox", "ICICI Direct", "HDFC Securities", "IndMoney",
                                    "Direct / Primary Institution", "Other (Add Custom Platform)"]
                mc1, mc2, mc3, mc4, mc5 = st.columns([1.5, 1.5, 1.2, 1.0, 1.2])
                with mc1:
                    sel_plat = st.selectbox("Platform", PRESET_PLATFORMS, key="inv_plat_sel")
                    final_plat = st.text_input("Custom Platform", key="inv_plat_custom") if sel_plat == "Other (Add Custom Platform)" else sel_plat
                with mc2:
                    sel_type = st.selectbox("Type", PRESET_TYPES, key="inv_type_sel")
                    final_type = st.text_input("Custom Type", key="inv_type_custom") if sel_type == "Other (Add Custom Type)" else sel_type
                with mc3:
                    inv_desc_val = st.text_input("Stock Code / Name", value="HDFCBANK", key="inv_desc_input")
                with mc4:
                    inv_amt_val = st.number_input("Invested (₹)", min_value=100.0, value=50000.0, step=5000.0, key="inv_amt_input")
                with mc5:
                    inv_yr_val = st.number_input("Year", min_value=1990, max_value=datetime.datetime.now().year + 5, value=datetime.datetime.now().year, step=1, key="inv_yr_input")
                    curr_val_input = st.number_input("Current Value (₹)", min_value=0.0, value=inv_amt_val * 1.10, step=5000.0, key="inv_curr_input")
                if st.button("➕ Add Holding", type="primary", use_container_width=True):
                    insert_investment(username=current_user["username"], platform=final_plat, investment_type=final_type,
                                     investment_amount=inv_amt_val, year_invested=inv_yr_val,
                                     current_value=curr_val_input, family_id=user_family_id, description=inv_desc_val)
                    st.success(f"Added {inv_desc_val}!")
                    st.rerun()

            # ── Holdings Grid ────────────────────────────────────────────────────
            if not inv_df.empty:
                st.markdown("---")

                # Distribution charts
                chart_c1, chart_c2, chart_c3 = st.columns(3)
                with chart_c1:
                    st.markdown("##### Asset Type")
                    fig_type = px.pie(inv_df, names="investment_type", values="current_value", hole=0.4, template="plotly_dark")
                    fig_type.update_layout(margin=dict(l=5,r=5,t=10,b=5), height=220)
                    st.plotly_chart(fig_type, use_container_width=True)
                with chart_c2:
                    st.markdown("##### Market Cap")
                    fig_mc = px.pie(inv_df, names="market_cap", values="current_value", hole=0.4, template="plotly_dark")
                    fig_mc.update_layout(margin=dict(l=5,r=5,t=10,b=5), height=220)
                    st.plotly_chart(fig_mc, use_container_width=True)
                with chart_c3:
                    st.markdown("##### Platform")
                    fig_plat = px.bar(inv_df.groupby("platform", as_index=False)["current_value"].sum(),
                                      x="platform", y="current_value", color="platform", template="plotly_dark",
                                      labels={"current_value": "₹", "platform": ""})
                    fig_plat.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", margin=dict(l=5,r=5,t=10,b=5), height=220, showlegend=False)
                    st.plotly_chart(fig_plat, use_container_width=True)

                # Grouped summary
                render_grouped_portfolio_summary(inv_df)

                # Editable grid
                with st.expander("✏️ Edit Holdings"):
                    all_asset_types = sorted(inv_df["investment_type"].unique().tolist())
                    sel_types = st.multiselect("Filter by Asset Class", all_asset_types, default=all_asset_types)
                    filt_inv = inv_df[inv_df["investment_type"].isin(sel_types)] if sel_types else inv_df.head(0)
                    if "resolved_name" not in inv_df.columns:
                        inv_df["resolved_name"] = ""
                    display_cols = ["id", "description", "resolved_name", "platform", "investment_type",
                                    "investment_amount", "year_invested", "current_value",
                                    "units", "avg_buy_price", "market_cap", "sector_segment",
                                    "unrealized_gain", "returns_pct"]
                    edited_holdings = st.data_editor(
                        filt_inv[display_cols] if not filt_inv.empty else filt_inv,
                        column_config={
                            "id": st.column_config.NumberColumn("ID", disabled=True),
                            "description": st.column_config.TextColumn("Stock / Name"),
                            "resolved_name": st.column_config.TextColumn("AMFI Name", disabled=True),
                            "platform": st.column_config.TextColumn("Platform"),
                            "investment_type": st.column_config.TextColumn("Type"),
                            "investment_amount": st.column_config.NumberColumn("Invested (₹)", format="₹ %.2f"),
                            "year_invested": st.column_config.NumberColumn("Year"),
                            "current_value": st.column_config.NumberColumn("Current Val (₹)", format="₹ %.2f"),
                            "units": st.column_config.NumberColumn("Units", format="%.4f"),
                            "avg_buy_price": st.column_config.NumberColumn("Avg Price", format="₹ %.2f"),
                            "market_cap": st.column_config.SelectboxColumn("Market Cap", options=["Large Cap", "Mid Cap", "Small Cap", "Multi Cap", "Unknown"]),
                            "sector_segment": st.column_config.TextColumn("Sector"),
                            "unrealized_gain": st.column_config.NumberColumn("Gain/Loss (₹)", format="₹ %.2f", disabled=True),
                            "returns_pct": st.column_config.NumberColumn("Return %", format="%.2f %%", disabled=True),
                        },
                        use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_holdings"
                    )
                    ec1, ec2 = st.columns([2, 1])
                    with ec1:
                        if st.button("💾 Save Edits", type="primary", use_container_width=True):
                            cnt_upd = update_investments_df(edited_holdings)
                            st.success(f"Updated {cnt_upd} entries!"); st.rerun()
                    with ec2:
                        del_id = st.number_input("Delete by ID", min_value=1, step=1, key="del_inv_id")
                        if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                            delete_investment(del_id)
                            st.success(f"Deleted ID {del_id}!"); st.rerun()
                    with st.expander("⚠️ Delete All Holdings"):
                        st.warning("Permanent — cannot be undone.")
                        if st.button("🗑️ Confirm Delete ALL", type="primary", use_container_width=True):
                            deleted_count = delete_all_investments(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)
                            st.success(f"Deleted {deleted_count} holdings!"); st.rerun()

                # Duplicate finder
                with st.expander("🧹 Find Duplicate Holdings"):
                    from database import find_duplicate_investments, delete_duplicate_investments
                    duplicates = find_duplicate_investments(username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id)
                    if not duplicates:
                        st.success("No duplicates found!")
                    else:
                        st.warning(f"Found {len(duplicates)} duplicate group(s).")
                        dup_ids = []
                        dup_list = []
                        for group in duplicates:
                            orig = group[0]
                            for d in group[1:]:
                                dup_ids.append(d["id"])
                                dup_list.append({"Dup ID": d["id"], "Original ID": orig["id"], "Platform": d["platform"], "Name": d["description"], "Invested": d["investment_amount"]})
                        st.dataframe(pd.DataFrame(dup_list), use_container_width=True)
                        if st.button(f"🗑️ Delete {len(dup_ids)} Duplicates", type="primary"):
                            st.success(f"Deleted {delete_duplicate_investments(dup_ids)} entries!"); st.rerun()

            # ── SIP Planner & Wealth Trajectory ─────────────────────────────────
            st.markdown("---")
            with st.expander("📈 SIP Planner & Wealth Growth Trajectory", expanded=True):
                curr_ins_monthly = float(st.session_state.get("budget_dict", {}).get("Insurance & Investments", 20000.0))
                use_portfolio_nw = st.toggle("Link Portfolio Net Worth", value=True)
                sip_c1, sip_c2, sip_c3 = st.columns(3)
                with sip_c1:
                    u_age = st.number_input("Your Age", min_value=18, max_value=85, value=current_user.get("age", 35), step=1, key="invest_user_age")
                    if u_age != current_user.get("age", 35):
                        from database import update_user_age
                        if update_user_age(current_user["username"], u_age):
                            st.session_state["user"]["age"] = u_age
                with sip_c2:
                    u_savings = tot_portfolio if use_portfolio_nw else st.number_input("Current Networth (₹)", min_value=0.0, value=tot_portfolio, step=50000.0, key="invest_user_savings_manual")
                    if use_portfolio_nw:
                        st.metric("💰 Linked Portfolio Value", format_inr_short(u_savings))
                with sip_c3:
                    u_sip_budget = st.number_input("Monthly Investment (₹)", min_value=1000.0, value=max(5000.0, curr_ins_monthly), step=1000.0, key="invest_user_sip")

                inv_plan = calculate_investment_plan(
                    age=u_age, current_savings=u_savings, monthly_investment_budget=u_sip_budget,
                    monthly_expenses=total_spent / max(1, num_months) if not df_fy.empty else 50000.0
                )

                ip1, ip2, ip3, ip4 = st.columns(4)
                ip1.metric("🚀 Equity", f"{inv_plan['equity_pct']:.0f}%", f"SIP {format_inr(inv_plan['equity_sip'])}")
                ip2.metric("🛡️ Debt", f"{inv_plan['debt_pct']:.0f}%", f"SIP {format_inr(inv_plan['debt_sip'])}")
                ip3.metric("🪙 Gold", f"{inv_plan['gold_pct']:.0f}%", f"SIP {format_inr(inv_plan['gold_sip'])}")
                ip4.metric("📈 Blended CAGR", f"~{inv_plan['blended_cagr_pct']}%/yr")

                ch1, ch2 = st.columns([1, 2])
                with ch1:
                    pie_df_sip = pd.DataFrame([
                        {"Asset": "Equity", "Allocation_%": inv_plan["equity_pct"]},
                        {"Asset": "Debt / FI", "Allocation_%": inv_plan["debt_pct"]},
                        {"Asset": "Gold", "Allocation_%": inv_plan["gold_pct"]},
                    ])
                    fig_asset = px.pie(pie_df_sip, names="Asset", values="Allocation_%",
                                       color_discrete_map={"Equity": "#38bdf8", "Debt / FI": "#34d399", "Gold": "#fbbf24"}, hole=0.4)
                    fig_asset.update_layout(margin=dict(l=5,r=5,t=5,b=5), height=220)
                    st.plotly_chart(fig_asset, use_container_width=True)
                with ch2:
                    proj_data = []
                    for yrs, p_data in inv_plan["projections"].items():
                        proj_data.append({"Horizon": f"{yrs}yr", "Total Invested": p_data["total_invested"], "Compounding Gain": p_data["wealth_gain"]})
                    fig_sip = px.bar(pd.DataFrame(proj_data), x="Horizon", y=["Total Invested", "Compounding Gain"],
                                     barmode="stack", template="plotly_dark",
                                     color_discrete_map={"Total Invested": "#64748b", "Compounding Gain": "#10b981"},
                                     labels={"value": "₹", "variable": ""})
                    fig_sip.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", margin=dict(l=5,r=5,t=10,b=5), height=220,
                                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)))
                    st.plotly_chart(fig_sip, use_container_width=True)

                em_status = inv_plan["emergency_status"]
                if em_status == "Sufficient":
                    st.success(f"✅ Emergency Buffer Healthy: {format_inr(u_savings)} > required {format_inr(inv_plan['req_emergency'])}")
                else:
                    st.warning(f"⚠️ Emergency Buffer Deficit: {format_inr(inv_plan['emergency_gap'])} short of 6-month target {format_inr(inv_plan['req_emergency'])}.")

                if st.button("💡 Generate AI Wealth Advisory", type="primary", use_container_width=True):
                    with st.spinner("🤖 Generating AI wealth strategy..."):
                        wealth_advice = generate_ai_wealth_advice(inv_plan)
                    st.success("🎉 AI Wealth Strategy Ready!")
                    st.info(wealth_advice.get("summary", ""))
                    for bullet in wealth_advice.get("key_takeaways", []):
                        st.markdown(f"- {bullet}")

            # ── Rebalance Advisor ────────────────────────────────────────────────
            st.markdown("---")
            with st.expander("⚖️ Portfolio Rebalance & Deploy New Money"):
                gemini_api_key_wp = (current_user.get("gemini_api_key") or get_admin_gemini_api_key()
                                     or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", ""))
                from investment_planner import generate_rebalance_advice, generate_new_money_advice

                advisor_user_context = st.text_area("💬 Goals / Context (optional)",
                    placeholder="e.g. I want to buy a house in 2 years",
                    help="AI incorporates this into recommendations.", key="inv_context")

                adv_mode = st.radio("Mode", ["🔄 Rebalance Existing Portfolio", "💰 Deploy New Money"], horizontal=True)

                country_opts_inv = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
                cur_country_inv  = current_user.get("country", "India")
                risk_opts_inv    = ["Conservative", "Moderate", "Aggressive"]

                rc1, rc2, rc3 = st.columns([1, 1.5, 1.5])
                with rc1:
                    inv_risk = st.selectbox("Risk Profile", risk_opts_inv,
                        index=risk_opts_inv.index(current_user.get("risk_tolerance", "Moderate")) if current_user.get("risk_tolerance") in risk_opts_inv else 1,
                        key="inv_risk_sel")
                with rc2:
                    inv_country = st.selectbox("Country", country_opts_inv,
                        index=country_opts_inv.index(cur_country_inv) if cur_country_inv in country_opts_inv else 0,
                        key="inv_country_sel")
                    if inv_country != cur_country_inv:
                        from database import update_user_profile
                        update_user_profile(current_user["username"], country=inv_country)
                        st.session_state["user"]["country"] = inv_country

                if adv_mode.startswith("💰"):
                    with rc3:
                        nm_amount = st.number_input("Amount to Invest (₹)", min_value=1000.0, value=50000.0, step=5000.0, key="nm_amount")
                        nm_mode   = st.selectbox("Mode", ["Lump Sum", "SIP (Monthly)"], key="nm_mode")

                run_inv_adv = st.button("▶️ Run Analysis", type="primary", use_container_width=True, key="run_inv_adv")
                if run_inv_adv:
                    if adv_mode.startswith("🔄"):
                        with st.spinner("Fetching live trend signals (30–45s)..."):
                            rebal_result = generate_rebalance_advice(inv_df, inv_risk, inv_country, advisor_user_context, gemini_api_key_wp)
                        st.session_state["rebal_result"] = rebal_result
                        st.session_state["nm_result"] = None
                    else:
                        with st.spinner("Generating personalised suggestions..."):
                            nm_result = generate_new_money_advice(inv_df, inv_risk, nm_amount, "SIP" if "SIP" in nm_mode else "Lump Sum", inv_country, advisor_user_context, gemini_api_key_wp)
                        st.session_state["nm_result"] = nm_result
                        st.session_state["rebal_result"] = None

                rebal_result = st.session_state.get("rebal_result")
                nm_result    = st.session_state.get("nm_result")

                if rebal_result:
                    if "error" in rebal_result:
                        st.warning(f"⚠️ {rebal_result['error']}")
                    else:
                        st.success(f"✅ Analysis for portfolio of {format_inr(rebal_result['total_value'])}")
                        alloc_c1, alloc_c2 = st.columns(2)
                        with alloc_c1:
                            st.markdown("##### Current Allocation")
                            curr_pie = pd.DataFrame(list(rebal_result["current_allocation"].items()), columns=["Asset", "%"])
                            fig_curr = px.pie(curr_pie, names="Asset", values="%", hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
                            fig_curr.update_layout(margin=dict(l=0,r=0,t=10,b=10), height=220, showlegend=True)
                            st.plotly_chart(fig_curr, use_container_width=True)
                        with alloc_c2:
                            st.markdown("##### Target Allocation")
                            tgt_pie = pd.DataFrame(list(rebal_result["target_allocation"].items()), columns=["Asset", "%"])
                            fig_tgt = px.pie(tgt_pie, names="Asset", values="%", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig_tgt.update_layout(margin=dict(l=0,r=0,t=10,b=10), height=220, showlegend=True)
                            st.plotly_chart(fig_tgt, use_container_width=True)
                        drift_df_r = pd.DataFrame(rebal_result["drift_table"])
                        if not drift_df_r.empty:
                            st.dataframe(drift_df_r[["Asset Class", "Current %", "Target %", "Drift %", "Action"]], use_container_width=True, hide_index=True)
                        if rebal_result.get("recommendations"):
                            st.markdown("##### 🤖 AI Recommendations")
                            for rec in rebal_result["recommendations"]:
                                ac = {"Buy": "#10b981", "Sell/Switch": "#f59e0b", "Hold": "#64748b"}.get(rec.get("action_type", ""), "#64748b")
                                st.markdown(f"""<div style="background:#1e293b; border-radius:8px; border-left:4px solid {ac}; padding:10px 14px; margin-bottom:6px;">
                                    <div style="font-weight:600; color:#f1f5f9;">{rec.get('title','')}</div>
                                    <div style="color:#38bdf8; font-size:0.85rem; margin:4px 0;">🏛️ {rec.get('instrument','')}</div>
                                    <div style="color:#94a3b8; font-size:0.82rem;">{rec.get('rationale','')}</div>
                                </div>""", unsafe_allow_html=True)

                if nm_result:
                    st.success("🎉 New Money Suggestions Ready!")
                    st.info(nm_result.get("summary", ""))
                    CLASS_ICONS  = {"equity": "🚀", "debt": "🛡️", "gold": "🪙", "tax_saving": "🏛️"}
                    CLASS_COLORS = {"equity": "#38bdf8", "debt": "#34d399", "gold": "#fbbf24", "tax_saving": "#a78bfa"}
                    for cls_key, instruments in nm_result.get("suggestions", {}).items():
                        if not instruments: continue
                        icon  = CLASS_ICONS.get(cls_key, "📌")
                        color = CLASS_COLORS.get(cls_key, "#94a3b8")
                        alloc_amt = nm_result.get("allocation_split", {}).get(cls_key.capitalize(), 0)
                        st.markdown(f"**{icon} {cls_key.replace('_',' ').title()}** — Suggested: ₹{alloc_amt:,.0f}")
                        for instr in instruments:
                            rc = {"Low":"#34d399","Very Low":"#10b981","Moderate":"#fbbf24","Moderate-High":"#f97316","High":"#ef4444"}.get(instr.get("risk",""),"#94a3b8")
                            st.markdown(f"""<div style="background:#1e293b; border-radius:8px; border-left:3px solid {color}; padding:10px 14px; margin-bottom:5px;">
                                <div style="font-weight:600; color:#f1f5f9;">{instr.get('name','')}</div>
                                <div style="color:{rc}; font-size:0.78rem;">Risk: {instr.get('risk','N/A')}</div>
                                <div style="color:#94a3b8; font-size:0.82rem;">{instr.get('rationale','')}</div>
                                <div style="color:{color}; font-weight:700; margin-top:4px;">{instr.get('suggested_amount','')}</div>
                            </div>""", unsafe_allow_html=True)

            # ── Retirement Planner ───────────────────────────────────────────────
            st.markdown("---")
            with st.expander("🏖️ Retirement Planner"):
                ret_col1, ret_col2 = st.columns(2)
                with ret_col1:
                    ret_age = st.number_input("🎯 Desired Retirement Age", min_value=u_age + 1, max_value=100, value=max(60, u_age + 10), step=1)
                    exp_return_str = st.text_input("📈 Expected CAGR (%) — leave blank for historical", placeholder="e.g. 12.5")
                with ret_col2:
                    benchmark_index = st.selectbox("📊 Benchmark (if CAGR blank)",
                        options=[("Nifty 50 (India)", "^NSEI"), ("BSE Sensex", "^BSESN"), ("S&P 500 (US)", "^GSPC"), ("NASDAQ", "^IXIC")],
                        format_func=lambda x: x[0])
                    hist_years = st.selectbox("Historical Data Period", options=[5, 10, 15, 20], index=1, format_func=lambda x: f"Last {x} Years")
                add_col1, add_col2 = st.columns(2)
                with add_col1:
                    one_time_exp_df = st.data_editor(pd.DataFrame([{"Expense Description": "", "Amount (₹)": 0.0, "Age": min(ret_age, u_age + 5)}]), num_rows="dynamic", key="one_time_exp_editor", use_container_width=True, hide_index=True)
                with add_col2:
                    add_recurring_exp = st.number_input("Additional Monthly Recurring Expenses (₹)", min_value=0.0, value=0.0, step=5000.0)
                one_time_expenses_list = []
                for _, row in one_time_exp_df.iterrows():
                    try: amt = float(row.get("Amount (₹)", 0) or 0)
                    except: amt = 0.0
                    try: age_val = int(row.get("Age", u_age) or u_age)
                    except: age_val = u_age
                    if amt > 0:
                        one_time_expenses_list.append({"amount": amt, "age": age_val})
                if st.button("🔮 Calculate Retirement Corpus", type="primary", use_container_width=True):
                    from investment_planner import fetch_index_historical_cagr, calculate_retirement_corpus, generate_ai_retirement_advisory
                    with st.spinner("Calculating..."):
                        if exp_return_str.strip():
                            try: cagr_decimal = float(exp_return_str.strip()) / 100.0
                            except: cagr_decimal = 0.12
                        else:
                            st.info(f"Fetching {hist_years}-yr CAGR for {benchmark_index[0]}...")
                            cagr_decimal = fetch_index_historical_cagr(benchmark_index[1], hist_years)
                            st.success(f"{hist_years}-yr CAGR for {benchmark_index[0]}: **{cagr_decimal*100:.2f}%**")
                        ret_plan = calculate_retirement_corpus(u_age, ret_age, u_savings, u_sip_budget, cagr_decimal, one_time_expenses_list, add_recurring_exp)
                        r1, r2, r3 = st.columns(3)
                        r1.metric("💰 Projected Corpus", format_inr(ret_plan["total_future_value"]), f"+{format_inr(ret_plan['wealth_gain'])} gain")
                        r2.metric("💵 Total Invested", format_inr(ret_plan["total_invested"]))
                        r3.metric("🏝️ Safe Monthly Withdrawal (4%)", format_inr(ret_plan["safe_monthly_withdrawal"]))
                    with st.spinner("🤖 Generating AI Retirement Advisory..."):
                        ret_advice = generate_ai_retirement_advisory(ret_plan, inv_df)
                        st.markdown("#### 🤖 AI Retirement Advisory")
                        st.info(ret_advice.get("summary", ""))
                        for item in ret_advice.get("key_takeaways", []):
                            st.markdown(f"- {item}")

        # ════════════════════════════════════════════════════════════════════════
        # TAB 4 ─ DEBTS & EMIs
        # ════════════════════════════════════════════════════════════════════════
        with wp_tab_debt:
            st.caption("Track loans, outstanding principal, interest rates, and simulate payoff strategies.")
            debts_df = get_debts(family_id=user_family_id)
            if not debts_df.empty:
                total_outstanding = debts_df["outstanding_principal"].sum()
                total_monthly_emi = debts_df["monthly_emi"].sum()
                dm1, dm2, dm3 = st.columns(3)
                dm1.metric("Total Outstanding", format_inr(total_outstanding))
                dm2.metric("Total Monthly EMI", format_inr(total_monthly_emi))
                dm3.metric("Active Loans", str(len(debts_df)))
                st.markdown("---")

            with st.expander("➕ Add New Debt / Liability", expanded=debts_df.empty):
                with st.form("add_debt_form"):
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        new_debt_name = st.text_input("Debt / Loan Name", placeholder="e.g. HDFC Home Loan")
                        new_debt_cat  = st.selectbox("Category", DEBT_CATEGORIES)
                    with dc2:
                        new_principal  = st.number_input("Total Principal", min_value=0.0, step=10000.0)
                        new_start_date = st.date_input("Start Date", value=datetime.date.today())
                    dc3, dc4, dc5 = st.columns(3)
                    with dc3: new_rate   = st.number_input("Interest Rate (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
                    with dc4: new_tenure = st.number_input("Tenure (Months)", min_value=1, step=12)
                    with dc5: new_emi    = st.number_input("Monthly EMI", min_value=0.0, step=1000.0)
                    if st.form_submit_button("💾 Save Liability", type="primary", use_container_width=True):
                        if new_debt_name and new_principal > 0:
                            if new_emi > 0:
                                if "budget_dict" in st.session_state:
                                    st.session_state["budget_dict"][new_debt_cat] = st.session_state["budget_dict"].get(new_debt_cat, 0.0) + new_emi
                                b_df = get_category_budget(target_fy_clean, new_debt_cat, family_id=user_family_id)
                                existing_val = float(b_df.iloc[0]["monthly_limit"]) if not b_df.empty else 0.0
                                set_category_budget(target_fy_clean, new_debt_cat, existing_val + new_emi, (existing_val + new_emi) * 12, family_id=user_family_id)
                            add_debt(new_debt_name, new_debt_cat, new_principal, new_principal, new_rate, new_emi, new_tenure, str(new_start_date), user_family_id)
                            st.success(f"Added {new_debt_name} — EMI {format_inr(new_emi)} synced to budget!"); st.rerun()
                        else:
                            st.error("Please provide a name and principal amount.")

            if not debts_df.empty:
                st.markdown("### 📊 Active Debt Portfolio")
                for idx, row in debts_df.iterrows():
                    did = row["id"]; dname = row["debt_name"]; dcat = row["debt_category"]
                    outstanding = row["outstanding_principal"]; total = row["total_principal"]
                    emi = row["monthly_emi"]; rate = row["interest_rate"]
                    paid_pct = max(0.0, min(100.0, ((total - outstanding) / total) * 100)) if total > 0 else 0.0
                    st.markdown(f"""
                    <div class="dashboard-box" style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                            <div>
                                <div style="font-size:1.1rem; font-weight:700; color:#f8fafc;">{dname}</div>
                                <div style="font-size:0.85rem; color:#94a3b8;">{dcat} · {rate}% Interest</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:1.2rem; font-weight:700; color:#ef4444;">{format_inr(outstanding)}</div>
                                <div style="font-size:0.85rem; color:#94a3b8;">Outstanding</div>
                            </div>
                        </div>
                        <div style="margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px;">
                                <span style="color:#64748b;">Paid: {paid_pct:.1f}%</span>
                                <span style="color:#64748b;">Total: {format_inr(total)}</span>
                            </div>
                            <div style="width:100%; background:#334155; border-radius:4px; height:8px;">
                                <div style="width:{paid_pct}%; background:#10b981; height:100%; border-radius:4px;"></div>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    with st.expander(f"💸 Log Payment · ✏️ Edit · 📜 History — {dname}"):
                        lp1, lp2 = st.columns(2)
                        with lp1:
                            with st.form(f"pay_debt_{did}"):
                                pay_date = st.date_input("Date", value=datetime.date.today(), key=f"pd_{did}")
                                pay_principal = st.number_input("Principal Portion (₹)", min_value=0.0, step=100.0, key=f"pp_{did}")
                                pay_interest  = st.number_input("Interest Portion (₹)", min_value=0.0, step=100.0, key=f"pi_{did}")
                                if st.form_submit_button("Record Payment", type="primary"):
                                    if pay_principal > 0 or pay_interest > 0:
                                        add_debt_payment(did, str(pay_date), pay_principal, pay_interest, user_family_id)
                                        st.success("Payment logged!"); st.rerun()
                        with lp2:
                            with st.form(f"edit_debt_{did}"):
                                e_dname  = st.text_input("Name", value=dname, key=f"edn_{did}")
                                e_dcat   = st.selectbox("Category", DEBT_CATEGORIES, index=DEBT_CATEGORIES.index(dcat) if dcat in DEBT_CATEGORIES else 0, key=f"edc_{did}")
                                e_out    = st.number_input("Outstanding (₹)", value=float(outstanding), min_value=0.0, step=100.0, key=f"edop_{did}")
                                e_emi    = st.number_input("EMI (₹)", value=float(emi), min_value=0.0, step=100.0, key=f"edemi_{did}")
                                uc1, uc2 = st.columns(2)
                                with uc1:
                                    if st.form_submit_button("Update", type="primary"):
                                        if update_debt(did, e_dname, e_dcat, float(total), e_out, float(rate), e_emi, int(row["tenure_months"]), row["start_date"], user_family_id):
                                            st.success("Updated!"); st.rerun()
                                with uc2:
                                    if st.form_submit_button("🚨 Delete"):
                                        if delete_debt(did, user_family_id):
                                            st.success("Deleted!"); st.rerun()
                        pay_df = get_debt_payments(did)
                        if not pay_df.empty:
                            st.markdown("**Payment History:**")
                            st.dataframe(pay_df[["payment_date", "principal_paid", "interest_paid"]], use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 🔮 Debt Payoff Simulator")
                sim_c1, sim_c2 = st.columns(2)
                with sim_c1:
                    strategy = st.selectbox("Payoff Strategy", ["Avalanche (Highest Interest First) - mathematically optimal", "Snowball (Lowest Balance First) - psychological wins"])
                with sim_c2:
                    sim_budget = st.number_input("Total Monthly Debt Budget (₹)", value=float(total_monthly_emi), min_value=float(total_monthly_emi), step=1000.0)
                if st.button("Run Simulation 🚀"):
                    total_months, total_interest, timeline_df = simulate_debt_payoff(debts_df, strategy, sim_budget)
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Months to Debt-Free", f"{total_months} months")
                    r2.metric("Total Interest Paid", format_inr_short(total_interest))
                    from dateutil.relativedelta import relativedelta
                    r3.metric("Payoff Date", (datetime.datetime.now() + relativedelta(months=total_months)).strftime("%b %Y"))
                    fig_debt = px.area(timeline_df, x="Month", y="Total Balance", color_discrete_sequence=["#ef4444"], template="plotly_dark")
                    fig_debt.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
                    st.plotly_chart(fig_debt, use_container_width=True)
            else:
                st.info("🎉 No active debts — you are debt-free!")

        # ════════════════════════════════════════════════════════════════════════
        # TAB 5 ─ TAX PLANNER  (promoted from 3 levels deep to top-level tab)
        # ════════════════════════════════════════════════════════════════════════
        with wp_tab_tax:
            from investment_planner import ADVISORY_DISCLAIMER
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
                compute_tax_saving_rebalance,
                FRSB_RATE, FRSB_RATE_EFFECTIVE, _sum_totals,
            )

            st.markdown("### 🧾 Income Manager & Tax Planner")
            st.caption(f"Log all income sources, compute your tax liability (FY 2025-26), and discover tax-saving opportunities. RBI FRSB: **{FRSB_RATE*100:.2f}%** (effective {FRSB_RATE_EFFECTIVE})")

            # ── Income Sources ───────────────────────────────────────────────────
            st.markdown("#### 💵 Income Sources")
            income_df = get_income_sources_df(username=current_user["username"], family_id=user_family_id, view_mode=view_mode)
            total_monthly_income = float(income_df["monthly_equivalent"].sum()) if not income_df.empty else 0.0
            total_annual_income  = total_monthly_income * 12.0

            if not income_df.empty:
                ki1, ki2, ki3 = st.columns(3)
                ki1.metric("📅 Monthly Income", format_inr(total_monthly_income))
                ki2.metric("📆 Annual Income",  format_inr(total_annual_income))
                ki3.metric("🔢 Sources", str(len(income_df)))
                if len(income_df) > 1:
                    fig_inc = px.bar(income_df.sort_values("monthly_equivalent", ascending=True),
                                     x="monthly_equivalent", y="source_name", orientation="h", color="income_type",
                                     labels={"monthly_equivalent": "Monthly (₹)", "source_name": ""},
                                     template="plotly_dark", height=max(180, len(income_df) * 40))
                    fig_inc.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", margin=dict(l=10,r=10,t=10,b=10))
                    st.plotly_chart(fig_inc, use_container_width=True)

            if "edit_inc_id" not in st.session_state:
                st.session_state["edit_inc_id"] = None
            _inc_icons = {"Salary / Regular Employment": "💼", "Business / Self-Employment": "🏢",
                          "Freelance / Consulting": "💻", "Rental Income": "🏠",
                          "Dividends / Investment Income": "📈", "Pension / Annuity": "🧓",
                          "Capital Gains": "💹", "Agricultural Income": "🌾", "Gifts / Inheritance": "🎁", "Other": "💰"}

            if not income_df.empty:
                inc_rows = list(income_df.iterrows())
                for row_start in range(0, len(inc_rows), 3):
                    grid_cols = st.columns(3)
                    for col_idx, (_, irow) in enumerate(inc_rows[row_start:row_start + 3]):
                        with grid_cols[col_idx]:
                            inc_icon = _inc_icons.get(str(irow["income_type"]), "💰")
                            is_editing = st.session_state.get("edit_inc_id") == irow["id"]
                            if is_editing:
                                with st.form(key=f"edit_inc_form_{irow['id']}"):
                                    e_name   = st.text_input("Source Name", value=str(irow["source_name"]))
                                    e_type   = st.selectbox("Type", INCOME_TYPES, index=INCOME_TYPES.index(irow["income_type"]) if irow["income_type"] in INCOME_TYPES else 0)
                                    e_amount = st.number_input("Amount (₹)", min_value=0.0, step=1000.0, value=float(irow["amount"]))
                                    e_freq   = st.selectbox("Frequency", FREQUENCY_OPTIONS, index=FREQUENCY_OPTIONS.index(irow["frequency"]) if irow["frequency"] in FREQUENCY_OPTIONS else 0)
                                    e_notes  = st.text_input("Notes", value=str(irow["notes"]) if irow["notes"] else "")
                                    esb1, esb2 = st.columns(2)
                                    with esb1:
                                        do_save = st.form_submit_button("💾 Save", type="primary", use_container_width=True)
                                    with esb2:
                                        do_cancel = st.form_submit_button("✖ Cancel", use_container_width=True)
                                    if do_save:
                                        if update_income_source(int(irow["id"]), source_name=e_name, income_type=e_type, amount=e_amount, frequency=e_freq, notes=e_notes):
                                            st.session_state["edit_inc_id"] = None; st.rerun()
                                    if do_cancel:
                                        st.session_state["edit_inc_id"] = None; st.rerun()
                            else:
                                notes_html = f"<div style='color:#64748b; font-size:0.72rem; font-style:italic; margin-top:6px;'>{irow['notes']}</div>" if irow.get("notes") else ""
                                st.markdown(f"""
                                <div style="background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155;
                                            border-radius:12px; padding:16px 18px; margin-bottom:4px; min-height:170px;">
                                    <div style="font-size:1.5rem;">{inc_icon}</div>
                                    <div style="font-weight:700; color:#f1f5f9; margin:6px 0 2px;">{irow['source_name']}</div>
                                    <div style="color:#94a3b8; font-size:0.74rem; margin-bottom:10px;">{irow['income_type']}</div>
                                    <div style="color:#38bdf8; font-weight:600;">{format_inr(float(irow['amount']))} <span style="color:#64748b; font-size:0.74rem;">/ {irow['frequency']}</span></div>
                                    <div style="display:flex; gap:20px; margin-top:8px;">
                                        <div><div style="color:#64748b; font-size:0.68rem;">Monthly</div><div style="color:#34d399; font-size:0.82rem; font-weight:600;">{format_inr(float(irow['monthly_equivalent']))}</div></div>
                                        <div><div style="color:#64748b; font-size:0.68rem;">Annual</div><div style="color:#fbbf24; font-size:0.82rem; font-weight:600;">{format_inr(float(irow['monthly_equivalent'])*12)}</div></div>
                                    </div>{notes_html}
                                </div>""", unsafe_allow_html=True)
                                cbtn1, cbtn2 = st.columns(2)
                                with cbtn1:
                                    if st.button("✏️ Edit", key=f"edit_inc_{irow['id']}", use_container_width=True):
                                        st.session_state["edit_inc_id"] = irow["id"]; st.rerun()
                                with cbtn2:
                                    if st.button("🗑️ Delete", key=f"del_inc_{irow['id']}", use_container_width=True):
                                        if delete_income_source(int(irow["id"]), user_family_id):
                                            if st.session_state.get("edit_inc_id") == irow["id"]:
                                                st.session_state["edit_inc_id"] = None
                                            st.rerun()
            else:
                st.info("No income sources yet. Add your first one below!")

            st.markdown("---")
            st.markdown("<div style='font-weight:700; color:#f1f5f9; margin-bottom:10px;'>➕ Add New Income Source</div>", unsafe_allow_html=True)
            with st.form("add_income_form"):
                ai1, ai2, ai3 = st.columns(3)
                with ai1:
                    i_name = st.text_input("Source Name", placeholder="e.g. Primary Salary")
                    i_type = st.selectbox("Income Type", INCOME_TYPES)
                with ai2:
                    i_amount = st.number_input("Amount (₹)", min_value=0.0, step=1000.0)
                    i_freq   = st.selectbox("Frequency", FREQUENCY_OPTIONS)
                with ai3:
                    i_from  = st.date_input("Effective From", value=datetime.date.today())
                    i_notes = st.text_input("Notes (Optional)")
                if st.form_submit_button("💾 Add Income Source", type="primary"):
                    if i_name and i_amount > 0:
                        new_inc_id = add_income_source(username=current_user["username"], family_id=user_family_id,
                                                        source_name=i_name, income_type=i_type, amount=i_amount,
                                                        frequency=i_freq, effective_from=str(i_from), notes=i_notes)
                        if new_inc_id:
                            st.success(f"✅ Added: {i_name}"); st.rerun()
                    else:
                        st.error("Please provide name and amount.")

            # ── Tax Planner Sections ─────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### 🏛️ Advanced Tax Planner (FY 2025-26)")
            tax_c1, tax_c2 = st.columns(2)
            with tax_c1:
                tax_country_opts = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
                tax_cur_country  = st.session_state.get("user", {}).get("country", "India")
                tax_country      = st.selectbox("🌍 Country of Tax Residence", tax_country_opts,
                                                index=tax_country_opts.index(tax_cur_country) if tax_cur_country in tax_country_opts else 0,
                                                key="tax_country_sel")
                if tax_country != tax_cur_country:
                    from database import update_user_profile
                    update_user_profile(current_user["username"], country=tax_country)
                    st.session_state["user"]["country"] = tax_country
            with tax_c2:
                if tax_country == "India":
                    tax_regime = st.selectbox("📋 Tax Regime", ["New Regime", "Old Regime"], key="tax_regime_sel",
                                              help="New: ₹75k std deduction. Old: ₹50k std + 80C/80D/HRA/24b.")
                else:
                    tax_regime = "N/A"
                    st.info(f"Tax rules auto-applied for {tax_country}.")

            if tax_country == "India":
                _user_key = current_user["username"]
                _fam_id   = current_user.get("family_id", 1)
                _fy       = "2025-26"
                _saved_ded = get_tax_deductions(_user_key, _fam_id, _fy)
                _saved_cg  = get_capital_gains(_user_key, _fam_id, _fy)

                # Section A — Deductions
                with st.expander("📋 Section A — Deductions & TDS", expanded=False):
                    st.caption("Enter deductions for FY 2025-26. Click Save to persist.")
                    _user_age = current_user.get("age", 35)
                    with st.form("tax_deduction_form"):
                        if tax_regime == "Old Regime":
                            st.markdown("##### 80C Investments (Max ₹1.5L)")
                            _dc1, _dc2, _dc3, _dc4 = st.columns(4)
                            _ppf   = _dc1.number_input("PPF (₹)", min_value=0.0, value=float(_saved_ded.get("ppf_contribution", 0)), step=1000.0, key="ded_ppf")
                            _elss  = _dc2.number_input("ELSS (₹)", min_value=0.0, value=float(_saved_ded.get("elss_investment", 0)), step=1000.0, key="ded_elss")
                            _lic   = _dc3.number_input("LIC Premium (₹)", min_value=0.0, value=float(_saved_ded.get("lic_premium", 0)), step=1000.0, key="ded_lic")
                            _hlp   = _dc4.number_input("Home Loan Principal (₹)", min_value=0.0, value=float(_saved_ded.get("home_loan_principal", 0)), step=1000.0, key="ded_hlp")
                            _dc5, _dc6, _dc7, _dc8 = st.columns(4)
                            _school = _dc5.number_input("School Fees (₹)", min_value=0.0, value=float(_saved_ded.get("school_fees", 0)), step=500.0, key="ded_school")
                            _nsc_r  = _dc6.number_input("NSC Interest Reinvested (₹)", min_value=0.0, value=float(_saved_ded.get("nsc_interest_reinvested", 0)), step=100.0, key="ded_nsc")
                            _epf    = _dc7.number_input("EPF (₹)", min_value=0.0, value=float(_saved_ded.get("epf_contribution", 0)), step=500.0, key="ded_epf")
                            _tsfd   = _dc8.number_input("Tax-Saver FD (₹)", min_value=0.0, value=float(_saved_ded.get("tax_saver_fd", 0)), step=1000.0, key="ded_tsfd")
                            _eighty_c_total = min(_ppf + _elss + _lic + _hlp + _school + _nsc_r + _epf + _tsfd, 150000)
                            st.caption(f"80C total (capped ₹1.5L): **{format_inr(_eighty_c_total)}**")
                            st.markdown("##### 80D — Health Insurance")
                            _hc1, _hc2, _hc3 = st.columns(3)
                            _hi_self = _hc1.number_input("Health Ins — Self & Family (₹)", min_value=0.0, value=float(_saved_ded.get("health_ins_self", 0)), step=500.0, key="ded_hi_self")
                            _hi_par  = _hc2.number_input("Health Ins — Parents (₹)", min_value=0.0, value=float(_saved_ded.get("health_ins_parents", 0)), step=500.0, key="ded_hi_par")
                            _par_sr  = _hc3.checkbox("Parents Senior Citizens", value=bool(_saved_ded.get("parents_senior", 0)), key="ded_par_sr")
                            st.markdown("##### HRA, Home Loan Interest & Others")
                            _oc1, _oc2, _oc3 = st.columns(3)
                            _hra_basic = _oc1.number_input("Basic Salary p.a. (₹)", min_value=0.0, value=float(_saved_ded.get("hra_basic_salary", 0)), step=1000.0, key="ded_hra_basic")
                            _hra_recv  = _oc2.number_input("HRA Received p.a. (₹)", min_value=0.0, value=float(_saved_ded.get("hra_received", 0)), step=1000.0, key="ded_hra_recv")
                            _rent_paid = _oc3.number_input("Rent Paid p.a. (₹)", min_value=0.0, value=float(_saved_ded.get("rent_paid", 0)), step=1000.0, key="ded_rent_paid")
                            _oc4, _oc5, _oc6 = st.columns(3)
                            _metro   = _oc4.checkbox("Metro City (50% HRA rule)", value=bool(_saved_ded.get("metro_city", 1)), key="ded_metro")
                            _hl_int  = _oc5.number_input("Home Loan Interest 24(b) (₹)", min_value=0.0, max_value=200000.0, value=float(_saved_ded.get("home_loan_interest", 0)), step=1000.0, key="ded_hl_int")
                            _nps_1b  = _oc6.number_input("NPS 80CCD(1B) (₹)", min_value=0.0, max_value=50000.0, value=float(_saved_ded.get("nps_80ccd_1b", 0)), step=500.0, key="ded_nps_1b")
                        else:
                            st.info("ℹ️ New Regime: Only Standard Deduction (₹75,000), NPS Employer 80CCD(2), and Professional Tax apply.")
                            _ppf=_elss=_lic=_hlp=_school=_nsc_r=_epf=_tsfd=0.0
                            _hi_self=_hi_par=_hra_basic=_hra_recv=_rent_paid=_hl_int=_nps_1b=0.0
                            _par_sr=False; _metro=True; _eighty_c_total=0.0
                        st.markdown("##### Common Deductions")
                        _cc1, _cc2, _cc3, _cc4 = st.columns(4)
                        _nps_emp  = _cc1.number_input("NPS Employer 80CCD(2) (₹)", min_value=0.0, value=float(_saved_ded.get("nps_employer_80ccd2", 0)), step=500.0, key="ded_nps_emp")
                        _prof_tax = _cc2.number_input("Professional Tax (₹ max ₹2,400)", min_value=0.0, max_value=2400.0, value=float(_saved_ded.get("professional_tax", 0)), step=200.0, key="ded_prof_tax")
                        _sb_int   = _cc3.number_input("Savings Bank Interest 80TTA/TTB (₹)", min_value=0.0, value=float(_saved_ded.get("savings_bank_interest", 0)), step=100.0, key="ded_sb_int")
                        _scss_int = _cc4.number_input("SCSS Interest 80TTB (₹)", min_value=0.0, value=float(_saved_ded.get("scss_interest", 0)), step=100.0, key="ded_scss_int")
                        st.markdown("##### TDS & Advance Tax Already Paid")
                        _tp1, _tp2 = st.columns(2)
                        _tds     = _tp1.number_input("TDS Deducted (₹)", min_value=0.0, value=float(_saved_ded.get("tds_deducted", 0)), step=1000.0, key="ded_tds")
                        _adv_pd  = _tp2.number_input("Advance Tax Paid (₹)", min_value=0.0, value=float(_saved_ded.get("advance_paid", 0)), step=1000.0, key="ded_adv_paid")
                        if st.form_submit_button("💾 Save Deductions", type="primary", use_container_width=True):
                            _ded_payload = {
                                "ppf_contribution": _ppf, "elss_investment": _elss, "lic_premium": _lic,
                                "home_loan_principal": _hlp, "school_fees": _school, "nsc_interest_reinvested": _nsc_r,
                                "epf_contribution": _epf, "tax_saver_fd": _tsfd,
                                "health_ins_self": _hi_self, "health_ins_parents": _hi_par, "parents_senior": int(_par_sr),
                                "nps_80ccd_1b": _nps_1b if tax_regime == "Old Regime" else 0,
                                "nps_employer_80ccd2": _nps_emp, "home_loan_interest": _hl_int,
                                "hra_basic_salary": _hra_basic, "hra_received": _hra_recv, "rent_paid": _rent_paid,
                                "metro_city": int(_metro), "professional_tax": _prof_tax,
                                "savings_bank_interest": _sb_int, "scss_interest": _scss_int,
                                "tds_deducted": _tds, "advance_paid": _adv_pd, "age": _user_age,
                            }
                            if upsert_tax_deductions(_user_key, _fam_id, _fy, _ded_payload):
                                _saved_ded = _ded_payload
                                st.success("✅ Deductions saved.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to save.")

                # Section B — Passive Income
                with st.expander("💰 Section B — Passive Income from Portfolio (Auto-Calculated)", expanded=False):
                    st.caption("Auto-derived from your investment holdings. Override any figure if needed.")
                    has_investments = inv_df is not None and not inv_df.empty
                    has_incomes     = income_df is not None and not income_df.empty
                    if has_investments or has_incomes:
                        with st.spinner("Deriving passive income..."):
                            _passive_entries = derive_investment_income(inv_df, income_sources_df=income_df)
                        if _passive_entries:
                            st.markdown(f"🔍 Found **{len(_passive_entries)}** passive income streams:")
                            _override_vals = {}
                            for _pi_idx, _pe in enumerate(_passive_entries):
                                _is_exempt   = "EXEMPT" in _pe.get("taxability", "").upper()
                                _card_border = "#10b981" if _is_exempt else "#38bdf8"
                                st.markdown(f"""<div style="background:#1e293b; border-radius:8px; border-left:4px solid {_card_border};
                                    padding:10px 14px; margin-bottom:6px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <span style="font-weight:700; color:{'#10b981' if _is_exempt else '#38bdf8'};">{_pe['source_name']}</span>
                                        <span style="color:{'#10b981' if _is_exempt else '#fbbf24'}; font-weight:700;">{format_inr(_pe['annual_amount'])}/yr</span>
                                    </div>
                                    <div style="color:#64748b; font-size:0.75rem; margin-top:3px;">{_pe['notes']} · {_pe['taxability']}</div>
                                </div>""", unsafe_allow_html=True)
                                _override_vals[_pi_idx] = st.number_input(f"Override: {_pe['source_name']} (₹/yr)", min_value=0.0, value=float(_pe["annual_amount"]), step=100.0, key=f"passive_override_{_pi_idx}", label_visibility="collapsed")
                            st.session_state["_passive_entries"]  = _passive_entries
                            st.session_state["_passive_overrides"] = _override_vals
                        else:
                            st.info("No passive streams detected. Add FD, FRSB Bond, SGB, or equity holdings with units.")
                    else:
                        st.info("No portfolio holdings found. Add investments first.")

                # Section C — Capital Gains
                with st.expander("📈 Section C — Capital Gains (Upload or Manual)", expanded=False):
                    st.caption("Upload broker/AIS capital gains statement to auto-extract LTCG & STCG.")
                    _cg_tabs = st.tabs(["📤 Upload Document", "✏️ Manual Entry", "📋 Saved Data"])
                    with _cg_tabs[0]:
                        st.markdown("""**Supported:** Zerodha PDF · ICICI Direct PDF · CAMS/KFintech CAS PDF · IT Dept AIS PDF · AIS JSON (decrypted) · AIS ZIP""")
                        with st.expander("ℹ️ AIS files — important note"):
                            st.info("AIS files are encrypted. Password = **PAN (uppercase) + DOB (DDMMYYYY)**. Decrypt with AIS Offline Utility → export JSON → upload here. Or use your broker's P&L PDF for more accurate LTCG/STCG figures.")
                        _fmt_map = {"Auto-detect":"auto","IT Dept AIS — PDF":"ais_pdf","IT Dept AIS — JSON (decrypted)":"ais","IT Dept AIS — ZIP (encrypted)":"ais_zip","ICICI Direct PDF":"icici","Zerodha PDF":"zerodha","CAMS / KFintech PDF":"cams","Anand Rathi PDF":"anand_rathi"}
                        _fmt_override = st.selectbox("Format override", list(_fmt_map.keys()), index=0, key="cg_fmt_override")
                        _cg_file = st.file_uploader("Upload capital gains document", type=["pdf", "json", "zip"], key="cg_upload_file")
                        ais_pan = ais_dob = None
                        if _cg_file is not None and _cg_file.name.lower().endswith(('.zip', '.json')):
                            with st.expander("AIS Decryption Options", expanded=True):
                                col_pan, col_dob = st.columns(2)
                                ais_pan = col_pan.text_input("PAN", key="ais_pan_input", help="Used to decrypt AIS. Not saved.").strip().upper()
                                ais_dob = col_dob.text_input("DOB (DDMMYYYY)", key="ais_dob_input").strip()
                        if _cg_file is not None:
                            with st.spinner(f"Parsing {_cg_file.name}..."):
                                _parsed_cg = parse_capital_gains(_cg_file, file_type_hint=_fmt_map.get(_fmt_override, "auto"), ais_pan=ais_pan, ais_dob=ais_dob)
                            _detected = _parsed_cg.get("detected_format", "unknown"); _src = _parsed_cg.get("source", "Unknown")
                            st.success(f"✅ Detected: **{_detected}** → parsed as **{_src}**")
                            for _pe_err in _parsed_cg.get("parse_errors", []):
                                st.warning(f"⚠️ {_pe_err}")
                            if _parsed_cg.get("debug_text"):
                                with st.expander("🔍 Debug: Raw PDF text"):
                                    st.code(_parsed_cg["debug_text"], language="text")
                            _cg_display = pd.DataFrame([
                                {"Category":"Equity LTCG","Amount (₹)":float(_parsed_cg["equity_ltcg"]),"Tax Rate":"12.5% (above ₹1.25L)","Key":"equity_ltcg"},
                                {"Category":"Equity STCG","Amount (₹)":float(_parsed_cg["equity_stcg"]),"Tax Rate":"20%","Key":"equity_stcg"},
                                {"Category":"Equity MF LTCG","Amount (₹)":float(_parsed_cg["equity_mf_ltcg"]),"Tax Rate":"12.5% (above ₹1.25L)","Key":"equity_mf_ltcg"},
                                {"Category":"Equity MF STCG","Amount (₹)":float(_parsed_cg["equity_mf_stcg"]),"Tax Rate":"20%","Key":"equity_mf_stcg"},
                                {"Category":"Debt MF LTCG","Amount (₹)":float(_parsed_cg["debt_mf_ltcg"]),"Tax Rate":"Slab","Key":"debt_mf_ltcg"},
                                {"Category":"Debt MF STCG","Amount (₹)":float(_parsed_cg["debt_mf_stcg"]),"Tax Rate":"Slab","Key":"debt_mf_stcg"},
                                {"Category":"Property LTCG","Amount (₹)":float(_parsed_cg["property_ltcg"]),"Tax Rate":"12.5% (no indexation)","Key":"property_ltcg"},
                                {"Category":"Property STCG","Amount (₹)":float(_parsed_cg["property_stcg"]),"Tax Rate":"Slab","Key":"property_stcg"},
                                {"Category":"Other LTCG","Amount (₹)":float(_parsed_cg["other_ltcg"]),"Tax Rate":"Slab","Key":"other_ltcg"},
                                {"Category":"Other STCG","Amount (₹)":float(_parsed_cg["other_stcg"]),"Tax Rate":"Slab","Key":"other_stcg"},
                            ])
                            _edited_df = st.data_editor(_cg_display, use_container_width=True, hide_index=True,
                                column_config={
                                    "Category": st.column_config.TextColumn("Category", disabled=True),
                                    "Amount (₹)": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, step=1000.0, format="₹%d"),
                                    "Tax Rate": st.column_config.TextColumn("Tax Rate", disabled=True),
                                    "Key": None,
                                })
                            _live_ltcg = _edited_df.loc[_edited_df["Key"].str.endswith("_ltcg"), "Amount (₹)"].sum()
                            _live_stcg = _edited_df.loc[_edited_df["Key"].str.endswith("_stcg"), "Amount (₹)"].sum()
                            st.markdown(f"**LTCG: {format_inr(_live_ltcg)} | STCG: {format_inr(_live_stcg)}**")
                            if st.button("💾 Save Capital Gains", type="primary", key="save_parsed_cg"):
                                for _, row in _edited_df.iterrows():
                                    _parsed_cg[row["Key"]] = float(row["Amount (₹)"])
                                _parsed_cg = _sum_totals(_parsed_cg)
                                if upsert_capital_gains(_user_key, _fam_id, _fy, _parsed_cg):
                                    _saved_cg = _parsed_cg
                                    st.success("✅ Capital gains saved."); st.rerun()
                    with _cg_tabs[1]:
                        st.markdown("Enter manually (₹):")
                        with st.form("manual_cg_form"):
                            _m1, _m2 = st.columns(2)
                            _m_eq_ltcg   = _m1.number_input("Equity LTCG (Stocks)", min_value=0.0, value=float(_saved_cg.get("equity_ltcg", 0)), step=1000.0, key="mcg_eq_ltcg")
                            _m_eq_stcg   = _m2.number_input("Equity STCG (Stocks)", min_value=0.0, value=float(_saved_cg.get("equity_stcg", 0)), step=1000.0, key="mcg_eq_stcg")
                            _m3, _m4 = st.columns(2)
                            _m_eqmf_ltcg = _m3.number_input("Equity MF LTCG", min_value=0.0, value=float(_saved_cg.get("equity_mf_ltcg", 0)), step=1000.0, key="mcg_eqmf_ltcg")
                            _m_eqmf_stcg = _m4.number_input("Equity MF STCG", min_value=0.0, value=float(_saved_cg.get("equity_mf_stcg", 0)), step=1000.0, key="mcg_eqmf_stcg")
                            _m5, _m6 = st.columns(2)
                            _m_dmf_ltcg  = _m5.number_input("Debt MF LTCG", min_value=0.0, value=float(_saved_cg.get("debt_mf_ltcg", 0)), step=1000.0, key="mcg_dmf_ltcg")
                            _m_dmf_stcg  = _m6.number_input("Debt MF STCG", min_value=0.0, value=float(_saved_cg.get("debt_mf_stcg", 0)), step=1000.0, key="mcg_dmf_stcg")
                            _m7, _m8 = st.columns(2)
                            _m_prop_ltcg = _m7.number_input("Property LTCG", min_value=0.0, value=float(_saved_cg.get("property_ltcg", 0)), step=1000.0, key="mcg_prop_ltcg")
                            _m_prop_stcg = _m8.number_input("Property STCG", min_value=0.0, value=float(_saved_cg.get("property_stcg", 0)), step=1000.0, key="mcg_prop_stcg")
                            if st.form_submit_button("💾 Save Capital Gains", type="primary", use_container_width=True):
                                _manual_cg = {"equity_ltcg": _m_eq_ltcg, "equity_stcg": _m_eq_stcg,
                                              "equity_mf_ltcg": _m_eqmf_ltcg, "equity_mf_stcg": _m_eqmf_stcg,
                                              "debt_mf_ltcg": _m_dmf_ltcg, "debt_mf_stcg": _m_dmf_stcg,
                                              "property_ltcg": _m_prop_ltcg, "property_stcg": _m_prop_stcg,
                                              "other_ltcg": 0.0, "other_stcg": 0.0}
                                _manual_cg = _sum_totals(_manual_cg)
                                if upsert_capital_gains(_user_key, _fam_id, _fy, _manual_cg):
                                    _saved_cg = _manual_cg
                                    st.success("✅ Saved!"); st.rerun()
                    with _cg_tabs[2]:
                        if _saved_cg:
                            st.markdown("**Saved Capital Gains (FY 2025-26):**")
                            cg_display_saved = {k: v for k, v in _saved_cg.items() if isinstance(v, (int, float)) and v > 0 and not k.startswith("_")}
                            st.dataframe(pd.DataFrame(list(cg_display_saved.items()), columns=["Category", "Amount (₹)"]), use_container_width=True, hide_index=True)
                        else:
                            st.info("No capital gains saved yet.")

                # ── Tax Computation ──────────────────────────────────────────────
                st.markdown("---")
                st.markdown("### 🧮 Compute Tax Liability")
                _passive_entries_sess  = st.session_state.get("_passive_entries", [])
                _passive_overrides_sess = st.session_state.get("_passive_overrides", {})
                _passive_final = []
                for _pi_idx, _pe in enumerate(_passive_entries_sess):
                    _pe_copy = dict(_pe)
                    _pe_copy["annual_amount"] = _passive_overrides_sess.get(_pi_idx, _pe["annual_amount"])
                    _passive_final.append(_pe_copy)

                if st.button("🧮 Compute Full Tax Liability", type="primary", use_container_width=True):
                    with st.spinner("Computing..."):
                        _ded_obj = compute_deductions(_saved_ded, tax_regime, _user_age)
                        _cg_tax_obj = compute_cg_tax(_saved_cg)
                        _tax_result = compute_full_tax(
                            gross_income=total_annual_income,
                            passive_income_entries=_passive_final,
                            deductions_obj=_ded_obj,
                            cg_tax_obj=_cg_tax_obj,
                            regime=tax_regime,
                            age=_user_age,
                            tds_paid=float(_saved_ded.get("tds_deducted", 0)),
                            advance_tax_paid=float(_saved_ded.get("advance_paid", 0)),
                        )
                    st.session_state["_tax_result"] = _tax_result

                _tax_result = st.session_state.get("_tax_result")
                if _tax_result:
                    t1, t2, t3, t4 = st.columns(4)
                    t1.metric("📊 Gross Income", format_inr(_tax_result.get("gross_income_total", total_annual_income)))
                    t2.metric("🏛️ Total Deductions", format_inr(_tax_result.get("total_deductions", 0)))
                    t3.metric("💰 Net Taxable Income", format_inr(_tax_result.get("net_taxable_income", 0)))
                    t4.metric("🧾 Net Tax Payable", format_inr(_tax_result.get("net_tax_payable", 0)),
                              delta=f"After TDS ({format_inr(_tax_result.get('tds_paid', 0))}) & advance tax",
                              delta_color="inverse" if _tax_result.get("net_tax_payable", 0) > 0 else "normal")

                    if _tax_result.get("advance_tax_schedule"):
                        st.markdown("#### 📅 Advance Tax Schedule")
                        adv_df = pd.DataFrame(_tax_result["advance_tax_schedule"])
                        st.dataframe(adv_df, use_container_width=True, hide_index=True)

                    if _tax_result.get("tax_saving_rebalance"):
                        st.markdown("#### 💡 Tax-Saving Rebalance Suggestions")
                        for tsr in _tax_result["tax_saving_rebalance"]:
                            st.markdown(f"- **{tsr.get('action', '')}**: {tsr.get('description', '')} — saves **{format_inr(tsr.get('tax_saving', 0))}**")


    # ----------------------------------------------------
    # ⚙️ SETTINGS & ADMIN
    # ----------------------------------------------------
    elif nav_selection == "🎓 Financial Academy":
        # ── Slim branded header ────────────────────────────────────────────────
        st.markdown("""
        <div style='display:flex;align-items:center;gap:10px;padding:8px 14px;
                    background:linear-gradient(90deg,#0f172a,#1e293b);
                    border-radius:8px;border-left:3px solid #34d399;margin-bottom:12px;'>
            <span style='font-size:1rem;'>🧭</span>
            <span style='font-size:1rem;font-weight:700;color:#34d399;'>FinCompass</span>
            <span style='color:#334155;'>|</span>
            <span style='color:#94a3b8;font-size:0.85rem;'>🎓 Financial Academy &nbsp;·&nbsp; Personalised Learning for Every Stage of Life</span>
        </div>
        """, unsafe_allow_html=True)
        from financial_academy import render_financial_academy_tab
        gemini_api_key = (
            current_user.get("gemini_api_key") or
            get_admin_gemini_api_key() or
            os.environ.get("GEMINI_API_KEY", "") or
            st.secrets.get("GEMINI_API_KEY", "")
        )
        render_financial_academy_tab(gemini_api_key)
        
    elif nav_selection == "⚙️ Settings & Admin":
        sa_tab1, sa_tab2, sa_tab3, sa_tab4 = st.tabs(["💾 Data Export", "👑 Admin", "👤 Profile", "ℹ️ About"])
        
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
                        pass # I'll update database.py in a sec if needed

                    if update_user_profile(current_user["username"], profile_data):
                        # Update session state dynamically
                        for k, v in profile_data.items():
                            st.session_state["user"][k] = v
                        
                        # Set recovery info
                        if new_email or new_sq:
                            pass

                        if new_email and not new_sa and not current_user.get("security_answer_hash"):
                            st.error("Please provide a Security Answer to set up recovery.")
                        else:
                            if new_sa:
                                set_user_recovery_info(current_user["username"], new_email, new_sq, new_sa)
                                st.session_state["user"]["email"] = new_email
                                st.session_state["user"]["security_question"] = new_sq
                            elif new_email != current_user.get("email") or new_sq != current_user.get("security_question"):
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
                        ok, msg = create_user(c_user, c_pwd, c_name, c_role, family_id=(user_family_id or current_user.get("family_id", 1)))
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
                    st.markdown("##### 🗑️ Delete User Account(s)")
                    non_admin_users = [u["username"] for u in users_list if u["username"] != "admin"]
                    if non_admin_users:
                        target_users_del = st.multiselect("Select Users to Delete", non_admin_users, key="admin_del_target")
                        if st.button("🗑️ Delete Selected Users", use_container_width=True, disabled=not target_users_del):
                            success_count = 0
                            error_messages = []
                            for target_user in target_users_del:
                                ok, msg = delete_user(target_user)
                                if ok:
                                    success_count += 1
                                else:
                                    error_messages.append(f"{target_user}: {msg}")
                            
                            if success_count > 0:
                                st.success(f"Successfully deleted {success_count} user(s).")
                            if error_messages:
                                for err in error_messages:
                                    st.error(err)
                            
                            if success_count > 0 or error_messages:
                                st.rerun()
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
