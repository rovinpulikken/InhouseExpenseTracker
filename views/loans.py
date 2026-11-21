"""
Loans & EMIs Page — Grow Section.
Single-level pill sub-navigation:
  1. Active Loans      (KPIs, Add Loan modal dialog, Loan cards with Log Payment / Edit / History)
  2. Payoff Simulator  (Avalanche vs. Snowball payoff curve & interest saved)
"""

import datetime
import plotly.express as px
import streamlit as st

from config import DEBT_CATEGORIES, format_inr, format_inr_short, get_indian_fy
from database import add_debt, add_debt_payment, get_debt_payments, update_debt, delete_debt, get_category_budget
from debt_simulator import simulate_debt_payoff
import data_layer
import ui


_dialog_deco = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def _add_loan_form_body(user_family_id: int, target_fy: str) -> None:
    with st.form("dlg_add_debt_form"):
        c1, c2 = st.columns(2)
        with c1:
            d_name = st.text_input("Loan / Debt Name", placeholder="e.g. HDFC Home Loan")
            d_cat = st.selectbox("Category", DEBT_CATEGORIES)
        with c2:
            d_principal = st.number_input("Total Principal (₹)", min_value=0.0, step=10000.0)
            d_start = st.date_input("Start Date", value=datetime.date.today())
        c3, c4, c5 = st.columns(3)
        with c3:
            d_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
        with c4:
            d_tenure = st.number_input("Tenure (Months)", min_value=1, value=60, step=12)
        with c5:
            d_emi = st.number_input("Monthly EMI (₹)", min_value=0.0, step=1000.0)
        if st.form_submit_button("💾 Save Liability", type="primary", use_container_width=True):
            if d_name.strip() and d_principal > 0:
                if d_emi > 0:
                    if "budget_dict" in st.session_state:
                        st.session_state["budget_dict"][d_cat] = st.session_state["budget_dict"].get(d_cat, 0.0) + d_emi
                    b_df = get_category_budget(target_fy, d_cat, family_id=user_family_id or 1)
                    existing_val = float(b_df.iloc[0]["monthly_limit"]) if not b_df.empty else 0.0
                    data_layer.set_category_budget(target_fy, d_cat, existing_val + d_emi, (existing_val + d_emi) * 12, family_id=user_family_id or 1)
                add_debt(d_name.strip(), d_cat, d_principal, d_principal, d_rate, d_emi, int(d_tenure), str(d_start), user_family_id or 1)
                data_layer.invalidate_data_cache()
                st.toast(f"✅ Added {d_name.strip()} — EMI synced to budget!")
                st.rerun()
            else:
                st.error("Please enter a loan name and principal > 0.")


if _dialog_deco is not None:

    @_dialog_deco("➕ Add New Loan / Liability")
    def _open_add_loan_dialog(user_family_id: int, target_fy: str) -> None:
        _add_loan_form_body(user_family_id, target_fy)

