"""
Insights Page — Analyze Section.
Single-level pill navigation:
  1. Overview  (KPIs, Category share, Top descriptions, quick jump into filtered Ledger)
  2. Trends    (QTD/H1/H2/YTD cumulative strip + Monthly / Quarterly / Half-Yearly chart)
  3. Alerts    (Surge & Anomaly Detector + AI Cost-Saving Advice)
  4. Inflation (CPI Erosion Calculator + Personalised Inflation Rate + Future Predictor)
"""

import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from config import format_inr, format_inr_short, format_month_label, get_indian_quarter
from categorizer import generate_ai_spend_rationalization
from cpi_data import get_cpi_df, calculate_cpi_inflation, calculate_personal_inflation_rate, CPI_CATEGORY_INFLATION
from database import get_period_surge_analytics
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("insights")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=True, show_month=True, page_key="insights"
    )
    view_mode = scope["view"]
    selected_fy = scope["fy"]
    selected_month = scope["month"]
    month_label = scope["month_label"]

    ui.render_page_header(
        "📊",
        "Insights & Analytics",
        subtitle="Understand where your money goes, spot unusual spikes, and forecast inflation.",
        accent="#818cf8",
        badge=f"{view_mode} · {selected_fy}",
    )

    sub_opts = ["📊 Overview", "📈 Trends", "🚨 Alerts", "📉 Inflation"]
    default_sub = ui.consume_target_sub("insights", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Insights View", sub_opts, key="ins_sub_nav", default=default_sub)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # Fetch FY expenses once from cache
    fy_df = data_layer.get_expenses_df(
        fy=selected_fy,
        username=current_user["username"],
        view_mode=view_mode,
        family_id=user_family_id,
        transaction_type="Expense",
    )

    if active_sub == "📊 Overview":
        _render_overview(fy_df, selected_fy, selected_month, month_label)
    elif active_sub == "📈 Trends":
        _render_trends(fy_df, selected_fy)
    elif active_sub == "🚨 Alerts":
        _render_alerts(current_user, user_family_id, view_mode, selected_fy)
    else:
        _render_inflation(current_user, user_family_id, view_mode)


def _render_overview(fy_df: pd.DataFrame, selected_fy: str, selected_month: str, month_label: str) -> None:
    if fy_df.empty:
        ui.render_empty_state(
            "📊",
            f"No spending data for {selected_fy}",
            "Log expenses or switch to 'All FYs' in the scope bar above.",
        )
        return

    period_df = ui.filter_df_by_month(fy_df, selected_month)
    p_total = float(period_df["amount"].sum()) if not period_df.empty else 0.0
    fy_total = float(fy_df["amount"].sum())
    top_cat = period_df.groupby("category")["amount"].sum().idxmax() if not period_df.empty else "—"

    # Biggest spike vs prior month
    cur_mk = selected_month if selected_month != "All Months" else datetime.date.today().strftime("%Y-%m")
    try:
        cur_dt = datetime.datetime.strptime(cur_mk, "%Y-%m").date()
        prev_mk = (cur_dt.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    except Exception:
        prev_mk = ""

    cur_m_df = ui.filter_df_by_month(fy_df, cur_mk)
    prev_m_df = ui.filter_df_by_month(fy_df, prev_mk) if prev_mk else pd.DataFrame()
    if not cur_m_df.empty and not prev_m_df.empty:
        delta = (cur_m_df.groupby("category")["amount"].sum() - prev_m_df.groupby("category")["amount"].sum()).dropna()
        spike_cat = delta.idxmax() if not delta.empty else "—"
        spike_val = float(delta.max()) if not delta.empty else 0.0
    else:
        spike_cat, spike_val = "—", 0.0

    ui.render_kpi_grid(
        [
            {"label": f"Spend ({month_label})", "value": format_inr_short(p_total), "sub": f"{len(period_df)} entries", "color": "#38bdf8", "accent": "#38bdf8"},
            {"label": f"FY Total ({selected_fy})", "value": format_inr_short(fy_total), "sub": f"{len(fy_df)} entries", "color": "#f8fafc"},
            {"label": "Top Category", "value": top_cat, "sub": month_label, "color": "#fbbf24"},
            {"label": "Biggest Spike vs Prior", "value": spike_cat, "sub": f"+{format_inr_short(spike_val)}" if spike_val > 0 else "steady", "color": "#f87171"},
        ],
        cols=4,
    )

    if period_df.empty:
        st.info(f"No expenses in **{month_label}**. Select another month or 'All Months' above.")
        return

    cat_sum = period_df.groupby("category", as_index=False)["amount"].agg(Total="sum", Entries="count").sort_values("Total", ascending=False)
    cat_sum["Share %"] = (cat_sum["Total"] / max(1.0, p_total) * 100.0).round(1)

    c1, c2 = st.columns([1.1, 1.3])
    with c1:
        st.markdown(f"##### 🍩 Category Share ({month_label})")
        fig_d = px.pie(
            cat_sum, names="category", values="Total", hole=0.5, template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_d.update_traces(textposition="inside", textinfo="percent+label")
        fig_d.update_layout(paper_bgcolor="rgba(0,0,0,0)", showlegend=False, height=280, margin=dict(l=6, r=6, t=10, b=6))
        st.plotly_chart(fig_d, use_container_width=True)

    with c2:
        st.markdown(f"##### 📋 Category Breakdown ({month_label})")
        st.dataframe(
            cat_sum,
            column_config={
                "category": st.column_config.TextColumn("Category"),
                "Total": st.column_config.NumberColumn("Total (₹)", format="₹ %.0f"),
                "Entries": st.column_config.NumberColumn("Count"),
                "Share %": st.column_config.NumberColumn("Share", format="%.1f%%"),
            },
            use_container_width=True,
            hide_index=True,
            height=240,
        )
        sel_drill = st.selectbox("Drill into category in Ledger", cat_sum["category"].tolist(), key="ins_drill_cat")
        if st.button(f"🔍 Open {sel_drill} in Ledger", use_container_width=True, key="ins_btn_drill"):
            ui.navigate_to("transactions", sub_tab="📅 Ledger", extra_state={"_ledger_cat_filter": sel_drill})


def _render_trends(fy_df: pd.DataFrame, selected_fy: str) -> None:
    if fy_df.empty:
        st.info(f"No expense data available for **{selected_fy}**.")
        return

    # Cumulative QTD / H1 / H2 / YTD derived in-memory (0 extra DB queries)
    ytd = float(fy_df["amount"].sum())
    h1 = float(fy_df[fy_df["half_year"] == "H1"]["amount"].sum()) if "half_year" in fy_df.columns else 0.0
    h2 = float(fy_df[fy_df["half_year"] == "H2"]["amount"].sum()) if "half_year" in fy_df.columns else 0.0
    curr_q, _ = get_indian_quarter(datetime.date.today())
    qtd = float(fy_df[fy_df["quarter"] == curr_q]["amount"].sum()) if "quarter" in fy_df.columns else 0.0

    ui.render_kpi_grid(
        [
            {"label": f"QTD ({curr_q})", "value": format_inr_short(qtd), "sub": format_inr(qtd), "color": "#38bdf8"},
            {"label": "H1 (Apr–Sep)", "value": format_inr_short(h1), "sub": format_inr(h1), "color": "#818cf8"},
            {"label": "H2 (Oct–Mar)", "value": format_inr_short(h2), "sub": format_inr(h2), "color": "#c084fc"},
            {"label": f"YTD ({selected_fy})", "value": format_inr_short(ytd), "sub": format_inr(ytd), "color": "#34d399"},
        ],
        cols=4,
    )

    gran = ui.segmented_pills("Granularity", ["Monthly", "Quarterly", "Half-Yearly"], key="ins_trend_gran", default="Monthly")
    df_t = fy_df.copy()
    df_t["YearMonth"] = pd.to_datetime(df_t["expense_date"], errors="coerce").dt.strftime("%Y-%m")

    if gran == "Monthly":
        agg = df_t.groupby(["YearMonth", "category"], as_index=False)["amount"].sum().sort_values("YearMonth")
        fig = px.bar(agg, x="YearMonth", y="amount", color="category", template="plotly_dark", labels={"YearMonth": "Month", "amount": "₹"})
    elif gran == "Quarterly":
        agg = df_t.groupby(["quarter", "category"], as_index=False)["amount"].sum().sort_values("quarter")
        fig = px.bar(agg, x="quarter", y="amount", color="category", barmode="group", template="plotly_dark", labels={"quarter": "Quarter", "amount": "₹"})
    else:
        agg = df_t.groupby(["half_year", "category"], as_index=False)["amount"].sum().sort_values("half_year")
        fig = px.bar(agg, x="half_year", y="amount", color="category", barmode="group", template="plotly_dark", labels={"half_year": "Half Year", "amount": "₹"})

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=8, r=8, t=20, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_alerts(current_user, user_family_id, view_mode: str, selected_fy: str) -> None:
    st.markdown("#### 🚨 Expense Surge & Anomaly Detector")
    st.caption("Compares any period against your historical baseline to surface unusual spending spikes.")

    c1, c2 = st.columns([1.3, 2])
    with c1:
        tf_type = st.selectbox("Granularity", ["Month-wise", "Quarter-wise", "Half Year-wise", "Financial Year"], key="ins_an_tf")

    # Single call to get available periods & initial surge analytics
    base_surge_df, avail_periods = get_period_surge_analytics(
        timeframe_type=tf_type, selected_period=None,
        fy=selected_fy, username=current_user["username"],
        view_mode=view_mode, family_id=user_family_id,
    )

    with c2:
        if avail_periods:
            fmt_fn = format_month_label if tf_type == "Month-wise" else str
            sel_period = st.selectbox("Period", avail_periods, format_func=fmt_fn, key="ins_an_period")
        else:
            sel_period = None
            st.info("No historical records available for this timeframe.")

    if not sel_period:
        return

    if sel_period == avail_periods[0]:
        surge_df = base_surge_df
    else:
        surge_df, _ = get_period_surge_analytics(
            timeframe_type=tf_type, selected_period=sel_period,
            fy=selected_fy, username=current_user["username"],
            view_mode=view_mode, family_id=user_family_id,
        )

    if surge_df.empty:
        st.info("No data found for this period.")
        return

    anomalies = surge_df[surge_df["Is_Anomaly"] == True]
    top_row = surge_df.iloc[0]
    tot_excess = float(surge_df["Surge_Amount"].apply(lambda x: max(0.0, x)).sum())

    ui.render_kpi_grid(
        [
            {"label": "Top Surging Category", "value": str(top_row["category"]), "sub": f"+{float(top_row['Surge_%']):.1f}% vs baseline", "color": "#f87171", "accent": "#f43f5e"},
            {"label": "Excess Over Baseline", "value": format_inr_short(tot_excess), "sub": format_inr(tot_excess), "color": "#fbbf24"},
            {"label": "Anomalies Flagged", "value": f"{len(anomalies)} categories", "sub": "≥ 15% & > ₹500 spike", "color": "#f43f5e" if len(anomalies) else "#34d399"},
        ],
        cols=3,
    )

    if st.button("🤖 Get AI Cost-Saving Advice for This Period", type="primary", use_container_width=True, key="ins_ai_surge"):
        with st.spinner("🤖 Gemini AI is analyzing spending spikes..."):
            ai_advice = generate_ai_spend_rationalization(surge_df, timeframe_label=f"{tf_type} ({sel_period})")
        st.success("🎉 AI Analysis Complete!")
        st.info(ai_advice.get("summary", ""))
        st.markdown(f"**💰 Potential Savings Target:** {ai_advice.get('total_potential_savings', '₹ 0')}")
        for idx, rec in enumerate(ai_advice.get("recommendations", []), 1):
            with st.expander(f"💡 #{idx} {rec.get('category', '—')} — Est. Savings: {rec.get('est_savings', '₹ 0')}"):
                st.markdown(f"**Issue:** {rec.get('issue', '')}")
                st.markdown(f"**Advice:** {rec.get('suggestion', '')}")

    chart_df = surge_df[surge_df["Period_Spend"] > 0]
    if not chart_df.empty:
        fig_s = px.bar(
            chart_df, x="category", y=["Period_Spend", "Baseline_Avg"], barmode="group",
            color_discrete_map={"Period_Spend": "#ef4444", "Baseline_Avg": "#3b82f6"},
            template="plotly_dark", height=320, labels={"value": "₹", "category": "", "variable": ""},
        )
        fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=24, b=8),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_s, use_container_width=True)

    st.dataframe(
        surge_df[["category", "Period_Spend", "Baseline_Avg", "Surge_Amount", "Surge_%", "Is_Anomaly"]],
        column_config={
            "category": st.column_config.TextColumn("Category"),
            "Period_Spend": st.column_config.NumberColumn("Spend (₹)", format="₹ %.0f"),
            "Baseline_Avg": st.column_config.NumberColumn("Baseline (₹)", format="₹ %.0f"),
            "Surge_Amount": st.column_config.NumberColumn("Excess (₹)", format="₹ %.0f"),
            "Surge_%": st.column_config.NumberColumn("Spike %", format="%.1f%%"),
            "Is_Anomaly": st.column_config.CheckboxColumn("Anomaly?"),
        },
        use_container_width=True,
        hide_index=True,
    )


def _render_inflation(current_user, user_family_id, view_mode: str) -> None:
    st.markdown("#### 📉 Inflation & Purchasing Power")
    inf1, inf2 = st.columns([1.2, 1.8])
    with inf1:
        st.markdown("##### Erosion Calculator")
        base_yr = st.number_input("Base Year", min_value=2018, max_value=2025, value=2020, key="ins_inf_base")
        curr_yr = st.number_input("Comparison Year", min_value=2019, max_value=2026, value=2025, key="ins_inf_curr")
        sample_amt = st.number_input("Amount in Base Year (₹)", value=10000.0, step=1000.0, key="ins_inf_amt")
        cum_inf = calculate_cpi_inflation(base_yr, curr_yr)
        req_amt = sample_amt * (1 + cum_inf / 100.0)
        st.success(f"₹{sample_amt:,.0f} ({base_yr}) → **{format_inr(req_amt)}** ({curr_yr}) · +{cum_inf:.1f}% CPI")

    with inf2:
        st.markdown("##### Indian CPI Annual Rate (%)")
        cpi_df = get_cpi_df()
        fig_cpi = px.line(cpi_df, x="Year", y="CPI Inflation (%)", markers=True, template="plotly_dark", color_discrete_sequence=["#fbbf24"])
        fig_cpi.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(l=8, r=8, t=10, b=8))
        st.plotly_chart(fig_cpi, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 🔮 Personal Expense Inflation Predictor")
    hist_bd = data_layer.cached_get_category_breakdown(
        fy=None,
        username=current_user["username"] if view_mode == "Private" else None,
        view_mode=view_mode,
        family_id=user_family_id,
    )
    personal_rate = calculate_personal_inflation_rate(hist_bd)

    p1, p2, p3 = st.columns(3)
    with p1:
        ui.render_kpi_grid(
            [{"label": "Personal Inflation Rate", "value": f"{personal_rate}%", "sub": "Weighted by your spend mix", "color": "#f87171", "accent": "#f43f5e"}],
            cols=2,
        )
    with p2:
        custom_inf = st.number_input("Inflation Rate (%)", value=float(personal_rate), step=0.5, format="%.2f", key="ins_pred_inf")
        pred_base = st.number_input("Base Year", min_value=2020, max_value=2030, value=2026, key="ins_pred_base")
    with p3:
        pred_target = st.number_input("Target Year", min_value=2026, max_value=2060, value=2036, key="ins_pred_tgt")
        default_exp = float(hist_bd["Total_Amount"].sum()) if not hist_bd.empty and "Total_Amount" in hist_bd.columns else 600000.0
        base_exp = st.number_input("Base Annual Spend (₹)", value=max(10000.0, default_exp), step=50000.0, key="ins_pred_exp")

    if pred_target > pred_base:
        yrs = list(range(pred_base, pred_target + 1))
        vals = [base_exp * ((1 + custom_inf / 100.0) ** (y - pred_base)) for y in yrs]
        fig_p = px.bar(pd.DataFrame({"Year": yrs, "Projected Annual Spend (₹)": vals}), x="Year", y="Projected Annual Spend (₹)", template="plotly_dark", color_discrete_sequence=["#ef4444"])
        fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=270, margin=dict(l=8, r=8, t=12, b=8))
        st.plotly_chart(fig_p, use_container_width=True)
        st.success(f"By **{pred_target}**, maintaining your lifestyle will require **{format_inr(vals[-1])}/year**.")

    with st.expander("📋 Category CPI Benchmarks", expanded=False):
        cat_cpi = [{"Category": c, "CPI Group": d["cpi_group"], "Avg Inflation %": d["avg_inflation"]} for c, d in CPI_CATEGORY_INFLATION.items()]
        st.dataframe(pd.DataFrame(cat_cpi), use_container_width=True, hide_index=True)

