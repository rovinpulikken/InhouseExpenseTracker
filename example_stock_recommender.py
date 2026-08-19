"""
Example Python implementation demonstrating how to call the Stock Recommendation Prompt Engine
using Google Gemini API (or any LLM) and parse the structured JSON output.
"""

import os
import json
from stock_prompts import (
    BASE_STOCK_SYSTEM_PROMPT,
    get_financially_savvy_prompt,
    get_goal_driven_prompt,
    get_sector_deep_dive_prompt
)

def run_savvy_screener_example(api_key: str = None):
    # 1. Build prompt with user's customized parameters
    user_prompt = get_financially_savvy_prompt(
        market_cap_segment="Large & Mid Cap",
        sector="Banking & Financials",
        min_roce=16.0,
        min_roe=15.0,
        max_pe=25.0,
        max_debt_to_equity=0.8,
        min_profit_cagr_3yr=18.0,
        num_recommendations=2
    )

    print("=== FINANCIALLY SAVVY PROMPT GENERATED ===")
    print(user_prompt[:300] + "...\n")
    
    # 2. Call Gemini API if API key is present
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("💡 [Demo Mode] Add GEMINI_API_KEY to execute live LLM inference.")
        return

    from google import genai
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[BASE_STOCK_SYSTEM_PROMPT, user_prompt]
    )

    print("=== GEMINI RECOMMENDATION RESULT ===")
    print(response.text)

if __name__ == "__main__":
    run_savvy_screener_example()
