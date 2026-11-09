"""
Monthly View Module for Inhouse Expense Tracker
Provides a dedicated monthly overview under Transactions with:
- Top-level Monthly Summary KPIs (Income, Expenses, Net Savings, Savings Rate)
- Filter options: "All Transactions", "Income", "Expenses", "Net Savings"
- Inline editing via st.data_editor (type, category, amount, description, visibility)
- Export to CSV
- Net Savings breakdown and insights
"""

import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import (
    EXPENSE_CATEGORIES,
    format_inr,
    format_inr_short,
    format_month_label,
    get_indian_fy
)
from database import (
    get_expenses_df,
    update_expenses_df,
    delete_multiple_expenses,
    insert_expenses,
    get_income_sources_df,
)

INCOME_CATEGORIES = [
    "Salary",
    "Bonus / Incentive",
    "Rental Income",
    "Dividends / Investment Income",
    "Business / Freelance",
    "Interest Income",
    "Refund",
    "Gift / Inheritance",
    "Agricultural Income",
    "Other Income",
]

ALL_TRANSACTION_CATEGORIES = sorted(list(set(EXPENSE_CATEGORIES + INCOME_CATEGORIES)))


def render_monthly_view(
    current_user: Dict[str, Any],
    selected_fy: str,
    view_mode: str,
    user_family_id: Optional[int],
):
    """
    Renders the Monthly View tab under Transactions.
    """
    st.markdown("### 📅 Monthly Transactions & Net Savings Ledger")
    st.caption("Inspect, inline-edit, and export all monthly cash flows with real-time income, expense, and savings summaries.")

    # 1. Fetch all transactions (both Expense & Income) for user/family scope
    # We fetch all FYs or selected FY
    all_tx_df = get_expenses_df(
        fy="All FYs" if selected_fy == "All FYs" else selected_fy,
        username=current_user["username"],
        view_mode=view_mode,
        family_id=user_family_id,
        transaction_type="All",
    )

    # Also fetch recurring income sources
    income_sources_df = get_income_sources_df(
        username=current_user["username"],
        family_id=user_family_id,
        view_mode=view_mode,
    )
    recurring_monthly_income = (
        float(income_sources_df["monthly_equivalent"].sum())
        if not income_sources_df.empty and "monthly_equivalent" in income_sources_df.columns
        else 0.0
    )

    # 2. Extract available months
    today = datetime.date.today()
    current_month_key = today.strftime("%Y-%m")
    
    month_keys_set = {current_month_key}
    if not all_tx_df.empty and "expense_date" in all_tx_df.columns:
        dates = pd.to_datetime(all_tx_df["expense_date"], errors="coerce").dropna()
        for mk in dates.dt.strftime("%Y-%m").unique():
            if mk and isinstance(mk, str):
                month_keys_set.add(mk)

    # Sort months descending (most recent first)
    sorted_month_keys = sorted(list(month_keys_set), reverse=True)

    # Month selection UI controls
    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 3.5, 1.5])
    
    # Store selected month in session state if not already set
    if "mv_selected_month" not in st.session_state or st.session_state["mv_selected_month"] not in sorted_month_keys:
        st.session_state["mv_selected_month"] = sorted_month_keys[0]

    cur_idx = sorted_month_keys.index(st.session_state["mv_selected_month"])

    with col_sel1:
        prev_disabled = cur_idx >= len(sorted_month_keys) - 1
        if st.button("◀ Older Month", disabled=prev_disabled, use_container_width=True, key="mv_btn_prev"):
            st.session_state["mv_selected_month"] = sorted_month_keys[cur_idx + 1]
            st.rerun()

    with col_sel2:
        def _label_fn(mk: str) -> str:
            try:
                dt = datetime.datetime.strptime(mk, "%Y-%m")
                return dt.strftime("%B %Y") + f"  ({mk})"
            except Exception:
                return mk

        chosen_month = st.selectbox(
            "Select Month",
            sorted_month_keys,
            index=cur_idx,
            format_func=_label_fn,
            key="mv_month_select_box",
            label_visibility="collapsed",
        )
        if chosen_month != st.session_state["mv_selected_month"]:
            st.session_state["mv_selected_month"] = chosen_month
            st.rerun()

    with col_sel3:
        next_disabled = cur_idx <= 0
        if st.button("Newer Month ▶", disabled=next_disabled, use_container_width=True, key="mv_btn_next"):
            st.session_state["mv_selected_month"] = sorted_month_keys[cur_idx - 1]
            st.rerun()

    sel_month = st.session_state["mv_selected_month"]
    try:
        sel_month_dt = datetime.datetime.strptime(sel_month, "%Y-%m")
        sel_month_title = sel_month_dt.strftime("%B %Y")
    except Exception:
        sel_month_title = sel_month

    # 3. Filter transactions for the selected month
    if not all_tx_df.empty and "expense_date" in all_tx_df.columns:
        all_tx_df["expense_dt_parsed"] = pd.to_datetime(all_tx_df["expense_date"], errors="coerce")
        month_df = all_tx_df[all_tx_df["expense_dt_parsed"].dt.strftime("%Y-%m") == sel_month].copy()
    else:
        month_df = pd.DataFrame()

    # Ensure transaction_type exists and is standardized
    if not month_df.empty:
        if "transaction_type" not in month_df.columns:
            month_df["transaction_type"] = "Expense"
        month_df["transaction_type"] = (
            month_df["transaction_type"].fillna("Expense").astype(str).str.strip().str.title()
        )
        # normalize
        month_df["transaction_type"] = month_df["transaction_type"].apply(
            lambda x: "Income" if x.lower() == "income" else "Expense"
        )
        month_df["amount"] = pd.to_numeric(month_df["amount"], errors="coerce").fillna(0.0)

    # 4. Compute Month Summary Metrics
    if not month_df.empty:
        tx_expense = float(month_df[month_df["transaction_type"] == "Expense"]["amount"].sum())
        tx_income = float(month_df[month_df["transaction_type"] == "Income"]["amount"].sum())
        total_tx_count = len(month_df)
    else:
        tx_expense = 0.0
        tx_income = 0.0
        total_tx_count = 0

    # Determine Total Income:
    # If explicit income transactions exist for this month, use tx_income.
    # If no income transactions logged but recurring income sources exist, use recurring_monthly_income.
    # If both exist and user wants combined, we use tx_income + recurring_monthly_income if tx_income is supplemental,
    # or max. Here, if tx_income > 0 we use tx_income, else recurring_monthly_income.
    if tx_income > 0:
        total_income = tx_income
        income_source_note = f"from {len(month_df[month_df['transaction_type'] == 'Income'])} logged transaction(s)"
    elif recurring_monthly_income > 0:
        total_income = recurring_monthly_income
        income_source_note = "from registered recurring income source(s)"
    else:
        total_income = 0.0
        income_source_note = "no income logged"

    net_savings = total_income - tx_expense
    savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

    # ── Top Summary KPI Cards ─────────────────────────────────────────────
    savings_color = "#10b981" if net_savings >= 0 else "#ef4444"
    savings_sign = "+" if net_savings > 0 else ""

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                padding: 18px 22px; border-radius: 14px; border: 1px solid #334155;
                margin-top: 10px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                <span>📊 Financial Summary for</span>
                <span style="color: #38bdf8;">{sel_month_title}</span>
            </div>
            <div style="font-size: 0.85rem; color: #94a3b8; background: #1e293b; padding: 4px 10px; border-radius: 8px; border: 1px solid #475569;">
                {total_tx_count} record(s) &bull; Income {income_source_note}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 14px; border-radius: 10px; border-left: 4px solid #38bdf8;">
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">💵 Total Income</div>
                <div style="font-size: 1.35rem; font-weight: 700; color: #38bdf8; margin-top: 4px;">{format_inr(total_income)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">{income_source_note}</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 14px; border-radius: 10px; border-left: 4px solid #f43f5e;">
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">💸 Total Expenses</div>
                <div style="font-size: 1.35rem; font-weight: 700; color: #f43f5e; margin-top: 4px;">{format_inr(tx_expense)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">all categorized spending</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 14px; border-radius: 10px; border-left: 4px solid {savings_color};">
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">💰 Net Savings</div>
                <div style="font-size: 1.35rem; font-weight: 700; color: {savings_color}; margin-top: 4px;">{savings_sign}{format_inr(net_savings)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">Income &minus; Expenses</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 14px; border-radius: 10px; border-left: 4px solid #a855f7;">
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">📈 Savings Rate</div>
                <div style="font-size: 1.35rem; font-weight: 700; color: #c084fc; margin-top: 4px;">{savings_rate:.1f}%</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">of monthly income retained</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5. Filter selector: "All Transactions", "Income", "Expenses", "Net Savings"
    st.markdown("#### 🔍 Filter & Transaction View")
    filter_options = ["All Transactions", "Income", "Expenses", "Net Savings"]
    selected_filter = st.radio(
        "Select Filter",
        options=filter_options,
        index=0,
        horizontal=True,
        key=f"mv_filter_radio_{sel_month}",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. View Handling based on selected filter
    if selected_filter == "Net Savings":
        _render_net_savings_deep_dive(
            month_df=month_df,
            sel_month_title=sel_month_title,
            total_income=total_income,
            tx_expense=tx_expense,
            net_savings=net_savings,
            savings_rate=savings_rate,
            recurring_monthly_income=recurring_monthly_income,
            income_sources_df=income_sources_df,
        )
    else:
        _render_transactions_table_and_editor(
            month_df=month_df,
            selected_filter=selected_filter,
            sel_month=sel_month,
            sel_month_title=sel_month_title,
            current_user=current_user,
            user_family_id=user_family_id,
            view_mode=view_mode,
        )


def _render_net_savings_deep_dive(
    month_df: pd.DataFrame,
    sel_month_title: str,
    total_income: float,
    tx_expense: float,
    net_savings: float,
    savings_rate: float,
    recurring_monthly_income: float,
    income_sources_df: pd.DataFrame,
):
    """
    Renders detailed Net Savings breakdown, waterfall / bar chart, and actionable insights.
    """
    st.markdown(f"#### 💰 Net Savings Analysis — {sel_month_title}")
    
    col_chart, col_details = st.columns([1.3, 1])

    with col_chart:
        # Waterfall or Bar comparison
        categories_spent = {}
        if not month_df.empty:
            exp_rows = month_df[month_df["transaction_type"] == "Expense"]
            if not exp_rows.empty:
                categories_spent = exp_rows.groupby("category")["amount"].sum().to_dict()

        chart_labels = ["Total Income"]
        chart_values = [total_income]
        chart_measures = ["relative"]

        # Sort top categories
        top_cats = sorted(categories_spent.items(), key=lambda x: x[1], reverse=True)[:5]
        for cat, amt in top_cats:
            chart_labels.append(f"− {cat[:14]}")
            chart_values.append(-amt)
            chart_measures.append("relative")

        other_spent = tx_expense - sum(amt for _, amt in top_cats)
        if other_spent > 0:
            chart_labels.append("− Other Exp")
            chart_values.append(-other_spent)
            chart_measures.append("relative")

        chart_labels.append("Net Savings")
        chart_values.append(net_savings)
        chart_measures.append("total")

        fig_waterfall = go.Figure(go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=chart_measures,
            x=chart_labels,
            textposition="outside",
            text=[format_inr_short(abs(v)) for v in chart_values],
            y=chart_values,
            connector={"line": {"color": "#64748b"}},
            decreasing={"marker": {"color": "#f43f5e"}},
            increasing={"marker": {"color": "#38bdf8"}},
            totals={"marker": {"color": "#10b981" if net_savings >= 0 else "#ef4444"}},
        ))

        fig_waterfall.update_layout(
            title=f"Cash Flow Bridge ({sel_month_title})",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f8fafc"),
            height=340,
            margin=dict(l=10, r=10, t=40, b=20),
            showlegend=False,
            yaxis=dict(gridcolor="#334155"),
            xaxis=dict(gridcolor="#334155"),
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)

    with col_details:
        st.markdown("##### 📌 Cash Flow Breakdown")
        breakdown_data = [
            {"Item": "💵 Monthly Income", "Amount": format_inr(total_income), "Type": "Inflow"},
            {"Item": "💸 Monthly Expenses", "Amount": format_inr(tx_expense), "Type": "Outflow"},
            {"Item": "💰 Net Savings", "Amount": format_inr(net_savings), "Type": "Net Result"},
            {"Item": "📈 Savings Rate", "Amount": f"{savings_rate:.1f}%", "Type": "Metric"},
        ]
        if recurring_monthly_income > 0 and total_income != recurring_monthly_income:
            breakdown_data.append({
                "Item": "ℹ️ Recurring Sources Baseline",
                "Amount": format_inr(recurring_monthly_income),
                "Type": "Reference",
            })
        
        st.table(pd.DataFrame(breakdown_data).set_index("Item"))

        # Health rule-of-thumb indicator
        if savings_rate >= 30:
            st.success(f"🌟 **Excellent Savings Rate ({savings_rate:.1f}%)**: Well above the recommended 20% benchmark!")
        elif savings_rate >= 20:
            st.info(f"✅ **Healthy Savings ({savings_rate:.1f}%)**: Meeting the standard 50/30/20 budget framework.")
        elif savings_rate > 0:
            st.warning(f"⚠️ **Modest Savings ({savings_rate:.1f}%)**: Try pruning discretionary categories to push towards 20%.")
        else:
            st.error(f"🚨 **Monthly Deficit**: Outflows exceeded income by {format_inr(abs(net_savings))}.")

    # Export Net Savings Summary
    summary_export_df = pd.DataFrame([
        {"Month": sel_month_title, "Metric": "Total Income", "Value (₹)": total_income},
        {"Month": sel_month_title, "Metric": "Total Expenses", "Value (₹)": tx_expense},
        {"Month": sel_month_title, "Metric": "Net Savings", "Value (₹)": net_savings},
        {"Month": sel_month_title, "Metric": "Savings Rate (%)", "Value (₹)": round(savings_rate, 2)},
    ])
    csv_bytes = summary_export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"📥 Export Net Savings Summary for {sel_month_title} to CSV",
        data=csv_bytes,
        file_name=f"Net_Savings_Summary_{sel_month_title.replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def _render_transactions_table_and_editor(
    month_df: pd.DataFrame,
    selected_filter: str,
    sel_month: str,
    sel_month_title: str,
    current_user: Dict[str, Any],
    user_family_id: Optional[int],
    view_mode: str,
):
    """
    Renders the transactions list with full inline editing and exporting.
    """
    # Filter the month dataframe
    if selected_filter == "Income":
        filtered_df = month_df[month_df["transaction_type"] == "Income"].copy() if not month_df.empty else pd.DataFrame()
        title_prefix = f"💵 Income Entries for {sel_month_title}"
    elif selected_filter == "Expenses":
        filtered_df = month_df[month_df["transaction_type"] == "Expense"].copy() if not month_df.empty else pd.DataFrame()
        title_prefix = f"💸 Expense Entries for {sel_month_title}"
    else:  # All Transactions
        filtered_df = month_df.copy() if not month_df.empty else pd.DataFrame()
        title_prefix = f"📋 All Transactions for {sel_month_title}"

    st.markdown(f"#### {title_prefix}")

    # Prepare DataFrame columns for data_editor
    display_cols = ["id", "expense_date", "transaction_type", "category", "description", "amount", "visibility", "Delete?"]

    if filtered_df.empty:
        st.info(f"No {selected_filter.lower()} found for **{sel_month_title}**.")
    else:
        # Standardize date to string YYYY-MM-DD
        filtered_df["expense_date"] = pd.to_datetime(filtered_df["expense_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        filtered_df["Delete?"] = False

        # Add missing columns safely
        for col in ["id", "category", "description", "amount", "visibility", "transaction_type"]:
            if col not in filtered_df.columns:
                filtered_df[col] = "" if col in ["category", "description"] else 0.0

        editor_data = filtered_df[display_cols].copy()

        edited_df = st.data_editor(
            editor_data,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "expense_date": st.column_config.TextColumn("Date (YYYY-MM-DD)", required=True),
                "transaction_type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["Expense", "Income"],
                    required=True,
                    width="small",
                ),
                "category": st.column_config.SelectboxColumn(
                    "Category",
                    options=ALL_TRANSACTION_CATEGORIES,
                    required=True,
                ),
                "description": st.column_config.TextColumn("Description"),
                "amount": st.column_config.NumberColumn(
                    "Amount (₹)",
                    min_value=0.0,
                    format="₹ %.2f",
                    required=True,
                ),
                "visibility": st.column_config.SelectboxColumn(
                    "Visibility",
                    options=["Family", "Private"],
                    required=True,
                    width="small",
                ),
                "Delete?": st.column_config.CheckboxColumn("Delete?", default=False, width="small"),
            },
            use_container_width=True,
            hide_index=True,
            key=f"monthly_editor_{sel_month}_{selected_filter.replace(' ', '_')}",
        )

        col_save, col_export = st.columns([1, 1])
        with col_save:
            if st.button(f"💾 Save Changes to {selected_filter}", type="primary", use_container_width=True, key=f"btn_save_{sel_month}"):
                # 1. Handle Deletions
                to_delete = edited_df[edited_df["Delete?"] == True]["id"].dropna().tolist()
                del_count = 0
                if to_delete:
                    int_ids = [int(i) for i in to_delete if i and not pd.isna(i)]
                    if int_ids:
                        del_count = delete_multiple_expenses(int_ids)

                # 2. Handle Updates
                rows_to_update = edited_df[edited_df["Delete?"] != True].copy()
                existing_rows = rows_to_update[rows_to_update["id"].notna() & (rows_to_update["id"] > 0)]
                upd_count = 0
                if not existing_rows.empty:
                    upd_count = update_expenses_df(existing_rows)

                # 3. Handle newly inserted rows (id is NaN or 0)
                new_rows = rows_to_update[rows_to_update["id"].isna() | (rows_to_update["id"] == 0)]
                ins_count = 0
                if not new_rows.empty:
                    new_records = []
                    for _, nr in new_rows.iterrows():
                        r_amt = float(nr.get("amount", 0.0) or 0.0)
                        if r_amt > 0:
                            new_records.append({
                                "date": str(nr.get("expense_date") or f"{sel_month}-01"),
                                "category": str(nr.get("category") or "Miscellaneous"),
                                "description": str(nr.get("description") or ""),
                                "amount": r_amt,
                                "visibility": str(nr.get("visibility") or "Family"),
                                "transaction_type": str(nr.get("transaction_type") or "Expense"),
                            })
                    if new_records:
                        ins_count = insert_expenses(
                            new_records,
                            source="Monthly View Grid",
                            username=current_user["username"],
                            visibility="Family",
                            family_id=user_family_id,
                        )

                msg_parts = []
                if upd_count > 0:
                    msg_parts.append(f"updated {upd_count} record(s)")
                if ins_count > 0:
                    msg_parts.append(f"added {ins_count} new record(s)")
                if del_count > 0:
                    msg_parts.append(f"deleted {del_count} record(s)")

                if msg_parts:
                    st.success(f"🎉 Successfully {', '.join(msg_parts)}!")
                else:
                    st.info("No modifications were detected.")
                st.rerun()

        with col_export:
            # Export to CSV
            export_df = filtered_df.drop(columns=["Delete?", "expense_dt_parsed"], errors="ignore")
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            export_filename = f"Transactions_{sel_month}_{selected_filter.replace(' ', '_')}.csv"
            st.download_button(
                label=f"📥 Export {selected_filter} to CSV",
                data=csv_data,
                file_name=export_filename,
                mime="text/csv",
                use_container_width=True,
                key=f"btn_export_{sel_month}_{selected_filter.replace(' ', '_')}",
            )

    # 7. Quick Add Entry for this month
    with st.expander(f"➕ Quick Add Entry for {sel_month_title}", expanded=filtered_df.empty):
        qa_col1, qa_col2, qa_col3, qa_col4 = st.columns([1.2, 1.2, 2.5, 1.5])
        
        # default date inside selected month
        default_day = min(today.day, 28) if sel_month == today.strftime("%Y-%m") else 1
        try:
            default_entry_date = datetime.date(int(sel_month.split("-")[0]), int(sel_month.split("-")[1]), default_day)
        except Exception:
            default_entry_date = today

        with qa_col1:
            qa_type = st.selectbox("Type", ["Expense", "Income"], key=f"qa_type_{sel_month}")
        with qa_col2:
            qa_date = st.date_input("Date", default_entry_date, key=f"qa_date_{sel_month}")
        with qa_col3:
            qa_desc = st.text_input("Description", placeholder="e.g. Monthly Salary, Freelance project, D-Mart", key=f"qa_desc_{sel_month}")
        with qa_col4:
            qa_amt = st.number_input("Amount (₹)", min_value=0.0, step=500.0, format="%.2f", key=f"qa_amt_{sel_month}")

        qa_col5, qa_col6 = st.columns([2, 1])
        with qa_col5:
            cat_list = INCOME_CATEGORIES if qa_type == "Income" else EXPENSE_CATEGORIES
            qa_cat = st.selectbox("Category", cat_list, key=f"qa_cat_{sel_month}")
        with qa_col6:
            qa_vis = st.selectbox("Visibility", ["Family", "Private"], key=f"qa_vis_{sel_month}")

        if st.button(f"➕ Add {qa_type} to {sel_month_title}", type="secondary", use_container_width=True, key=f"qa_btn_{sel_month}"):
            if qa_amt > 0:
                insert_expenses([{
                    "date": qa_date.isoformat(),
                    "category": qa_cat,
                    "description": qa_desc,
                    "amount": qa_amt,
                    "visibility": qa_vis,
                    "transaction_type": qa_type,
                }], source="Monthly View Quick Add", username=current_user["username"], visibility=qa_vis, family_id=user_family_id)
                st.success(f"✅ Added {qa_type} of {format_inr(qa_amt)} under '{qa_cat}'!")
                st.rerun()
            else:
                st.warning("Please enter an amount greater than ₹ 0.")
