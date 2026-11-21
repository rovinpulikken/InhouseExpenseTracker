"""
Settings Page — More Section.
Single-level pill sub-navigation splitting the old monolithic profile form into focused panels:
  1. Profile      (Name, DOB/auto-calculated Age with role-based lock, Location, Risk Tolerance)
  2. Integrations (Gemini API Key, Gmail IMAP Email & App Password, Statement PDF Password)
  3. Security     (Change Password, Password Recovery Email & Security Question)
  4. Family       (Active Household name, Join Code, Members directory)
  5. Data         (Turso/SQLite storage status + Retry button, Full Backup link, About FinCompass)
"""

import datetime
import pandas as pd
import streamlit as st

from database import (
    update_user_profile,
    update_user_password,
    set_user_recovery_info,
    get_db_type,
    check_turso_connection,
    enable_turso,
    init_db,
)
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, is_super_admin = ui.get_active_user()
    ui.render_mobile_quick_bar("settings")

    ui.render_page_header(
        "⚙️",
        "Settings",
        subtitle="Manage your personal profile, API integrations, account security, family workspace, and cloud sync.",
        accent="#94a3b8",
        badge=f"@{current_user['username']}",
    )

    sub_opts = ["👤 Profile", "🔌 Integrations", "🔒 Security", "🏠 Family", "💾 Data"]
    default_sub = ui.consume_target_sub("settings", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Settings Section", sub_opts, key="set_sub_nav", default=default_sub)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if active_sub == "👤 Profile":
        _render_profile(current_user, is_super_admin)
    elif active_sub == "🔌 Integrations":
        _render_integrations(current_user)
    elif active_sub == "🔒 Security":
        _render_security(current_user)
    elif active_sub == "🏠 Family":
        _render_family(current_user, user_family_id)
    else:
        _render_data_and_about()


def _render_profile(current_user, is_super_admin: bool) -> None:
    today = datetime.date.today()
    dob_str = str(current_user.get("dob") or "").strip()
    is_dob_set = False
    if dob_str:
        try:
            parsed_dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
            is_dob_set = True
        except Exception:
            parsed_dob = datetime.date(1990, 1, 1)
    else:
        cur_age = int(current_user.get("age", 35) or 35)
        parsed_dob = datetime.date(max(1900, today.year - cur_age), 1, 1)

    calc_age = max(0, today.year - parsed_dob.year - ((today.month, today.day) < (parsed_dob.month, parsed_dob.day)))
    is_admin_or_super = is_super_admin or current_user.get("role") in ("Admin", "Super Admin")
    can_edit_dob = is_admin_or_super or (not is_dob_set)

    with st.form("set_profile_form"):
        st.markdown("##### Basic Information")
        c1, c2 = st.columns(2)
        new_name = c1.text_input("Full Name", value=current_user.get("full_name", ""))
        new_dob = c2.date_input(
            "Date of Birth",
            value=parsed_dob,
            min_value=datetime.date(1900, 1, 1),
            max_value=today,
            disabled=not can_edit_dob,
            help="Editable by Admin/Super Admin." if is_admin_or_super else ("Locked once set." if is_dob_set else "Set your Date of Birth."),
        )
        c3, c4 = st.columns(2)
        c3.number_input("Age (Auto-Calculated)", min_value=0, max_value=120, value=calc_age, disabled=True)
        sex_opts = ["Not Specified", "Male", "Female", "Other"]
        cur_sex = current_user.get("sex", "Not Specified")
        new_sex = c4.selectbox("Sex", sex_opts, index=sex_opts.index(cur_sex) if cur_sex in sex_opts else 0)

        st.markdown("##### Location & Financial Profile")
        l1, l2, l3 = st.columns(3)
        new_city = l1.text_input("City", value=current_user.get("city", ""))
        new_state = l2.text_input("State", value=current_user.get("state", ""))
        new_country = l3.text_input("Country", value=current_user.get("country", "India"))
        new_addr = st.text_area("Address", value=current_user.get("address", ""), height=70)

        f1, f2, f3 = st.columns(3)
        inc_opts = ["Not Specified", "< ₹10L", "₹10L - ₹25L", "₹25L - ₹50L", "> ₹50L"]
        cur_inc = current_user.get("income_range", "Not Specified")
        new_inc = f1.selectbox("Annual Income Range", inc_opts, index=inc_opts.index(cur_inc) if cur_inc in inc_opts else 0)
        mar_opts = ["Not Specified", "Single", "Married", "Divorced", "Widowed"]
        cur_mar = current_user.get("marital_status", "Not Specified")
        new_mar = f2.selectbox("Marital Status", mar_opts, index=mar_opts.index(cur_mar) if cur_mar in mar_opts else 0)
        risk_opts = ["Conservative", "Moderate", "Aggressive"]
        cur_risk = current_user.get("risk_tolerance", "Moderate")
        new_risk = f3.selectbox("Risk Tolerance", risk_opts, index=risk_opts.index(cur_risk) if cur_risk in risk_opts else 1)
        new_occ = st.text_input("Occupation / Profession", value=current_user.get("occupation", ""))

        if st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True):
            final_dob = new_dob.isoformat() if can_edit_dob else dob_str
            final_age = max(0, today.year - new_dob.year - ((today.month, today.day) < (new_dob.month, new_dob.day))) if can_edit_dob else calc_age
            payload = {
                "full_name": new_name, "age": final_age, "sex": new_sex, "dob": final_dob,
                "address": new_addr, "city": new_city, "state": new_state, "country": new_country,
                "income_range": new_inc, "occupation": new_occ, "marital_status": new_mar, "risk_tolerance": new_risk,
            }
            if update_user_profile(current_user["username"], payload):
                for k, v in payload.items():
                    st.session_state["user"][k] = v
                data_layer.invalidate_data_cache()
                st.toast("✅ Profile saved!")
                st.rerun()
            else:
                st.error("Failed to save profile.")


