"""
Investment & Wealth Portfolio Planner Engine.
Calculates age-adjusted asset allocation (Equity, Debt, Gold, Insurance),
SIP breakdown, compound wealth projections (5, 10, 15, 20 yrs), and Gemini AI advice.
"""

import os
from typing import Dict, Any, List, Tuple
import pandas as pd

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
                model="gemini-2.5-flash",
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
                model="gemini-2.5-flash",
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
                model="gemini-2.5-flash",
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

def calculate_retirement_corpus(current_age: int, retirement_age: int, current_savings: float, monthly_sip: float, cagr_decimal: float) -> Dict[str, Any]:
    """
    Calculates the projected retirement corpus based on current age and savings.
    """
    years = max(1, retirement_age - current_age)
    n_months = years * 12
    r_monthly = cagr_decimal / 12.0
    
    # Future value of lump sum savings
    fv_lump = current_savings * ((1 + r_monthly) ** n_months)
    
    # Future value of monthly SIP
    if r_monthly > 0:
        fv_sip = monthly_sip * (((1 + r_monthly) ** n_months - 1) / r_monthly) * (1 + r_monthly)
    else:
        fv_sip = monthly_sip * n_months

    total_fv = round(fv_lump + fv_sip, 2)
    total_invested = round(current_savings + (monthly_sip * n_months), 2)
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
                model="gemini-2.5-flash",
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
