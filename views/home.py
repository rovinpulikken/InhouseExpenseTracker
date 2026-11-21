"""
Home Page — Mobile-First Executive Command Center.
Shows:
  1. This Month Cash Flow KPI strip (Income, Spent, Net Savings, Savings Rate)
  2. Quick Actions bar (Add, Import, Open Ledger, Monthly Report)
  3. Needs Attention alerts (only shown if non-empty: over-budget, portfolio triggers)
  4. Spend by Category Donut + Recent 5 Transactions
  5. 6-Month Cash Flow Trend (Income vs. Expense)
  6. Net Worth & Financial Health Score tile
"""

import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from config import format_inr, format_inr_short, get_indian_fy
from financial_report import compute_financial_health
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("home")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=True, show_month=True, page_key="home"
    )
    view_mode = scope["view"]
    selected_fy = scope["fy"]
    selected_month = scope["month"]
    month_label = scope["month_label"]

    ui.render_page_header(
        "🏠",
        f"Welcome back, {current_user.get('full_name', current_user['username'])}",
        subtitle="Your financial snapshot at a glance.",
        accent="#38bdf8",
        badge=f"{view_mode} · {month_label if selected_month != 'All Months' else selected_fy}",
    )

    if data_layer.is_sandbox_mode():
        st.info("🎯 **Sandbox Mission**: Review the simulated finances below. Try switching months or adding an entry.")

    # Fetch cached core datasets once
    all_tx_fy = data_layer.get_expenses_df(
        fy=selected_fy,
        username=current_user["username"],
        view_mode=view_mode,
        family_id=user_family_id,
        transaction_type="All",
    )
    period_tx = ui.filter_df_by_month(all_tx_fy, selected_month)

    income_sources_df = data_layer.cached_get_income_sources_df(
        username=current_user["username"],
        family_id=user_family_id,
        view_mode=view_mode,
    )
    recurring_monthly_inc = (
        float(income_sources_df["monthly_equivalent"].sum())
        if not income_sources_df.empty and "monthly_equivalent" in income_sources_df.columns
        else 0.0
    )

    # Normalize transaction types
    if not period_tx.empty:
        if "transaction_type" not in period_tx.columns:
            period_tx["transaction_type"] = "Expense"
        period_tx["transaction_type"] = period_tx["transaction_type"].fillna("Expense").astype(str).str.strip().str.title()
        period_tx["amount"] = pd.to_numeric(period_tx["amount"], errors="coerce").fillna(0.0)
        exp_df = period_tx[period_tx["transaction_type"] != "Income"]
        inc_df = period_tx[period_tx["transaction_type"] == "Income"]
    else:
        exp_df = pd.DataFrame()
        inc_df = pd.DataFrame()

    tx_expense = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
    tx_income = float(inc_df["amount"].sum()) if not inc_df.empty else 0.0

    # Compute period income (explicit logged income or recurring baseline)
    num_months_in_scope = 1
    if selected_month == "All Months" and not all_tx_fy.empty and "Month_Key" in all_tx_fy.columns:
        num_months_in_scope = max(1, int(all_tx_fy["Month_Key"].nunique()))
    if tx_income > 0:
        period_income = tx_income
        inc_sub = f"{len(inc_df)} logged inflow(s)"
    elif recurring_monthly_inc > 0:
        period_income = recurring_monthly_inc * num_months_in_scope
        inc_sub = "from recurring income"
    else:
        period_income = 0.0
        inc_sub = "add income in Tax & Income"

    net_savings = period_income - tx_expense
    savings_rate = (net_savings / period_income * 100.0) if period_income > 0 else 0.0
    sav_color = "#34d399" if net_savings >= 0 else "#f87171"

    # ── 1. This Period Cash Flow KPI Strip ───────────────────────────────
    ui.render_kpi_grid(
        [
            {
                "label": f"Income ({month_label})",
                "value": format_inr_short(period_income),
                "sub": inc_sub,
                "color": "#38bdf8",
                "accent": "#38bdf8",
            },
            {
                "label": f"Spent ({month_label})",
                "value": format_inr_short(tx_expense),
                "sub": f"{len(exp_df)} expense(s)",
                "color": "#f43f5e",
                "accent": "#f43f5e",
            },
            {
                "label": "Net Savings",
                "value": f"{'+' if net_savings > 0 else ''}{format_inr_short(net_savings)}",
                "sub": "Income − Expenses",
                "color": sav_color,
                "accent": sav_color,
            },
            {
                "label": "Savings Rate",
                "value": f"{savings_rate:.1f}%",
                "sub": "Target: ≥ 20%",
                "color": "#c084fc",
                "accent": "#a855f7",
            },
        ],
        cols=4,
    )

    # ── 2. Quick Actions (4 chips) ──────────────────────────────────────
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("➕ Add Transaction", type="primary", use_container_width=True, key="home_qa_add"):
            ui.open_add_transaction_dialog(current_user, user_family_id)
    with qa2:
        if st.button("📤 Import Statement", use_container_width=True, key="home_qa_imp"):
            ui.navigate_to("transactions", sub_tab="📤 Import")
    with qa3:
        if st.button("📅 Open Ledger", use_container_width=True, key="home_qa_led"):
            ui.navigate_to("transactions", sub_tab="📅 Ledger")
    with qa4:
        if st.button("📑 Monthly Report", use_container_width=True, key="home_qa_rep"):
            ui.navigate_to("reports", sub_tab="📄 Statements")

    # Fetch portfolio, debts, budgets for alerts & net worth tile
    target_fy_clean = selected_fy if selected_fy != "All FYs" else (scope["all_fys"][0] if scope["all_fys"] else get_indian_fy(datetime.date.today()))
    inv_df = data_layer.get_user_investments_df(
        username=current_user["username"] if view_mode != "Family" else None,
        family_id=user_family_id,
    )
    debts_df = data_layer.cached_get_debts(family_id=user_family_id)
    budget_status = data_layer.get_budget_status(
        target_fy_clean, username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )

    # ── 3. Needs Attention (only rendered if non-empty) ─────────────────
    alerts = []
    if not budget_status.empty and "Utilization_%" in budget_status.columns:
        over_b = budget_status[(budget_status["Annual_Budget"] > 0) & (budget_status["Utilization_%"] >= 80.0)].sort_values("Utilization_%", ascending=False)
        for _, r in over_b.head(3).iterrows():
            util = float(r["Utilization_%"])
            icon = "🚨" if util > 100 else "⚠️"
            alerts.append(
                {
                    "icon": icon,
                    "text": f"**{r['category']}** is at **{util:.0f}%** of annual budget ({format_inr_short(float(r['Actual_Spent']))} / {format_inr_short(float(r['Annual_Budget']))})",
                    "action": "budgets",
                    "btn": "Review Budget",
                }
            )
    if not inv_df.empty and "returns_pct" in inv_df.columns:
        for _, r in inv_df.iterrows():
            sl = float(r.get("stop_loss_pct") or 0.0)
            tp = float(r.get("target_profit_pct") or 0.0)
            ret = float(r.get("returns_pct") or 0.0)
            hname = r.get("resolved_name") or r.get("description") or r.get("platform")
            if sl < 0 and ret <= sl:
                alerts.append({"icon": "🔴", "text": f"**{hname}** hit stop-loss ({ret:.1f}%)", "action": "portfolio", "btn": "Open Portfolio"})
            elif tp > 0 and ret >= tp:
                alerts.append({"icon": "🟢", "text": f"**{hname}** reached target profit (+{ret:.1f}%)", "action": "portfolio", "btn": "Open Portfolio"})

    if alerts:
        st.markdown("##### 🔔 Needs Attention")
        for idx, al in enumerate(alerts[:4]):
            ac1, ac2 = st.columns([4, 1.2])
            with ac1:
                st.markdown(
                    f'<div class="fc-card" style="padding:10px 14px; margin-bottom:6px; border-left:3px solid #f59e0b;">'
                    f'{al["icon"]} {al["text"]}</div>',
                    unsafe_allow_html=True,
                )
            with ac2:
                if st.button(al["btn"], key=f"home_al_{idx}", use_container_width=True):
                    ui.navigate_to(al["action"])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 4. Spend by Category Donut + Recent 5 Transactions ──────────────
    col_donut, col_recent = st.columns([1.1, 1.2])

    with col_donut:
        st.markdown(f"##### 🍩 Spending Mix ({month_label})")
        if not exp_df.empty:
            cat_sum = exp_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            top_n = cat_sum.head(6).copy()
            if len(cat_sum) > 6:
                other_val = float(cat_sum.iloc[6:]["amount"].sum())
                top_n = pd.concat([top_n, pd.DataFrame([{"category": "Other", "amount": other_val}])], ignore_index=True)

            fig_d = px.pie(
                top_n,
                names="category",
                values="amount",
                hole=0.52,
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_d.update_traces(textposition="inside", textinfo="percent+label")
            fig_d.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                height=265,
                margin=dict(l=4, r=4, t=8, b=8),
            )
            st.plotly_chart(fig_d, use_container_width=True)

            top_cat = cat_sum.iloc[0]["category"]
            if st.button(f"🔍 Inspect {top_cat} in Ledger", key="home_inspect_top", use_container_width=True):
                ui.navigate_to("transactions", sub_tab="📅 Ledger", extra_state={"_ledger_cat_filter": top_cat})
        else:
            if ui.render_empty_state(
                "💸",
                f"No expenses logged for {month_label}",
                "Log your first expense or import a statement to see your spending breakdown.",
                cta_label="➕ Log First Expense",
                cta_key="home_empty_add",
            ):
                ui.open_add_transaction_dialog(current_user, user_family_id)

    with col_recent:
        r_hdr1, r_hdr2 = st.columns([2.5, 1])
        with r_hdr1:
            st.markdown("##### 🧾 Recent Transactions")
        with r_hdr2:
            if st.button("See all →", key="home_see_all_tx", use_container_width=True):
                ui.navigate_to("transactions", sub_tab="📅 Ledger")

        if not period_tx.empty:
            recent_5 = period_tx.sort_values("expense_date", ascending=False).head(5)
            for _, row in recent_5.iterrows():
                ui.render_tx_card(row.to_dict())
        else:
            st.caption("No transactions in this period yet.")

    st.markdown("---")

    # ── 5. 6-Month Cash Flow Trend + Net Worth Tile ─────────────────────
    col_trend, col_nw = st.columns([1.4, 1])

    with col_trend:
        st.markdown("##### 📈 6-Month Cash Flow Trend")
        all_hist = data_layer.get_expenses_df(
            fy="All FYs",
            username=current_user["username"],
            view_mode=view_mode,
            family_id=user_family_id,
            transaction_type="All",
        )
        if not all_hist.empty and "expense_date" in all_hist.columns:
            all_hist["Month_Key"] = pd.to_datetime(all_hist["expense_date"], errors="coerce").dt.strftime("%Y-%m")
            if "transaction_type" not in all_hist.columns:
                all_hist["transaction_type"] = "Expense"
            all_hist["transaction_type"] = all_hist["transaction_type"].fillna("Expense").astype(str).str.strip().str.title()
            recent_months = sorted(all_hist["Month_Key"].dropna().unique())[-6:]
            sub_6 = all_hist[all_hist["Month_Key"].isin(recent_months)]
            piv = (
                sub_6.groupby(["Month_Key", "transaction_type"], as_index=False)["amount"]
                .sum()
            )
            fig_t = px.bar(
                piv,
                x="Month_Key",
                y="amount",
                color="transaction_type",
                barmode="group",
                color_discrete_map={"Expense": "#f43f5e", "Income": "#34d399"},
                template="plotly_dark",
                labels={"Month_Key": "", "amount": "₹", "transaction_type": ""},
            )
            fig_t.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=4, r=4, t=10, b=4),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_t, use_container_width=True)
        else:
            st.info("Log transactions across multiple months to unlock your cash-flow trajectory.")

    with col_nw:
        st.markdown("##### 🏛️ Net Worth & Health")
        tot_portfolio = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
        tot_debt = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty and "outstanding_principal" in debts_df.columns else 0.0
        net_worth = tot_portfolio - tot_debt

        monthly_exp_est = tx_expense / max(1, num_months_in_scope)
        monthly_inc_est = period_income / max(1, num_months_in_scope)
        health = compute_financial_health(
            user=current_user,
            inv_df=inv_df,
            debts_df=debts_df,
            income_df=income_sources_df,
            expenses_df=exp_df,
            monthly_income=monthly_inc_est,
            monthly_expenses=monthly_exp_est,
        )
        score = health["score"]
        rating = health["rating"]
        r_color = health["rating_color"]
        nw_color = "#34d399" if net_worth >= 0 else "#f87171"

        st.markdown(
            f"""
            <div class="fc-card" style="border-left: 4px solid {r_color};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <div class="fc-kpi-label">Net Worth</div>
                        <div style="font-size:1.55rem; font-weight:800; color:{nw_color};">{format_inr_short(net_worth)}</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="fc-kpi-label">Health Score</div>
                        <div style="font-size:1.4rem; font-weight:800; color:{r_color};">{score:.0f}<span style="font-size:0.8rem;color:#64748b;">/100</span></div>
                        <span class="fc-badge" style="background:rgba(255,255,255,0.08); color:{r_color};">{rating}</span>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.84rem; color:#cbd5e1; border-top:1px solid #243249; padding-top:10px;">
                    <span>📈 Portfolio: <b>{format_inr_short(tot_portfolio)}</b></span>
                    <span>🏦 Debt: <b style="color:#f87171;">{format_inr_short(tot_debt)}</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        nb1, nb2 = st.columns(2)
        with nb1:
            if st.button("🩺 Health Report", use_container_width=True, key="home_go_health"):
                ui.navigate_to("reports", sub_tab="🩺 Health Report")
        with nb2:
            if st.button("📈 Portfolio", use_container_width=True, key="home_go_port"):
                ui.navigate_to("portfolio")

