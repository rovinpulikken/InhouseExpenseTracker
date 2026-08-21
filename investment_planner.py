"""
Investment & Wealth Portfolio Planner Engine.
Calculates age-adjusted asset allocation (Equity, Debt, Gold, Insurance),
SIP breakdown, compound wealth projections (5, 10, 15, 20 yrs), and Gemini AI advice.
"""

import os
from typing import Dict, Any, List, Tuple
import pandas as pd

BASE_STOCK_SYSTEM_PROMPT = """
You are a Senior Equity Research Analyst & Quantitative Portfolio Strategist specializing in the {country} Stock Market with deep expertise in fundamental valuation, technical momentum, corporate governance, and risk management.

Your objective is to provide objective, high-conviction, data-backed stock analysis and recommendations tailored to the user's specific financial parameters or return goals.

Key Rules:
1. Focus on {country} listed securities with healthy liquidity.
2. Enforce strict forensic checks: Avoid companies with high promoter pledge (>5%), auditor red flags, or severe debt traps.
3. Align all financial year metrics with the local Financial Year.
4. Provide structured, actionable, and realistic valuation targets and stop-losses.
5. Always output in valid format that can be used by the app.        
"""

def calculate_investment_plan(
    age: int,
    current_savings: float,
    monthly_investment_budget: float,
    monthly_expenses: float = 50000.0
) -> Dict[str, Any]:
    """
    Computes asset allocation percentages, monthly SIP breakdown,
    wealth projections, and emergency fund status.
    """
    age = max(18, min(85, int(age)))
    current_savings = max(0.0, float(current_savings))
    monthly_investment_budget = max(0.0, float(monthly_investment_budget))
    monthly_expenses = max(1000.0, float(monthly_expenses))

    # Rule of 110 for Age-Based Equity Allocation
    equity_pct = max(20.0, min(85.0, float(110 - age)))
    gold_pct = 10.0 if age < 60 else 15.0
    debt_pct = max(10.0, float(100.0 - equity_pct - gold_pct))

    # Reserve ~10% of monthly budget for Term / Health Insurance premium provisioning
    insurance_monthly = round(min(monthly_investment_budget * 0.10, 5000.0), 2)
    investable_sip_monthly = max(0.0, monthly_investment_budget - insurance_monthly)

    equity_sip = round(investable_sip_monthly * (equity_pct / 100.0), 2)
    debt_sip = round(investable_sip_monthly * (debt_pct / 100.0), 2)
    gold_sip = round(investable_sip_monthly * (gold_pct / 100.0), 2)

    # Historical Benchmark Expected CAGR Assumptions (Indian Markets)
    equity_cagr = 0.12  # 12% CAGR
    debt_cagr = 0.07    # 7% CAGR (PPF / EPF / Debt Mutual Funds)
    gold_cagr = 0.08    # 8% CAGR (Sovereign Gold Bonds / Gold ETF)

    blended_cagr = (equity_pct * equity_cagr + debt_pct * debt_cagr + gold_pct * gold_cagr) / 100.0

    # Compound Interest & Wealth Projections over 5, 10, 15, 20 Years
    projections = {}
    years_list = [5, 10, 15, 20]

    for yrs in years_list:
        n_months = yrs * 12
        r_monthly = blended_cagr / 12.0
        
        # Future value of lump sum savings
        fv_lump = current_savings * ((1 + r_monthly) ** n_months)
        
        # Future value of monthly SIP
        if r_monthly > 0:
            fv_sip = investable_sip_monthly * (((1 + r_monthly) ** n_months - 1) / r_monthly) * (1 + r_monthly)
        else:
            fv_sip = investable_sip_monthly * n_months

        total_fv = round(fv_lump + fv_sip, 2)
        total_invested = round(current_savings + (investable_sip_monthly * n_months), 2)
        wealth_gain = round(total_fv - total_invested, 2)

        projections[yrs] = {
            "years": yrs,
            "total_future_value": total_fv,
            "total_invested": total_invested,
            "wealth_gain": wealth_gain
        }

    # Emergency Fund Requirement: 6 months of monthly expenses
    req_emergency = monthly_expenses * 6.0
    emergency_status = "Sufficient" if current_savings >= req_emergency else "Deficit"
    emergency_gap = max(0.0, req_emergency - current_savings)

    # Detailed Instrument Breakdown
    sip_instruments = [
        {
            "asset_class": "🚀 Equity Mutual Funds",
            "allocation_pct": f"{equity_pct:.0f}%",
            "monthly_sip": equity_sip,
            "recommended_instruments": "Nifty 50 Index Fund (50%), Flexi Cap Fund (30%), Midcap Fund (20%)"
        },
        {
            "asset_class": "🛡️ Debt & Fixed Income",
            "allocation_pct": f"{debt_pct:.0f}%",
            "monthly_sip": debt_sip,
            "recommended_instruments": "Public Provident Fund (PPF), EPF Voluntary, Corporate Bond / Liquid Funds"
        },
        {
            "asset_class": "🪙 Sovereign Gold / SGB",
            "allocation_pct": f"{gold_pct:.0f}%",
            "monthly_sip": gold_sip,
            "recommended_instruments": "Sovereign Gold Bonds (SGB) via RBI / Gold ETFs"
        },
        {
            "asset_class": "🚑 Insurance Shield Cover",
            "allocation_pct": "Protection",
            "monthly_sip": insurance_monthly,
            "recommended_instruments": "Pure Term Life Insurance (15-20x annual income) + Family Health Super Top-Up"
        }
    ]

    return {
        "age": age,
        "current_savings": current_savings,
        "monthly_investment_budget": monthly_investment_budget,
        "investable_sip_monthly": investable_sip_monthly,
        "insurance_monthly": insurance_monthly,
        "equity_pct": equity_pct,
        "debt_pct": debt_pct,
        "gold_pct": gold_pct,
        "blended_cagr_pct": round(blended_cagr * 100.0, 2),
        "equity_sip": equity_sip,
        "debt_sip": debt_sip,
        "gold_sip": gold_sip,
        "projections": projections,
        "req_emergency": req_emergency,
        "emergency_status": emergency_status,
        "emergency_gap": emergency_gap,
        "sip_instruments": sip_instruments
    }

