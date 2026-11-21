"""
Cached data access facade for FinCompass.
Wraps database reads with @st.cache_data(ttl=120) so page switches and widget interactions
avoid redundant Turso HTTP round-trips, while cleanly supporting Sandbox Mode and instant
cache invalidation on writes.
"""

import os
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

import database
from sandbox_data import (
    sandbox_get_expenses_df,
    sandbox_get_user_investments_df,
    sandbox_get_budget_status,
    mock_success,
)


def is_sandbox_mode() -> bool:
    return bool(st.session_state.get("is_sandbox_mode", False))


def invalidate_data_cache() -> None:
    """Clear cached database reads after any write mutation."""
    st.cache_data.clear()


def get_gemini_api_key(current_user: Optional[Dict[str, Any]] = None) -> str:
    """Resolve Gemini API key from user profile, admin profile, env, or secrets."""
    user_key = (current_user or {}).get("gemini_api_key") or ""
    if user_key:
        return user_key
    admin_key = cached_get_admin_gemini_api_key()
    if admin_key:
        return admin_key
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        return env_key
    try:
        return st.secrets.get("GEMINI_API_KEY", "") or ""
    except Exception:
        return ""


@st.cache_data(ttl=120, show_spinner=False)
def _cached_expenses_df(
    fy: Optional[str],
    category: Optional[str],
    username: Optional[str],
    view_mode: str,
    family_id: Optional[int],
    transaction_type: Optional[str],
) -> pd.DataFrame:
    return database.get_expenses_df(
        fy=fy,
        category=category,
        username=username,
        view_mode=view_mode,
        family_id=family_id,
        transaction_type=transaction_type,
    )


def get_expenses_df(
    fy: Optional[str] = None,
    category: Optional[str] = None,
    username: Optional[str] = None,
    view_mode: str = "Family",
    family_id: Optional[int] = 1,
    transaction_type: Optional[str] = "Expense",
) -> pd.DataFrame:
    if is_sandbox_mode():
        return sandbox_get_expenses_df(
            fy=fy,
            category=category,
            username=username,
            view_mode=view_mode,
            family_id=family_id,
            transaction_type=transaction_type,
        ).copy()
    return _cached_expenses_df(
        fy=fy,
        category=category,
        username=username,
        view_mode=view_mode,
        family_id=family_id,
        transaction_type=transaction_type,
    ).copy()


@st.cache_data(ttl=120, show_spinner=False)
def _cached_all_financial_years(
    username: Optional[str] = None,
    view_mode: str = "Family",
    family_id: Optional[int] = 1,
) -> List[str]:
    return database.get_all_financial_years(
        username=username, view_mode=view_mode, family_id=family_id
    )


def cached_get_all_financial_years(
    username: Optional[str] = None,
    view_mode: str = "Family",
    family_id: Optional[int] = 1,
) -> List[str]:
    if is_sandbox_mode():
        df = sandbox_get_expenses_df(
            fy="All FYs", username=username, view_mode=view_mode, family_id=family_id
        )
        if not df.empty and "financial_year" in df.columns:
            return sorted(df["financial_year"].dropna().unique().tolist(), reverse=True)
        return []
    return _cached_all_financial_years(
        username=username, view_mode=view_mode, family_id=family_id
    )


@st.cache_data(ttl=120, show_spinner=False)
def _cached_investments_df(
    username: Optional[str], family_id: Optional[int]
) -> pd.DataFrame:
    return database.get_user_investments_df(username=username, family_id=family_id)


def get_user_investments_df(
    username: Optional[str] = None, family_id: Optional[int] = 1
) -> pd.DataFrame:
    if is_sandbox_mode():
        return sandbox_get_user_investments_df(
            username=username or "sandbox_user", family_id=family_id
        ).copy()
    return _cached_investments_df(username=username, family_id=family_id).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_debts(family_id: Optional[int] = 1) -> pd.DataFrame:
    return database.get_debts(family_id=family_id or 1).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_income_sources_df(
    username: str,
    family_id: Optional[int] = None,
    view_mode: str = "Family",
) -> pd.DataFrame:
    return database.get_income_sources_df(
        username=username, family_id=family_id, view_mode=view_mode
    ).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_savings_goals(family_id: Optional[int] = 1) -> pd.DataFrame:
    return database.get_savings_goals(family_id=family_id or 1).copy()


@st.cache_data(ttl=120, show_spinner=False)
def _cached_budget_status(
    fy: str,
    username: Optional[str],
    view_mode: str,
    family_id: Optional[int],
) -> pd.DataFrame:
    return database.get_budget_status(
        fy=fy, username=username, view_mode=view_mode, family_id=family_id
    )