def _render_integrations(current_user) -> None:
    st.markdown("#### 🔌 AI & Statement Integrations")
    st.caption("Configure your Gemini API key, Gmail IMAP credentials, and default PDF statement password.")
    with st.form("set_integrations_form"):
        api_key = st.text_input("Gemini API Key", value=current_user.get("gemini_api_key") or "", type="password", help="Used for AI statement parsing, portfolio optimization, and advisory.")
        imap_email = st.text_input("Gmail Address (IMAP Sync)", value=current_user.get("imap_email") or "", placeholder="your.email@gmail.com")
        imap_pwd = st.text_input("Google App Password (16 chars)", value=current_user.get("imap_app_password") or "", type="password", help="Create at myaccount.google.com/apppasswords.")
        pdf_pwd = st.text_input("Default Bank/Card PDF Password", value=current_user.get("pdf_password") or "", type="password")
        if st.form_submit_button("💾 Save Integrations", type="primary", use_container_width=True):
            payload = {
                "gemini_api_key": api_key.strip(),
                "imap_email": imap_email.strip(),
                "imap_app_password": imap_pwd.strip().replace(" ", ""),
                "pdf_password": pdf_pwd.strip(),
            }
            if update_user_profile(current_user["username"], payload):
                for k, v in payload.items():
                    st.session_state["user"][k] = v
                data_layer.invalidate_data_cache()
                st.toast("✅ Integration settings saved!")
                st.rerun()


def _render_security(current_user) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🔑 Change Password")
        with st.form("set_pwd_form"):
            p1 = st.text_input("New Password", type="password", help="Minimum 4 characters")
            p2 = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("💾 Update Password", type="primary", use_container_width=True):
                if p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = update_user_password(current_user["username"], p1)
                    if ok:
                        st.toast("✅ Password updated!")
                    else:
                        st.error(msg)
    with c2:
        st.markdown("##### 🛡️ Recovery Email & Security Question")
        sq_opts = ["What was the name of your first pet?", "In what city were you born?", "What is your mother's maiden name?", "What high school did you attend?"]
        cur_sq = current_user.get("security_question", "")
        with st.form("set_rec_form"):
            r_email = st.text_input("Recovery Email", value=current_user.get("email") or "")
            r_sq = st.selectbox("Security Question", sq_opts, index=sq_opts.index(cur_sq) if cur_sq in sq_opts else 0)
            r_sa = st.text_input("New Security Answer (leave blank to keep existing)", type="password")
            if st.form_submit_button("💾 Save Recovery Settings", type="primary", use_container_width=True):
                if set_user_recovery_info(current_user["username"], r_email, r_sq, r_sa):
                    st.session_state["user"]["email"] = r_email
                    st.session_state["user"]["security_question"] = r_sq
                    st.toast("✅ Recovery info updated!")
                    st.rerun()


def _render_family(current_user, user_family_id) -> None:
    fam_name = current_user.get("family_name", "Primary Household")
    fam_code = current_user.get("family_code", "PRIMARY-1001")
    st.markdown(
        f"""
        <div class="fc-card" style="border-left: 4px solid #38bdf8;">
            <div style="font-size:1.05rem; font-weight:700; color:#f8fafc;">🏠 {fam_name}</div>
            <div style="margin-top:6px; color:#94a3b8; font-size:0.88rem;">
                Family Join Code: <code style="color:#fbbf24; font-size:1rem; padding:3px 8px;">{fam_code}</code>
            </div>
            <div style="margin-top:4px; color:#64748b; font-size:0.78rem;">Share this join code with household members so they can join your shared workspace.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    users = data_layer.cached_get_all_users(family_id=user_family_id)
    if users:
        st.markdown("##### 👥 Household Members")
        st.dataframe(pd.DataFrame(users)[["username", "full_name", "role"]], use_container_width=True, hide_index=True)


def _render_data_and_about() -> None:
    st.markdown("#### 🌐 Cloud Database & Storage Status")
    db_type = get_db_type()
    if "Turso" in db_type and "fallback" not in db_type.lower():
        st.success(f"✅ Connected to **{db_type}** — your records sync to the cloud automatically.")
    else:
        st.warning(f"💻 Currently running on **{db_type}**.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Test / Reconnect Turso Cloud", type="primary", use_container_width=True, key="set_retry_turso"):
            enable_turso()
            ok, err = check_turso_connection(force_probe=True)
            st.session_state["_turso_ok"] = ok
            st.session_state["_turso_err"] = err
            if ok:
                init_db(force=True)
                data_layer.invalidate_data_cache()
                st.toast("✅ Reconnected to Turso Cloud!")
            else:
                st.error(f"Turso unreachable: {err}")
            st.rerun()
    with c2:
        if st.button("📦 Go to Reports & Data Exports", use_container_width=True, key="set_go_exports"):
            ui.navigate_to("reports", sub_tab="📦 Exports")

    st.markdown("---")
    st.markdown("#### ℹ️ About FinCompass")
    st.caption("FinCompass: Smart Financial Hub — Mobile-first Household Expense Tracker, Portfolio Analyzer, Retirement & India Tax Planner.")

