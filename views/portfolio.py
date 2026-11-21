"""
Portfolio Page — Grow Section.
Always-visible portfolio valuation header + single-level pill sub-navigation:
  1. Holdings    (grouped Mutual Funds / Stocks / Others + Edit mode grid + on-demand Maintenance)
  2. Allocation  (Asset/Cap/Sector/Platform breakdown, Concentration alerts, Playbook, Movers & Shakers)
  3. Advisor     (Algo Advisor + AI Review + Rebalance/Deploy + Ask AI Strategist chat)
  4. SIP Planner (Age-based Equity/Debt/Gold SIP split & compounding projections)
"""

import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from config import format_inr, format_inr_short
from database import (
    record_portfolio_snapshot,
    update_user_profile,
    update_user_age,
    find_duplicate_investments,
    delete_duplicate_investments,
)
from investment_planner import (
    calculate_investment_plan,
    generate_ai_wealth_advice,
    generate_ai_portfolio_suggestions,
    generate_rebalance_advice,
    generate_new_money_advice,
    fetch_benchmark_trends,
    generate_strategist_chat_response,
)
import live_market_tracker
import statement_parser
import data_layer
import ui


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_benchmark_trends():
    return fetch_benchmark_trends()


_dialog_deco = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def _add_holdings_body(current_user, user_family_id) -> None:
    mode = ui.segmented_pills("Add Mode", ["📤 Import Statement", "✍️ Manual Entry"], key="port_add_mode", default="📤 Import Statement")
    if mode == "📤 Import Statement":
        st.caption("Upload broker CSV, Excel, PDF, or screenshot. Gemini AI extracts holdings automatically.")
        tpl = pd.DataFrame({
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
        st.download_button("⬇️ Download Standard CSV Template", tpl.to_csv(index=False).encode(), "investment_template.csv", "text/csv")
        uf = st.file_uploader("Upload CSV, Excel, PDF or Image", type=["csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg"], key="port_stmt_upload")
        if uf and st.button("🚀 Parse & Import", type="primary", use_container_width=True, key="port_stmt_parse"):
            api_key = data_layer.get_gemini_api_key(current_user)
            with st.spinner("Parsing broker statement..."):
                try:
                    parsed_data = statement_parser.identify_and_parse_statement(uf.getvalue(), uf.name, api_key=api_key)
                    if parsed_data:
                        import amfi_lookup
                        for inv_dict in parsed_data:
                            code_candidate = inv_dict.get("name_or_symbol") or inv_dict.get("platform")
                            if code_candidate and str(code_candidate).strip().isdigit():
                                resolved = amfi_lookup.resolve_amfi_code(code_candidate)
                                if resolved:
                                    inv_dict["resolved_name"] = resolved["name"]
                                    inv_dict["sector_segment"] = resolved["category"]
                        cnt = data_layer.batch_insert_investments(parsed_data, username=current_user["username"], family_id=user_family_id or 1)
                        st.toast(f"🎉 Imported {cnt} holding(s)!")
                        st.rerun()
                    else:
                        st.warning("Could not extract holdings from this file.")
                except Exception as e:
                    st.error(f"Parse error: {e}")
    else:
        PRESET_TYPES = [
            "Equity (Stocks)", "Mutual funds", "Structured funds", "EPF", "PPF",
            "KVP (Kisan Vikas Patra)", "NSC (National Savings Certificate)",
            "Fixed Deposits / Recurring Deposits", "Startup investments",
            "Gold / Sovereign Gold Bonds (SGB)", "Real Estate", "Other (Add Custom Type)",
        ]
        PRESET_PLATFORMS = [
            "Zerodha", "Groww", "SBI / SBI Mutual Fund", "Post Office", "Coin (Zerodha)",
            "Angel One", "Upstox", "ICICI Direct", "HDFC Securities", "IndMoney",
            "Direct / Primary Institution", "Other (Add Custom Platform)",
        ]
        c1, c2 = st.columns(2)
        with c1:
            sel_plat = st.selectbox("Platform", PRESET_PLATFORMS, key="port_m_plat")
            final_plat = st.text_input("Custom Platform", key="port_m_plat_c") if sel_plat == "Other (Add Custom Platform)" else sel_plat
            inv_desc = st.text_input("Stock Symbol / Fund Name", value="", placeholder="e.g. HDFCBANK or Nifty 50 Index", key="port_m_desc")
        with c2:
            sel_type = st.selectbox("Asset Type", PRESET_TYPES, key="port_m_type")
            final_type = st.text_input("Custom Type", key="port_m_type_c") if sel_type == "Other (Add Custom Type)" else sel_type
            inv_yr = st.number_input("Year Invested", min_value=1990, max_value=datetime.date.today().year + 2, value=datetime.date.today().year, step=1, key="port_m_yr")
        c3, c4 = st.columns(2)
        with c3:
            inv_amt = st.number_input("Invested Amount (₹)", min_value=100.0, value=50000.0, step=5000.0, key="port_m_amt")
        with c4:
            curr_val = st.number_input("Current Value (₹)", min_value=0.0, value=55000.0, step=5000.0, key="port_m_cur")

        if st.button("➕ Add Holding", type="primary", use_container_width=True, key="port_m_save"):
            if not inv_desc.strip():
                st.warning("Please enter a holding name or stock symbol.")
                return
            data_layer.insert_investment(
                username=current_user["username"],
                platform=final_plat,
                investment_type=final_type,
                investment_amount=inv_amt,
                year_invested=int(inv_yr),
                current_value=curr_val,
                family_id=user_family_id or 1,
                description=inv_desc.strip(),
            )
            st.toast(f"✅ Added {inv_desc.strip()}!")
            st.rerun()


if _dialog_deco is not None:

    @_dialog_deco("➕ Add / Import Holdings", width="large")
    def _open_add_holdings_dialog(current_user, user_family_id) -> None:
        _add_holdings_body(current_user, user_family_id)

else:

    def _open_add_holdings_dialog(current_user, user_family_id) -> None:
        with st.expander("➕ Add / Import Holdings", expanded=True):
            _add_holdings_body(current_user, user_family_id)


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("portfolio")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=False, show_month=False, page_key="port"
    )
    view_mode = scope["view"]

    ui.render_page_header(
        "📈",
        "Investment Portfolio",
        subtitle="Track holdings, monitor allocation drift, get algorithmic & AI advice, and plan SIPs.",
        accent="#10b981",
        badge=f"{view_mode} View",
    )

    inv_df = data_layer.get_user_investments_df(
        username=current_user["username"] if view_mode != "Family" else None,
        family_id=user_family_id,
    )
    tot_invested = float(inv_df["investment_amount"].sum()) if not inv_df.empty and "investment_amount" in inv_df.columns else 0.0
    tot_portfolio = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
    tot_gain = tot_portfolio - tot_invested
    tot_ret_pct = (tot_gain / tot_invested * 100.0) if tot_invested > 0 else 0.0
    gain_color = "#34d399" if tot_gain >= 0 else "#f87171"

    ui.render_kpi_grid(
        [
            {"label": "Portfolio Value", "value": format_inr_short(tot_portfolio), "sub": format_inr(tot_portfolio), "color": "#38bdf8", "accent": "#38bdf8"},
            {"label": "Total Invested", "value": format_inr_short(tot_invested), "sub": f"{len(inv_df)} holding(s)", "color": "#f8fafc"},
            {"label": "Unrealised P&L", "value": f"{'+' if tot_gain > 0 else ''}{format_inr_short(tot_gain)}", "sub": f"{tot_ret_pct:+.2f}% return", "color": gain_color, "accent": gain_color},
            {"label": "Asset Classes", "value": str(inv_df["investment_type"].nunique() if not inv_df.empty and "investment_type" in inv_df.columns else 0), "sub": "Diversification", "color": "#c084fc"},
        ],
        cols=4,
    )

    # Action bar
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if st.button("➕ Add / Import Holdings", type="primary", use_container_width=True, key="port_btn_add"):
            _open_add_holdings_dialog(current_user, user_family_id)
    with ac2:
        if st.button("🔄 Sync Live Prices", use_container_width=True, disabled=inv_df.empty, key="port_btn_sync"):
            with st.spinner("Fetching latest NAVs & prices..."):
                updated_df = live_market_tracker.update_portfolio_live_prices(inv_df.copy())
                data_layer.update_investments_df(updated_df)
                record_portfolio_snapshot(user_family_id or 1, float(updated_df["current_value"].sum()))
                data_layer.invalidate_data_cache()
            st.toast("✅ Live prices synced!")
            st.rerun()
    with ac3:
        if st.button("📑 Portfolio Statement", use_container_width=True, key="port_btn_stmt"):
            ui.navigate_to("reports", sub_tab="📄 Statements")

    # Compact historical deltas strip
    if not inv_df.empty:
        deltas = data_layer.cached_get_portfolio_snapshots_deltas(user_family_id or 1, tot_portfolio)
        def _fmt_d(d):
            v, p = d["value"], d["percent"]
            return f"{'+' if v >= 0 else ''}{format_inr_short(v)} ({'+' if v >= 0 else ''}{p:.1f}%)"
        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.caption(f"Last Sync: **{_fmt_d(deltas['previous_sync'])}**")
        dc2.caption(f"7D: **{_fmt_d(deltas['weekly'])}**")
        dc3.caption(f"30D: **{_fmt_d(deltas['monthly'])}**")
        dc4.caption(f"1Y: **{_fmt_d(deltas['yearly'])}**")

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    sub_opts = ["💼 Holdings", "🥧 Allocation", "🧭 Advisor", "🎯 SIP Planner"]
    default_sub = ui.consume_target_sub("portfolio", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Portfolio View", sub_opts, key="port_sub_nav", default=default_sub)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    if active_sub == "💼 Holdings":
        _render_holdings(inv_df, current_user, user_family_id, view_mode)
    elif active_sub == "🥧 Allocation":
        _render_allocation(inv_df, tot_portfolio, current_user)
    elif active_sub == "🧭 Advisor":
        _render_advisor(inv_df, tot_portfolio, current_user, user_family_id)
    else:
        _render_sip_planner(inv_df, tot_portfolio, current_user, user_family_id, view_mode)


def _render_grouped_summary(holdings_df: pd.DataFrame) -> None:
    def _get_rec(row):
        ret = row.get("returns_pct")
        if pd.isna(ret):
            return "Hold ⏳"
        sl = float(row.get("stop_loss_pct") or 0.0)
        tp = float(row.get("target_profit_pct") or 0.0)
        if sl < 0 and ret <= sl:
            return "🔴 Stop Loss Hit"
        if tp > 0 and ret >= tp:
            return "🟢 Target Hit"
        if ret <= -15:
            return "Risk ⚠️"
        if ret >= 20:
            return "Sell 🎯"
        if -5 <= ret <= 10:
            return "Buy ❇️"
        return "Hold ⏳"

    df = holdings_df.copy()
    df["Recommendation"] = df.apply(_get_rec, axis=1) if "returns_pct" in df.columns else "Hold ⏳"

    mf_mask = df["investment_type"].astype(str).str.lower().str.contains("mutual fund|mf", na=False)
    eq_mask = df["investment_type"].astype(str).str.lower().str.contains("equity|stock", na=False) & ~mf_mask
    other_mask = ~(mf_mask | eq_mask)

    col_cfg = {
        "description": st.column_config.TextColumn("Name / Ticker"),
        "resolved_name": st.column_config.TextColumn("AMFI Name"),
        "platform": st.column_config.TextColumn("Platform"),
        "investment_amount": st.column_config.NumberColumn("Invested (₹)", format="₹ %.0f"),
        "current_value": st.column_config.NumberColumn("Current (₹)", format="₹ %.0f"),
        "unrealized_gain": st.column_config.NumberColumn("P&L (₹)", format="₹ %.0f"),
        "returns_pct": st.column_config.NumberColumn("Return", format="%.1f%%"),
        "Recommendation": st.column_config.TextColumn("Signal"),
    }

    for title, sub_df in [("📈 Mutual Funds", df[mf_mask]), ("📊 Stocks (Equity)", df[eq_mask]), ("🏦 Other Investments", df[other_mask])]:
        if sub_df.empty:
            continue
        t_val = float(sub_df["current_value"].sum())
        t_inv = float(sub_df["investment_amount"].sum())
        t_ret = ((t_val - t_inv) / t_inv * 100.0) if t_inv > 0 else 0.0
        with st.expander(f"{title} ({len(sub_df)}) · {format_inr_short(t_val)} ({t_ret:+.1f}%)", expanded=True):
            cols = [c for c in ["description", "resolved_name", "platform", "investment_amount", "current_value", "unrealized_gain", "returns_pct", "Recommendation"] if c in sub_df.columns]
            st.dataframe(sub_df[cols], use_container_width=True, hide_index=True, column_config=col_cfg)


def _render_holdings(inv_df: pd.DataFrame, current_user, user_family_id, view_mode: str) -> None:
    if inv_df.empty:
        if ui.render_empty_state(
            "💼",
            "No investment holdings yet",
            "Import a broker statement (Zerodha, ICICI, CAMS/CAS) or add your first holding manually.",
            cta_label="➕ Add / Import Holdings",
            cta_key="hold_empty_add",
        ):
            _open_add_holdings_dialog(current_user, user_family_id)
        return

    edit_mode = st.toggle("✏️ Edit Holdings Grid", value=False, key="port_edit_toggle")

    if not edit_mode:
        _render_grouped_summary(inv_df)
    else:
        all_types = sorted(inv_df["investment_type"].dropna().unique().tolist())
        sel_types = st.multiselect("Filter by Asset Class", all_types, default=all_types, key="port_ed_types")
        filt = inv_df[inv_df["investment_type"].isin(sel_types)] if sel_types else inv_df.head(0)
        if "resolved_name" not in filt.columns:
            filt["resolved_name"] = ""
        dcols = [c for c in ["id", "description", "resolved_name", "platform", "investment_type", "investment_amount", "year_invested", "current_value", "units", "avg_buy_price", "market_cap", "sector_segment", "stop_loss_pct", "target_profit_pct", "unrealized_gain", "returns_pct"] if c in filt.columns]
        edited = st.data_editor(
            filt[dcols],
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
                "stop_loss_pct": st.column_config.NumberColumn("Stop Loss %", format="%.1f", min_value=-100.0, max_value=0.0),
                "target_profit_pct": st.column_config.NumberColumn("Target %", format="%.1f", min_value=0.0),
                "unrealized_gain": st.column_config.NumberColumn("P&L (₹)", format="₹ %.2f", disabled=True),
                "returns_pct": st.column_config.NumberColumn("Return %", format="%.2f%%", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="port_holdings_editor",
        )
        if st.button("💾 Save Holding Edits", type="primary", use_container_width=True, key="port_save_ed"):
            cnt = data_layer.update_investments_df(edited)
            st.toast(f"✅ Updated {cnt} holding(s)!")
            st.rerun()

    # Maintenance (strictly on-demand duplicate scan)
    with st.expander("🧰 Maintenance — Delete & Duplicate Scan", expanded=False):
        m1, m2 = st.columns([2, 1])
        with m1:
            del_id = st.number_input("Delete Holding by ID", min_value=1, step=1, key="port_del_id")
        with m2:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Delete", use_container_width=True, key="port_btn_del_id"):
                data_layer.delete_investment(int(del_id))
                st.toast(f"🗑️ Deleted holding #{del_id}.")
                st.rerun()

        st.markdown("---")
        if st.button("🕵️ Scan for Duplicate Holdings", use_container_width=True, key="port_scan_dups"):
            dups = find_duplicate_investments(
                username=current_user["username"] if view_mode != "Family" else None,
                family_id=user_family_id,
            )
            st.session_state["_port_dup_groups"] = dups

        if "_port_dup_groups" in st.session_state:
            dups = st.session_state["_port_dup_groups"]
            if not dups:
                st.success("✅ No duplicate holdings found!")
            else:
                dup_ids, dup_rows = [], []
                for grp in dups:
                    orig = grp[0]
                    for d in grp[1:]:
                        dup_ids.append(d["id"])
                        dup_rows.append({"Dup ID": d["id"], "Original ID": orig["id"], "Platform": d["platform"], "Name": d["description"], "Invested": d["investment_amount"]})
                st.dataframe(pd.DataFrame(dup_rows), use_container_width=True, hide_index=True)
                if st.button(f"🗑️ Delete {len(dup_ids)} Duplicates", type="primary", key="port_del_dups"):
                    cnt = delete_duplicate_investments(dup_ids)
                    data_layer.invalidate_data_cache()
                    st.session_state.pop("_port_dup_groups", None)
                    st.toast(f"🗑️ Deleted {cnt} duplicate holding(s).")
                    st.rerun()

        st.markdown("---")
        confirm_all = st.checkbox("I understand this permanently deletes ALL holdings", key="port_chk_del_all")
        if st.button("🔥 Delete ALL Holdings", type="primary", disabled=not confirm_all, use_container_width=True, key="port_btn_del_all"):
            cnt = data_layer.delete_all_investments(
                username=current_user["username"] if view_mode != "Family" else None,
                family_id=user_family_id,
            )
            st.toast(f"🔥 Deleted {cnt} holding(s).")
            st.rerun()


def _render_allocation(inv_df: pd.DataFrame, tot_portfolio: float, current_user) -> None:
    if inv_df.empty:
        st.info("Add holdings to inspect allocation charts, concentration risks, and top movers.")
        return

    chart_choice = ui.segmented_pills("Breakdown", ["Asset Type", "Market Cap", "Sector / Theme", "Platform"], key="port_alloc_by", default="Asset Type")
    c1, c2 = st.columns(2)
    with c1:
        if chart_choice == "Asset Type":
            fig = px.pie(inv_df, names="investment_type", values="current_value", hole=0.45, template="plotly_dark")
        elif chart_choice == "Market Cap":
            fig = px.pie(inv_df, names="market_cap", values="current_value", hole=0.45, template="plotly_dark")
        elif chart_choice == "Sector / Theme":
            sec = inv_df[inv_df["sector_segment"].astype(str).str.strip().astype(bool)]
            fig = px.pie(sec, names="sector_segment", values="current_value", hole=0.45, template="plotly_dark") if not sec.empty else None
        else:
            fig = px.bar(inv_df.groupby("platform", as_index=False)["current_value"].sum(), x="platform", y="current_value", color="platform", template="plotly_dark")
            fig.update_layout(showlegend=False)

        if fig is not None:
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=6, r=6, t=10, b=6))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector tags recorded yet.")

    with c2:
        top = inv_df.copy()
        top["_name"] = top["description"].astype(str)
        if "resolved_name" in top.columns:
            rn = top["resolved_name"].fillna("").astype(str).str.strip()
            top["_name"] = rn.where(rn != "", top["_name"])
        top = top.nlargest(8, "current_value").sort_values("current_value")
        fig_top = px.bar(top, x="current_value", y="_name", orientation="h", template="plotly_dark", title="Top Holdings", labels={"current_value": "₹", "_name": ""})
        fig_top.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=6, r=6, t=34, b=6))
        st.plotly_chart(fig_top, use_container_width=True)

    # Concentration warnings
    if "sector_segment" in inv_df.columns and tot_portfolio > 0:
        for sec, val in inv_df.groupby("sector_segment")["current_value"].sum().items():
            if pd.isna(sec) or sec == "Unknown" or not str(sec).strip():
                continue
            pct = (float(val) / tot_portfolio) * 100.0
            if pct > 30.0:
                st.warning(f"⚠️ **Concentration Risk:** **{pct:.1f}%** ({format_inr_short(float(val))}) is in **{sec}**.")

    # Playbook alerts
    with st.expander("📖 Automated Investment Playbook"):
        p1, p2 = st.columns(2)
        with p1:
            rule_tp = st.checkbox("Take Profits at +25%", value=True, key="pb_tp")
            rule_sl = st.checkbox("-8% Stop Loss on Stocks", value=False, key="pb_sl")
        with p2:
            rule_ad = st.checkbox("Average Down on -15% drops", value=True, key="pb_ad")
            rule_fr = st.checkbox("'Free Ride' (+100% gain) alerts", value=True, key="pb_fr")

        if "returns_pct" in inv_df.columns:
            alerts = []
            for _, r in inv_df.iterrows():
                name = r.get("resolved_name") or r.get("description")
                ret = float(r["returns_pct"] or 0.0)
                itype = str(r.get("investment_type", "")).lower()
                if rule_fr and ret >= 100:
                    alerts.append(f"🎉 **{name}** (+{ret:.1f}%) — Free Ride zone.")
                elif rule_tp and 25 <= ret < 100:
                    alerts.append(f"📈 **{name}** (+{ret:.1f}%) — Take Profit zone.")
                elif rule_sl and ret <= -8 and ("stock" in itype or "equity" in itype):
                    alerts.append(f"🚨 **{name}** ({ret:.1f}%) — Stop-Loss triggered.")
                elif rule_ad and ret <= -15 and ("mutual" in itype or "etf" in itype or "index" in itype):
                    alerts.append(f"🛒 **{name}** ({ret:.1f}%) — Buy the Dip candidate.")
            if alerts:
                for a in alerts:
                    st.info(a)
            else:
                st.success("No active playbook triggers right now.")

    # Movers & Shakers
    if "returns_pct" in inv_df.columns:
        avg_ret = float(inv_df["returns_pct"].mean())
        st.markdown(f"##### 🚀 Movers & Shakers *(Portfolio Avg: {avg_ret:.1f}%)*")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**Top Outperformers**")
            for _, r in inv_df[inv_df["returns_pct"] > avg_ret].sort_values("returns_pct", ascending=False).head(3).iterrows():
                st.markdown(f"- 🟢 **{r.get('resolved_name') or r.get('description')}**: {r['returns_pct']:.1f}%")
        with m2:
            st.markdown("**Lagging Holdings**")
            for _, r in inv_df[inv_df["returns_pct"] < avg_ret].sort_values("returns_pct", ascending=True).head(3).iterrows():
                nm = r.get("resolved_name") or r.get("description")
                st.markdown(f"- 🔴 **{nm}**: {r['returns_pct']:.1f}%")
                if st.button(f"🔍 AI Alternatives for {nm}", key=f"port_opt_{r['id']}"):
                    st.session_state["optimize_target"] = dict(r)

        if "optimize_target" in st.session_state:
            tgt = st.session_state["optimize_target"]
            with st.expander(f"🤖 AI Optimization: {tgt.get('resolved_name') or tgt.get('description')}", expanded=True):
                if st.button("Generate Replacements (Gemini)", key="port_gen_repl"):
                    with st.spinner("Analyzing Indian market alternatives..."):
                        try:
                            from academy_assessment import get_gemini_client
                            client = get_gemini_client(data_layer.get_gemini_api_key(current_user))
                            resp = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=f"The user holds {tgt.get('resolved_name') or tgt.get('description')} in {tgt.get('sector_segment')}, return {tgt.get('returns_pct', 0):.2f}%. Suggest 3 better Indian market alternatives with brief rationale.",
                            )
                            st.markdown(resp.text)
                        except Exception as e:
                            from ai_errors import friendly_gemini_error
                            st.error(friendly_gemini_error(e))
                if st.button("Close", key="port_close_opt"):
                    del st.session_state["optimize_target"]
                    st.rerun()