def get_budget_status(
    fy: str,
    username: Optional[str] = None,
    view_mode: str = "Family",
    family_id: Optional[int] = 1,
) -> pd.DataFrame:
    if is_sandbox_mode():
        return sandbox_get_budget_status(
            fy=fy, username=username, view_mode=view_mode, family_id=family_id
        ).copy()
    return _cached_budget_status(
        fy=fy, username=username, view_mode=view_mode, family_id=family_id
    ).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_suggested_budgets(
    fy: str,
    username: Optional[str] = None,
    view_mode: str = "Family",
    target_total_monthly: Optional[float] = None,
    family_id: Optional[int] = 1,
) -> pd.DataFrame:
    return database.get_suggested_budgets(
        fy=fy,
        username=username,
        view_mode=view_mode,
        target_total_monthly=target_total_monthly,
        family_id=family_id,
    ).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_category_breakdown(
    fy: Optional[str] = None,
    username: Optional[str] = None,
    view_mode: str = "Family",
    family_id: Optional[int] = 1,
    transaction_type: str = "Expense",
) -> pd.DataFrame:
    return database.get_category_breakdown(
        fy=fy,
        username=username,
        view_mode=view_mode,
        family_id=family_id,
        transaction_type=transaction_type,
    ).copy()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_all_families() -> List[Dict[str, Any]]:
    return database.get_all_families()


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_all_users(family_id: Optional[int] = 1) -> List[Dict[str, Any]]:
    return database.get_all_users(family_id=family_id)


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_portfolio_snapshots_deltas(
    family_id: int, current_value: float
) -> Dict[str, Dict[str, float]]:
    return database.get_portfolio_snapshots_deltas(family_id, current_value)


@st.cache_data(ttl=300, show_spinner=False)
def cached_get_admin_gemini_api_key() -> str:
    try:
        return database.get_admin_gemini_api_key() or ""
    except Exception:
        return ""


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_tax_deductions(
    username: str, family_id: int, financial_year: str = "2025-26"
) -> dict:
    return database.get_tax_deductions(username, family_id, financial_year)


@st.cache_data(ttl=120, show_spinner=False)
def cached_get_capital_gains(
    username: str, family_id: int, financial_year: str = "2025-26"
) -> dict:
    return database.get_capital_gains(username, family_id, financial_year)


def insert_expenses(*args, **kwargs) -> int:
    if is_sandbox_mode():
        mock_success(*args, **kwargs)
        return len(args[0]) if args and isinstance(args[0], list) else 1
    cnt = database.insert_expenses(*args, **kwargs)
    invalidate_data_cache()
    return cnt


def update_expenses_df(*args, **kwargs) -> int:
    if is_sandbox_mode():
        mock_success(*args, **kwargs)
        return 1
    cnt = database.update_expenses_df(*args, **kwargs)
    invalidate_data_cache()
    return cnt


def delete_expense(*args, **kwargs) -> None:
    if is_sandbox_mode():
        return
    database.delete_expense(*args, **kwargs)
    invalidate_data_cache()


def delete_multiple_expenses(*args, **kwargs) -> int:
    if is_sandbox_mode():
        return 0
    cnt = database.delete_multiple_expenses(*args, **kwargs)
    invalidate_data_cache()
    return cnt


def delete_month_expenses(*args, **kwargs) -> int:
    if is_sandbox_mode():
        return 0
    cnt = database.delete_month_expenses(*args, **kwargs)
    invalidate_data_cache()
    return cnt


def insert_investment(*args, **kwargs) -> int:
    if is_sandbox_mode():
        mock_success(*args, **kwargs)
        return 1
    res = database.insert_investment(*args, **kwargs)
    invalidate_data_cache()
    return res


def update_investments_df(*args, **kwargs) -> int:
    if is_sandbox_mode():
        mock_success(*args, **kwargs)
        return 1
    res = database.update_investments_df(*args, **kwargs)
    invalidate_data_cache()
    return res


def batch_insert_investments(*args, **kwargs) -> int:
    if is_sandbox_mode():
        mock_success(*args, **kwargs)
        return 1
    res = database.batch_insert_investments(*args, **kwargs)
    invalidate_data_cache()
    return res


def delete_investment(*args, **kwargs) -> bool:
    if is_sandbox_mode():
        return True
    res = database.delete_investment(*args, **kwargs)
    invalidate_data_cache()
    return res


def delete_all_investments(*args, **kwargs) -> int:
    if is_sandbox_mode():
        return 0
    res = database.delete_all_investments(*args, **kwargs)
    invalidate_data_cache()
    return res


def batch_set_category_budgets(*args, **kwargs) -> int:
    if is_sandbox_mode():
        return 0
    res = database.batch_set_category_budgets(*args, **kwargs)
    invalidate_data_cache()
    return res


def set_category_budget(*args, **kwargs) -> None:
    if is_sandbox_mode():
        return
    database.set_category_budget(*args, **kwargs)
    invalidate_data_cache()

