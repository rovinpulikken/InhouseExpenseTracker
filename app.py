"""
FinCompass: Smart Financial Hub — Mobile-First Modular Entrypoint.
Handles authentication, Turso cloud status, global sidebar navigation via st.navigation,
and dispatches exclusively to the active page module under views/.
"""

import datetime
import os
import random
import sys

# Ensure repository root is on sys.path for Streamlit Cloud deployment
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import streamlit as st

from database import (
    init_db,
    seed_sample_data_if_empty,
    check_turso_connection,
    enable_turso,
    get_db_type,
    authenticate_user,
    create_family,
    join_family_by_code,
    update_user_password,
    set_user_recovery_info,
    get_user_recovery_info,
    verify_security_answer,
    set_recovery_otp,
    verify_recovery_otp,
    clear_recovery_otp,
)
from email_utils import send_otp_email
import data_layer
import ui

# Page Config
st.set_page_config(
    page_title="FinCompass: Smart Financial Hub",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="auto",
)

ui.inject_global_styles()

# Initialize Database & Seed Data (with fallback protection; guarded to run once per process)
try:
    init_db()
    seed_sample_data_if_empty()
except Exception as _e_init:
    print(f"[Startup Warning] DB initialization caught error: {_e_init}")

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
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
            border: 1px solid #dc2626;
            border-left: 5px solid #ef4444;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        ">
            <span style="font-size: 1.4rem; line-height: 1;">⚠️</span>
            <div>
                <div style="font-weight: 700; color: #fca5a5; font-size: 0.92rem; margin-bottom: 2px;">
                    Turso Remote Database Unreachable
                </div>
                <div style="color: #fecaca; font-size: 0.82rem; line-height: 1.45;">
                    The app fell back to <strong>local SQLite</strong>. Data entered now will <em>not</em> sync to the cloud.
                </div>
                <div style="margin-top: 6px; background: rgba(0,0,0,0.3); border-radius: 6px; padding: 5px 9px;
                            font-family: monospace; font-size: 0.76rem; color: #fda4af; word-break: break-all;">
                    {_err_detail}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🔄 Retry Turso Cloud Connection", key="btn_retry_turso_conn"):
        enable_turso()
        _ok_retry, _err_retry = check_turso_connection(force_probe=True)
        st.session_state["_turso_ok"] = _ok_retry
        st.session_state["_turso_err"] = _err_retry
        if _ok_retry:
            try:
                init_db(force=True)
                seed_sample_data_if_empty()
                data_layer.invalidate_data_cache()
            except Exception as _e_retry:
                print(f"[Retry Warning] DB init error: {_e_retry}")
        st.rerun()


