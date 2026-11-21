"""
Financial Academy Page — More Section.
Thin wrapper around financial_academy.render_financial_academy_tab().
"""

import streamlit as st
from financial_academy import render_financial_academy_tab
import data_layer
import ui


def render() -> None:
    current_user, _, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("academy")
    ui.render_page_header(
        "🎓",
        "Financial Academy",
        subtitle="Personalised assessments, interactive learning paths, and sandbox missions.",
        accent="#34d399",
    )
    render_financial_academy_tab(data_layer.get_gemini_api_key(current_user))