def generate_ai_wealth_advice(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates personalized wealth strategy and milestone advisory using Gemini AI (with fallback).
    """
    if not plan:
        return {"summary": "No investment plan data provided.", "key_takeaways": []}

    # 1. Try Gemini AI Generation first
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass

        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Act as a Senior Certified Financial Planner (CFP) for Indian Personal Wealth Management.
            Analyze this user profile:
            - Age: {plan['age']}
            - Current Accumulated Savings: ₹ {plan['current_savings']:,}
            - Monthly Investment SIP Budget: ₹ {plan['investable_sip_monthly']:,}
            - Age-Based Asset Allocation: {plan['equity_pct']:.0f}% Equity, {plan['debt_pct']:.0f}% Debt, {plan['gold_pct']:.0f}% Gold
            - 10-Year Projected Corpus: ₹ {plan['projections'][10]['total_future_value']:,}
            - 20-Year Projected Corpus: ₹ {plan['projections'][20]['total_future_value']:,}
            - Emergency Fund Status: {plan['emergency_status']} (Gap: ₹ {plan['emergency_gap']:,})

            Provide strategic, actionable advice tailored for an Indian investor.
            Return a JSON object with keys:
            - 'summary': high level overview paragraph
            - 'key_takeaways': list of 4 bullet string suggestions on asset allocation, tax efficiency (80C, 10(10D), LTCG), emergency fund, and retirement goal.
            """
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            if response and response.text:
                import json
                cleaned = response.text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                return parsed
    except Exception:
        pass

    # 2. Intelligent Fallback Advisory Engine
    em_msg = "Your current savings fulfill this safety buffer!" if plan['emergency_status'] == 'Sufficient' else f"Prioritize assigning ₹ {int(plan['emergency_gap']):,} into Liquid Funds / High-Yield Savings before aggressive equity expansion."
    
    takeaways = [
        f"🎯 **Asset Allocation**: At age {plan['age']}, maintain a **{plan['equity_pct']:.0f}% Equity** and **{plan['debt_pct']:.0f}% Debt** split to balance high long-term growth with capital stability.",
        f"💰 **SIP Compounding Power**: Investing ₹ {int(plan['investable_sip_monthly']):,}/month can grow your wealth to **₹ {int(plan['projections'][10]['total_future_value']):,}** in 10 years and **₹ {int(plan['projections'][20]['total_future_value']):,}** in 20 years!",
        f"🏦 **Emergency Reserve**: Your target emergency fund is ₹ {int(plan['req_emergency']):,}. {em_msg}",
        "🛡️ **Risk & Tax Optimization**: Utilize PPF / EPF for tax-free fixed returns under 80C, and ensure pure term insurance cover equal to at least 15x your annual expenses."
    ]

    return {
        "summary": f"Based on your age ({plan['age']}) and monthly investment budget of ₹ {int(plan['investable_sip_monthly']):,}, your wealth plan is optimized for an expected ~{plan['blended_cagr_pct']}% blended CAGR.",
        "key_takeaways": takeaways
    }

def generate_ai_portfolio_suggestions(holdings_df: Any) -> Dict[str, Any]:
    """
    Generates AI suggestions for active portfolio holdings across platforms and investment types.
    Uses Google Gemini AI (with fallback to an intelligent rule engine).
    """
    if holdings_df is None or holdings_df.empty:
        return {
            "summary": "No active holdings found in your portfolio. Add assets to get AI recommendations.",
            "recommendations": []
        }

    total_invested = float(holdings_df["investment_amount"].sum()) if "investment_amount" in holdings_df.columns else 0.0
    total_current = float(holdings_df["current_value"].sum()) if "current_value" in holdings_df.columns else 0.0
    total_gain = total_current - total_invested
    overall_return_pct = round((total_gain / total_invested) * 100.0, 2) if total_invested > 0 else 0.0

    by_type = holdings_df.groupby("investment_type")["current_value"].sum().to_dict() if "investment_type" in holdings_df.columns else {}
    by_platform = holdings_df.groupby("platform")["current_value"].sum().to_dict() if "platform" in holdings_df.columns else {}

    holdings_summary = holdings_df[["platform", "investment_type", "investment_amount", "current_value", "year_invested"]].to_dict("records")

    # 1. Try Gemini AI generation
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass

        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Act as an expert Indian Wealth Manager and Portfolio Analyst.
            Analyze the user's active holdings:
            - Total Invested Capital: ₹ {total_invested:,}
            - Current Portfolio Value: ₹ {total_current:,} (Unrealized Gain: ₹ {total_gain:,}, Overall Return: {overall_return_pct}%)
            - Asset Breakdown by Type: {by_type}
            - Platform Distribution: {by_platform}
            - Individual Holdings: {holdings_summary}

            Provide actionable, smart suggestions for:
            1. Platform & Broker Risk Concentration
            2. Asset Class Balance (Equity, Mutual Funds, EPF, PPF, Startup, etc.)
            3. Tax Efficiency (Section 80C, LTCG ₹1.25L exemption, Debt taxation)
            4. Rebalancing & Profit Booking Advice

            Format response as JSON with keys:
            - 'summary': string summary paragraph
            - 'recommendations': list of objects with 'title', 'observation', 'suggestion'
            """
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            if response and response.text:
                import json
                cleaned = response.text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                return parsed
    except Exception:
        pass

    # 2. Rule-based Fallback Suggestions
    recs = []

    if by_type:
        max_type = max(by_type, key=by_type.get)
        max_type_val = by_type[max_type]
        type_pct = (max_type_val / total_current) * 100.0 if total_current > 0 else 0
        if type_pct > 60:
            recs.append({
                "title": f"⚠️ Asset Type Concentration in {max_type}",
                "observation": f"{max_type} comprises {type_pct:.1f}% (₹ {int(max_type_val):,}) of your total portfolio.",
                "suggestion": f"Consider diversifying incremental monthly SIPs into complementary asset classes (e.g. PPF/EPF for fixed income or Index Funds for broad equity exposure)."
            })

    if len(by_platform) == 1:
        plat_name = list(by_platform.keys())[0]
        recs.append({
            "title": f"📌 Platform Concentration ({plat_name})",
            "observation": f"All holdings are centralized on a single platform ({plat_name}).",
            "suggestion": "While convenient, consider holding long-term debt or government instruments (SGB, PPF, Post Office NSC) directly with primary institutions or secondary demat brokers."
        })

    tax_types = [t for t in by_type.keys() if t in ["EPF", "PPF", "NSC", "KVP"]]
    if not tax_types:
        recs.append({
            "title": "🛡️ Tax-Deferred Fixed Income Gap (Section 80C)",
            "observation": "No active EPF, PPF, NSC, or KVP holdings detected in your portfolio.",
            "suggestion": "Evaluate opening a PPF or increasing Voluntary EPF (VPF) to lock in tax-free 7.1%+ returns under Section 80C."
        })
    else:
        recs.append({
            "title": "🎉 Healthy Tax-Saving Fixed Income Allocation",
            "observation": f"Actively holding tax-advantaged instruments: {', '.join(tax_types)}.",
            "suggestion": "Maintain disciplined annual contributions to maximize compounding."
        })

    if overall_return_pct > 15:
        recs.append({
            "title": f"🚀 Strong Portfolio Returns ({overall_return_pct}%)",
            "observation": f"Your overall portfolio has generated +₹ {int(total_gain):,} in unrealized gains.",
            "suggestion": "Review long-term vs short-term holdings to optimize LTCG tax harvesting (₹ 1.25 Lakh tax-free threshold annually)."
        })

    return {
        "summary": f"Your portfolio of **{len(holdings_df)}** holding(s) is valued at **₹ {int(total_current):,}** with an overall return of **{overall_return_pct}%**.",
        "recommendations": recs
    }

def analyze_portfolio_segments(holdings_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Groups portfolio by asset class, market cap, and sector.
    """
    if holdings_df is None or holdings_df.empty:
        return {"asset_class": {}, "market_cap": {}, "sector": {}}

    # Fill NaNs for new columns
    if "market_cap" not in holdings_df.columns: holdings_df["market_cap"] = "Unknown"
    if "sector_segment" not in holdings_df.columns: holdings_df["sector_segment"] = "Unknown"

    holdings_df["market_cap"] = holdings_df["market_cap"].fillna("Unknown")
    holdings_df["sector_segment"] = holdings_df["sector_segment"].fillna("Unknown")

    total_value = holdings_df["current_value"].sum()
    if total_value <= 0:
         return {"asset_class": {}, "market_cap": {}, "sector": {}}

    def _get_percentages(groupby_col):
        grouped = holdings_df.groupby(groupby_col)["current_value"].sum()
        pcts = (grouped / total_value) * 100
        return pcts.round(2).to_dict()

    return {
        "asset_class": _get_percentages("investment_type"),
        "market_cap": _get_percentages("market_cap"),
        "sector": _get_percentages("sector_segment")
    }

def calculate_asset_allocation_drift(current_segments: Dict[str, Any], target_allocation: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Compares current asset class allocation against target allocation.
    Returns a list of drift details for rebalancing.
    """
    asset_class_actual = current_segments.get("asset_class", {})
    drifts = []

    # Ensure all target keys are evaluated
    all_keys = set(asset_class_actual.keys()).union(set(target_allocation.keys()))
    
    for key in all_keys:
        actual = asset_class_actual.get(key, 0.0)
        target = target_allocation.get(key, 0.0)
        drift = actual - target
        action = "Rebalance: Sell" if drift > 5.0 else ("Rebalance: Buy" if drift < -5.0 else "Hold")
        
        drifts.append({
            "asset_class": key,
            "actual_pct": round(actual, 2),
            "target_pct": round(target, 2),
            "drift_pct": round(drift, 2),
            "action": action
        })
    return drifts

def generate_ai_segment_advisory(segments: Dict[str, Any], risk_profile: str) -> str:
    """
    Generates AI advisory on the portfolio's segment diversification and risk profile alignment.
    """
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass

        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Act as an expert Indian Wealth Manager. Analyze this portfolio segmentation:
            - Risk Profile: {risk_profile}
            - Asset Classes: {segments['asset_class']}
            - Market Cap Spread: {segments['market_cap']}
            - Sector Exposure: {segments['sector']}
            
            Provide a concise 2-3 paragraph analysis of the diversification. Is it aligned with a {risk_profile} risk profile? 
            What are the potential concentration risks and what sectors/market caps should the user consider adding?
            Keep the tone professional and actionable.
            """
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            if response and response.text:
                return response.text
    except Exception as e:
        print(f"Error in AI segment advisory: {e}")
        pass
    
    return f"Your portfolio is heavily invested in {list(segments['asset_class'].keys())[:2] if segments['asset_class'] else 'various assets'}. Ensure this matches your {risk_profile} risk tolerance and consider diversifying across missing sectors."

def fetch_index_historical_cagr(ticker: str, years: int) -> float:
    """
    Fetches historical market data for the given index ticker using yfinance
    and calculates the CAGR over the specified number of years.
    Returns the CAGR as a decimal (e.g. 0.12 for 12%).
    """
    import yfinance as yf
    from datetime import datetime, timedelta

    end_date = datetime.now()
    # Add a buffer to ensure we get trading days
    start_date = end_date - timedelta(days=(years * 365) + 30)
    
    try:
        data = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False)
        if data.empty:
            return 0.12 # Fallback
            
        # Get the first price around 'years' ago
        target_start_date = end_date - timedelta(days=years * 365)
        
        # Find the closest date in the index
        closest_start_idx = data.index.get_indexer([target_start_date], method='nearest')[0]
        start_price = float(data.iloc[closest_start_idx]['Close'])
        end_price = float(data.iloc[-1]['Close'])
        
        if start_price <= 0:
            return 0.12
            
        cagr = ((end_price / start_price) ** (1 / years)) - 1
        return round(cagr, 4)
    except Exception as e:
        print(f"Error fetching yfinance data for {ticker}: {e}")
        return 0.12 # Fallback to standard 12%

def calculate_retirement_corpus(current_age: int, retirement_age: int, current_savings: float, monthly_sip: float, cagr_decimal: float, one_time_expenses: List[Dict[str, Any]] = None, additional_monthly_expense: float = 0.0) -> Dict[str, Any]:
    """
    Calculates the projected retirement corpus based on current age and savings, accounting for expenses.
    """
    if one_time_expenses is None:
        one_time_expenses = []

    years = max(1, retirement_age - current_age)
    n_months = years * 12
    r_monthly = cagr_decimal / 12.0
    
    # Future value of lump sum savings
    fv_lump = current_savings * ((1 + r_monthly) ** n_months)
    
    # Future value of monthly SIP
    if r_monthly > 0:
        fv_sip = monthly_sip * (((1 + r_monthly) ** n_months - 1) / r_monthly) * (1 + r_monthly)
        fv_recurring_exp = additional_monthly_expense * (((1 + r_monthly) ** n_months - 1) / r_monthly) * (1 + r_monthly)
    else:
        fv_sip = monthly_sip * n_months
        fv_recurring_exp = additional_monthly_expense * n_months

    # Future value of one time expenses
    fv_one_time_total = 0.0
    total_one_time_invested_reduction = 0.0
    for exp in one_time_expenses:
        exp_age = exp.get("age", current_age)
        exp_amount = exp.get("amount", 0.0)
        
        # Only consider expenses that occur between current age and retirement age
        if current_age <= exp_age <= retirement_age:
            months_from_now = (exp_age - current_age) * 12
            months_to_compound = max(0, n_months - months_from_now)
            fv_exp = exp_amount * ((1 + r_monthly) ** months_to_compound)
            fv_one_time_total += fv_exp
            total_one_time_invested_reduction += exp_amount

    total_fv = round(fv_lump + fv_sip - fv_recurring_exp - fv_one_time_total, 2)
    # Ensure total_fv does not drop below 0
    total_fv = max(0.0, total_fv)

    total_invested = round(current_savings + (monthly_sip * n_months) - (additional_monthly_expense * n_months) - total_one_time_invested_reduction, 2)
    wealth_gain = round(total_fv - total_invested, 2)

    # 4% Safe Withdrawal Rate (SWR) monthly
    swr_monthly = round((total_fv * 0.04) / 12.0, 2)

    return {
        "years_to_retirement": years,
        "total_future_value": total_fv,
        "total_invested": total_invested,
        "wealth_gain": wealth_gain,
        "safe_monthly_withdrawal": swr_monthly,
        "cagr_used_pct": round(cagr_decimal * 100.0, 2)
    }

def generate_ai_retirement_advisory(retirement_plan: Dict[str, Any], holdings_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generates AI suggestions for retirement using the calculated corpus and the user's active holdings.
    """
    total_current = float(holdings_df["current_value"].sum()) if holdings_df is not None and not holdings_df.empty and "current_value" in holdings_df.columns else 0.0
    
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass

        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Act as an expert Indian Retirement Planner. Analyze this profile:
            - Years to Retirement: {retirement_plan['years_to_retirement']}
            - Current Portfolio Value: ₹ {total_current:,}
            - Expected CAGR: {retirement_plan['cagr_used_pct']}%
            - Projected Corpus at Retirement: ₹ {retirement_plan['total_future_value']:,}
            - Safe Monthly Withdrawal (4% rule): ₹ {retirement_plan['safe_monthly_withdrawal']:,}

            Provide a highly actionable retirement strategy. 
            Format response as JSON with keys:
            - 'summary': string summary paragraph assessing if the corpus is healthy.
            - 'key_takeaways': list of 4 bullet points focusing on inflation impact, asset shifting near retirement (equity to debt glide path), tax-free withdrawal strategies, and SWP (Systematic Withdrawal Plan) structure.
            """
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            if response and response.text:
                import json
                cleaned = response.text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                return parsed
    except Exception as e:
        print(f"AI retirement advisory failed: {e}")
        pass

    return {
        "summary": f"Your projected retirement corpus is ₹ {int(retirement_plan['total_future_value']):,}, yielding a safe monthly withdrawal of ₹ {int(retirement_plan['safe_monthly_withdrawal']):,}.",
        "key_takeaways": [
            "Consider inflation: ₹1 today will lose purchasing power over the years to your retirement.",
            "Start shifting your portfolio from Equity to Debt 3-5 years before your retirement date to protect your capital from market volatility.",
            "Use a Systematic Withdrawal Plan (SWP) for tax-efficient monthly income.",
            "Maximize your EPF and PPF contributions as they provide tax-free compounding."
        ]
    }


# ============================================================
# SMART INVESTMENT ADVISOR — NEW FUNCTIONS
# ============================================================

ADVISORY_DISCLAIMER = (
    "\u26a0\ufe0f **Advisory Disclaimer**: All recommendations are generated for informational purposes only "
    "and do not constitute financial advice. Trend signals are based on historical price data and "
    "technical indicators (SMA crossovers, momentum). Past performance is not a guarantee of "
    "future returns. Please consult a SEBI-registered financial advisor before making investment decisions."
)

# Country-specific curated instrument universe
COUNTRY_UNIVERSE: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "India": {
        "equity": [
            {"name": "Reliance Industries Ltd", "type": "Stock", "rationale": "Largest Indian conglomerate with deep moats in energy, retail, and telecom.", "risk": "Moderate"},
            {"name": "HDFC Bank Ltd", "type": "Stock", "rationale": "Leading private sector bank with consistent growth and strong asset quality.", "risk": "Moderate"},
            {"name": "Tata Motors Ltd", "type": "Stock", "rationale": "Market leader in the Indian EV transition with strong legacy CV business.", "risk": "High"},
            {"name": "Nifty 50 Index Fund", "type": "MF", "rationale": "Broad large-cap exposure, lowest cost, tracks India's top 50 companies.", "risk": "Moderate"},
            {"name": "Mirae Asset Flexi Cap Fund", "type": "MF", "rationale": "Actively managed across large/mid/small caps, consistently top-rated.", "risk": "Moderate-High"},
            {"name": "Parag Parikh Flexi Cap Fund", "type": "MF", "rationale": "Diversified across India + global equities; defensive moat.", "risk": "Moderate"},
            {"name": "HDFC Mid Cap Opportunities Fund", "type": "MF", "rationale": "Strong mid-cap exposure for aggressive investors with 5+ yr horizon.", "risk": "High"},
            {"name": "Motilal Oswal Nasdaq 100 FOF", "type": "MF", "rationale": "US tech exposure via Indian MF wrapper; USD hedging opportunity.", "risk": "High"},
        ],
        "debt": [
            {"name": "SBI Liquid Fund", "type": "MF", "rationale": "Safest parking for short-term funds, near-instant redemption, ~7% return.", "risk": "Low"},
            {"name": "ICICI Pru Corporate Bond Fund", "type": "MF", "rationale": "AA+ rated corporate bonds, 2-3 yr horizon, better than FD post-tax.", "risk": "Low-Moderate"},
            {"name": "Public Provident Fund (PPF)", "type": "Govt", "rationale": "Tax-free 7.1% return, backed by GoI, 15-yr lock-in. Best for 80C.", "risk": "Very Low"},
            {"name": "EPF Voluntary Contribution (VPF)", "type": "Govt", "rationale": "8.15% tax-free return, 80C eligible — highest risk-free return in India.", "risk": "Very Low"},
        ],
        "gold": [
            {"name": "Sovereign Gold Bond (SGB)", "type": "Govt", "rationale": "2.5% annual interest + gold price appreciation + capital gains exemption on maturity.", "risk": "Low-Moderate"},
            {"name": "Nippon India Gold ETF", "type": "ETF", "rationale": "Liquid real-time gold exposure without physical storage risk.", "risk": "Moderate"},
        ],
        "tax_saving": [
            {"name": "Mirae Asset ELSS Tax Saver", "type": "ELSS", "rationale": "80C deduction up to Rs1.5L, lowest 3-yr lock-in, equity upside.", "risk": "Moderate-High"},
            {"name": "Axis Long Term Equity (ELSS)", "type": "ELSS", "rationale": "Consistent long-term performer, 80C eligible.", "risk": "Moderate-High"},
        ]
    },
    "United States": {
        "equity": [
            {"name": "Microsoft Corp (MSFT)", "type": "Stock", "rationale": "Enterprise software and cloud computing powerhouse with strong AI integration.", "risk": "Moderate"},
            {"name": "Apple Inc (AAPL)", "type": "Stock", "rationale": "Consumer tech giant with massive free cash flow and sticky ecosystem.", "risk": "Moderate"},
            {"name": "NVIDIA Corp (NVDA)", "type": "Stock", "rationale": "Undisputed leader in AI hardware and data center GPUs.", "risk": "High"},
            {"name": "Vanguard S&P 500 ETF (VOO)", "type": "ETF", "rationale": "Cheapest S&P 500 tracker (0.03% expense ratio), essential core holding.", "risk": "Moderate"},
            {"name": "iShares Russell 2000 ETF (IWM)", "type": "ETF", "rationale": "Small-cap diversification for higher growth potential over long horizon.", "risk": "High"},
            {"name": "Invesco QQQ (NASDAQ-100)", "type": "ETF", "rationale": "Top 100 NASDAQ tech giants; high-growth but concentrated sector risk.", "risk": "High"},
        ],
        "debt": [
            {"name": "Vanguard Total Bond Market ETF (BND)", "type": "ETF", "rationale": "Diversified US bond exposure, stability ballast for equity-heavy portfolios.", "risk": "Low"},
            {"name": "iShares TIPS Bond ETF (TIP)", "type": "ETF", "rationale": "Inflation-protected US Treasury bonds.", "risk": "Low"},
        ],
        "gold": [
            {"name": "SPDR Gold MiniShares ETF (GLDM)", "type": "ETF", "rationale": "Low-cost physical gold backed ETF, effective inflation hedge.", "risk": "Moderate"},
        ],
        "tax_saving": [
            {"name": "Maximize 401(k) Contributions", "type": "Tax-Advantaged", "rationale": "Pre-tax contributions reduce W2 taxable income. $23,000 annual limit (2024).", "risk": "N/A"},
            {"name": "Roth IRA Contribution", "type": "Tax-Advantaged", "rationale": "After-tax contributions grow tax-free. $7,000 limit (2024).", "risk": "N/A"},
        ]
    },
    "UAE": {
        "equity": [
            {"name": "iShares MSCI World ETF (IWDA)", "type": "ETF", "rationale": "Diversified global equity across 23 developed markets.", "risk": "Moderate"},
            {"name": "Vanguard FTSE All-World ETF (VWRA)", "type": "ETF", "rationale": "Most comprehensive global equity ETF for UAE-based investors.", "risk": "Moderate"},
        ],
        "debt": [
            {"name": "iShares Global Aggregate Bond ETF (AGGG)", "type": "ETF", "rationale": "Global investment-grade bonds; stability buffer.", "risk": "Low"},
        ],
        "gold": [
            {"name": "SPDR Gold Shares (GLD)", "type": "ETF", "rationale": "Standard international gold ETF; accessible from UAE.", "risk": "Moderate"},
        ],
        "tax_saving": [
            {"name": "No Income Tax in UAE", "type": "Info", "rationale": "UAE has no personal income tax. Focus on NPS/PPF if NRI and plan DTAA implications.", "risk": "N/A"},
        ]
    }
}

# Target allocation by risk profile (% of total portfolio)
TARGET_ALLOCATION: Dict[str, Dict[str, float]] = {
    "Conservative": {"Equity": 30.0, "Debt": 55.0, "Gold": 10.0, "Other/Cash": 5.0},
    "Moderate":     {"Equity": 55.0, "Debt": 30.0, "Gold": 10.0, "Other/Cash": 5.0},
    "Aggressive":   {"Equity": 75.0, "Debt": 15.0, "Gold":  5.0, "Other/Cash": 5.0},
}

ASSET_CLASS_MAP = {
    "Equity (Stocks)": "Equity",
    "Mutual funds": "Equity",
    "Structured funds": "Equity",
    "Gold / Sovereign Gold Bonds (SGB)": "Gold",
    "EPF": "Debt",
    "PPF": "Debt",
    "NSC (National Savings Certificate)": "Debt",
    "KVP (Kisan Vikas Patra)": "Debt",
    "Fixed Deposits / Recurring Deposits": "Debt",
    "Startup investments": "Other/Cash",
    "Real Estate": "Other/Cash",
}


def _map_asset_class(investment_type: str) -> str:
    for key, cls in ASSET_CLASS_MAP.items():
        if key.lower() in investment_type.lower():
            return cls
    return "Other/Cash"


def _pct_to_inr(pct: float, total: float) -> str:
    val = (pct / 100.0) * total
    if val >= 10000000:
        return f"Rs{val/10000000:.2f} Cr"
    elif val >= 100000:
        return f"Rs{val/100000:.2f} L"
    return f"Rs{val:,.0f}"


def fetch_stock_trend_signal(ticker: str, days: int = 210) -> Dict[str, Any]:
    """
    Fetches price history from yfinance and computes SMA crossover + momentum signals.
    - 20-SMA vs 50-SMA: Golden Cross = bullish, Death Cross = bearish
    - Price vs 200-SMA: long-term trend confirmation
    - 30-day momentum: recent price change %
    Returns: signal (Strong Buy/Buy/Hold/Reduce/Caution), strength_score (0-100), details.
    """
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        end = datetime.now()
        start = end - timedelta(days=max(days, 210))
        data = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"), progress=False)
        if data.empty or len(data) < 20:
            return {"signal": "Insufficient Data", "strength_score": 50,
                    "details": f"Not enough price history for {ticker}.", "ticker": ticker,
                    "current_price": None, "momentum_pct": None}

        close = data["Close"].squeeze()
        current_price = float(close.iloc[-1])
        sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
        sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        price_30d_ago = float(close.iloc[-30]) if len(close) >= 30 else float(close.iloc[0])
        momentum_pct = ((current_price - price_30d_ago) / price_30d_ago) * 100.0 if price_30d_ago > 0 else 0.0

        score = 50
        signals = []

        if sma20 and sma50:
            if sma20 > sma50:
                score += 20
                signals.append(f"Golden Cross: 20-SMA ({sma20:.1f}) > 50-SMA ({sma50:.1f})")
            else:
                score -= 20
                signals.append(f"Death Cross: 20-SMA ({sma20:.1f}) < 50-SMA ({sma50:.1f})")

        if sma200:
            if current_price > sma200:
                score += 15
                signals.append(f"Above 200-SMA ({sma200:.1f}) — long-term uptrend")
            else:
                score -= 15
                signals.append(f"Below 200-SMA ({sma200:.1f}) — long-term downtrend")

        if momentum_pct > 5:
            score += 15
            signals.append(f"Strong 30d momentum: +{momentum_pct:.1f}%")
        elif momentum_pct > 0:
            score += 5
            signals.append(f"Positive 30d momentum: +{momentum_pct:.1f}%")
        elif momentum_pct < -5:
            score -= 15
            signals.append(f"Negative 30d momentum: {momentum_pct:.1f}%")
        else:
            score -= 5
            signals.append(f"Slightly negative momentum: {momentum_pct:.1f}%")

        score = max(0, min(100, score))
        if score >= 70:   signal_label = "Strong Buy"
        elif score >= 55: signal_label = "Buy"
        elif score >= 40: signal_label = "Hold"
        elif score >= 25: signal_label = "Reduce"
        else:             signal_label = "Caution"

        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "signal": signal_label,
            "strength_score": score,
            "momentum_pct": round(momentum_pct, 2),
            "sma20": round(sma20, 2) if sma20 else None,
            "sma50": round(sma50, 2) if sma50 else None,
            "sma200": round(sma200, 2) if sma200 else None,
            "details": " | ".join(signals)
        }
    except Exception as e:
        return {"signal": "Error", "strength_score": 50, "details": str(e),
                "ticker": ticker, "current_price": None, "momentum_pct": None}