# ----------------------------------------------------
# AUTHENTICATION SCREEN
# ----------------------------------------------------
def _render_auth_screen() -> None:
    hero_path = os.path.join(repo_root, "assets", "brand_hero.jpg")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    main_left, main_right = st.columns([1.15, 1], gap="large")

    with main_left:
        if os.path.exists(hero_path):
            st.image(hero_path, use_container_width=True)

    with main_right:
        st.markdown(
            """
            <div style="margin: 0 auto 16px; padding: 18px 20px 10px; border-radius: 12px;
                        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        border: 1px solid #1d4ed8; text-align: center;">
                <div style="font-size: 1.9rem; font-weight: 900;
                            background: linear-gradient(90deg, #38bdf8, #fbbf24);
                            -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🧭 FinCompass
                </div>
                <p style="color: #94a3b8; font-size: 0.86rem; margin: 4px 0 0;">
                    Smart Financial Hub &middot; Mobile-First &middot; 360° Wealth View
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        auth_tab1, auth_tab2, auth_tab3 = st.tabs([
            "🔑 Sign In",
            "🏠 Register Family",
            "👨‍👩‍👧 Join Family",
        ])

        with auth_tab1:
            with st.form("login_form"):
                login_user = st.text_input("Username", placeholder="e.g. admin", key="login_username").strip()
                login_pwd = st.text_input("Password", type="password", placeholder="••••••••", key="login_pwd")
                submit_login = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)
                if submit_login:
                    user_record = authenticate_user(login_user, login_pwd)
                    if user_record:
                        st.session_state["user"] = user_record
                        st.session_state["_active_family_id"] = user_record.get("family_id", 1)
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            with st.expander("Forgot Password?"):
                st.caption("Recover your account using your email OTP or security question.")
                rec_username = st.text_input("Enter your Username", key="rec_user")
                if st.button("Find Account", key="btn_find_rec"):
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
                    rec_method = st.radio("Recovery Method", ["Answer Security Question", "Send OTP to Email"], key="rec_method")
                    if rec_method == "Answer Security Question":
                        if not info.get("security_question"):
                            st.warning("No security question configured for this account.")
                        else:
                            st.write(f"**Question:** {info['security_question']}")
                            ans = st.text_input("Your Answer", type="password", key="rec_ans")
                            if st.button("Verify Answer", key="btn_ver_ans"):
                                if verify_security_answer(r_user, ans):
                                    st.session_state["recovery_verified"] = True
                                    st.rerun()
                                else:
                                    st.error("Incorrect answer.")
                    else:
                        if not info.get("email"):
                            st.warning("No recovery email configured for this account.")
                        else:
                            st.write(f"OTP destination: **{info['email'][:3]}***@{info['email'].split('@')[-1]}**")
                            oc1, oc2 = st.columns(2)
                            with oc1:
                                if st.button("Send OTP", key="btn_send_otp"):
                                    otp = str(random.randint(100000, 999999))
                                    if set_recovery_otp(r_user, otp) and send_otp_email(info["email"], otp):
                                        st.success("OTP Sent!")
                                    else:
                                        st.error("Failed to send OTP. Check SMTP settings.")
                            with oc2:
                                otp_in = st.text_input("6-digit OTP", key="rec_otp")
                                if st.button("Verify OTP", key="btn_ver_otp"):
                                    if verify_recovery_otp(r_user, otp_in):
                                        clear_recovery_otp(r_user)
                                        st.session_state["recovery_verified"] = True
                                        st.rerun()
                                    else:
                                        st.error("Invalid or expired OTP.")

                    if st.session_state.get("recovery_verified"):
                        new_pwd = st.text_input("New Password", type="password", key="rec_new_pwd")
                        if st.button("Reset Password", type="primary", key="btn_reset_pwd"):
                            if len(new_pwd) < 4:
                                st.error("Password must be at least 4 characters.")
                            else:
                                update_user_password(r_user, new_pwd)
                                st.success("Password reset! You can now sign in.")
                                for k in ("recovery_user", "recovery_info", "recovery_verified"):
                                    st.session_state.pop(k, None)
                                st.rerun()

        with auth_tab2:
            st.caption("Create a new isolated Family Household & become its Family Admin.")
            with st.form("create_family_form"):
                new_fam_name = st.text_input("Family / Household Name", placeholder="e.g. Pulikken Household", key="reg_fam_name")
                fam_admin_user = st.text_input("Admin Username", placeholder="e.g. rovin_admin", key="reg_fam_user")
                fam_admin_fullname = st.text_input("Your Full Name", placeholder="e.g. Rovin Pulikken", key="reg_fam_name_full")
                fam_admin_pwd = st.text_input("Password", type="password", key="reg_fam_pwd")
                fam_admin_email = st.text_input("Recovery Email", placeholder="e.g. you@example.com", key="reg_fam_email")
                fam_admin_sq = st.selectbox(
                    "Security Question",
                    ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"],
                    key="reg_fam_sq",
                )
                fam_admin_sa = st.text_input("Security Answer", type="password", key="reg_fam_sa")
                if st.form_submit_button("🏠 Register Family", type="primary", use_container_width=True):
                    if not fam_admin_email or not fam_admin_sa:
                        st.error("Email and Security Answer are required for recovery.")
                    else:
                        ok, msg, u_rec = create_family(new_fam_name, fam_admin_user, fam_admin_pwd, fam_admin_fullname, fam_admin_email, fam_admin_sq, fam_admin_sa)
                        if ok and u_rec:
                            st.session_state["user"] = u_rec
                            st.session_state["_active_family_id"] = u_rec.get("family_id", 1)
                            data_layer.invalidate_data_cache()
                            st.rerun()
                        else:
                            st.error(msg)

        with auth_tab3:
            st.caption("Join an existing Family using your Family Admin's Join Code.")
            with st.form("join_family_form"):
                join_code = st.text_input("Family Join Code", placeholder="e.g. FAM-PULIKKEN-92A1", key="join_fam_code").strip()
                join_user = st.text_input("Desired Username", placeholder="e.g. priya", key="join_user_name").strip()
                join_full = st.text_input("Your Full Name", placeholder="e.g. Priya Pulikken", key="join_full_name")
                join_pwd = st.text_input("Password", type="password", key="join_user_pwd")
                join_email = st.text_input("Recovery Email", placeholder="e.g. priya@example.com", key="join_email")
                join_sq = st.selectbox(
                    "Security Question",
                    ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"],
                    key="join_sq",
                )
                join_sa = st.text_input("Security Answer", type="password", key="join_sa")
                if st.form_submit_button("👨‍👩‍👧 Join Family", type="primary", use_container_width=True):
                    if not join_email or not join_sa:
                        st.error("Email and Security Answer are required for recovery.")
                    else:
                        ok, msg, u_rec = join_family_by_code(join_code, join_user, join_pwd, join_full, "Member", join_email, join_sq, join_sa)
                        if ok and u_rec:
                            st.session_state["user"] = u_rec
                            st.session_state["_active_family_id"] = u_rec.get("family_id", 1)
                            data_layer.invalidate_data_cache()
                            st.rerun()
                        else:
                            st.error(msg)


# ----------------------------------------------------
# LAZY PAGE DISPATCHERS (only imports the active page!)
# ----------------------------------------------------
def _pg_home():
    from views.home import render
    render()


def _pg_transactions():
    from views.transactions import render
    render()


def _pg_budgets():
    from views.budgets import render
    render()


def _pg_insights():
    from views.insights import render
    render()


def _pg_reports():
    from views.reports import render
    render()


def _pg_portfolio():
    from views.portfolio import render
    render()


def _pg_loans():
    from views.loans import render
    render()


def _pg_tax():
    from views.tax_income import render
    render()


def _pg_retirement():
    from views.retirement import render
    render()


def _pg_academy():
    from views.academy import render
    render()


def _pg_settings():
    from views.settings import render
    render()


def _pg_admin():
    from views.admin import render
    render()


# ----------------------------------------------------
# MAIN APPLICATION ROUTER
# ----------------------------------------------------
if "user" not in st.session_state:
    _render_auth_screen()
else:
    current_user = st.session_state["user"]

    # Auto-calculate age from DOB whenever present
    if current_user.get("dob"):
        try:
            _dob_dt = datetime.datetime.strptime(str(current_user["dob"]).strip(), "%Y-%m-%d").date()
            _today = datetime.date.today()
            current_user["age"] = max(0, _today.year - _dob_dt.year - ((_today.month, _today.day) < (_dob_dt.month, _dob_dt.day)))
        except Exception:
            pass

    # Mandatory recovery setup for legacy users missing email/security question
    if not current_user.get("email") or not current_user.get("security_question"):
        st.warning("⚠️ Action Required: Complete your password recovery details to secure your account.")
        with st.form("mandatory_setup_form"):
            setup_email = st.text_input("Email Address (Mandatory)", value=current_user.get("email") or "")
            setup_sq = st.selectbox(
                "Security Question",
                ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"],
            )
            setup_sa = st.text_input("Security Answer", type="password")
            if st.form_submit_button("Save & Continue", type="primary", use_container_width=True):
                if not setup_email or not setup_sa:
                    st.error("Email and Security Answer are mandatory.")
                elif set_user_recovery_info(current_user["username"], setup_email, setup_sq, setup_sa):
                    st.session_state["user"]["email"] = setup_email
                    st.session_state["user"]["security_question"] = setup_sq
                    st.rerun()
                else:
                    st.error("Failed to save recovery info.")
        if st.button("Sign Out"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    is_super_admin = (current_user.get("username") == "admin" or current_user.get("role") == "Super Admin")
    is_admin = is_super_admin or (current_user.get("role") == "Admin")

    # ── Clean Compact Sidebar ───────────────────────────────────────────
    st.sidebar.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding: 2px 0 8px;">
            <div>
                <div style="font-size:1.15rem; font-weight:900;
                            background:linear-gradient(90deg,#38bdf8,#fbbf24);
                            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                    🧭 FinCompass
                </div>
                <div style="font-size:0.76rem; color:#94a3b8;">
                    🏠 {current_user.get('family_name', 'Primary Household')}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Super Admin household switcher
    if is_super_admin:
        all_fams = data_layer.cached_get_all_families()
        fam_opts = ["🌐 All Families"] + [f"{f['family_name']} ({f['family_code']})" for f in all_fams]
        sel_fam = st.sidebar.selectbox("Household Scope", fam_opts, index=0, key="sb_super_fam", label_visibility="collapsed")
        if sel_fam == "🌐 All Families":
            st.session_state["_active_family_id"] = None
        else:
            code = sel_fam.split("(")[-1].replace(")", "").strip()
            matched = next((f for f in all_fams if f["family_code"] == code), None)
            st.session_state["_active_family_id"] = matched["id"] if matched else 1
    else:
        st.session_state["_active_family_id"] = current_user.get("family_id", 1)

    active_family_id = st.session_state.get("_active_family_id", 1)

    # Global 1-tap primary action button
    if st.sidebar.button("➕ Add Transaction", type="primary", use_container_width=True, key="sb_btn_add_tx"):
        ui.open_add_transaction_dialog(current_user, active_family_id)

    if st.session_state.pop("_reopen_add_tx", False):
        ui.open_add_transaction_dialog(current_user, active_family_id)

    # Sandbox banner (strictly gated behind is_sandbox_mode)
    if st.session_state.get("is_sandbox_mode", False):
        st.error("🎮 **SANDBOX MODE ACTIVE**: Data is simulated. Your real financial data is safe and hidden.")

    # ── Grouped Navigation (st.navigation) ──────────────────────────────
    p_home = st.Page(_pg_home, title="Home", icon="🏠", url_path="home", default=True)
    p_tx = st.Page(_pg_transactions, title="Transactions", icon="💸", url_path="transactions")
    p_budgets = st.Page(_pg_budgets, title="Budgets & Goals", icon="🎯", url_path="budgets")

    p_insights = st.Page(_pg_insights, title="Insights", icon="📊", url_path="insights")
    p_reports = st.Page(_pg_reports, title="Reports", icon="📑", url_path="reports")

    p_portfolio = st.Page(_pg_portfolio, title="Portfolio", icon="📈", url_path="portfolio")
    p_loans = st.Page(_pg_loans, title="Loans & EMIs", icon="🏦", url_path="loans")

    p_tax = st.Page(_pg_tax, title="Tax & Income", icon="🧾", url_path="tax")
    p_retire = st.Page(_pg_retirement, title="Retirement", icon="🏖️", url_path="retirement")

    p_academy = st.Page(_pg_academy, title="Academy", icon="🎓", url_path="academy")
    p_settings = st.Page(_pg_settings, title="Settings", icon="⚙️", url_path="settings")
    p_admin = st.Page(_pg_admin, title="Admin", icon="👑", url_path="admin")

    more_pages = [p_academy, p_settings]
    if is_admin:
        more_pages.append(p_admin)

    pages_registry = {
        "home": p_home,
        "transactions": p_tx,
        "budgets": p_budgets,
        "insights": p_insights,
        "reports": p_reports,
        "portfolio": p_portfolio,
        "loans": p_loans,
        "tax": p_tax,
        "retirement": p_retire,
        "academy": p_academy,
        "settings": p_settings,
        "admin": p_admin,
    }
    st.session_state["_pages"] = pages_registry

    pg = st.navigation(
        {
            "Track": [p_home, p_tx, p_budgets],
            "Analyze": [p_insights, p_reports],
            "Grow": [p_portfolio, p_loans],
            "Plan": [p_tax, p_retire],
            "More": more_pages,
        },
        position="sidebar",
    )

    # Subtle sidebar footer (Sign Out + Cloud sync status dot)
    st.sidebar.markdown("---")
    db_t = get_db_type()
    is_cloud = ("Turso" in db_t and "fallback" not in db_t.lower())
    dot_color = "#10b981" if is_cloud else "#f59e0b"
    dot_label = "Cloud synced" if is_cloud else "Local SQLite"
    st.sidebar.markdown(
        f'<div style="font-size:0.75rem; color:#94a3b8; margin-bottom:8px;">'
        f'<span style="color:{dot_color};">●</span> {dot_label} &middot; @{current_user["username"]}</div>',
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🚪 Sign Out", use_container_width=True, key="sb_sign_out"):
        st.session_state.clear()
        st.rerun()

    pg.run()
