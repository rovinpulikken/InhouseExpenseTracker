"""
Shared Mobile-First Design System, Global Scope Bar, Mobile Quick Bar,
and Global Add Transaction Dialog for FinCompass.
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

from config import (
    EXPENSE_CATEGORIES,
    format_inr,
    format_inr_short,
    get_indian_fy,
)
from categorizer import auto_categorize_description
import data_layer

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


def inject_global_styles() -> None:
    """Inject a single, cohesive mobile-first stylesheet across the entire app."""
    st.markdown(
        """
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <style>
            /* ── Base Layout & Spacing ─────────────────────────────── */
            header[data-testid="stHeader"] {
                background: rgba(11, 17, 32, 0.9) !important;
                backdrop-filter: blur(8px);
                border-bottom: 1px solid rgba(30, 41, 59, 0.7);
            }
            .block-container {
                padding-top: 3.6rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1240px;
            }
            /* ── Sidebar Navigation Always Expanded & High-Contrast ── */
            section[data-testid="stSidebar"] {
                background-color: #10192b !important;
                border-right: 1px solid #1e293b;
            }
            [data-testid="stSidebarNavItems"] {
                max-height: none !important;
            }
            [data-testid="stSidebarNavLink"] span,
            [data-testid="stSidebarNavSeparator"] {
                color: #e2e8f0 !important;
            }
            [data-testid="stSidebarNavLink"][aria-current="page"] {
                background: rgba(56, 189, 248, 0.16) !important;
                border-left: 3px solid #38bdf8 !important;
            }
            [data-testid="stSidebarNavLink"][aria-current="page"] span {
                color: #38bdf8 !important;
                font-weight: 700 !important;
            }
            /* ── Top Quick-Navigation Bar (Always Visible) ─────────── */
            div[data-testid="stElementContainer"]:has(.fc-qnav-marker),
            div[data-testid="element-container"]:has(.fc-qnav-marker) {
                display: none !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.fc-qnav-marker) {
                gap: 6px !important;
                align-items: center !important;
                margin-bottom: 6px !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.fc-qnav-marker) button {
                padding: 0.35rem 0.5rem !important;
                font-size: 0.85rem !important;
                font-weight: 600 !important;
                white-space: nowrap !important;
            }
            /* ── Unified Page Header ───────────────────────────────── */
            .fc-page-hdr {
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 8px;
                padding: 12px 16px;
                background: linear-gradient(135deg, #0f172a 0%, #162032 100%);
                border: 1px solid #1e293b;
                border-radius: 12px;
                margin-bottom: 14px;
            }
            .fc-page-hdr-title {
                font-size: 1.25rem;
                font-weight: 800;
                color: #f8fafc;
                margin: 0;
                line-height: 1.2;
            }
            .fc-page-hdr-sub {
                font-size: 0.82rem;
                color: #94a3b8;
                margin: 2px 0 0 0;
            }
            .fc-scope-badge {
                font-size: 0.76rem;
                font-weight: 600;
                color: #38bdf8;
                background: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.28);
                padding: 4px 10px;
                border-radius: 999px;
                white-space: nowrap;
            }
            /* ── Unified Responsive KPI Grid ───────────────────────── */
            .fc-kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }
            .fc-kpi-grid.cols-3 {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }
            .fc-kpi-grid.cols-2 {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .fc-kpi-card {
                background: linear-gradient(145deg, #162032 0%, #0f172a 100%);
                border: 1px solid #26354d;
                border-radius: 12px;
                padding: 14px 16px;
                min-width: 0;
            }
            .fc-kpi-label {
                font-size: 0.72rem;
                font-weight: 600;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .fc-kpi-value {
                font-size: 1.45rem;
                font-weight: 800;
                color: #f8fafc;
                margin-top: 4px;
                line-height: 1.15;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .fc-kpi-sub {
                font-size: 0.74rem;
                color: #64748b;
                margin-top: 3px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            /* ── Cards, Alerts & Badges ────────────────────────────── */
            .fc-card {
                background: #131d2f;
                border: 1px solid #243249;
                border-radius: 12px;
                padding: 14px 16px;
                margin-bottom: 10px;
            }
            .fc-tx-card {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                background: #131d2f;
                border: 1px solid #223047;
                border-radius: 10px;
                padding: 11px 14px;
                margin-bottom: 8px;
            }
            .fc-tx-title {
                font-size: 0.92rem;
                font-weight: 600;
                color: #f1f5f9;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .fc-tx-meta {
                font-size: 0.76rem;
                color: #94a3b8;
                margin-top: 2px;
            }
            .fc-tx-amt {
                font-size: 0.98rem;
                font-weight: 700;
                white-space: nowrap;
                text-align: right;
            }
            .fc-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.03em;
            }
            .fc-badge-ok { background: #064e3b; color: #6ee7b7; }
            .fc-badge-warn { background: #78350f; color: #fde047; }
            .fc-badge-over { background: #881337; color: #fecdd3; }
            .fc-badge-info { background: #0c4a6e; color: #7dd3fc; }
            .fc-empty {
                text-align: center;
                padding: 28px 20px;
                background: rgba(22, 32, 50, 0.6);
                border: 1px dashed #334155;
                border-radius: 12px;
                margin: 12px 0;
            }
            /* ── Progress Bar ──────────────────────────────────────── */
            .fc-bar-track {
                width: 100%;
                height: 8px;
                background: #1e293b;
                border-radius: 999px;
                overflow: hidden;
                margin: 6px 0;
            }
            .fc-bar-fill {
                height: 100%;
                border-radius: 999px;
            }
            /* ── Legacy Compatibility Classes ──────────────────────── */
            .dashboard-box {
                background-color: #131d2f;
                border-radius: 12px;
                padding: 16px;
                border: 1px solid #243249;
                margin-bottom: 14px;
            }
            .metric-card {
                background-color: #162032;
                border-radius: 10px;
                padding: 14px;
                border: 1px solid #26354d;
            }
            .metric-value { font-size: 1.45rem; font-weight: 700; color: #f8fafc; }
            .metric-label { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
            .surge-badge { background: #881337; color: #fecdd3; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem; }
            .normal-badge { background: #064e3b; color: #6ee7b7; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem; }

            /* ── Onboarding Tour & Navigation Help Components ──────── */
            .fc-tour-progress {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            }
            .fc-tour-dots {
                display: flex;
                gap: 7px;
                align-items: center;
            }
            .fc-tour-dot {
                width: 9px;
                height: 9px;
                border-radius: 999px;
                background: #334155;
                transition: all 0.2s ease;
            }
            .fc-tour-dot.active {
                width: 24px;
                background: #38bdf8;
            }
            .fc-tour-dot.done {
                background: #34d399;
            }
            .fc-tour-step-lbl {
                font-size: 0.78rem;
                color: #94a3b8;
                font-weight: 600;
            }
            .fc-tour-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
                margin: 10px 0 6px;
            }
            .fc-tour-card {
                background: #131d2f;
                border: 1px solid #243249;
                border-radius: 10px;
                padding: 12px 14px;
            }
            .fc-tour-card-title {
                font-size: 0.94rem;
                font-weight: 700;
                color: #f8fafc;
                margin-bottom: 4px;
            }
            .fc-tour-card-desc {
                font-size: 0.83rem;
                color: #cbd5e1;
                line-height: 1.4;
            }

            /* ── Mobile Responsive Overrides (<= 768px) ────────────── */
            @media screen and (max-width: 768px) {
                .block-container {
                    padding-left: 0.75rem !important;
                    padding-right: 0.75rem !important;
                    padding-top: 3.3rem !important;
                }
                .fc-tour-grid {
                    grid-template-columns: 1fr !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.fc-qnav-marker) {
                    flex-direction: row !important;
                    flex-wrap: wrap !important;
                    gap: 6px !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.fc-qnav-marker) > div[data-testid="stColumn"],
                div[data-testid="stHorizontalBlock"]:has(.fc-qnav-marker) > div[data-testid="column"] {
                    flex: 1 1 30% !important;
                    min-width: 96px !important;
                    width: auto !important;
                }
                .fc-kpi-grid,
                .fc-kpi-grid.cols-3 {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                    gap: 8px !important;
                }
                .fc-kpi-card {
                    padding: 11px 12px !important;
                }
                .fc-kpi-value {
                    font-size: 1.2rem !important;
                }
                .fc-page-hdr {
                    padding: 10px 12px !important;
                }
                .fc-page-hdr-title {
                    font-size: 1.08rem !important;
                }
                /* Ensure 44px minimum touch target on buttons */
                .stButton > button,
                .stDownloadButton > button {
                    min-height: 44px !important;
                }
                [data-testid="stTabs"] [role="tablist"] {
                    overflow-x: auto !important;
                    flex-wrap: nowrap !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(
    icon: str,
    title: str,
    subtitle: str = "",
    accent: str = "#38bdf8",
    badge: str = "",
    help_key: Optional[str] = None,
) -> None:
    """Render a single clean contextual header bar with an optional `❓ Guide` popover."""
    badge_html = f'<span class="fc-scope-badge">{badge}</span>' if badge else ""
    sub_html = f'<div class="fc-page-hdr-sub">{subtitle}</div>' if subtitle else ""
    hdr_html = f"""
        <div class="fc-page-hdr" style="border-left: 4px solid {accent};">
            <div>
                <div class="fc-page-hdr-title">{icon} {title}</div>
                {sub_html}
            </div>
            {badge_html}
        </div>
    """
    if help_key:
        import onboarding
        hc1, hc2 = st.columns([5.6, 1.0], vertical_alignment="center")
        with hc1:
            st.markdown(hdr_html, unsafe_allow_html=True)
        with hc2:
            onboarding.render_page_help_popover(help_key)
    else:
        st.markdown(hdr_html, unsafe_allow_html=True)


def render_kpi_grid(items: List[Dict[str, Any]], cols: int = 4) -> None:
    """
    Render a responsive KPI card grid (4 cols desktop -> 2x2 mobile).
    Each item: {"label", "value", "sub" (opt), "color" (opt), "accent" (opt)}
    """
    col_cls = f"cols-{cols}" if cols in (2, 3) else ""
    cards_html = []
    for item in items:
        label = item.get("label", "")
        val = item.get("value", "—")
        sub = item.get("sub", "")
        color = item.get("color", "#f8fafc")
        accent = item.get("accent")
        border_style = f"border-left: 3px solid {accent};" if accent else ""
        sub_html = f'<div class="fc-kpi-sub">{sub}</div>' if sub else ""
        cards_html.append(
            f'<div class="fc-kpi-card" style="{border_style}">'
            f'<div class="fc-kpi-label">{label}</div>'
            f'<div class="fc-kpi-value" style="color:{color};">{val}</div>'
            f'{sub_html}'
            f'</div>'
        )
    st.markdown(
        f'<div class="fc-kpi-grid {col_cls}">{"".join(cards_html)}</div>',
        unsafe_allow_html=True,
    )


def render_empty_state(
    icon: str,
    title: str,
    subtitle: str,
    cta_label: Optional[str] = None,
    cta_key: Optional[str] = None,
) -> bool:
    """Render a clean guided empty state card; returns True if the CTA button was clicked."""
    st.markdown(
        f"""
        <div class="fc-empty">
            <div style="font-size: 2rem; margin-bottom: 6px;">{icon}</div>
            <div style="font-size: 1rem; font-weight: 700; color: #f1f5f9;">{title}</div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cta_label:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            return st.button(cta_label, type="primary", use_container_width=True, key=cta_key)
    return False


def segmented_pills(
    label: str,
    options: List[str],
    key: str,
    default: Optional[str] = None,
) -> str:
    """Single-level sub-navigation selector using st.segmented_control with radio fallback."""
    chosen_default = default if default in options else options[0]
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state[key] = chosen_default

    if hasattr(st, "segmented_control"):
        val = st.segmented_control(
            label,
            options=options,
            default=st.session_state.get(key, chosen_default),
            key=key,
            label_visibility="collapsed",
        )
        return val if val in options else chosen_default

    idx = options.index(st.session_state.get(key, chosen_default))
    return st.radio(
        label,
        options=options,
        index=idx,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )


def get_active_user() -> Tuple[Dict[str, Any], Optional[int], bool]:
    """Return (current_user, user_family_id, is_super_admin) from session state."""
    current_user = st.session_state["user"]
    is_super_admin = (
        current_user.get("username") == "admin"
        or current_user.get("role") == "Super Admin"
    )
    user_family_id = st.session_state.get(
        "_active_family_id", current_user.get("family_id", 1)
    )
    return current_user, user_family_id, is_super_admin


def navigate_to(page_key: str, sub_tab: Optional[str] = None, extra_state: Optional[Dict[str, Any]] = None) -> None:
    """Programmatically navigate to a registered st.Page key with optional sub-page pre-selection."""
    if extra_state:
        for k, v in extra_state.items():
            st.session_state[k] = v
    if sub_tab:
        st.session_state[f"_nav_target_sub_{page_key}"] = sub_tab
    pages_map = st.session_state.get("_pages", {})
    target = pages_map.get(page_key)
    if target is not None:
        st.switch_page(target)


def consume_target_sub(page_key: str, valid_options: List[str], default: str) -> str:
    """Read and clear any pending deep-link sub-page selection."""
    pending_key = f"_nav_target_sub_{page_key}"
    pending = st.session_state.pop(pending_key, None)
    if pending in valid_options:
        return pending
    return default


def render_mobile_quick_bar(active_key: str) -> None:
    """
    Always-visible top quick-navigation pill bar across desktop and mobile.
    Highlights the active page and provides 1-tap access to core sections + Add Transaction.
    """
    pages_map = st.session_state.get("_pages", {})
    if not pages_map:
        return

    nav_items = [
        ("home", "🏠 Home", 1.0),
        ("transactions", "💸 Transactions", 1.35),
        ("budgets", "🎯 Budgets", 1.05),
        ("insights", "📊 Insights", 1.05),
        ("reports", "📑 Reports", 1.05),
        ("portfolio", "📈 Portfolio", 1.15),
    ]
    visible_items = [item for item in nav_items if item[0] in pages_map]
    if not visible_items:
        return

    weights = [w for _, _, w in visible_items] + [0.95]
    cols = st.columns(weights)
    for idx, (pkey, label, _) in enumerate(visible_items):
        with cols[idx]:
            if idx == 0:
                st.markdown('<span class="fc-qnav-marker" style="display:none;"></span>', unsafe_allow_html=True)
            is_active = (pkey == active_key)
            if st.button(
                label,
                key=f"qnav_{active_key}_{pkey}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                if not is_active:
                    navigate_to(pkey)
    with cols[-1]:
        if st.button(
            "➕ Add",
            key=f"qnav_{active_key}_add",
            type="primary",
            use_container_width=True,
            help="Log a new Expense or Income transaction",
        ):
            current_user, user_family_id, _ = get_active_user()
            open_add_transaction_dialog(current_user, user_family_id)


def render_scope_bar(
    current_user: Dict[str, Any],
    user_family_id: Optional[int],
    show_view: bool = True,
    show_fy: bool = True,
    show_month: bool = True,
    page_key: str = "global",
) -> Dict[str, Any]:
    """
    Single source of truth for View Mode, Financial Year, and Month across all pages.
    Stored in st.session_state["scope"] = {"view": ..., "fy": ..., "month": "YYYY-MM" | "All Months"}.
    """
    today = datetime.date.today()
    current_fy = get_indian_fy(today)
    current_mk = today.strftime("%Y-%m")

    if "scope" not in st.session_state:
        st.session_state["scope"] = {
            "view": "Family",
            "fy": current_fy,
            "month": current_mk,
        }

    scope = st.session_state["scope"]

    # Fetch available FYs & months cheaply from cache
    all_fys = data_layer.cached_get_all_financial_years(
        username=current_user["username"],
        view_mode=scope["view"],
        family_id=user_family_id,
    )
    fy_options = ["All FYs"] + all_fys
    if scope["fy"] not in fy_options:
        scope["fy"] = all_fys[0] if all_fys else "All FYs"

    # Derive available month keys (YYYY-MM) from cached transactions for the selected FY
    avail_month_keys: List[str] = []
    if show_month:
        all_tx = data_layer.get_expenses_df(
            fy="All FYs" if scope["fy"] == "All FYs" else scope["fy"],
            username=current_user["username"],
            view_mode=scope["view"],
            family_id=user_family_id,
            transaction_type="All",
        )
        mk_set = set()
        if scope["fy"] == "All FYs" or scope["fy"] == current_fy:
            mk_set.add(current_mk)
        if not all_tx.empty and "expense_date" in all_tx.columns:
            parsed = pd.to_datetime(all_tx["expense_date"], errors="coerce").dropna()
            for mk in parsed.dt.strftime("%Y-%m").unique():
                if mk and isinstance(mk, str):
                    mk_set.add(mk)
        avail_month_keys = sorted(list(mk_set), reverse=True)
        month_options = ["All Months"] + avail_month_keys
        if scope["month"] not in month_options:
            scope["month"] = avail_month_keys[0] if avail_month_keys else "All Months"
    else:
        month_options = ["All Months"]

    def _fmt_month(mk: str) -> str:
        if mk == "All Months":
            return "All Months"
        try:
            dt = datetime.datetime.strptime(mk, "%Y-%m")
            return dt.strftime("%b %Y")
        except Exception:
            return mk

    view_map = {"🏠 Family": "Family", "🔒 Private": "Private", "🌐 All": "All"}
    rev_view_map = {v: k for k, v in view_map.items()}

    # Build slim bar columns
    active_cols = []
    if show_view:
        active_cols.append("view")
    if show_fy:
        active_cols.append("fy")
    if show_month:
        active_cols.append("month")

    if active_cols:
        weights = []
        for c in active_cols:
            if c == "view":
                weights.append(1.2)
            elif c == "fy":
                weights.append(1.2)
            else:
                weights.append(2.2)
        cols = st.columns(weights)

        for col_obj, kind in zip(cols, active_cols):
            with col_obj:
                if kind == "view":
                    v_labels = list(view_map.keys())
                    cur_v_label = rev_view_map.get(scope["view"], "🏠 Family")
                    sel_v = st.selectbox(
                        "View",
                        v_labels,
                        index=v_labels.index(cur_v_label),
                        key=f"scope_view_{page_key}",
                        label_visibility="collapsed",
                    )
                    new_v = view_map[sel_v]
                    if new_v != scope["view"]:
                        scope["view"] = new_v
                        st.rerun()

                elif kind == "fy":
                    sel_fy = st.selectbox(
                        "Financial Year",
                        fy_options,
                        index=fy_options.index(scope["fy"]),
                        key=f"scope_fy_{page_key}",
                        label_visibility="collapsed",
                    )
                    if sel_fy != scope["fy"]:
                        scope["fy"] = sel_fy
                        scope["month"] = "All Months" if sel_fy != current_fy else current_mk
                        st.rerun()

                elif kind == "month":
                    mc_prev, mc_sel, mc_next = st.columns([0.55, 2.4, 0.55])
                    cur_m = scope["month"]
                    cur_idx = avail_month_keys.index(cur_m) if cur_m in avail_month_keys else -1

                    with mc_prev:
                        can_older = (cur_idx >= 0 and cur_idx < len(avail_month_keys) - 1)
                        if st.button("◀", key=f"scope_m_prev_{page_key}", disabled=not can_older, use_container_width=True, help="Older month"):
                            scope["month"] = avail_month_keys[cur_idx + 1]
                            st.rerun()
                    with mc_sel:
                        sel_m = st.selectbox(
                            "Month",
                            month_options,
                            index=month_options.index(cur_m) if cur_m in month_options else 0,
                            format_func=_fmt_month,
                            key=f"scope_m_sel_{page_key}",
                            label_visibility="collapsed",
                        )
                        if sel_m != scope["month"]:
                            scope["month"] = sel_m
                            st.rerun()
                    with mc_next:
                        can_newer = (cur_idx > 0)
                        if st.button("▶", key=f"scope_m_next_{page_key}", disabled=not can_newer, use_container_width=True, help="Newer month"):
                            scope["month"] = avail_month_keys[cur_idx - 1]
                            st.rerun()

    return {
        "view": scope["view"],
        "fy": scope["fy"],
        "month": scope["month"],
        "all_fys": all_fys,
        "avail_month_keys": avail_month_keys,
        "month_label": _fmt_month(scope["month"]),
    }


def filter_df_by_month(df: pd.DataFrame, month_key: str) -> pd.DataFrame:
    """Filter a transactions DataFrame to a YYYY-MM month_key (or return all if 'All Months')."""
    if df is None or df.empty or month_key == "All Months":
        return df if df is not None else pd.DataFrame()
    if "Month_Key" in df.columns:
        return df[df["Month_Key"] == month_key].copy()
    if "expense_date" in df.columns:
        dt_series = pd.to_datetime(df["expense_date"], errors="coerce")
        return df[dt_series.dt.strftime("%Y-%m") == month_key].copy()
    return df.copy()


def render_tx_card(row: Dict[str, Any]) -> None:
    """Render a compact, mobile-friendly transaction card."""
    desc = str(row.get("description") or "").strip() or str(row.get("category") or "Transaction")
    cat = str(row.get("category") or "Miscellaneous")
    t_type = str(row.get("transaction_type") or "Expense").strip().title()
    vis = str(row.get("visibility") or "Family")
    raw_dt = row.get("expense_date")
    try:
        dt_str = pd.to_datetime(raw_dt).strftime("%d %b %Y")
    except Exception:
        dt_str = str(raw_dt)[:10]
    amt = float(row.get("amount") or 0.0)
    is_inc = t_type.lower() == "income"
    amt_color = "#34d399" if is_inc else "#f8fafc"
    amt_prefix = "+" if is_inc else "−"
    icon = "💵" if is_inc else "💸"
    vis_dot = "🔒" if vis == "Private" else "🏠"

    st.markdown(
        f"""
        <div class="fc-tx-card">
            <div style="min-width: 0; flex: 1;">
                <div class="fc-tx-title">{icon} {desc}</div>
                <div class="fc-tx-meta">{dt_str} &middot; {cat} &middot; {vis_dot} {vis}</div>
            </div>
            <div class="fc-tx-amt" style="color: {amt_color};">{amt_prefix}{format_inr(amt)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# GLOBAL ADD TRANSACTION DIALOG (1-tap from anywhere)
# ---------------------------------------------------------------------------
_dialog_decorator = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


if _dialog_decorator is not None:

    @_dialog_decorator("➕ Add Transaction")
    def _add_tx_modal(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
        _render_add_tx_body(current_user, user_family_id)

else:

    def _add_tx_modal(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
        with st.expander("➕ Add Transaction", expanded=True):
            _render_add_tx_body(current_user, user_family_id)


def _render_add_tx_body(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
    tx_type = segmented_pills(
        "Transaction Type",
        ["💸 Expense", "💵 Income"],
        key="dlg_tx_type",
        default="💸 Expense",
    )
    is_income = "Income" in tx_type

    amount = st.number_input(
        "Amount (₹)",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
        key="dlg_tx_amt",
    )
    desc = st.text_input(
        "Description",
        placeholder="e.g. Swiggy dinner, D-Mart groceries, Monthly Salary",
        key="dlg_tx_desc",
    )

    if is_income:
        cat_opts = INCOME_CATEGORIES
        default_idx = 0
    else:
        cat_opts = EXPENSE_CATEGORIES
        predicted = auto_categorize_description(desc) if desc else EXPENSE_CATEGORIES[0]
        default_idx = cat_opts.index(predicted) if predicted in cat_opts else 0

    category = st.selectbox(
        "Category ✨" if (desc and not is_income) else "Category",
        cat_opts,
        index=default_idx,
        key="dlg_tx_cat",
    )

    c1, c2 = st.columns(2)
    with c1:
        # Default date: today, or 1st of currently viewed historical month if different
        default_dt = datetime.date.today()
        scope_month = st.session_state.get("scope", {}).get("month", "")
        if scope_month and scope_month != "All Months" and scope_month != default_dt.strftime("%Y-%m"):
            try:
                y, m = scope_month.split("-")
                default_dt = datetime.date(int(y), int(m), 1)
            except Exception:
                pass
        tx_date = st.date_input("Date", value=default_dt, key="dlg_tx_date")
    with c2:
        default_vis = "Private" if st.session_state.get("scope", {}).get("view") == "Private" else "Family"
        visibility = st.selectbox(
            "Visibility",
            ["Family", "Private"],
            index=0 if default_vis == "Family" else 1,
            key="dlg_tx_vis",
        )

    b1, b2 = st.columns(2)
    with b1:
        save_close = st.button("💾 Save", type="primary", use_container_width=True, key="dlg_tx_save")
    with b2:
        save_another = st.button("➕ Save & Add Another", use_container_width=True, key="dlg_tx_save_more")

    if save_close or save_another:
        if amount <= 0:
            st.warning("Please enter an amount greater than ₹ 0.")
            return
        t_clean = "Income" if is_income else "Expense"
        data_layer.insert_expenses(
            [
                {
                    "date": tx_date.isoformat(),
                    "category": category,
                    "description": desc.strip() or category,
                    "amount": float(amount),
                    "visibility": visibility,
                    "transaction_type": t_clean,
                }
            ],
            source="Quick Add Dialog",
            username=current_user["username"],
            visibility=visibility,
            family_id=user_family_id or 1,
        )
        st.toast(f"✅ Added {t_clean}: {format_inr(amount)} ({category})")
        if save_another:
            st.session_state["_reopen_add_tx"] = True
        else:
            st.session_state.pop("_reopen_add_tx", None)
        st.rerun()


def open_add_transaction_dialog(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
    """Trigger the global Add Transaction modal dialog."""
    _add_tx_modal(current_user, user_family_id)