def generate_rebalance_advice(
    holdings_df: Any,
    risk_profile: str = "Moderate",
    country: str = "India",
    user_context: str = ""
) -> Dict[str, Any]:
    """
    Computes current vs target allocation, drift table, yfinance trend signals for
    equity holdings, and Gemini-powered rebalancing recommendations.
    """
    if holdings_df is None or holdings_df.empty:
        return {"error": "No holdings found. Add your investments first.",
                "current_allocation": {}, "target_allocation": TARGET_ALLOCATION.get(risk_profile, TARGET_ALLOCATION["Moderate"]),
                "drift_table": [], "recommendations": [], "trend_signals": []}

    holdings_df = holdings_df.copy()
    holdings_df["broad_class"] = holdings_df["investment_type"].apply(_map_asset_class)
    total_value = float(holdings_df["current_value"].sum())
    if total_value <= 0:
        return {"error": "Portfolio value is zero. Please update current values.",
                "current_allocation": {}, "target_allocation": {}, "drift_table": [], "recommendations": [], "trend_signals": []}

    current_alloc = holdings_df.groupby("broad_class")["current_value"].sum()
    current_pct = ((current_alloc / total_value) * 100.0).round(2).to_dict()
    target = TARGET_ALLOCATION.get(risk_profile, TARGET_ALLOCATION["Moderate"])
    all_classes = set(current_pct.keys()) | set(target.keys())

    drift_table = []
    for cls in sorted(all_classes):
        actual = current_pct.get(cls, 0.0)
        tgt = target.get(cls, 0.0)
        drift = round(actual - tgt, 2)
        if drift > 7:
            action, detail = "Reduce — Overweight", f"Move ~{drift:.0f}% ({_pct_to_inr(drift, total_value)}) from {cls} to underweight classes."
        elif drift < -7:
            action, detail = "Buy — Underweight", f"Deploy ~{abs(drift):.0f}% ({_pct_to_inr(abs(drift), total_value)}) more into {cls}."
        else:
            action, detail = "Hold — On Track", "Within +/-7% of target. No immediate action needed."
        drift_table.append({"Asset Class": cls, "Current %": actual, "Target %": tgt, "Drift %": drift, "Action": action, "Detail": detail})

    # yfinance trend signals for ALL equity holdings
    trend_signals = []
    equity_hold = holdings_df[holdings_df["broad_class"] == "Equity"]
    for _, row in equity_hold.iterrows():
        desc = str(row.get("description", "")).strip()
        res_name = str(row.get("resolved_name", "")).strip()
        ticker_candidate = desc or res_name
        
        # Combine description and resolved name if they differ, so the UI shows "103819 (Fund Name)"
        display_name = ticker_candidate
        if desc and res_name and desc.lower() != res_name.lower():
            if desc.isdigit() and not res_name.isdigit():
                display_name = f'{desc} ("{res_name}")'
            elif res_name.isdigit() and not desc.isdigit():
                display_name = f'{res_name} ("{desc}")'
            else:
                display_name = f'{desc} ("{res_name}")'

        inv_type = str(row.get("investment_type", "")).lower()
        
        units = float(row.get("units") or 0.0)
        curr_val = float(row.get("current_value") or 0.0)
        portfolio_price = round(curr_val / units, 2) if units > 0 else None

        if ticker_candidate and len(ticker_candidate) >= 2:
            is_mf = "mutual fund" in inv_type or "mf" in inv_type or ticker_candidate.isdigit()
            
            # 1. Calculate Personal Return Signal (applies to both MFs and Stocks)
            ret_pct = float(row.get("returns_pct", 0.0))
            if ret_pct > 15:
                sig_text, score = "Strong Hold", 85
                detail = f"Excellent portfolio return (+{ret_pct:.1f}%). Highly recommended to hold."
            elif ret_pct > 5:
                sig_text, score = "Hold", 65
                detail = f"Steady portfolio return (+{ret_pct:.1f}%). Good core holding."
            elif ret_pct > 0:
                sig_text, score = "Hold", 55
                detail = f"Positive portfolio return (+{ret_pct:.1f}%). Monitor performance."
            elif ret_pct > -5:
                sig_text, score = "Caution", 40
                detail = f"Slightly negative return ({ret_pct:.1f}%). Evaluate fundamentals."
            else:
                sig_text, score = "Reduce / Review", 25
                detail = f"Poor portfolio return ({ret_pct:.1f}%). Consider reallocating."
                
            sig = {
                "holding_name": display_name,
                "ticker": "Mutual Fund" if ticker_candidate.isdigit() else ticker_candidate,
                "current_price": portfolio_price,
                "signal": sig_text,
                "strength_score": score,
                "momentum_pct": ret_pct,
                "details": f"Personal Return: {detail}"
            }

            # 2. For Stocks, try to augment with Yahoo Finance Technicals
            if not is_mf:
                yf_ticker = ticker_candidate.upper()
                if country == "India" and "." not in yf_ticker:
                    yf_ticker += ".NS"
                yf_sig = fetch_stock_trend_signal(yf_ticker)
                
                # If yfinance succeeded, blend the signals
                if yf_sig.get("signal") != "Insufficient Data":
                    # Average the technical score and personal score
                    blended_score = int((score + yf_sig.get("strength_score", 50)) / 2)
                    sig["strength_score"] = blended_score
                    
                    if blended_score >= 70:   sig["signal"] = "Strong Buy/Hold"
                    elif blended_score >= 55: sig["signal"] = "Buy/Hold"
                    elif blended_score >= 40: sig["signal"] = "Hold"
                    elif blended_score >= 25: sig["signal"] = "Reduce"
                    else:                     sig["signal"] = "Caution"
                    
                    # Combine details
                    tech_detail = yf_sig.get('details', '')
                    if not tech_detail:
                        tech_detail = " | ".join([s for s in yf_sig.get("signals", [])])
                    
                    sig["details"] = f"**Personal:** {detail} | **Technical:** {tech_detail}"
            
            trend_signals.append(sig)

    # Sector breakdown
    sector_alloc = holdings_df.groupby("sector_segment")["current_value"].sum()
    sector_pct = ((sector_alloc / total_value) * 100.0).round(2).to_dict()

    # Gemini rebalancing & sector narrative
    recommendations = []
    sector_analysis = []
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass
        if api_key:
            client = genai.Client(api_key=api_key)
            system_prompt = BASE_STOCK_SYSTEM_PROMPT.format(country=country)
            prompt = f"""
            {system_prompt}

            Rebalancing advice for:
            Risk Profile: {risk_profile}, Country: {country}, Portfolio: Rs{total_value:,.0f}
            Current Allocation: {current_pct}
            Target: {target}
            Sector Breakdown: {sector_pct}
            Drifts: {[d for d in drift_table if d['Action'] != 'Hold — On Track']}
            Equity Trend Signals: {trend_signals}

            User's Specific Context / Goals: {user_context}
            (Ensure recommendations directly address this context if provided.)

            Recommend specific {country} instruments. 
            Output strictly as JSON with keys:
            - 'recommendations': list of {{title, action_type (Buy/Sell/Hold), instrument, rationale}}. Max 5 items.
            - 'sector_analysis': list of {{sector, action_type (Buy/Sell/Hold), rationale}}. Max 4 items based on current macro environment.
            - 'detailed_plan': list of strings containing a step-by-step roadmap that details exactly HOW the plan will meet the user's specific goals, including expected outcomes. Max 5 steps.
            """
            resp = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt)
            if resp and resp.text:
                import json
                parsed = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
                recommendations = parsed.get("recommendations", [])
                sector_analysis = parsed.get("sector_analysis", [])
                detailed_plan = parsed.get("detailed_plan", [])
    except Exception:
        pass

    if not recommendations:
        universe = COUNTRY_UNIVERSE.get(country, COUNTRY_UNIVERSE["India"])
        for row in drift_table:
            if "Buy" in row["Action"]:
                key = row["Asset Class"].lower()
                instruments = universe.get(key, [])
                instr_name = instruments[0]["name"] if instruments else f"{row['Asset Class']} Fund"
                recommendations.append({"title": f"Increase {row['Asset Class']}", "action_type": "Buy", "instrument": instr_name, "rationale": row["Detail"]})
            elif "Reduce" in row["Action"]:
                recommendations.append({"title": f"Reduce {row['Asset Class']} exposure", "action_type": "Sell/Switch", "instrument": "Existing overweight holdings", "rationale": row["Detail"]})

    return {"current_allocation": current_pct, "target_allocation": target, "total_value": total_value,
            "drift_table": drift_table, "recommendations": recommendations, "trend_signals": trend_signals, 
            "sector_analysis": sector_analysis, "risk_profile": risk_profile, "detailed_plan": locals().get("detailed_plan", [])}