def _render_advisor(inv_df: pd.DataFrame, tot_portfolio: float, current_user, user_family_id) -> None:
    from algo_advisor import render_algo_advisor
    algo_sip = float(st.session_state.get("invest_user_sip", max(5000.0, float(st.session_state.get("budget_dict", {}).get("Insurance & Investments", 20000.0)))))
    render_algo_advisor(inv_df, current_user, algo_sip)

    st.markdown("---")
    st.markdown("#### 🤖 AI Portfolio Review & Rebalancing")
    debts_df = data_layer.cached_get_debts(family_id=user_family_id or 1)
    goals_df = data_layer.cached_get_savings_goals(family_id=user_family_id or 1)

    if not inv_df.empty:
        if st.button("🤖 Run AI Portfolio Review", type="primary", use_container_width=True, key="port_ai_rev"):
            with st.spinner("🤖 Gemini AI analyzing portfolio..."):
                res = generate_ai_portfolio_suggestions(inv_df, current_user, debts_df, goals_df)
            st.info(res.get("summary", ""))
            for rec in res.get("recommendations", []):
                with st.expander(f"**{rec.get('title', 'Recommendation')}**"):
                    st.markdown(f"**Observation:** {rec.get('observation', '')}")
                    st.markdown(f"**Suggestion:** {rec.get('suggestion', '')}")

    with st.expander("⚖️ Rebalance or Deploy New Money (AI)", expanded=False):
        adv_ctx = st.text_area("Goals / Context (optional)", placeholder="e.g. Saving for a home down payment in 3 years", key="port_adv_ctx")
        adv_mode = st.radio("Mode", ["🔄 Rebalance Existing Portfolio", "💰 Deploy New Money"], horizontal=True, key="port_adv_mode")
        c1, c2 = st.columns(2)
        risk_opts = ["Conservative", "Moderate", "Aggressive"]
        country_opts = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
        with c1:
            inv_risk = st.selectbox("Risk Profile", risk_opts, index=risk_opts.index(current_user.get("risk_tolerance", "Moderate")) if current_user.get("risk_tolerance") in risk_opts else 1, key="port_adv_risk")
        with c2:
            cur_ctry = current_user.get("country", "India")
            inv_ctry = st.selectbox("Country", country_opts, index=country_opts.index(cur_ctry) if cur_ctry in country_opts else 0, key="port_adv_ctry")
            if inv_ctry != cur_ctry:
                update_user_profile(current_user["username"], {"country": inv_ctry})
                st.session_state["user"]["country"] = inv_ctry

        nm_amt, nm_mode = 50000.0, "SIP (Monthly)"
        if adv_mode.startswith("💰"):
            n1, n2 = st.columns(2)
            nm_amt = n1.number_input("Amount to Invest (₹)", min_value=1000.0, value=50000.0, step=5000.0, key="port_nm_amt")
            nm_mode = n2.selectbox("Mode", ["Lump Sum", "SIP (Monthly)"], key="port_nm_mode")

        if st.button("▶️ Run Analysis", type="primary", use_container_width=True, key="port_run_adv"):
            api_key = data_layer.get_gemini_api_key(current_user)
            if adv_mode.startswith("🔄"):
                with st.spinner("Fetching trend signals & generating rebalance plan..."):
                    st.session_state["rebal_result"] = generate_rebalance_advice(inv_df, inv_risk, inv_ctry, adv_ctx, api_key)
                    st.session_state["nm_result"] = None
            else:
                with st.spinner("Generating deployment suggestions..."):
                    st.session_state["nm_result"] = generate_new_money_advice(inv_df, inv_risk, nm_amt, "SIP" if "SIP" in nm_mode else "Lump Sum", inv_ctry, adv_ctx, api_key)
                    st.session_state["rebal_result"] = None

        rebal = st.session_state.get("rebal_result")
        if rebal:
            if "error" in rebal:
                st.warning(rebal["error"])
            else:
                drift_df = pd.DataFrame(rebal.get("drift_table", []))
                if not drift_df.empty:
                    st.dataframe(drift_df[["Asset Class", "Current %", "Target %", "Drift %", "Action"]], use_container_width=True, hide_index=True)
                for rec in rebal.get("recommendations", []):
                    st.markdown(f"- **{rec.get('title', '')}** — *{rec.get('instrument', '')}*: {rec.get('rationale', '')}")

        nm_res = st.session_state.get("nm_result")
        if nm_res:
            st.info(nm_res.get("summary", ""))
            for cls_k, instrs in nm_res.get("suggestions", {}).items():
                if not instrs:
                    continue
                st.markdown(f"**{cls_k.replace('_', ' ').title()}**")
                for ins in instrs:
                    st.markdown(f"- **{ins.get('name', '')}** ({ins.get('risk', 'N/A')}): {ins.get('rationale', '')} — *{ins.get('suggested_amount', '')}*")

    # ── Ask AI Strategist Chat (consolidated from Market Insights) ───────
    st.markdown("---")
    st.markdown("#### 💬 Ask AI Investment Strategist")
    st.caption("Chat about macro trends, sectors, or your portfolio mix. Live benchmarks load only when you ask a question.")

    if "strategist_messages" not in st.session_state:
        st.session_state["strategist_messages"] = [
            {"role": "assistant", "content": "Hello! Ask me anything about Indian/global market trends, sector rotation, or your current portfolio."}
        ]

    for msg in st.session_state["strategist_messages"]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Ask your investment strategist (e.g., 'View on IT vs Banking sectors?')..."):
        st.chat_message("user").markdown(prompt)
        st.session_state["strategist_messages"].append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Loading benchmarks & thinking..."):
                trends = _cached_benchmark_trends()
                tot_debt = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty else 0.0
                inv_splits = ""
                if not inv_df.empty:
                    splits = inv_df.groupby("investment_type")["current_value"].sum().to_dict()
                    inv_splits = " Splits: " + ", ".join(f"{k}: {format_inr_short(v)}" for k, v in splits.items())
                sys_ctx = (
                    "You are a seasoned investment strategist. Provide objective, data-backed market & portfolio analysis.\n"
                    f"[Context: Market Benchmarks={trends}; Net Worth={format_inr_short(tot_portfolio - tot_debt)}; Portfolio={format_inr_short(tot_portfolio)}.{inv_splits}]"
                )
                msgs = [{"role": "user", "content": sys_ctx}] + st.session_state["strategist_messages"]
                reply = generate_strategist_chat_response(msgs, data_layer.get_gemini_api_key(current_user))
                st.markdown(reply)
        st.session_state["strategist_messages"].append({"role": "assistant", "content": reply})


