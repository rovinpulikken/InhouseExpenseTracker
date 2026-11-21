"""
Central Reports Hub — Analyze Section.
Hybrid Reporting Architecture:
  1. Statements    (Monthly Statement, FY Annual Summary, Portfolio Statement, Tax Summary) — on-demand
  2. Health Report (5-Pillar Financial Health Status & Customisable Audit Report) — on-demand
  3. Exports       (One-click raw CSV / Excel data backups across all entities)
"""

import datetime
import pandas as pd
import streamlit as st

from config import format_inr_short, get_indian_fy
from financial_report import render_financial_health_report_ui
import reports_engine
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, is_super_admin = ui.get_active_user()
    ui.render_mobile_quick_bar("reports")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=True, show_month=False, page_key="reports"
    )
    view_mode = scope["view"]
    selected_fy = scope["fy"]
    all_fys = scope["all_fys"]

    ui.render_page_header(
        "📑",
        "Reports & Statements",
        subtitle="Generate print-ready PDF/HTML statements, Excel workbooks, and full data exports on demand.",
        accent="#38bdf8",
        badge=f"{view_mode} · {selected_fy}",
        help_key="reports",
    )

    sub_opts = ["📄 Statements", "🩺 Health Report", "📦 Exports"]
    default_sub = ui.consume_target_sub("reports", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Reports Section", sub_opts, key="rep_sub_nav", default=default_sub)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if active_sub == "📄 Statements":
        _render_statements(current_user, user_family_id, view_mode, selected_fy, all_fys)
    elif active_sub == "🩺 Health Report":
        _render_health_report(current_user, user_family_id, view_mode, selected_fy)
    else:
        _render_exports(current_user, user_family_id, view_mode, selected_fy, is_super_admin)


def _render_statements(current_user, user_family_id, view_mode: str, selected_fy: str, all_fys) -> None:
    user_label = f"{current_user.get('full_name', current_user['username'])} ({view_mode})"
    clean_user = (current_user.get("username") or "user").replace(" ", "_")

    all_tx = data_layer.get_expenses_df(
        fy="All FYs",
        username=current_user["username"],
        view_mode=view_mode,
        family_id=user_family_id,
        transaction_type="All",
    )
    inc_df = data_layer.cached_get_income_sources_df(
        username=current_user["username"], family_id=user_family_id, view_mode=view_mode
    )
    rec_mo_inc = float(inc_df["monthly_equivalent"].sum()) if not inc_df.empty and "monthly_equivalent" in inc_df.columns else 0.0

    # Available months across all history
    mk_set = {datetime.date.today().strftime("%Y-%m")}
    if not all_tx.empty and "expense_date" in all_tx.columns:
        for mk in pd.to_datetime(all_tx["expense_date"], errors="coerce").dropna().dt.strftime("%Y-%m").unique():
            if mk:
                mk_set.add(mk)
    avail_months = sorted(list(mk_set), reverse=True)

    col1, col2 = st.columns(2)

    # ── Card 1: Monthly Statement ────────────────────────────────────────
    with col1:
        with st.container(border=True):
            st.markdown("#### 📅 Monthly Statement")
            st.caption("Income, expenses by category vs. budget, net savings, and itemized transactions.")
            sel_m = st.selectbox("Select Month", avail_months, key="rep_stmt_month")
            if st.button("⚡ Generate Monthly Statement", type="primary", use_container_width=True, key="rep_gen_mo"):
                m_df = ui.filter_df_by_month(all_tx, sel_m)
                try:
                    m_fy = get_indian_fy(datetime.datetime.strptime(sel_m, "%Y-%m").date())
                except Exception:
                    m_fy = selected_fy
                b_df = data_layer.get_budget_status(m_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id)
                data = reports_engine.build_monthly_statement_data(m_df, sel_m, recurring_monthly_income=rec_mo_inc, budget_df=b_df)
                st.session_state["_rep_monthly_cache"] = {
                    "key": sel_m,
                    "html": reports_engine.generate_monthly_statement_html(data, user_label=user_label),
                    "xlsx": reports_engine.generate_monthly_statement_excel(data),
                }

            mc = st.session_state.get("_rep_monthly_cache")
            if mc and mc.get("key") == sel_m:
                d1, d2 = st.columns(2)
                d1.download_button("🖨️ HTML / PDF", mc["html"], f"Monthly_Statement_{sel_m}.html", "text/html", use_container_width=True)
                d2.download_button("📊 Excel (.xlsx)", mc["xlsx"], f"Monthly_Statement_{sel_m}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # ── Card 2: FY Annual Summary ────────────────────────────────────────
    with col2:
        with st.container(border=True):
            st.markdown("#### 📆 FY Annual Summary")
            st.caption("12-month cash flow breakdown, top spending categories, and annual savings rate.")
            fy_opts = ["All FYs"] + list(all_fys)
            sel_fy_rep = st.selectbox("Select Financial Year", fy_opts, index=fy_opts.index(selected_fy) if selected_fy in fy_opts else 0, key="rep_stmt_fy")
            if st.button("⚡ Generate FY Summary", type="primary", use_container_width=True, key="rep_gen_fy"):
                fy_tx = data_layer.get_expenses_df(
                    fy=sel_fy_rep, username=current_user["username"], view_mode=view_mode, family_id=user_family_id, transaction_type="All"
                )
                fy_data = reports_engine.build_fy_summary_data(fy_tx, sel_fy_rep, annual_recurring_income=rec_mo_inc * 12.0)
                st.session_state["_rep_fy_cache"] = {
                    "key": sel_fy_rep,
                    "html": reports_engine.generate_fy_summary_html(fy_data, user_label=user_label),
                    "xlsx": reports_engine.generate_fy_summary_excel(fy_data),
                }

            fc = st.session_state.get("_rep_fy_cache")
            if fc and fc.get("key") == sel_fy_rep:
                d1, d2 = st.columns(2)
                safe_fy = sel_fy_rep.replace(" ", "_")
                d1.download_button("🖨️ HTML / PDF", fc["html"], f"FY_Summary_{safe_fy}.html", "text/html", use_container_width=True)
                d2.download_button("📊 Excel (.xlsx)", fc["xlsx"], f"FY_Summary_{safe_fy}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    col3, col4 = st.columns(2)

    # ── Card 3: Portfolio Statement ──────────────────────────────────────
    with col3:
        with st.container(border=True):
            st.markdown("#### 📈 Portfolio Valuation Statement")
            st.caption("Complete asset allocation, unrealised P&L, and holding-level valuation snapshot.")
            inv_df = data_layer.get_user_investments_df(
                username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id
            )
            tot_val = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
            st.caption(f"Current Portfolio: **{format_inr_short(tot_val)}** across **{len(inv_df)}** holding(s).")
            if st.button("⚡ Generate Portfolio Statement", type="primary", use_container_width=True, key="rep_gen_port"):
                st.session_state["_rep_port_cache"] = {
                    "html": reports_engine.generate_portfolio_statement_html(inv_df, user_label=user_label),
                    "xlsx": reports_engine.generate_portfolio_statement_excel(inv_df),
                }
            pc = st.session_state.get("_rep_port_cache")
            if pc:
                today_s = datetime.date.today().strftime("%Y%m%d")
                d1, d2 = st.columns(2)
                d1.download_button("🖨️ HTML / PDF", pc["html"], f"Portfolio_Statement_{clean_user}_{today_s}.html", "text/html", use_container_width=True)
                d2.download_button("📊 Excel (.xlsx)", pc["xlsx"], f"Portfolio_Statement_{clean_user}_{today_s}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # ── Card 4: Tax Summary Statement ────────────────────────────────────
    with col4:
        with st.container(border=True):
            st.markdown("#### 🧾 Tax Liability Summary")
            st.caption("Printable summary of your latest computed India income tax, deductions, and advance tax schedule.")
            tax_res = st.session_state.get("_tax_result")
            if tax_res:
                st.caption(f"Computed Tax: **{format_inr_short(float(tax_res.get('total_tax', 0)))}** · Balance Due: **{format_inr_short(float(tax_res.get('balance_due', 0)))}**")
                if st.button("⚡ Generate Tax Summary", type="primary", use_container_width=True, key="rep_gen_tax"):
                    regime = st.session_state.get("tax_regime_sel", "New Regime")
                    st.session_state["_rep_tax_html"] = reports_engine.generate_tax_summary_html(tax_res, fy=selected_fy, regime=regime, user_label=user_label)
                if st.session_state.get("_rep_tax_html"):
                    st.download_button(
                        "🖨️ Download Tax Summary (HTML / PDF)",
                        st.session_state["_rep_tax_html"],
                        f"Tax_Summary_{clean_user}.html",
                        "text/html",
                        use_container_width=True,
                    )
            else:
                st.info("Run a tax calculation in **Tax & Income → Tax Summary** first.")
                if st.button("🧾 Go to Tax & Income", use_container_width=True, key="rep_go_tax"):
                    ui.navigate_to("tax", sub_tab="🧮 Tax Summary")

    col5, col6 = st.columns(2)

    # ── Card 5: Debt & Amortization Schedule ─────────────────────────────
    with col5:
        with st.container(border=True):
            st.markdown("#### 🏦 Debt & Amortization Schedule")
            st.caption("Active loans, weighted average interest rate, total EMI obligations, and payoff horizon.")
            debts_df = data_layer.cached_get_debts(family_id=user_family_id)
            tot_debt = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty and "outstanding_principal" in debts_df.columns else 0.0
            st.caption(f"Outstanding Principal: **{format_inr_short(tot_debt)}** across **{len(debts_df)}** loan(s).")
            if st.button("⚡ Generate Debt Schedule", type="primary", use_container_width=True, key="rep_gen_debt"):
                st.session_state["_rep_debt_cache"] = {
                    "html": reports_engine.generate_debt_schedule_html(debts_df, user_label=user_label),
                    "xlsx": reports_engine.generate_debt_schedule_excel(debts_df),
                }
            dc = st.session_state.get("_rep_debt_cache")
            if dc:
                today_s = datetime.date.today().strftime("%Y%m%d")
                d1, d2 = st.columns(2)
                d1.download_button("🖨️ HTML / PDF", dc["html"], f"Debt_Schedule_{clean_user}_{today_s}.html", "text/html", use_container_width=True)
                d2.download_button("📊 Excel (.xlsx)", dc["xlsx"], f"Debt_Schedule_{clean_user}_{today_s}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # ── Card 6: Financial Health Report Shortcut ─────────────────────────
    with col6:
        with st.container(border=True):
            st.markdown("#### 🩺 360° Financial Health Audit")
            st.caption("5-pillar diagnostic score, investment audit, debt ratios, and customisable multi-tab Excel & PDF report.")
            st.caption("Switch to the **🩺 Health Report** pill above to customise sections and generate on demand.")
            if st.button("🩺 Open Health Report Builder", use_container_width=True, key="rep_go_health_card"):
                ui.navigate_to("reports", sub_tab="🩺 Health Report")


def _render_health_report(current_user, user_family_id, view_mode: str, selected_fy: str) -> None:
    inv_df = data_layer.get_user_investments_df(
        username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id
    )
    debts_df = data_layer.cached_get_debts(family_id=user_family_id)
    exp_df = data_layer.get_expenses_df(
        fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id, transaction_type="Expense"
    )
    inc_df = data_layer.cached_get_income_sources_df(
        username=current_user["username"], family_id=user_family_id, view_mode=view_mode
    )
    mo_inc = float(inc_df["monthly_equivalent"].sum()) if not inc_df.empty and "monthly_equivalent" in inc_df.columns else float(st.session_state.get("budget_dict", {}).get("__income__", 0.0))
    n_months = max(1, int(exp_df["Month_Key"].nunique()) if not exp_df.empty and "Month_Key" in exp_df.columns else 1)
    mo_exp = float(exp_df["amount"].sum()) / n_months if not exp_df.empty else 0.0

    render_financial_health_report_ui(
        current_user=current_user,
        inv_df=inv_df,
        debts_df=debts_df,
        income_df=inc_df,
        expenses_df=exp_df,
        monthly_income=mo_inc,
        monthly_expenses=mo_exp,
    )


def _render_exports(current_user, user_family_id, view_mode: str, selected_fy: str, is_super_admin: bool) -> None:
    st.markdown("#### 📦 Raw Data Exports")
    st.caption("Download clean CSV snapshots of your financial datasets for backup or offline analysis.")
    today_s = datetime.date.today().strftime("%Y%m%d")

    e1, e2 = st.columns(2)
    with e1:
        with st.container(border=True):
            st.markdown("##### 💸 Transactions (All Types)")
            scope_choice = st.radio("Range", [f"Current Scope ({selected_fy})", "All Historical Years"], horizontal=True, key="exp_tx_range")
            fy_arg = selected_fy if scope_choice.startswith("Current") else "All FYs"
            tx_df = data_layer.get_expenses_df(
                fy=fy_arg, username=current_user["username"], view_mode=view_mode, family_id=user_family_id, transaction_type="All"
            )
            st.caption(f"**{len(tx_df)}** record(s) ready.")
            st.download_button(
                "📥 Download Transactions CSV",
                data=tx_df.to_csv(index=False).encode("utf-8"),
                file_name=f"FinCompass_Transactions_{fy_arg.replace(' ', '_')}_{today_s}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=tx_df.empty,
            )

        with st.container(border=True):
            st.markdown("##### 🏦 Loans & EMIs")
            debts_df = data_layer.cached_get_debts(family_id=user_family_id)
            st.caption(f"**{len(debts_df)}** loan record(s) ready.")
            st.download_button(
                "📥 Download Loans CSV",
                data=debts_df.to_csv(index=False).encode("utf-8"),
                file_name=f"FinCompass_Loans_{today_s}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=debts_df.empty,
            )

    with e2:
        with st.container(border=True):
            st.markdown("##### 📈 Investment Holdings")
            inv_df = data_layer.get_user_investments_df(
                username=current_user["username"] if view_mode != "Family" else None, family_id=user_family_id
            )
            st.caption(f"**{len(inv_df)}** holding(s) ready.")
            st.download_button(
                "📥 Download Holdings CSV",
                data=inv_df.to_csv(index=False).encode("utf-8"),
                file_name=f"FinCompass_Holdings_{today_s}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=inv_df.empty,
            )

        with st.container(border=True):
            st.markdown("##### 💵 Income Sources")
            inc_df = data_layer.cached_get_income_sources_df(
                username=current_user["username"], family_id=user_family_id, view_mode=view_mode
            )
            st.caption(f"**{len(inc_df)}** income source(s) ready.")
            st.download_button(
                "📥 Download Income Sources CSV",
                data=inc_df.to_csv(index=False).encode("utf-8"),
                file_name=f"FinCompass_Income_{today_s}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=inc_df.empty,
            )