def generate_new_money_advice(
    holdings_df: Any,
    risk_profile: str = "Moderate",
    amount: float = 50000.0,
    mode: str = "Lump Sum",
    country: str = "India",
    user_context: str = ""
) -> Dict[str, Any]:
    """
    Recommends specific instruments for deploying new money (lump-sum or SIP)
    based on risk profile, existing allocation gaps, and country.
    """
    universe = COUNTRY_UNIVERSE.get(country, COUNTRY_UNIVERSE["India"])
    target = TARGET_ALLOCATION.get(risk_profile, TARGET_ALLOCATION["Moderate"])

    current_pct: Dict[str, float] = {}
    if holdings_df is not None and not holdings_df.empty:
        hdf = holdings_df.copy()
        hdf["broad_class"] = hdf["investment_type"].apply(_map_asset_class)
        total = float(hdf["current_value"].sum())
        if total > 0:
            current_pct = ((hdf.groupby("broad_class")["current_value"].sum() / total) * 100.0).round(2).to_dict()

    splits: Dict[str, float] = {}
    for cls, tgt_pct in target.items():
        gap = max(0.0, tgt_pct - current_pct.get(cls, 0.0))
        splits[cls] = gap
    total_gap = sum(splits.values()) or 1.0
    alloc = {cls: round((gap / total_gap) * amount, 2) for cls, gap in splits.items()}

    suggestions: Dict[str, List[Dict]] = {}
    for cls, instruments in universe.items():
        label = cls.capitalize()
        cls_amount = alloc.get(label, amount * 0.5)
        n = max(1, len(instruments[:3]))
        suggestions[cls] = []
        for instr in instruments[:3]:
            entry = dict(instr)
            per_instr = round(cls_amount / n, 2)
            entry["suggested_amount"] = f"Rs{per_instr:,.0f} / month" if mode == "SIP" else f"Rs{per_instr:,.0f} one-time"
            suggestions[cls].append(entry)

    summary = f"For a {risk_profile} investor in {country}: deploy {mode} of Rs{amount:,.0f} across the suggested instruments below."
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass
        if api_key:
            client = genai.Client(api_key=api_key)
            system_prompt = BASE_STOCK_SYSTEM_PROMPT.format(country=country)
            prompt = f"""
            {system_prompt}

            Risk={risk_profile}, Mode={mode}, Amount=Rs{amount:,.0f}, Country={country}
            Current portfolio: {current_pct}, Target: {target}
            Pre-selected: {{{', '.join(f'{k}: {[i["name"] for i in v[:2]]}' for k, v in suggestions.items())}}}

            User's Specific Context / Goals: {user_context}
            (Ensure the rationale directly addresses this context if provided.)

            Enhance rationale for current {country} market environment.
            Output JSON strictly with keys: 
            - 'summary': string, overarching strategy summary.
            - 'detailed_plan': list of strings containing a step-by-step roadmap that details exactly HOW the deployment plan will meet the user's specific goals, including expected outcomes. Max 5 steps.
            Keep instruments same.
            """
            resp = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt)
            if resp and resp.text:
                import json
                parsed = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
                summary = parsed.get("summary", summary)
                detailed_plan = parsed.get("detailed_plan", [])
    except Exception:
        pass

    return {"mode": mode, "amount": amount, "country": country, "risk_profile": risk_profile,
            "allocation_split": alloc, "suggestions": suggestions, "summary": summary, "detailed_plan": locals().get("detailed_plan", [])}