def _render_sip_planner(inv_df: pd.DataFrame, tot_portfolio: float, current_user, user_family_id, view_mode: str) -> None:
    st.markdown("#### 🎯 SIP Planner & Compounding Trajectory")
    curr_ins = float(st.session_state.get("budget_dict", {}).get("Insurance & Investments", 20000.0))
    use_nw = st.toggle("Link Portfolio Value", value=True, key="sip_link_nw")

    c1, c2, c3 = st.columns(3)
    with c1:
        u_age = st.number_input("Your Age", min_value=18, max_value=85, value=int(current_user.get("age", 35) or 35), step=1, key="invest_user_age")
        if u_age != current_user.get("age", 35):
            if update_user_age(current_user["username"], int(u_age)):
                st.session_state["user"]["age"] = int(u_age)
    with c2:
        u_sav = tot_portfolio if use_nw else st.number_input("Current Savings (₹)", min_value=0.0, value=tot_portfolio, step=50000.0, key="sip_manual_sav")
        if use_nw:
            st.metric("Linked Portfolio", format_inr_short(u_sav))
    with c3:
        u_sip = st.number_input("Monthly SIP (₹)", min_value=1000.0, value=max(5000.0, curr_ins), step=1000.0, key="invest_user_sip")

    exp_df = data_layer.get_expenses_df(
        fy=st.session_state.get("scope", {}).get("fy", "All FYs"),
        username=current_user["username"], view_mode=view_mode, family_id=user_family_id,
    )
    n_mo = max(1, int(exp_df["Month_Key"].nunique()) if not exp_df.empty and "Month_Key" in exp_df.columns else 1)
    avg_mo_exp = float(exp_df["amount"].sum()) / n_mo if not exp_df.empty else 50000.0

    plan = calculate_investment_plan(age=int(u_age), current_savings=u_sav, monthly_investment_budget=u_sip, monthly_expenses=avg_mo_exp)

    ui.render_kpi_grid(
        [
            {"label": "Equity", "value": f"{plan['equity_pct']:.0f}%", "sub": f"SIP {format_inr_short(plan['equity_sip'])}/mo", "color": "#38bdf8"},
            {"label": "Debt / Fixed", "value": f"{plan['debt_pct']:.0f}%", "sub": f"SIP {format_inr_short(plan['debt_sip'])}/mo", "color": "#34d399"},
            {"label": "Gold", "value": f"{plan['gold_pct']:.0f}%", "sub": f"SIP {format_inr_short(plan['gold_sip'])}/mo", "color": "#fbbf24"},
            {"label": "Blended CAGR", "value": f"~{plan['blended_cagr_pct']}%/yr", "sub": "Expected long-term", "color": "#c084fc"},
        ],
        cols=4,
    )

    ch1, ch2 = st.columns([1, 2])
    with ch1:
        pie_df = pd.DataFrame([
            {"Asset": "Equity", "Pct": plan["equity_pct"]},
            {"Asset": "Debt", "Pct": plan["debt_pct"]},
            {"Asset": "Gold", "Pct": plan["gold_pct"]},
        ])
        fig_a = px.pie(pie_df, names="Asset", values="Pct", hole=0.45, color_discrete_map={"Equity": "#38bdf8", "Debt": "#34d399", "Gold": "#fbbf24"}, template="plotly_dark")
        fig_a.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=230, margin=dict(l=4, r=4, t=4, b=4))
        st.plotly_chart(fig_a, use_container_width=True)
    with ch2:
        proj = [{"Horizon": f"{yrs}yr", "Invested": pd_i["total_invested"], "Gain": pd_i["wealth_gain"]} for yrs, pd_i in plan["projections"].items()]
        fig_s = px.bar(pd.DataFrame(proj), x="Horizon", y=["Invested", "Gain"], barmode="stack", template="plotly_dark",
                       color_discrete_map={"Invested": "#64748b", "Gain": "#10b981"}, labels={"value": "₹", "variable": ""})
        fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=230, margin=dict(l=4, r=4, t=10, b=4),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_s, use_container_width=True)

    if plan["emergency_status"] == "Sufficient":
        st.success(f"✅ Emergency Buffer Healthy: {format_inr(u_sav)} > 6-month target ({format_inr(plan['req_emergency'])})")
    else:
        st.warning(f"⚠️ Emergency Buffer Deficit: {format_inr(plan['emergency_gap'])} short of 6-month target ({format_inr(plan['req_emergency'])}).")

    if st.button("💡 Generate AI Wealth Advisory", type="primary", use_container_width=True, key="sip_ai_adv"):
        with st.spinner("🤖 Generating AI wealth strategy..."):
            advice = generate_ai_wealth_advice(plan)
        st.info(advice.get("summary", ""))
        for b in advice.get("key_takeaways", []):
            st.markdown(f"- {b}")

