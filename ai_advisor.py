import os
import json
import streamlit as st
from typing import Dict, Any

def generate_financial_health_report(
    age: int,
    total_net_worth: float,
    total_debt: float,
    avg_monthly_spend: float,
    curr_monthly_spend: float,
    top_categories: dict,
    api_key: str
) -> str:
    """
    Calls the Gemini API to generate a personalized financial health and retirement summary.
    """
    if not api_key:
        return "⚠️ Gemini API key is missing. Please configure it in the Settings tab to generate this report."

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return "⚠️ Google GenAI SDK is not installed. Please run `pip install google-genai`."

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an expert, empathetic financial advisor. The user wants a summary of their financial health, specifically focusing on:
    1. Their ability to retire by age 60.
    2. Adherence to generally accepted norms (e.g., the 50/30/20 rule, debt-to-asset ratios).
    3. Actionable suggestions to improve savings and spending habits.

    Here is the user's current macro financial data:
    - Age: {age} (Years until 60: {max(0, 60 - age)})
    - Total Active Investments (Net Worth): ₹{total_net_worth:,.2f}
    - Total Outstanding Debt: ₹{total_debt:,.2f}
    - Average Monthly Spend: ₹{avg_monthly_spend:,.2f}
    - Current Month Spend: ₹{curr_monthly_spend:,.2f}
    - Top Spending Categories: {json.dumps(top_categories)}

    Please provide a concise, structured markdown report with the following sections:
    ### 🏥 Financial Health Overview
    (Assess their net worth vs debt, and comment on their average spending)

    ### 🏖️ Retirement by 60 Assessment
    (Given their current age of {age} and their net worth, how on-track are they? What should their target corpus roughly be to sustain their current average monthly spend of ₹{avg_monthly_spend:,.2f}?)

    ### 💡 Spending Habits & Saving Suggestions
    (Provide 3-4 concrete, actionable tips based on their top spending categories and macro numbers. Suggest a healthy savings rate they should target.)

    Keep the tone encouraging, realistic, and highly readable using emojis and bullet points where appropriate. DO NOT use raw HTML, stick to pure Markdown.
    """

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error generating report from Gemini: {str(e)}"