def _india_new_regime_tax(gross: float) -> float:
    """India New Regime FY 2024-25 with Rs75,000 standard deduction + 4% cess."""
    taxable = max(0.0, gross - 75000.0)
    slabs = [(300000, 0.0), (400000, 0.05), (300000, 0.10), (300000, 0.15), (300000, 0.20), (float("inf"), 0.30)]
    tax = 0.0; remaining = taxable
    for lim, rate in slabs:
        chunk = min(remaining, lim); tax += chunk * rate; remaining -= chunk
        if remaining <= 0: break
    if taxable <= 700000: tax = 0.0  # 87A rebate
    return round(tax * 1.04, 2)


def _india_old_regime_tax(gross: float, eighty_c: float, std_ded: float) -> float:
    """India Old Regime FY 2024-25 with 4% cess."""
    taxable = max(0.0, gross - std_ded - eighty_c)
    slabs = [(250000, 0.0), (250000, 0.05), (250000, 0.20), (float("inf"), 0.30)]
    tax = 0.0; remaining = taxable
    for lim, rate in slabs:
        chunk = min(remaining, lim); tax += chunk * rate; remaining -= chunk
        if remaining <= 0: break
    return round(tax * 1.04, 2)


def compute_tax_liability(
    income_sources_df: Any,
    holdings_df: Any,
    country: str = "India",
    tax_regime: str = "New Regime"
) -> Dict[str, Any]:
    """
    Computes estimated annual tax liability from income sources + investment holdings.
    Supports India (Old/New Regime), United States, UAE (no tax), and Other.
    Returns gross income, taxable income, estimated tax, effective rate, and savings opportunities.
    """
    gross_annual = 0.0
    income_breakdown: List[Dict[str, Any]] = []
    if income_sources_df is not None and not income_sources_df.empty:
        for _, row in income_sources_df.iterrows():
            monthly_eq = float(row.get("monthly_equivalent", 0.0))
            annual_eq = monthly_eq * 12.0
            gross_annual += annual_eq
            income_breakdown.append({"source": row["source_name"], "type": row["income_type"], "annual": round(annual_eq, 2)})

    if country == "India":
        eighty_c_types = {"PPF", "EPF", "NSC", "KVP"}
        eighty_c_invested = 0.0
        if holdings_df is not None and not holdings_df.empty:
            for _, row in holdings_df.iterrows():
                itype = str(row.get("investment_type", ""))
                invested = float(row.get("investment_amount", 0.0))
                if any(t in itype for t in eighty_c_types) or "elss" in itype.lower():
                    eighty_c_invested += invested
        eighty_c_deduction = min(150000.0, eighty_c_invested)
        std_ded = 50000.0
        savings_opportunities: List[Dict[str, str]] = []

        if tax_regime == "Old Regime":
            taxable_income = max(0.0, gross_annual - std_ded - eighty_c_deduction)
            total_tax = _india_old_regime_tax(gross_annual, eighty_c_deduction, std_ded)
            if eighty_c_deduction < 150000:
                gap = 150000 - eighty_c_deduction
                savings_opportunities.append({"opportunity": "Maximize 80C", "detail": f"Invest Rs{gap:,.0f} more in PPF/ELSS/VPF to save up to Rs{gap*0.30:,.0f} in tax."})
            new_tax = _india_new_regime_tax(gross_annual)
            if new_tax < total_tax:
                savings_opportunities.append({"opportunity": "Switch to New Regime", "detail": f"New Regime: Rs{new_tax:,.0f} vs Old: Rs{total_tax:,.0f}. Saving: Rs{total_tax-new_tax:,.0f}."})
        else:
            taxable_income = max(0.0, gross_annual - 75000.0)
            total_tax = _india_new_regime_tax(gross_annual)
            old_tax = _india_old_regime_tax(gross_annual, eighty_c_deduction, std_ded)
            if old_tax < total_tax and eighty_c_deduction > 0:
                savings_opportunities.append({"opportunity": "Consider Old Regime", "detail": f"With Rs{eighty_c_deduction:,.0f} in 80C, Old Regime: Rs{old_tax:,.0f} saves Rs{total_tax-old_tax:,.0f}."})
            savings_opportunities.append({"opportunity": "NPS 80CCD(1B)", "detail": "Invest up to Rs50,000 in NPS for extra deduction applicable even in New Regime (employer route)."})

        # LTCG check
        equity_gain = 0.0
        if holdings_df is not None and not holdings_df.empty:
            for _, row in holdings_df.iterrows():
                if _map_asset_class(str(row.get("investment_type", ""))) == "Equity":
                    gain = float(row.get("current_value", 0)) - float(row.get("investment_amount", 0))
                    yr = int(row.get("year_invested", 2024))
                    if gain > 0 and (2025 - yr) >= 1:
                        equity_gain += gain
        if equity_gain > 125000:
            ltcg_tax = (equity_gain - 125000) * 0.125
            savings_opportunities.append({"opportunity": "LTCG Tax Harvesting", "detail": f"Equity LTCG: Rs{equity_gain:,.0f}. Rs1.25L exempt; estimated LTCG tax: Rs{ltcg_tax:,.0f}. Harvest losses to offset."})

        eff_rate = round((total_tax / gross_annual) * 100, 2) if gross_annual > 0 else 0.0
        return {"country": "India", "tax_regime": tax_regime, "gross_annual_income": round(gross_annual, 2),
                "taxable_income": round(taxable_income, 2), "eighty_c_deduction": round(eighty_c_deduction, 2),
                "estimated_tax": round(total_tax, 2), "effective_rate_pct": eff_rate,
                "income_breakdown": income_breakdown, "savings_opportunities": savings_opportunities}

    elif country == "United States":
        taxable = max(0.0, gross_annual - 14600.0)
        brackets = [(11600, 0.10), (33550, 0.12), (50550, 0.22), (96950, 0.24), (206700, 0.32), (243725, 0.35), (float("inf"), 0.37)]
        tax = 0.0; remaining = taxable
        for lim, rate in brackets:
            chunk = min(remaining, lim); tax += chunk * rate; remaining -= chunk
            if remaining <= 0: break
        eff_rate = round((tax / gross_annual) * 100, 2) if gross_annual > 0 else 0.0
        return {"country": "United States", "tax_regime": "Single Filer (2024)",
                "gross_annual_income": round(gross_annual, 2), "taxable_income": round(taxable, 2),
                "estimated_tax": round(tax, 2), "effective_rate_pct": eff_rate,
                "income_breakdown": income_breakdown,
                "savings_opportunities": [
                    {"opportunity": "Maximize 401(k)", "detail": "Contribute $23,000 pre-tax to reduce taxable income immediately."},
                    {"opportunity": "Roth IRA", "detail": "$7,000 after-tax contribution grows completely tax-free."},
                    {"opportunity": "HSA (HDHP users)", "detail": "$4,150 individual / $8,300 family — triple tax benefit."}
                ]}
    else:
        return {"country": country, "tax_regime": "No Personal Income Tax",
                "gross_annual_income": round(gross_annual, 2), "taxable_income": 0.0,
                "estimated_tax": 0.0, "effective_rate_pct": 0.0,
                "income_breakdown": income_breakdown,
                "savings_opportunities": [
                    {"opportunity": "No Income Tax", "detail": f"{country} has no personal income tax. Focus on maximizing investment returns."},
                    {"opportunity": "NRI India Tax (if applicable)", "detail": "Indian-sourced income (rent, FDs, dividends) may still be taxable in India. Verify DTAA implications."},
                    {"opportunity": "Corporate Structure", "detail": "Consider UAE Free Zone entity to efficiently manage business income."}
                ]}
