"""
Budgets & Goals Page — Track Section.
Replaces the old 125-widget Budget Adjuster with:
  - Budgets (default = read-first status cards sorted with over-budget groups first)
  - Edit Budgets toggle -> clean single st.data_editor table + 3 quick presets + 1 Save button
  - Goals -> 2-column progress cards + New Goal modal dialog
"""

import datetime
import pandas as pd
import streamlit as st

from config import EXPENSE_CATEGORIES, CATEGORY_GROUPS, GROUP_COLOURS, format_inr, format_inr_short, get_indian_fy
from database import add_savings_goal, delete_savings_goal, add_goal_contribution
import data_layer
import ui


_dialog_deco = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def _new_goal_form_body(user_family_id: int) -> None:
    with st.form("dlg_new_goal_form"):
        g_name = st.text_input("Goal Name", placeholder="e.g. Child's Education, Emergency Fund")
        g_target = st.number_input("Target Amount (₹)", min_value=0.0, step=10000.0)
        g_date = st.date_input("Target Date", value=datetime.date.today() + datetime.timedelta(days=365))
        g_contrib = st.number_input("Planned Monthly Contribution (₹)", min_value=0.0, step=1000.0)
        if st.form_submit_button("💾 Create Goal", type="primary", use_container_width=True):
            if g_name.strip() and g_target > 0:
                add_savings_goal(user_family_id or 1, g_name.strip(), g_target, str(g_date), g_contrib)
                data_layer.invalidate_data_cache()
                st.toast(f"🏆 Goal '{g_name.strip()}' created!")
                st.rerun()
            else:
                st.error("Please provide a goal name and target amount > 0.")


if _dialog_deco is not None:

    @_dialog_deco("🏆 Create New Savings Goal")
    def _open_new_goal_dialog(user_family_id: int) -> None:
        _new_goal_form_body(user_family_id)

else:

    def _open_new_goal_dialog(user_family_id: int) -> None:
        with st.expander("🏆 Create New Savings Goal", expanded=True):
            _new_goal_form_body(user_family_id)


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("budgets")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=True, show_month=False, page_key="budgets"
    )
    view_mode = scope["view"]
    selected_fy = scope["fy"]
    target_fy = selected_fy if selected_fy != "All FYs" else (scope["all_fys"][0] if scope["all_fys"] else get_indian_fy(datetime.date.today()))

    ui.render_page_header(
        "🎯",
        "Budgets & Goals",
        subtitle="Monitor category limits, catch overspending early, and track savings targets.",
        accent="#10b981",
        badge=f"{view_mode} · {target_fy}",
    )

    sub_opts = ["🎯 Budgets", "🏆 Goals"]
    default_sub = ui.consume_target_sub("budgets", sub_opts, sub_opts[0])
    active_sub = ui.segmented_pills("Budgets & Goals", sub_opts, key="bud_sub_nav", default=default_sub)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    if active_sub == "🎯 Budgets":
        _render_budgets(current_user, user_family_id, view_mode, target_fy)
    else:
        _render_goals(user_family_id)