else:

    def _open_add_loan_dialog(user_family_id: int, target_fy: str) -> None:
        with st.expander("➕ Add New Loan / Liability", expanded=True):
            _add_loan_form_body(user_family_id, target_fy)


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("loans")

    target_fy = st.session_state.get("scope", {}).get("fy") or get_indian_fy(datetime.date.today())
    if target_fy == "All FYs":
        target_fy = get_indian_fy(datetime.date.today())

    ui.render_page_header(
        "🏦",
        "Loans & EMIs",
        subtitle="Track outstanding balances, log repayments, and simulate debt-free timelines.",
        accent="#f43f5e",
    )

    debts_df = data_layer.cached_get_debts(family_id=user_family_id or 1)
    tot_out = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty else 0.0
    tot_emi = float(debts_df["monthly_emi"].sum()) if not debts_df.empty else 0.0

    ui.render_kpi_grid(
        [
            {"label": "Total Outstanding", "value": format_inr_short(tot_out), "sub": format_inr(tot_out), "color": "#f87171", "accent": "#f43f5e"},
            {"label": "Monthly EMI", "value": format_inr_short(tot_emi), "sub": format_inr(tot_emi) + "/mo", "color": "#fbbf24"},
            {"label": "Active Loans", "value": str(len(debts_df)), "sub": "Debt-free!" if debts_df.empty else "Tracked liabilities", "color": "#38bdf8"},
        ],
        cols=3,
    )

    sub_opts = ["🏦 Active Loans", "🔮 Payoff Simulator"]
    default_sub = ui.consume_target_sub("loans", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Loans Section", sub_opts, key="loans_sub_nav", default=default_sub)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if active_sub == "🏦 Active Loans":
        lh1, lh2 = st.columns([3, 1.3])
        with lh1:
            st.markdown("#### 📊 Active Debt Portfolio")
        with lh2:
            if st.button("➕ Add Loan", type="primary", use_container_width=True, key="loan_btn_add"):
                _open_add_loan_dialog(user_family_id or 1, target_fy)

        if debts_df.empty:
            if ui.render_empty_state(
                "🎉",
                "You are debt-free!",
                "No active loans recorded. Add a loan if you want to track EMI schedules and payoff simulations.",
                cta_label="➕ Add Loan / Liability",
                cta_key="loan_empty_add",
            ):
                _open_add_loan_dialog(user_family_id or 1, target_fy)
            return

        for _, row in debts_df.iterrows():
            did = int(row["id"])
            dname = row["debt_name"]
            dcat = row["debt_category"]
            outstanding = float(row["outstanding_principal"])
            total = float(row["total_principal"])
            emi = float(row["monthly_emi"])
            rate = float(row["interest_rate"])
            paid_pct = max(0.0, min(100.0, ((total - outstanding) / total) * 100.0)) if total > 0 else 0.0

            st.markdown(
                f"""
                <div class="fc-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                        <div>
                            <div style="font-size:1.05rem; font-weight:700; color:#f8fafc;">{dname}</div>
                            <div style="font-size:0.82rem; color:#94a3b8;">{dcat} &middot; {rate:.2f}% p.a. &middot; EMI {format_inr_short(emi)}/mo</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.15rem; font-weight:800; color:#f87171;">{format_inr_short(outstanding)}</div>
                            <div style="font-size:0.75rem; color:#64748b;">of {format_inr_short(total)}</div>
                        </div>
                    </div>
                    <div class="fc-bar-track"><div class="fc-bar-fill" style="width:{paid_pct:.1f}%; background:#10b981;"></div></div>
                    <div style="font-size:0.76rem; color:#94a3b8;">{paid_pct:.1f}% repaid</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(f"💸 Log Payment · ✏️ Edit · 📜 History — {dname}"):
                lp1, lp2 = st.columns(2)
                with lp1:
                    with st.form(f"loan_pay_{did}"):
                        pay_dt = st.date_input("Date", value=datetime.date.today(), key=f"lpd_{did}")
                        pay_pr = st.number_input("Principal Paid (₹)", min_value=0.0, step=500.0, key=f"lpp_{did}")
                        pay_in = st.number_input("Interest Paid (₹)", min_value=0.0, step=500.0, key=f"lpi_{did}")
                        if st.form_submit_button("💾 Record Payment", type="primary", use_container_width=True):
                            if pay_pr > 0 or pay_in > 0:
                                add_debt_payment(did, str(pay_dt), pay_pr, pay_in, user_family_id or 1)
                                data_layer.invalidate_data_cache()
                                st.toast(f"✅ Logged payment for {dname}.")
                                st.rerun()
                with lp2:
                    with st.form(f"loan_edit_{did}"):
                        e_name = st.text_input("Name", value=dname, key=f"len_{did}")
                        e_cat = st.selectbox("Category", DEBT_CATEGORIES, index=DEBT_CATEGORIES.index(dcat) if dcat in DEBT_CATEGORIES else 0, key=f"lec_{did}")
                        e_out = st.number_input("Outstanding (₹)", value=outstanding, min_value=0.0, step=500.0, key=f"leo_{did}")
                        e_emi = st.number_input("Monthly EMI (₹)", value=emi, min_value=0.0, step=500.0, key=f"lee_{did}")
                        u1, u2 = st.columns(2)
                        with u1:
                            if st.form_submit_button("Update", type="primary", use_container_width=True):
                                update_debt(did, e_name, e_cat, total, e_out, rate, e_emi, int(row["tenure_months"] or 60), row["start_date"], user_family_id or 1)
                                data_layer.invalidate_data_cache()
                                st.toast("✅ Loan updated.")
                                st.rerun()
                        with u2:
                            if st.form_submit_button("🗑️ Delete", use_container_width=True):
                                delete_debt(did, user_family_id or 1)
                                data_layer.invalidate_data_cache()
                                st.toast(f"🗑️ Deleted {dname}.")
                                st.rerun()

                pay_df = get_debt_payments(did)
                if not pay_df.empty:
                    st.markdown("**Payment History**")
                    st.dataframe(pay_df[["payment_date", "principal_paid", "interest_paid"]], use_container_width=True, hide_index=True)

    else:
        st.markdown("#### 🔮 Debt Payoff Simulator")
        if debts_df.empty:
            st.info("🎉 You have no active loans to simulate!")
            return

        sc1, sc2 = st.columns(2)
        with sc1:
            strategy = st.selectbox(
                "Payoff Strategy",
                ["Avalanche (Highest Interest First) - mathematically optimal", "Snowball (Lowest Balance First) - psychological wins"],
                key="loan_sim_strat",
            )
        with sc2:
            sim_budget = st.number_input(
                "Total Monthly Debt Budget (₹)",
                value=max(1000.0, tot_emi),
                min_value=max(1.0, tot_emi),
                step=1000.0,
                key="loan_sim_bud",
            )

        if st.button("🚀 Run Payoff Simulation", type="primary", use_container_width=True, key="loan_sim_run"):
            total_months, total_interest, timeline_df = simulate_debt_payoff(debts_df, strategy, sim_budget)
            from dateutil.relativedelta import relativedelta
            payoff_dt = (datetime.datetime.now() + relativedelta(months=total_months)).strftime("%b %Y")
            ui.render_kpi_grid(
                [
                    {"label": "Months to Debt-Free", "value": f"{total_months} mo", "color": "#38bdf8"},
                    {"label": "Total Interest Paid", "value": format_inr_short(total_interest), "color": "#f87171"},
                    {"label": "Projected Debt-Free Date", "value": payoff_dt, "color": "#34d399"},
                ],
                cols=3,
            )
            fig_d = px.area(timeline_df, x="Month", y="Total Balance", color_discrete_sequence=["#ef4444"], template="plotly_dark")
            fig_d.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=8, r=8, t=12, b=8))
            st.plotly_chart(fig_d, use_container_width=True)

