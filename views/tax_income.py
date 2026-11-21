"""
Tax & Income Page — Plan Section.
Progress stepper + single-level pill sub-navigation:
  1. Income        (Income Sources CRUD + Form 16/26AS/AIS extraction + ON-DEMAND Passive Income detection)
  2. Deductions    (Country/Regime selector + 80C / 80D / HRA / 24b / NPS / TDS form)
  3. Capital Gains (Upload Broker/AIS PDF/JSON/ZIP + Manual entry + Saved CG)
  4. Tax Summary   (Full India tax computation + Advance Tax schedule + Tax-saving ideas + Report export)
"""

import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from config import format_inr, format_inr_short
from database import (
    add_income_source,
    delete_income_source,
    update_income_source,
    update_user_profile,
    upsert_tax_deductions,
    upsert_capital_gains,
    INCOME_TYPES,
    FREQUENCY_OPTIONS,
)
from tax_engine import (
    derive_investment_income,
    parse_capital_gains,
    compute_full_tax,
    FRSB_RATE,
    FRSB_RATE_EFFECTIVE,
    _sum_totals,
    parse_income_documents,
)
import data_layer
import ui


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("tax")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=False, show_fy=True, show_month=False, page_key="tax"
    )
    view_mode = scope["view"]
    fy_clean = "2025-26"
    if scope["fy"] and scope["fy"] != "All FYs":
        fy_clean = scope["fy"].replace("FY ", "").strip()

    ui.render_page_header(
        "🧾",
        "Tax & Income Planner",
        subtitle=f"Log income, configure deductions & capital gains, and estimate tax liability. RBI FRSB: {FRSB_RATE*100:.2f}% ({FRSB_RATE_EFFECTIVE}).",
        accent="#fbbf24",
        badge=f"FY {fy_clean}",
        help_key="tax",
    )

    user_key = current_user["username"]
    fam_id = user_family_id or 1

    income_df = data_layer.cached_get_income_sources_df(username=user_key, family_id=fam_id, view_mode=view_mode)
    saved_ded = data_layer.cached_get_tax_deductions(user_key, fam_id, fy_clean)
    saved_cg = data_layer.cached_get_capital_gains(user_key, fam_id, fy_clean)

    # Compact progress stepper
    s1 = "✅" if not income_df.empty else "1️⃣"
    s2 = "✅" if saved_ded else "2️⃣"
    s3 = "✅" if saved_cg else "3️⃣"
    s4 = "✅" if st.session_state.get("_tax_result") else "4️⃣"
    st.caption(f"{s1} Income  →  {s2} Deductions  →  {s3} Capital Gains  →  {s4} Tax Summary")

    sub_opts = ["💵 Income", "📋 Deductions", "📈 Capital Gains", "🧮 Tax Summary"]
    default_sub = ui.consume_target_sub("tax", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Tax Section", sub_opts, key="tax_sub_nav", default=default_sub)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if active_sub == "💵 Income":
        _render_income(current_user, fam_id, view_mode, income_df)
    elif active_sub == "📋 Deductions":
        _render_deductions(current_user, user_key, fam_id, fy_clean, saved_ded)
    elif active_sub == "📈 Capital Gains":
        _render_capital_gains(current_user, user_key, fam_id, fy_clean, saved_cg, income_df)
    else:
        _render_tax_summary(current_user, user_key, fam_id, fy_clean, income_df, saved_ded, saved_cg)


def _render_income(current_user, fam_id: int, view_mode: str, income_df: pd.DataFrame) -> None:
    tot_mo = float(income_df["monthly_equivalent"].sum()) if not income_df.empty and "monthly_equivalent" in income_df.columns else 0.0
    tot_yr = tot_mo * 12.0

    ui.render_kpi_grid(
        [
            {"label": "Monthly Income", "value": format_inr_short(tot_mo), "sub": format_inr(tot_mo), "color": "#38bdf8", "accent": "#38bdf8"},
            {"label": "Annual Income", "value": format_inr_short(tot_yr), "sub": format_inr(tot_yr), "color": "#34d399"},
            {"label": "Active Sources", "value": str(len(income_df)), "sub": "Recurring streams", "color": "#fbbf24"},
        ],
        cols=3,
    )

    if not income_df.empty:
        if len(income_df) > 1:
            fig_i = px.pie(income_df, values="monthly_equivalent", names="income_type", hole=0.48, template="plotly_dark")
            fig_i.update_traces(textposition="inside", textinfo="percent+label")
            fig_i.update_layout(paper_bgcolor="rgba(0,0,0,0)", showlegend=False, height=220, margin=dict(l=4, r=4, t=4, b=4))
            st.plotly_chart(fig_i, use_container_width=True)

        edit_df = income_df.copy()
        edit_df["Delete?"] = False
        dcols = ["source_name", "income_type", "amount", "frequency", "monthly_equivalent", "notes", "Delete?"]
        edited_inc = st.data_editor(
            edit_df[dcols],
            column_config={
                "source_name": st.column_config.TextColumn("Source Name", required=True),
                "income_type": st.column_config.SelectboxColumn("Type", options=INCOME_TYPES, required=True),
                "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0, format="₹%d", required=True),
                "frequency": st.column_config.SelectboxColumn("Frequency", options=FREQUENCY_OPTIONS, required=True),
                "monthly_equivalent": st.column_config.NumberColumn("Monthly Eq. (₹)", disabled=True, format="₹%d"),
                "notes": st.column_config.TextColumn("Notes"),
                "Delete?": st.column_config.CheckboxColumn("🗑️ Delete", default=False),
            },
            use_container_width=True,
            hide_index=True,
            key="tax_inc_editor",
        )
        if st.button("💾 Apply Income Changes", type="primary", key="tax_inc_apply"):
            changed = False
            for i, row in edited_inc.iterrows():
                orig = income_df.iloc[i]
                inc_id = int(orig["id"])
                if row["Delete?"]:
                    delete_income_source(inc_id, fam_id)
                    changed = True
                elif (
                    row["source_name"] != orig["source_name"]
                    or row["income_type"] != orig["income_type"]
                    or row["amount"] != orig["amount"]
                    or row["frequency"] != orig["frequency"]
                    or str(row["notes"]) != str(orig.get("notes", ""))
                ):
                    update_income_source(inc_id, source_name=row["source_name"], income_type=row["income_type"], amount=row["amount"], frequency=row["frequency"], notes=str(row["notes"]))
                    changed = True
            if changed:
                data_layer.invalidate_data_cache()
                st.toast("✅ Income sources updated.")
                st.rerun()
    else:
        st.info("No recurring income sources yet. Add one manually or extract from Form 16 / AIS below.")

    with st.expander("➕ Add New Income Source (Manual or Form 16 / AIS)", expanded=income_df.empty):
        add_mode = st.radio("Entry Mode", ["✍️ Manual Entry", "📄 Auto-Extract PDF (Form 16 / 26AS / AIS)"], horizontal=True, key="tax_add_inc_mode")
        if add_mode.startswith("✍️"):
            with st.form("tax_add_inc_form"):
                a1, a2, a3 = st.columns(3)
                i_name = a1.text_input("Source Name", placeholder="e.g. Primary Salary")
                i_type = a1.selectbox("Income Type", INCOME_TYPES)
                i_amt = a2.number_input("Amount (₹)", min_value=0.0, step=1000.0)
                i_freq = a2.selectbox("Frequency", FREQUENCY_OPTIONS)
                i_from = a3.date_input("Effective From", value=datetime.date.today())
                i_notes = a3.text_input("Notes (Optional)")
                if st.form_submit_button("💾 Add Income Source", type="primary", use_container_width=True):
                    if i_name.strip() and i_amt > 0:
                        add_income_source(current_user["username"], fam_id, i_name.strip(), i_type, i_amt, i_freq, str(i_from), i_notes)
                        data_layer.invalidate_data_cache()
                        st.toast(f"✅ Added income source: {i_name.strip()}")
                        st.rerun()
                    else:
                        st.error("Provide source name and amount > 0.")
        else:
            docs = st.file_uploader("Upload Form 16, Form 26AS, or AIS PDF", type=["pdf"], accept_multiple_files=True, key="tax_inc_docs")
            if docs:
                if st.button("🚀 Extract Income from PDF(s)", type="primary", key="tax_ext_inc_btn"):
                    extracted = []
                    with st.spinner("Parsing tax documents..."):
                        for d in docs:
                            extracted.extend(parse_income_documents(d.read(), d.name))
                    for item in extracted:
                        item["Selected"] = True
                        item["Frequency"] = "Annual"
                    st.session_state["extracted_incomes"] = extracted

            if st.session_state.get("extracted_incomes"):
                ed_ext = st.data_editor(
                    pd.DataFrame(st.session_state["extracted_incomes"]),
                    column_config={
                        "Selected": st.column_config.CheckboxColumn("Include?", default=True),
                        "Source": st.column_config.TextColumn("File", disabled=True),
                        "Type": st.column_config.SelectboxColumn("Type", options=INCOME_TYPES, required=True),
                        "Description": st.column_config.TextColumn("Source Name", required=True),
                        "Amount": st.column_config.NumberColumn("Amount (₹)", format="₹%d", min_value=0, required=True),
                        "Frequency": st.column_config.SelectboxColumn("Frequency", options=FREQUENCY_OPTIONS, required=True),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="tax_ext_editor",
                )
                if st.button("💾 Save Selected Incomes", type="primary", key="tax_save_ext_inc"):
                    sel = ed_ext[ed_ext["Selected"] == True]
                    for _, r in sel.iterrows():
                        add_income_source(current_user["username"], fam_id, r["Description"], r["Type"], r["Amount"], r["Frequency"], str(datetime.date.today()))
                    st.session_state["extracted_incomes"] = []
                    data_layer.invalidate_data_cache()
                    st.toast(f"✅ Added {len(sel)} income source(s)!")
                    st.rerun()

    # On-demand Passive Income detection (zero automatic yfinance calls!)
    st.markdown("---")
    st.markdown("##### 💰 Passive Income from Portfolio (On-Demand)")
    st.caption("Derives FD, PPF, EPF, SGB, FRSB interest and equity dividends from your logged holdings.")
    if st.button("🔍 Detect Passive Income from Portfolio", use_container_width=True, key="tax_detect_passive"):
        inv_df = data_layer.get_user_investments_df(
            username=current_user["username"] if view_mode != "Family" else None, family_id=fam_id
        )
        with st.spinner("Scanning holdings & dividend history..."):
            entries = derive_investment_income(inv_df, income_sources_df=income_df)
        st.session_state["_passive_entries"] = entries
        st.session_state["_passive_overrides"] = {idx: float(e["annual_amount"]) for idx, e in enumerate(entries)}

    p_entries = st.session_state.get("_passive_entries", [])
    if p_entries:
        overrides = st.session_state.get("_passive_overrides", {})
        for idx, pe in enumerate(p_entries):
            is_ex = "EXEMPT" in pe.get("taxability", "").upper()
            b_col = "#10b981" if is_ex else "#38bdf8"
            c1, c2 = st.columns([2.5, 1.2])
            with c1:
                st.markdown(
                    f'<div class="fc-card" style="border-left:3px solid {b_col}; padding:10px 12px; margin-bottom:4px;">'
                    f'<div style="font-weight:700; color:{b_col};">{pe["source_name"]}</div>'
                    f'<div style="color:#94a3b8; font-size:0.78rem;">{pe["notes"]} · {pe["taxability"]}</div></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                overrides[idx] = st.number_input("₹/yr", min_value=0.0, value=float(overrides.get(idx, pe["annual_amount"])), step=100.0, key=f"tax_p_ov_{idx}")
        st.session_state["_passive_overrides"] = overrides


def _render_deductions(current_user, user_key: str, fam_id: int, fy_clean: str, saved_ded: dict) -> None:
    c1, c2 = st.columns(2)
    with c1:
        ctry_opts = ["India", "United States", "UAE", "United Kingdom", "Singapore", "Other"]
        cur_ctry = st.session_state.get("user", {}).get("country", "India")
        tax_ctry = st.selectbox("🌍 Country of Tax Residence", ctry_opts, index=ctry_opts.index(cur_ctry) if cur_ctry in ctry_opts else 0, key="tax_country_sel")
        if tax_ctry != cur_ctry:
            update_user_profile(user_key, {"country": tax_ctry})
            st.session_state["user"]["country"] = tax_ctry
    with c2:
        tax_regime = st.selectbox("📋 Tax Regime", ["New Regime", "Old Regime"], key="tax_regime_sel") if tax_ctry == "India" else "N/A"

    if tax_ctry != "India":
        st.info(f"India-specific deduction form is hidden because country is set to **{tax_ctry}**.")
        return

    user_age = int(current_user.get("age", 35) or 35)
    with st.form("tax_ded_form"):
        if tax_regime == "Old Regime":
            st.markdown("##### Section 80C (Cap ₹1.5L)")
            d1, d2, d3, d4 = st.columns(4)
            ppf = d1.number_input("PPF (₹)", min_value=0.0, value=float(saved_ded.get("ppf_contribution", 0)), step=1000.0)
            elss = d2.number_input("ELSS (₹)", min_value=0.0, value=float(saved_ded.get("elss_investment", 0)), step=1000.0)
            lic = d3.number_input("LIC Premium (₹)", min_value=0.0, value=float(saved_ded.get("lic_premium", 0)), step=1000.0)
            hlp = d4.number_input("Home Loan Principal (₹)", min_value=0.0, value=float(saved_ded.get("home_loan_principal", 0)), step=1000.0)
            d5, d6, d7, d8 = st.columns(4)
            school = d5.number_input("School Fees (₹)", min_value=0.0, value=float(saved_ded.get("school_fees", 0)), step=500.0)
            nsc = d6.number_input("NSC Interest (₹)", min_value=0.0, value=float(saved_ded.get("nsc_interest_reinvested", 0)), step=100.0)
            epf = d7.number_input("EPF (₹)", min_value=0.0, value=float(saved_ded.get("epf_contribution", 0)), step=500.0)
            tsfd = d8.number_input("Tax-Saver FD (₹)", min_value=0.0, value=float(saved_ded.get("tax_saver_fd", 0)), step=1000.0)

            st.markdown("##### Section 80D, HRA & Others")
            h1, h2, h3 = st.columns(3)
            hi_self = h1.number_input("Health Ins — Self (₹)", min_value=0.0, value=float(saved_ded.get("health_ins_self", 0)), step=500.0)
            hi_par = h2.number_input("Health Ins — Parents (₹)", min_value=0.0, value=float(saved_ded.get("health_ins_parents", 0)), step=500.0)
            par_sr = h3.checkbox("Parents Senior Citizens", value=bool(saved_ded.get("parents_senior", 0)))

            o1, o2, o3 = st.columns(3)
            hra_basic = o1.number_input("Basic Salary p.a. (₹)", min_value=0.0, value=float(saved_ded.get("hra_basic_salary", 0)), step=1000.0)
            hra_recv = o2.number_input("HRA Received p.a. (₹)", min_value=0.0, value=float(saved_ded.get("hra_received", 0)), step=1000.0)
            rent_paid = o3.number_input("Rent Paid p.a. (₹)", min_value=0.0, value=float(saved_ded.get("rent_paid", 0)), step=1000.0)

            o4, o5, o6 = st.columns(3)
            metro = o4.checkbox("Metro City (50% HRA)", value=bool(saved_ded.get("metro_city", 1)))
            hl_int = o5.number_input("Home Loan Interest 24(b) (₹)", min_value=0.0, max_value=200000.0, value=float(saved_ded.get("home_loan_interest", 0)), step=1000.0)
            nps_1b = o6.number_input("NPS 80CCD(1B) (₹)", min_value=0.0, max_value=50000.0, value=float(saved_ded.get("nps_80ccd_1b", 0)), step=500.0)
        else:
            st.info("ℹ️ **New Regime:** Standard Deduction (₹75,000), NPS Employer 80CCD(2), and Professional Tax apply.")
            ppf = elss = lic = hlp = school = nsc = epf = tsfd = 0.0
            hi_self = hi_par = hra_basic = hra_recv = rent_paid = hl_int = nps_1b = 0.0
            par_sr = False
            metro = True

        st.markdown("##### Common Deductions & Taxes Paid")
        c1, c2, c3, c4 = st.columns(4)
        nps_emp = c1.number_input("NPS Employer 80CCD(2) (₹)", min_value=0.0, value=float(saved_ded.get("nps_employer_80ccd2", 0)), step=500.0)
        prof_tax = c2.number_input("Professional Tax (₹)", min_value=0.0, max_value=2400.0, value=float(saved_ded.get("professional_tax", 0)), step=200.0)
        sb_int = c3.number_input("Savings Interest 80TTA/TTB (₹)", min_value=0.0, value=float(saved_ded.get("savings_bank_interest", 0)), step=100.0)
        scss_int = c4.number_input("SCSS Interest (₹)", min_value=0.0, value=float(saved_ded.get("scss_interest", 0)), step=100.0)

        t1, t2 = st.columns(2)
        tds = t1.number_input("TDS Already Deducted (₹)", min_value=0.0, value=float(saved_ded.get("tds_deducted", 0)), step=1000.0)
        adv_pd = t2.number_input("Advance Tax Paid (₹)", min_value=0.0, value=float(saved_ded.get("advance_paid", 0)), step=1000.0)

        if st.form_submit_button("💾 Save Deductions", type="primary", use_container_width=True):
            payload = {
                "ppf_contribution": ppf, "elss_investment": elss, "lic_premium": lic, "home_loan_principal": hlp,
                "school_fees": school, "nsc_interest_reinvested": nsc, "epf_contribution": epf, "tax_saver_fd": tsfd,
                "health_ins_self": hi_self, "health_ins_parents": hi_par, "parents_senior": int(par_sr),
                "nps_80ccd_1b": nps_1b if tax_regime == "Old Regime" else 0.0,
                "nps_employer_80ccd2": nps_emp, "home_loan_interest": hl_int,
                "hra_basic_salary": hra_basic, "hra_received": hra_recv, "rent_paid": rent_paid,
                "metro_city": int(metro), "professional_tax": prof_tax,
                "savings_bank_interest": sb_int, "scss_interest": scss_int,
                "tds_deducted": tds, "advance_paid": adv_pd, "age": user_age,
            }
            if upsert_tax_deductions(user_key, fam_id, fy_clean, payload):
                data_layer.invalidate_data_cache()
                st.toast("✅ Deductions saved!")
                st.rerun()


def _render_capital_gains(current_user, user_key: str, fam_id: int, fy_clean: str, saved_cg: dict, income_df: pd.DataFrame) -> None:
    cg_mode = st.radio("Capital Gains Entry", ["📤 Upload Broker / AIS", "✏️ Manual Entry", "📋 Saved Data"], horizontal=True, key="tax_cg_mode")

    if cg_mode == "📤 Upload Broker / AIS":
        st.caption("Supports: Zerodha PDF · ICICI Direct PDF · CAMS/KFintech CAS PDF · IT Dept AIS PDF/JSON/ZIP")
        fmt_map = {"Auto-detect": "auto", "IT Dept AIS — PDF": "ais_pdf", "IT Dept AIS — JSON": "ais", "IT Dept AIS — ZIP": "ais_zip", "ICICI Direct PDF": "icici", "Zerodha PDF": "zerodha", "CAMS / KFintech PDF": "cams", "Anand Rathi PDF": "anand_rathi"}
        fmt_sel = st.selectbox("Format Override", list(fmt_map.keys()), key="tax_cg_fmt")
        cg_file = st.file_uploader("Upload Capital Gains Statement", type=["pdf", "json", "zip"], key="tax_cg_file")
        ais_pan = ais_dob = None
        if cg_file and cg_file.name.lower().endswith((".zip", ".json")):
            p1, p2 = st.columns(2)
            ais_pan = p1.text_input("PAN (not saved)", key="tax_ais_pan").strip().upper()
            ais_dob = p2.text_input("DOB (DDMMYYYY)", key="tax_ais_dob").strip()

        if cg_file:
            with st.spinner(f"Parsing {cg_file.name}..."):
                parsed_cg = parse_capital_gains(cg_file, file_type_hint=fmt_map.get(fmt_sel, "auto"), ais_pan=ais_pan, ais_dob=ais_dob)
            st.success(f"✅ Detected: **{parsed_cg.get('detected_format', 'unknown')}** → {parsed_cg.get('source', 'Unknown')}")
            for err in parsed_cg.get("parse_errors", []):
                st.warning(f"⚠️ {err}")
            cg_disp = pd.DataFrame([
                {"Category": "Equity LTCG", "Amount (₹)": float(parsed_cg["equity_ltcg"]), "Tax Rate": "12.5% (>₹1.25L)", "Key": "equity_ltcg"},
                {"Category": "Equity STCG", "Amount (₹)": float(parsed_cg["equity_stcg"]), "Tax Rate": "20%", "Key": "equity_stcg"},
                {"Category": "Equity MF LTCG", "Amount (₹)": float(parsed_cg["equity_mf_ltcg"]), "Tax Rate": "12.5% (>₹1.25L)", "Key": "equity_mf_ltcg"},
                {"Category": "Equity MF STCG", "Amount (₹)": float(parsed_cg["equity_mf_stcg"]), "Tax Rate": "20%", "Key": "equity_mf_stcg"},
                {"Category": "Debt MF LTCG", "Amount (₹)": float(parsed_cg["debt_mf_ltcg"]), "Tax Rate": "Slab", "Key": "debt_mf_ltcg"},
                {"Category": "Debt MF STCG", "Amount (₹)": float(parsed_cg["debt_mf_stcg"]), "Tax Rate": "Slab", "Key": "debt_mf_stcg"},
                {"Category": "Property LTCG", "Amount (₹)": float(parsed_cg["property_ltcg"]), "Tax Rate": "12.5%", "Key": "property_ltcg"},
                {"Category": "Property STCG", "Amount (₹)": float(parsed_cg["property_stcg"]), "Tax Rate": "Slab", "Key": "property_stcg"},
            ])
            ed_cg = st.data_editor(
                cg_disp, use_container_width=True, hide_index=True,
                column_config={"Category": st.column_config.TextColumn(disabled=True), "Tax Rate": st.column_config.TextColumn(disabled=True), "Key": None},
                key="tax_cg_ed",
            )
            if st.button("💾 Save Capital Gains", type="primary", use_container_width=True, key="tax_cg_save"):
                for _, r in ed_cg.iterrows():
                    parsed_cg[r["Key"]] = float(r["Amount (₹)"])
                parsed_cg = _sum_totals(parsed_cg)
                if upsert_capital_gains(user_key, fam_id, fy_clean, parsed_cg):
                    data_layer.invalidate_data_cache()
                    st.toast("✅ Capital gains saved!")
                    st.rerun()

    elif cg_mode == "✏️ Manual Entry":
        with st.form("tax_cg_manual_form"):
            m1, m2 = st.columns(2)
            eq_l = m1.number_input("Equity LTCG (₹)", min_value=0.0, value=float(saved_cg.get("equity_ltcg", 0)), step=1000.0)
            eq_s = m2.number_input("Equity STCG (₹)", min_value=0.0, value=float(saved_cg.get("equity_stcg", 0)), step=1000.0)
            mf_l = m1.number_input("Equity MF LTCG (₹)", min_value=0.0, value=float(saved_cg.get("equity_mf_ltcg", 0)), step=1000.0)
            mf_s = m2.number_input("Equity MF STCG (₹)", min_value=0.0, value=float(saved_cg.get("equity_mf_stcg", 0)), step=1000.0)
            dm_l = m1.number_input("Debt MF LTCG (₹)", min_value=0.0, value=float(saved_cg.get("debt_mf_ltcg", 0)), step=1000.0)
            dm_s = m2.number_input("Debt MF STCG (₹)", min_value=0.0, value=float(saved_cg.get("debt_mf_stcg", 0)), step=1000.0)
            pr_l = m1.number_input("Property LTCG (₹)", min_value=0.0, value=float(saved_cg.get("property_ltcg", 0)), step=1000.0)
            pr_s = m2.number_input("Property STCG (₹)", min_value=0.0, value=float(saved_cg.get("property_stcg", 0)), step=1000.0)
            if st.form_submit_button("💾 Save Capital Gains", type="primary", use_container_width=True):
                mc = _sum_totals({
                    "equity_ltcg": eq_l, "equity_stcg": eq_s, "equity_mf_ltcg": mf_l, "equity_mf_stcg": mf_s,
                    "debt_mf_ltcg": dm_l, "debt_mf_stcg": dm_s, "property_ltcg": pr_l, "property_stcg": pr_s,
                    "other_ltcg": 0.0, "other_stcg": 0.0,
                })
                if upsert_capital_gains(user_key, fam_id, fy_clean, mc):
                    data_layer.invalidate_data_cache()
                    st.toast("✅ Capital gains saved!")
                    st.rerun()
    else:
        if saved_cg:
            disp = {k: v for k, v in saved_cg.items() if isinstance(v, (int, float)) and v > 0 and not k.startswith("_")}
            if disp:
                st.dataframe(pd.DataFrame(list(disp.items()), columns=["Category", "Amount (₹)"]), use_container_width=True, hide_index=True)
            else:
                st.info("All saved capital gains amounts are ₹0.")
        else:
            st.info("No capital gains saved for this FY yet.")


def _render_tax_summary(current_user, user_key: str, fam_id: int, fy_clean: str, income_df: pd.DataFrame, saved_ded: dict, saved_cg: dict) -> None:
    tax_regime = st.selectbox("Tax Regime for Computation", ["New Regime", "Old Regime"], index=0 if st.session_state.get("tax_regime_sel", "New Regime") == "New Regime" else 1, key="tax_sum_regime")

    if st.button("🧮 Compute Full Tax Liability", type="primary", use_container_width=True, key="tax_btn_compute"):
        ded_copy = dict(saved_ded or {})
        ded_copy["age"] = int(current_user.get("age", 35) or 35)
        with st.spinner("Computing India tax liability..."):
            res = compute_full_tax(
                income_sources_df=income_df,
                passive_income_entries=st.session_state.get("_passive_entries", []),
                passive_overrides=st.session_state.get("_passive_overrides", {}),
                cg_data=saved_cg or {},
                deductions=ded_copy,
                tds_deducted=float(ded_copy.get("tds_deducted", 0)),
                advance_paid=float(ded_copy.get("advance_paid", 0)),
                tax_regime=tax_regime,
            )
        st.session_state["_tax_result"] = res
        st.session_state["tax_regime_sel"] = tax_regime

    res = st.session_state.get("_tax_result")
    if not res:
        st.info("Click **Compute Full Tax Liability** above to calculate tax due, advance tax instalments, and saving opportunities.")
        return

    bal_due = float(res.get("balance_due", 0))
    ui.render_kpi_grid(
        [
            {"label": "Gross Slab Income", "value": format_inr_short(float(res.get("gross_slab_income", 0))), "color": "#38bdf8"},
            {"label": "Total Deductions", "value": format_inr_short(float(res.get("total_deduction", 0))), "color": "#34d399"},
            {"label": "Net Taxable Income", "value": format_inr_short(float(res.get("taxable_income", 0))), "color": "#f8fafc"},
            {"label": "Total Tax", "value": format_inr_short(float(res.get("total_tax", 0))), "sub": f"Due: {format_inr_short(bal_due)}", "color": "#f87171" if bal_due > 0 else "#34d399"},
        ],
        cols=4,
    )

    with st.expander("🔍 Income & Capital Gains Breakdown"):
        for ib in res.get("income_breakdown", []):
            st.markdown(f"- {ib.get('source', 'Income')}: **{format_inr(float(ib.get('annual', 0)))}**")
        for pb in res.get("passive_breakdown", []):
            if "EXEMPT" not in pb.get("taxability", "").upper():
                st.markdown(f"- {pb.get('source', 'Passive')}: **{format_inr(float(pb.get('annual', 0)))}**")
        if float(res.get("cg_slab_addition", 0)) > 0:
            st.markdown(f"- Capital Gains added to slab: **{format_inr(float(res['cg_slab_addition']))}**")

    if res.get("advance_tax_schedule"):
        st.markdown("##### 📅 Advance Tax Schedule")
        st.dataframe(pd.DataFrame(res["advance_tax_schedule"]), use_container_width=True, hide_index=True)

    if res.get("savings_opportunities"):
        st.markdown("##### 💡 Tax-Saving Opportunities")
        for opp in res["savings_opportunities"]:
            st.markdown(f"- **{opp.get('opportunity', '')}:** {opp.get('detail', '')}")

    if st.button("📑 Export Tax Summary Report", use_container_width=True, key="tax_go_reports"):
        ui.navigate_to("reports", sub_tab="📄 Statements")