def _render_budgets(current_user, user_family_id, view_mode: str, target_fy: str) -> None:
    budget_status = data_layer.get_budget_status(
        target_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )

    tot_budget = float(budget_status["Annual_Budget"].sum()) if not budget_status.empty and "Annual_Budget" in budget_status.columns else 0.0
    tot_spent = float(budget_status["Actual_Spent"].sum()) if not budget_status.empty and "Actual_Spent" in budget_status.columns else 0.0
    tot_rem = tot_budget - tot_spent
    tot_util = (tot_spent / tot_budget * 100.0) if tot_budget > 0 else 0.0
    over_cnt = int(((budget_status["Annual_Budget"] > 0) & (budget_status["Utilization_%"] > 100)).sum()) if not budget_status.empty else 0

    ui.render_kpi_grid(
        [
            {"label": f"Annual Budget ({target_fy})", "value": format_inr_short(tot_budget), "sub": f"{format_inr_short(tot_budget/12)}/mo", "color": "#38bdf8", "accent": "#38bdf8"},
            {"label": "Actual Spent", "value": format_inr_short(tot_spent), "sub": f"{tot_util:.1f}% utilised", "color": "#f43f5e" if tot_util > 100 else "#f8fafc"},
            {"label": "Remaining", "value": format_inr_short(tot_rem), "sub": "Buffer" if tot_rem >= 0 else "Over budget", "color": "#34d399" if tot_rem >= 0 else "#f87171"},
            {"label": "Over-Budget", "value": f"{over_cnt} categories", "sub": "Needs review" if over_cnt > 0 else "All on track", "color": "#f87171" if over_cnt > 0 else "#34d399"},
        ],
        cols=4,
    )

    edit_mode = st.toggle("✏️ Edit Budget Allocations", value=(tot_budget == 0), key="bud_edit_toggle")

    if edit_mode:
        _render_budget_editor_fragment(current_user, user_family_id, view_mode, target_fy)
        return

    # ── Status View (sorted: over-budget groups first) ───────────────────
    if budget_status.empty or tot_budget == 0:
        ui.render_empty_state(
            "🎯",
            f"No budgets configured for {target_fy}",
            "Toggle 'Edit Budget Allocations' above to auto-fill from historical averages or set custom limits.",
        )
        return

    bs_map = {row["category"]: row for _, row in budget_status.iterrows()}
    group_cards = []
    for grp_name, grp_cats in CATEGORY_GROUPS.items():
        rows = []
        for cat in grp_cats:
            r = bs_map.get(cat)
            if r is not None and (float(r["Annual_Budget"]) > 0 or float(r["Actual_Spent"]) > 0):
                rows.append((cat, float(r["Actual_Spent"]), float(r["Annual_Budget"]), float(r["Utilization_%"])))
        if rows:
            g_spent = sum(x[1] for x in rows)
            g_budget = sum(x[2] for x in rows)
            g_util = (g_spent / g_budget * 100.0) if g_budget > 0 else 0.0
            group_cards.append((g_util, grp_name, g_spent, g_budget, rows))

    # Sort highest utilisation first so trouble spots are immediately visible
    group_cards.sort(key=lambda x: x[0], reverse=True)

    for g_util, grp_name, g_spent, g_budget, rows in group_cards:
        badge_cls = "fc-badge-over" if g_util > 100 else ("fc-badge-warn" if g_util > 80 else "fc-badge-ok")
        badge_txt = "OVER" if g_util > 100 else ("DANGER" if g_util > 80 else "ON TRACK")
        bar_col = "#ef4444" if g_util > 100 else ("#f59e0b" if g_util > 80 else "#10b981")

        with st.expander(
            f"{grp_name}  ·  {format_inr_short(g_spent)} / {format_inr_short(g_budget)}  ({g_util:.0f}%)  [{badge_txt}]",
            expanded=(g_util >= 80),
        ):
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="color:#94a3b8; font-size:0.84rem;">Group Utilisation: <b>{g_util:.1f}%</b></span>
                    <span class="fc-badge {badge_cls}">{badge_txt}</span>
                </div>
                <div class="fc-bar-track"><div class="fc-bar-fill" style="width:{min(100.0, g_util):.1f}%; background:{bar_col};"></div></div>
                """,
                unsafe_allow_html=True,
            )
            for cat, sp, bd, ut in sorted(rows, key=lambda x: x[3], reverse=True):
                c1, c2, c3 = st.columns([2.6, 2.2, 1.1])
                with c1:
                    st.markdown(f"**{cat}**")
                    st.caption(f"{format_inr(sp)} / {format_inr(bd)}")
                with c2:
                    st.progress(min(ut / 100.0, 1.0))
                    st.caption(f"{ut:.0f}% used")
                with c3:
                    if st.button("View →", key=f"bud_view_{cat}", use_container_width=True):
                        ui.navigate_to("transactions", sub_tab="📅 Ledger", extra_state={"_ledger_cat_filter": cat})


def _render_budget_editor_fragment(current_user, user_family_id, view_mode: str, target_fy: str) -> None:
    """Single clean table editor + 3 quick presets (replaces old 125-button adjuster)."""
    suggested_df = data_layer.cached_get_suggested_budgets(
        fy=target_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )
    inc_df = data_layer.cached_get_income_sources_df(
        username=current_user["username"], family_id=user_family_id, view_mode=view_mode
    )
    default_inc = float(inc_df["monthly_equivalent"].sum()) if not inc_df.empty and "monthly_equivalent" in inc_df.columns else 100000.0
    if default_inc <= 0:
        default_inc = 100000.0

    # Map category -> group
    cat_to_group = {}
    for gname, gcats in CATEGORY_GROUPS.items():
        for gc in gcats:
            cat_to_group[gc] = gname

    draft_key = f"_budget_editor_draft_{target_fy}_{user_family_id}"
    if draft_key not in st.session_state:
        rows = []
        for _, r in suggested_df.iterrows():
            cat = r["category"]
            m_lim = float(r["monthly_limit"]) if float(r["monthly_limit"]) > 0 else float(r["suggested_monthly"])
            rows.append({
                "Group": cat_to_group.get(cat, "🗂 Other"),
                "Category": cat,
                "Hist. Avg (₹/mo)": round(float(r.get("hist_monthly_avg", 0.0)), 0),
                "Monthly Limit (₹)": round(m_lim, 0),
            })
        st.session_state[draft_key] = pd.DataFrame(rows)

    st.markdown("##### ⚡ Quick Budget Presets")
    p1, p2, p3, p4 = st.columns([1.4, 1.1, 1.1, 1.2])
    with p1:
        monthly_income = st.number_input("Monthly Income (₹)", min_value=0.0, value=float(default_inc), step=5000.0, key="bud_ed_income")
    with p2:
        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Match History", use_container_width=True, key="bud_pre_hist"):
            df_d = st.session_state[draft_key].copy()
            df_d["Monthly Limit (₹)"] = df_d["Hist. Avg (₹/mo)"]
            st.session_state[draft_key] = df_d
            st.rerun()
    with p3:
        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
        if st.button("🎯 80 / 20 Rule", use_container_width=True, key="bud_pre_8020"):
            prop_df = data_layer.cached_get_suggested_budgets(
                fy=target_fy, username=current_user["username"], view_mode=view_mode,
                target_total_monthly=monthly_income * 0.80, family_id=user_family_id,
            )
            prop_map = dict(zip(prop_df["category"], prop_df["suggested_monthly"]))
            df_d = st.session_state[draft_key].copy()
            df_d["Monthly Limit (₹)"] = df_d["Category"].map(
                lambda c: round(monthly_income * 0.20, 0) if c == "Insurance & Investments" else round(float(prop_map.get(c, 0.0)), 0)
            )
            st.session_state[draft_key] = df_d
            st.rerun()
    with p4:
        target_spend = st.number_input("Scale Target (₹/mo)", min_value=0.0, value=float(st.session_state[draft_key]["Monthly Limit (₹)"].sum()), step=5000.0, key="bud_pre_target")

    if st.button("📐 Scale All Categories to Target", key="bud_btn_scale"):
        df_d = st.session_state[draft_key].copy()
        cur_sum = float(df_d["Monthly Limit (₹)"].sum())
        if cur_sum > 0 and target_spend > 0:
            factor = target_spend / cur_sum
            df_d["Monthly Limit (₹)"] = (df_d["Monthly Limit (₹)"] * factor).round(0)
            st.session_state[draft_key] = df_d
            st.rerun()

    st.markdown("##### ✏️ Category Limits Table")
    df_display = st.session_state[draft_key].copy()
    df_display["Annual Cap (₹)"] = (df_display["Monthly Limit (₹)"] * 12.0).round(0)

    edited = st.data_editor(
        df_display,
        column_config={
            "Group": st.column_config.TextColumn("Group", disabled=True),
            "Category": st.column_config.TextColumn("Category", disabled=True),
            "Hist. Avg (₹/mo)": st.column_config.NumberColumn("Hist. Avg (₹/mo)", format="₹ %d", disabled=True),
            "Monthly Limit (₹)": st.column_config.NumberColumn("Monthly Limit (₹)", min_value=0.0, step=500.0, format="₹ %d", required=True),
            "Annual Cap (₹)": st.column_config.NumberColumn("Annual Cap (₹)", format="₹ %d", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key=f"bud_table_editor_{target_fy}",
    )

    total_m = float(edited["Monthly Limit (₹)"].sum())
    if monthly_income > 0 and total_m > monthly_income:
        st.warning(f"⚠️ Total monthly budget ({format_inr(total_m)}) exceeds monthly income ({format_inr(monthly_income)}).")
    else:
        st.caption(f"Total Monthly Allocation: **{format_inr(total_m)}** ({format_inr(total_m * 12)}/yr)")

    if st.button("💾 Save All Budgets", type="primary", use_container_width=True, key="bud_save_all"):
        records = [
            {
                "category": str(r["Category"]),
                "monthly_limit": float(r["Monthly Limit (₹)"] or 0.0),
                "annual_limit": float(r["Monthly Limit (₹)"] or 0.0) * 12.0,
            }
            for _, r in edited.iterrows()
        ]
        cnt = data_layer.batch_set_category_budgets(target_fy, records, family_id=user_family_id or 1)
        st.session_state["budget_dict"] = {r["category"]: r["monthly_limit"] for r in records}
        st.session_state["budget_dict"]["__income__"] = float(monthly_income)
        st.session_state.pop(draft_key, None)
        st.toast(f"✅ Saved {cnt} category budgets for {target_fy}!")
        st.rerun()


def _render_goals(user_family_id) -> None:
    goals_df = data_layer.cached_get_savings_goals(family_id=user_family_id or 1)

    gh1, gh2 = st.columns([3, 1.2])
    with gh1:
        st.markdown("#### 🏆 Savings Goals")
    with gh2:
        if st.button("➕ New Goal", type="primary", use_container_width=True, key="goal_btn_new"):
            _open_new_goal_dialog(user_family_id or 1)

    if goals_df.empty:
        if ui.render_empty_state(
            "🏆",
            "No savings goals yet",
            "Create a goal for your emergency fund, vacation, home down payment, or child's education.",
            cta_label="➕ Create First Goal",
            cta_key="goal_empty_new",
        ):
            _open_new_goal_dialog(user_family_id or 1)
        return

    goal_rows = list(goals_df.iterrows())
    for row_start in range(0, len(goal_rows), 2):
        gcols = st.columns(2)
        for col_idx, (_, goal) in enumerate(goal_rows[row_start : row_start + 2]):
            with gcols[col_idx]:
                pct = min(1.0, float(goal["current_saved"]) / float(goal["target_amount"])) if float(goal["target_amount"]) > 0 else 0.0
                bar_col = "#10b981" if pct >= 0.75 else ("#fbbf24" if pct >= 0.4 else "#38bdf8")
                t_date = f" · Target: {goal['target_date']}" if goal.get("target_date") else ""
                st.markdown(
                    f"""
                    <div class="fc-card">
                        <div style="font-weight:700; color:#f1f5f9; font-size:0.98rem;">{goal['goal_name']}</div>
                        <div style="display:flex; justify-content:space-between; margin:8px 0 4px;">
                            <span style="color:#34d399; font-weight:700;">{format_inr_short(float(goal['current_saved']))}</span>
                            <span style="color:#94a3b8; font-size:0.82rem;">of {format_inr_short(float(goal['target_amount']))}</span>
                        </div>
                        <div class="fc-bar-track"><div class="fc-bar-fill" style="width:{pct*100:.1f}%; background:{bar_col};"></div></div>
                        <div style="color:#64748b; font-size:0.75rem; margin-top:4px;">{int(pct*100)}% complete{t_date}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.popover("⚙️ Manage Goal", use_container_width=True):
                    c_amt = st.number_input("Add Contribution (₹)", min_value=0.0, step=1000.0, key=f"g_contrib_{goal['id']}")
                    if st.button("➕ Add Funds", type="primary", use_container_width=True, key=f"g_add_{goal['id']}"):
                        if c_amt > 0 and add_goal_contribution(int(goal["id"]), user_family_id or 1, c_amt):
                            data_layer.invalidate_data_cache()
                            st.toast(f"✅ Added {format_inr(c_amt)} to {goal['goal_name']}!")
                            st.rerun()
                    st.markdown("---")
                    if st.button("🗑️ Delete Goal", use_container_width=True, key=f"g_del_{goal['id']}"):
                        if delete_savings_goal(int(goal["id"]), user_family_id or 1):
                            data_layer.invalidate_data_cache()
                            st.toast(f"🗑️ Deleted goal '{goal['goal_name']}'.")
                            st.rerun()

