"""
Retirement Planner Page — Plan Section.
Clean single-page wizard:
  1. Net Investable Corpus summary + Saved Run bar
  2. Inputs (Option A: Structured Table OR Option B: Natural-Language Free-Text Vision)
  3. Results (Executive Summary & AI Advisory / Expense Plan & Inflation Surge / Milestones / Year-by-Year Trajectory)
Preserves 100% of retirement calculation & free-text parsing logic without importlib.reload overhead.
"""

import datetime
import hashlib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import format_inr, format_inr_short
import database
import investment_planner
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("retirement")

    view_mode = st.session_state.get("scope", {}).get("view", "Family")
    selected_fy = st.session_state.get("scope", {}).get("fy", "All FYs")

    ui.render_page_header(
        "🏖️",
        "Retirement Planner",
        subtitle="Model your retirement corpus, inflation-adjusted lifestyle surge, milestones, and 4% SWP.",
        accent="#c084fc",
        help_key="retirement",
    )

    u_age = int(st.session_state.get("invest_user_age", current_user.get("age", 35)) or 35)
    u_sip_budget = float(
        st.session_state.get(
            "invest_user_sip",
            max(5000.0, float(st.session_state.get("budget_dict", {}).get("Insurance & Investments", 20000.0))),
        )
    )

    inv_df = data_layer.get_user_investments_df(
        username=current_user["username"] if view_mode != "Family" else None,
        family_id=user_family_id,
    )
    debts_df = data_layer.cached_get_debts(family_id=user_family_id or 1)
    exp_df = data_layer.get_expenses_df(
        fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )
    n_mo = max(1, int(exp_df["Month_Key"].nunique()) if not exp_df.empty and "Month_Key" in exp_df.columns else 1)
    avg_mo_exp = float(exp_df["amount"].sum()) / n_mo if not exp_df.empty else 50000.0

    tot_portfolio = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
    re_keywords = ["real estate", "property", "land", "plot", "flat", "apartment", "house", "villa"]
    if not inv_df.empty and "investment_type" in inv_df.columns:
        is_re = inv_df["investment_type"].astype(str).str.lower().apply(lambda x: any(k in x for k in re_keywords))
        real_estate_val = float(inv_df[is_re]["current_value"].sum())
        liquid_portfolio_val = float(inv_df[~is_re]["current_value"].sum())
    else:
        real_estate_val = 0.0
        liquid_portfolio_val = tot_portfolio

    tot_debt_val = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty and "outstanding_principal" in debts_df.columns else 0.0
    net_liquid_starting = max(0.0, liquid_portfolio_val - tot_debt_val)

    # Corpus breakdown strip
    ui.render_kpi_grid(
        [
            {"label": "Liquid Portfolio", "value": format_inr_short(liquid_portfolio_val), "sub": "Investable assets", "color": "#38bdf8"},
            {"label": "Real Estate (Excl.)", "value": format_inr_short(real_estate_val), "sub": "Excluded from SWP", "color": "#94a3b8"},
            {"label": "Debt Deducted", "value": f"-{format_inr_short(tot_debt_val)}", "sub": "Outstanding principal", "color": "#f87171"},
            {"label": "Net Starting Corpus", "value": format_inr_short(net_liquid_starting), "sub": f"Age {u_age} · SIP {format_inr_short(u_sip_budget)}/mo", "color": "#34d399", "accent": "#10b981"},
        ],
        cols=4,
    )

    # Saved Run Banner
    saved_plan = database.get_saved_retirement_plan(current_user["username"], user_family_id or 1, "Last Run")
    if saved_plan:
        sp_ret = saved_plan.get("ret_plan", {})
        sc1, sc2, sc3 = st.columns([3, 1.1, 0.9])
        with sc1:
            st.markdown(
                f'<div class="fc-card" style="padding:10px 14px; border-left:4px solid #38bdf8; margin-bottom:8px;">'
                f'💾 <b>Saved Run ({saved_plan.get("_saved_at", "Saved")}):</b> '
                f'Age <b>{sp_ret.get("current_age", "—")} → {sp_ret.get("retirement_age", "—")}</b> · '
                f'Corpus: <b>{format_inr_short(float(sp_ret.get("total_future_value", 0)))}</b> · '
                f'SWP: <b>{format_inr_short(float(sp_ret.get("safe_monthly_withdrawal", 0)))}/mo</b></div>',
                unsafe_allow_html=True,
            )
        with sc2:
            if st.button("📂 Load Saved", key="ret_load_saved", use_container_width=True):
                st.session_state["active_retirement_plan"] = saved_plan
                st.rerun()
        with sc3:
            if st.button("🗑️ Delete", key="ret_del_saved", use_container_width=True):
                database.delete_saved_retirement_plan(current_user["username"], user_family_id or 1, "Last Run")
                st.session_state.pop("active_retirement_plan", None)
                st.toast("🗑️ Cleared saved retirement plan.")
                st.rerun()

    # Step 1: Core Assumptions
    st.markdown("#### 1️⃣ Assumptions & Goals")
    rc1, rc2 = st.columns(2)
    with rc1:
        optb_active = "Option B" in str(st.session_state.get("ret_input_source_selection_v2", ""))
        ret_age = st.number_input(
            "Desired Retirement Age (Option A)" if not optb_active else "Desired Retirement Age (read from Option B text)",
            min_value=u_age + 1,
            max_value=100,
            value=max(60, u_age + 10),
            step=1,
            disabled=optb_active,
            key="ret_age_input",
        )
        exp_return_str = st.text_input("Expected CAGR (%) — leave blank for benchmark", placeholder="e.g. 12.0", key="ret_cagr_str")
    with rc2:
        benchmark_index = st.selectbox(
            "Benchmark Index (if CAGR blank)",
            options=[("Nifty 50 (India)", "^NSEI"), ("BSE Sensex", "^BSESN"), ("S&P 500 (US)", "^GSPC"), ("NASDAQ", "^IXIC")],
            format_func=lambda x: x[0],
            key="ret_bench_idx",
        )
        hist_years = st.selectbox("Historical Period", options=[5, 10, 15, 20], index=1, format_func=lambda x: f"Last {x} Years", key="ret_hist_yrs")

    ret_input_mode = st.radio(
        "Milestone & Expense Input Mode",
        options=[
            "📋 Option A: Structured Fields & Milestone Table",
            "💬 Option B: Free-Text Vision Statement",
        ],
        horizontal=True,
        key="ret_input_source_selection_v2",
    )
    is_free_text = "Option B" in ret_input_mode

    if not is_free_text:
        a1, a2 = st.columns(2)
        with a1:
            st.caption("📋 **One-Time Milestone Expenses**")
            ms_ed = st.data_editor(
                pd.DataFrame([{"Expense Description": "", "Amount (₹)": 0.0, "Age": min(ret_age, u_age + 5)}]),
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="one_time_exp_editor",
            )
        with a2:
            st.caption("💳 **Monthly Living & Extra Recurring Expenses**")
            base_living = st.number_input("Current Monthly Living Expense (₹)", min_value=5000.0, value=max(10000.0, float(round(avg_mo_exp, -3))), step=5000.0, key="ret_base_living_expense")
            add_rec = st.number_input("Additional Monthly Recurring Expense (₹)", min_value=0.0, value=0.0, step=5000.0, key="ret_add_recurring_expense")

        active_milestones = []
        for _, row in ms_ed.iterrows():
            try:
                amt = float(row.get("Amount (₹)") or 0.0)
            except Exception:
                amt = 0.0
            try:
                age_v = int(row.get("Age") or u_age)
            except Exception:
                age_v = u_age
            if amt > 0:
                active_milestones.append({
                    "amount": amt,
                    "age": age_v,
                    "description": str(row.get("Expense Description") or "Milestone Goal").strip(),
                    "source": "Milestone Table",
                })

        active_source_label = "📋 Option A: Structured Fields"
        calc_base_living_exp = float(base_living)
        calc_recurring_exp = float(add_rec)
        calc_user_age = int(u_age)
        calc_ret_age = int(ret_age)
        active_user_context = ""
        ignore_free_text = True
    else:
        ret_text = st.text_area(
            "Describe your retirement vision in plain English",
            placeholder="e.g. I am 45 now and plan to retire at 60. Monthly living expense of 1.5 lakhs. Daughter's education 7 lakhs/year starting 2028 for 4 years. Marriage expense 50 lakhs in 2035. Standard medical buffer.",
            height=110,
            key="ret_user_context_input",
        )
        parsed = investment_planner.extract_free_text_parameters(ret_text, base_age=u_age, current_year=datetime.date.today().year)
        text_ms = parsed.get("milestones", [])
        ob_age = int(parsed.get("detected_age") or u_age)
        ob_ret_age = int(parsed.get("detected_retirement_age") or ret_age)
        ob_living = float(parsed.get("monthly_living_expense") or avg_mo_exp)
        ob_med = float(parsed.get("monthly_medical_expense") or 0.0)

        sig = hashlib.md5(f"{ret_text}|{u_age}".encode("utf-8")).hexdigest()
        if st.session_state.get("opt_b_text_sig") != sig:
            st.session_state["opt_b_text_sig"] = sig
            st.session_state["opt_b_confirmed_living_exp"] = max(5000.0, float(round(ob_living, -2)))
            st.session_state["opt_b_confirmed_medical_exp"] = float(ob_med)
            st.session_state["opt_b_confirmed_ret_age"] = int(min(100, max(ob_age + 1, ob_ret_age)))
        if int(st.session_state.get("opt_b_confirmed_ret_age", 0)) <= ob_age:
            st.session_state["opt_b_confirmed_ret_age"] = int(min(100, ob_age + 1))

        o1, o2, o3 = st.columns(3)
        conf_living = o1.number_input("Extracted Living Expense (₹/mo)", min_value=5000.0, step=5000.0, key="opt_b_confirmed_living_exp")
        conf_med = o2.number_input("Healthcare Buffer (₹/mo)", min_value=0.0, step=5000.0, key="opt_b_confirmed_medical_exp")
        conf_ret_age = o3.number_input("Target Retirement Age", min_value=ob_age + 1, max_value=100, step=1, key="opt_b_confirmed_ret_age")

        if text_ms:
            with st.expander(f"📋 Extracted Milestones ({len(text_ms)})", expanded=True):
                mdf = pd.DataFrame(text_ms)
                mdf["Amount (₹)"] = mdf["amount"].apply(format_inr)
                mcols = [c for c in ["description", "Amount (₹)", "age", "calendar_year", "source"] if c in mdf.columns]
                st.dataframe(mdf[mcols], use_container_width=True, hide_index=True)

        active_source_label = "💬 Option B: Free-Text Vision"
        active_milestones = text_ms
        calc_base_living_exp = float(conf_living)
        calc_recurring_exp = float(conf_med)
        calc_user_age = int(ob_age)
        calc_ret_age = int(conf_ret_age)
        active_user_context = ret_text
        ignore_free_text = False

    if st.button("🔮 Calculate Retirement Corpus", type="primary", use_container_width=True, key="ret_btn_calc"):
        with st.spinner("Projecting corpus, inflation surge & AI advisory..."):
            if exp_return_str.strip():
                try:
                    cagr_dec = float(exp_return_str.strip()) / 100.0
                except Exception:
                    cagr_dec = 0.12
            else:
                cagr_dec = investment_planner.fetch_index_historical_cagr(benchmark_index[1], hist_years)

            ret_plan = investment_planner.calculate_retirement_corpus(
                current_age=calc_user_age,
                retirement_age=calc_ret_age,
                current_savings=liquid_portfolio_val,
                monthly_sip=u_sip_budget,
                cagr_decimal=cagr_dec,
                one_time_expenses=active_milestones,
                additional_monthly_expense=calc_recurring_exp,
                outstanding_debt=tot_debt_val,
                real_estate_value=real_estate_val,
                inflation_rate=0.06,
            )
            exp_plan = investment_planner.generate_detailed_retirement_expense_plan(
                current_age=calc_user_age,
                retirement_age=calc_ret_age,
                base_monthly_expense=calc_base_living_exp,
                additional_monthly_expense=calc_recurring_exp,
                one_time_expenses=active_milestones,
                user_context=active_user_context,
                inflation_rate=0.06,
                life_expectancy=85,
                safe_monthly_withdrawal=ret_plan.get("safe_monthly_withdrawal", 0.0),
                ignore_free_text_overrides=ignore_free_text,
            )
            ret_advice = investment_planner.generate_ai_retirement_advisory(
                ret_plan, inv_df, user_context=active_user_context, api_key=data_layer.get_gemini_api_key(current_user)
            )

        st.session_state["active_retirement_plan"] = {
            "ret_plan": ret_plan,
            "exp_plan": exp_plan,
            "ret_advice": ret_advice,
            "source_mode": active_source_label,
            "_saved_at": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
        }

    # Step 2: Display Active Result
    bundle = st.session_state.get("active_retirement_plan")
    if not bundle:
        return

    ret_plan = bundle.get("ret_plan", {})
    exp_plan = bundle.get("exp_plan", {})
    ret_advice = bundle.get("ret_advice", {})

    st.markdown("---")
    ui.render_kpi_grid(
        [
            {"label": "Projected Liquid Corpus", "value": format_inr_short(float(ret_plan.get("total_future_value", 0))), "sub": f"+{format_inr_short(float(ret_plan.get('wealth_gain', 0)))} gain", "color": "#34d399", "accent": "#10b981"},
            {"label": "Total Invested", "value": format_inr_short(float(ret_plan.get("total_invested", 0))), "color": "#38bdf8"},
            {"label": "Safe Monthly SWP (4%)", "value": format_inr_short(float(ret_plan.get("safe_monthly_withdrawal", 0))), "sub": "per month", "color": "#fbbf24"},
            {"label": "Today's Value (6% Inf.)", "value": format_inr_short(float(ret_plan.get("corpus_today_value", 0))), "sub": f"~{format_inr_short(float(ret_plan.get('swr_today_value', 0)))}/mo today", "color": "#c084fc"},
        ],
        cols=4,
    )

    view_choice = ui.segmented_pills(
        "Result View",
        ["🤖 Advisory", "📈 Inflation Surge", "🎯 Milestones", "🗓️ Trajectory"],
        key="ret_result_view",
        default="🤖 Advisory",
    )

    if view_choice == "🤖 Advisory":
        st.info(ret_advice.get("summary", ""))
        for item in ret_advice.get("key_takeaways", []):
            st.markdown(f"- {item}")

    elif view_choice == "📈 Inflation Surge":
        st.warning(
            f"At **{exp_plan.get('inflation_rate_pct', 6.0)}% inflation**, **{format_inr(exp_plan.get('base_monthly_today', 0))}/mo** today "
            f"becomes **{format_inr(exp_plan.get('monthly_living_at_ret', 0))}/mo** at Age {exp_plan.get('retirement_age', 60)} "
            f"(**{exp_plan.get('inflation_surge_multiplier', 1.0)}x**)."
        )
        traj = exp_plan.get("trajectory", [])
        if traj:
            tdf = pd.DataFrame(traj)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tdf["Age"], y=tdf["Monthly_Living_Cost"], mode="lines", name="Inflated Monthly Cost", line=dict(color="#f43f5e", width=3), fill="tozeroy", fillcolor="rgba(244,63,94,0.12)"))
            fig.add_trace(go.Scatter(x=tdf["Age"], y=[float(ret_plan.get("safe_monthly_withdrawal", 0))] * len(tdf), mode="lines", name="Safe Monthly SWP", line=dict(color="#34d399", width=2.5, dash="dash")))
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, margin=dict(l=8, r=8, t=20, b=8), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    elif view_choice == "🎯 Milestones":
        ms_list = exp_plan.get("milestones", [])
        if ms_list:
            mt = pd.DataFrame(ms_list)
            mt["Today (₹)"] = mt["amount_today"].apply(format_inr)
            mt["Inflated (₹)"] = mt["inflated_amount"].apply(format_inr)
            st.dataframe(mt[["description", "target_age", "years_away", "Today (₹)", "Inflated (₹)"]], use_container_width=True, hide_index=True)
        else:
            st.info("No one-time milestone outlays scheduled.")
        for sugg in exp_plan.get("strategic_suggestions", []):
            st.markdown(f"- {sugg}")

    else:
        tdf = pd.DataFrame(exp_plan.get("trajectory", []))
        if not tdf.empty:
            st.dataframe(tdf, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Download Trajectory CSV",
                data=tdf.to_csv(index=False).encode("utf-8"),
                file_name=f"retirement_trajectory_{current_user['username']}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    sc1, sc2 = st.columns([2.5, 1])
    with sc1:
        if st.button("💾 Save Plan as 'Last Run'", type="secondary", use_container_width=True, key="ret_btn_save"):
            if database.save_retirement_plan(current_user["username"], user_family_id or 1, bundle, "Last Run"):
                st.toast("✅ Retirement plan saved!")
                st.rerun()
    with sc2:
        if st.button("🔄 Clear View", use_container_width=True, key="ret_btn_clr"):
            st.session_state.pop("active_retirement_plan", None)
            st.rerun()

