"""
Admin Page — More Section (Role-Gated: Admin & Super Admin only).
Single-level pill sub-navigation:
  1. Users & Roles (Create member, update roles, delete accounts)
  2. Raw DB Log    (Full interactive inline database log & export)
"""

import pandas as pd
import streamlit as st

from config import EXPENSE_CATEGORIES
from database import create_user, update_user_role, delete_user
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, is_super_admin = ui.get_active_user()
    ui.render_mobile_quick_bar("admin")

    if current_user.get("role") != "Admin" and not is_super_admin:
        st.error("⚠️ Administrator privileges are required to access this page.")
        return

    ui.render_page_header(
        "👑",
        "Admin Console",
        subtitle="Manage household member accounts, roles, and raw database records.",
        accent="#e11d48",
        badge="Super Admin" if is_super_admin else "Family Admin",
        help_key="admin",
    )

    sub_opts = ["👥 Users & Roles", "🗄️ Raw DB Log"]
    default_sub = ui.consume_target_sub("admin", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Admin Section", sub_opts, key="adm_sub_nav", default=default_sub)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if active_sub == "👥 Users & Roles":
        _render_users(current_user, user_family_id)
    else:
        _render_raw_db_log(current_user, user_family_id, is_super_admin)


def _render_users(current_user, user_family_id) -> None:
    st.markdown("##### ➕ Register New Household Member")
    with st.form("adm_create_user"):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1.4])
        c_user = c1.text_input("Username", placeholder="e.g. priya").strip().lower()
        c_name = c2.text_input("Full Name", placeholder="e.g. Priya Sharma").strip()
        c_pwd = c3.text_input("Initial Password", type="password")
        c_role = c4.selectbox("Role", ["Member", "Admin"])
        if st.form_submit_button("🚀 Create Account", type="primary", use_container_width=True):
            ok, msg = create_user(c_user, c_pwd, c_name, c_role, family_id=(user_family_id or current_user.get("family_id", 1)))
            if ok:
                data_layer.invalidate_data_cache()
                st.toast(f"✅ {msg}")
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown("##### 👥 Member Directory")
    users = data_layer.cached_get_all_users(family_id=user_family_id)
    if users:
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**🎭 Update User Role**")
            target_u = st.selectbox("Select User", [u["username"] for u in users], key="adm_role_u")
            new_r = st.selectbox("Assign Role", ["Member", "Admin"], key="adm_role_r")
            if st.button("Update Role", type="primary", use_container_width=True, key="adm_btn_role"):
                ok, msg = update_user_role(target_u, new_r)
                if ok:
                    data_layer.invalidate_data_cache()
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
        with m2:
            st.markdown("**🗑️ Delete User Account(s)**")
            non_admin = [u["username"] for u in users if u["username"] != "admin"]
            if non_admin:
                targets = st.multiselect("Select Users to Delete", non_admin, key="adm_del_u")
                if st.button("🗑️ Delete Selected", use_container_width=True, disabled=not targets, key="adm_btn_del"):
                    del_ok = 0
                    for tu in targets:
                        ok, msg = delete_user(tu)
                        if ok:
                            del_ok += 1
                        else:
                            st.error(f"{tu}: {msg}")
                    if del_ok:
                        data_layer.invalidate_data_cache()
                        st.toast(f"🗑️ Deleted {del_ok} account(s).")
                        st.rerun()
            else:
                st.caption("No secondary users to delete.")


def _render_raw_db_log(current_user, user_family_id, is_super_admin: bool) -> None:
    scope = st.session_state.get("scope", {"view": "Family", "fy": "All FYs"})
    view_mode = scope.get("view", "Family")
    selected_fy = scope.get("fy", "All FYs")

    st.caption("Raw database records editor for administrators. Double-click cells to modify and click **Save All Edits**.")
    expenses_table = data_layer.get_expenses_df(
        fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id, transaction_type="All"
    )
    if expenses_table.empty:
        st.info("No records found for the active scope.")
        return

    if "expense_date" in expenses_table.columns:
        expenses_table["expense_date"] = pd.to_datetime(expenses_table["expense_date"], errors="coerce").dt.date

    desired_cols = ["id", "expense_date", "transaction_type", "category", "description", "amount", "financial_year", "quarter", "half_year", "visibility", "username"]
    if is_super_admin:
        desired_cols.append("family_id")
    desired_cols.append("source_note")
    cols_to_show = [c for c in desired_cols if c in expenses_table.columns]

    col_cfg = {
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "expense_date": st.column_config.DateColumn("Date", required=True),
        "transaction_type": st.column_config.SelectboxColumn("Type", options=["Expense", "Income"], required=True),
        "category": st.column_config.SelectboxColumn("Category", options=ui.ALL_TRANSACTION_CATEGORIES, required=True),
        "description": st.column_config.TextColumn("Description"),
        "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
        "financial_year": st.column_config.TextColumn("FY", disabled=True),
        "quarter": st.column_config.TextColumn("Q", disabled=True),
        "half_year": st.column_config.TextColumn("H", disabled=True),
        "visibility": st.column_config.SelectboxColumn("Sharing", options=["Family", "Private"], required=True),
        "username": st.column_config.TextColumn("Logged By", disabled=True),
        "family_id": st.column_config.NumberColumn("Family ID", disabled=True),
        "source_note": st.column_config.TextColumn("Source", disabled=True),
    }

    edited_db = st.data_editor(
        expenses_table[cols_to_show],
        num_rows="dynamic",
        column_config={c: col_cfg[c] for c in cols_to_show if c in col_cfg},
        use_container_width=True,
        hide_index=True,
        key="adm_raw_db_editor",
    )
    a1, a2 = st.columns(2)
    with a1:
        if st.button("💾 Save All Database Edits", type="primary", use_container_width=True, key="adm_save_db"):
            cnt = data_layer.update_expenses_df(edited_db)
            st.toast(f"✅ Updated {cnt} record(s)!")
            st.rerun()
    with a2:
        st.download_button(
            "📥 Export Raw Table CSV",
            data=expenses_table.to_csv(index=False).encode("utf-8"),
            file_name=f"FinCompass_RawDB_{selected_fy.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

