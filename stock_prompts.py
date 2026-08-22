"""
Consolidated Stock Recommendation Prompt Engine for Indian Equities (NSE/BSE).
Production-ready prompt generators and structured schemas for Python applications.
"""

import json
from typing import Dict, Any, Optional, List

# ==============================================================================
# 1. CORE SYSTEM PROMPT
# ==============================================================================

BASE_STOCK_SYSTEM_PROMPT = """
You are a Senior Equity Research Analyst & Quantitative Portfolio Strategist specializing in the Indian Stock Market (NSE/BSE) with deep expertise in fundamental valuation, technical momentum, corporate governance, and risk management.

Your objective is to provide objective, high-conviction, data-backed stock analysis and recommendations tailored to the user's specific financial parameters or return goals.

Key Rules:
1. Focus on NSE/BSE listed securities with healthy liquidity.
2. Enforce strict forensic checks: Avoid companies with high promoter pledge (>5%), auditor red flags, or severe debt traps.
3. Align all financial year metrics with the Indian Financial Year (Apr-Mar).
4. Provide structured, actionable, and realistic valuation targets and stop-losses.
5. Always output in valid JSON format matching the requested schema.
"""

# ==============================================================================
# 2. FINANCIALLY SAVVY (PARAMETER-DRIVEN) PROMPT GENERATOR
# ==============================================================================

def get_financially_savvy_prompt(
    market_cap_segment: str = "Mid Cap (101-250)",
    sector: str = "Any Sector",
    min_roce: float = 18.0,
    min_roe: float = 15.0,
    max_pe: Optional[float] = 35.0,
    max_peg: Optional[float] = 1.3,
    max_debt_to_equity: float = 0.5,
    min_profit_cagr_3yr: float = 15.0,
    min_sales_cagr_3yr: float = 12.0,
    max_promoter_pledge: float = 0.0,
    technical_filters: Optional[List[str]] = None,
    num_recommendations: int = 3
) -> str:
    """
    Generates a prompt for financially savvy / quant users with specific screening filters.
    """
    tech_str = ", ".join(technical_filters) if technical_filters else "Trading above 50 DMA and 200 DMA, RSI (14) between 45 and 65"
    pe_str = f"P/E Ratio <= {max_pe}" if max_pe else "P/E < Industry Average"
    peg_str = f"PEG Ratio <= {max_peg}" if max_peg else "PEG Ratio < 1.2 (Growth at a Reasonable Price)"

    prompt = f"""
Analyze the Indian Equity Universe (NSE/BSE) and recommend the top {num_recommendations} stocks strictly meeting the following quantitative and fundamental parameters:

### Screening Criteria:
1. **Market Cap Segment**: {market_cap_segment}
2. **Sector**: {sector}
3. **Profitability & Efficiency**:
   - ROCE >= {min_roce}%
   - ROE >= {min_roe}%
4. **Growth & Valuation**:
   - 3-Year Profit CAGR >= {min_profit_cagr_3yr}%
   - 3-Year Sales CAGR >= {min_sales_cagr_3yr}%
   - {pe_str}
   - {peg_str}
5. **Solvency & Balance Sheet**:
   - Debt-to-Equity (D/E) <= {max_debt_to_equity} (or Net Cash)
   - Promoter Share Pledge <= {max_promoter_pledge}%
6. **Technical & Momentum**:
   - {tech_str}

### Output Requirement:
Return ONLY a valid JSON array of objects with the following schema:
```json
[
  {{
    "stock_name": "Company Name Ltd",
    "ticker": "NSE_SYMBOL",
    "sector": "Sector Name",
    "market_cap_tier": "Large/Mid/Small",
    "current_price_approx": 1250.0,
    "metrics_scorecard": {{
      "roce_pct": 24.5,
      "roe_pct": 21.0,
      "pe_ratio": 26.4,
      "peg_ratio": 0.95,
      "debt_to_equity": 0.12,
      "profit_cagr_3yr_pct": 22.0
    }},
    "investment_thesis": [
      "Key competitive advantage / moat",
      "Revenue catalyst / capacity expansion / industry tailwind",
      "Earnings visibility over next 6-8 quarters"
    ],
    "valuation_verdict": "Undervalued / Fairly Valued / Growth at Reasonable Price",
    "key_risks": [
      "Risk factor 1",
      "Risk factor 2"
    ],
    "actionable_levels": {{
      "buy_range_inr": "1200 - 1260",
      "target_price_inr": 1550.0,
      "stop_loss_inr": 1120.0,
      "upside_potential_pct": 24.0,
      "recommended_timeframe": "12 - 18 Months"
    }}
  }}
]
```
"""
    return prompt.strip()

# ==============================================================================
# 3. GOAL-DRIVEN / TARGET RETURN (BEGINNER-FRIENDLY) PROMPT GENERATOR
# ==============================================================================

def get_goal_driven_prompt(
    target_return_pct: str = "15% - 20% (Moderate Growth)",
    investment_horizon: str = "Medium Term (1 - 3 Years)",
    risk_profile: str = "Moderate / Balanced",
    preferred_theme: str = "Any Sector / Best Available",
    investment_mode: str = "Lump-sum or Monthly SIP",
    num_recommendations: int = 3
) -> str:
    """
    Generates a prompt for retail/beginner users based on target return, timeframe, and risk comfort.
    """
    prompt = f"""
Recommend {num_recommendations} Indian stocks (NSE/BSE) tailored for a retail investor with the following investment objectives:

### Investor Profile:
- **Target Expected Return**: {target_return_pct}
- **Investment Horizon**: {investment_horizon}
- **Risk Tolerance Level**: {risk_profile}
- **Preferred Sector / Theme**: {preferred_theme}
- **Investment Style**: {investment_mode}

### Guidelines:
- Explain the business in simple, relatable terms (avoid overwhelming Wall Street jargon).
- Clearly explain WHY this stock can deliver the requested {target_return_pct} return in plain English.
- Detail the real-world risks in straightforward terms.
- Include maximum portfolio allocation guidance (e.g., "Do not allocate more than 8% of total portfolio").

### Output Requirement:
Return ONLY a valid JSON array of objects with the following schema:
```json
[
  {{
    "stock_name": "Company Name Ltd",
    "ticker": "NSE_SYMBOL",
    "sector": "Sector Name",
    "business_summary_simple": "One-line simple explanation of what the company sells/makes",
    "why_it_fits_your_goal": "Clear explanation of how this stock can achieve the target return",
    "key_growth_catalysts": [
      "Catalyst 1 (e.g. Building 2 new factories to double production)",
      "Catalyst 2 (e.g. Government increasing defense/infra budget)"
    ],
    "what_could_go_wrong": [
      "Key risk in simple terms"
    ],
    "how_to_invest": {{
      "ideal_entry_price": "₹ 850 - ₹ 890",
      "target_price": "₹ 1,100",
      "expected_gain_pct": 25.0,
      "holding_period": "12 - 24 Months",
      "max_portfolio_weight_pct": 7.0,
      "suitable_for_sip": true
    }}
  }}
]
```
"""
    return prompt.strip()

# ==============================================================================
# 4. SECTOR-SPECIFIC DEEP DIVE PROMPT GENERATOR
# ==============================================================================

def get_sector_deep_dive_prompt(
    sector_name: str,
    focus_theme: str = "Market Leaders & Emerging Winners",
    num_recommendations: int = 2
) -> str:
    """
    Generates specialized prompts with sector-specific KPI checklists (e.g. Banking NIM/NPA, IT TCV, Pharma USFDA).
    """
    sector_kpi_guide = {
        "Banking & Financials": "Net Interest Margin (NIM > 3.5%), Gross/Net NPA trends, CASA Ratio (>40%), Credit Growth vs Industry",
        "IT & Technology": "Constant Currency (CC) revenue growth, Large deal TCV pipeline, Attrition trends, Margin resilience against wage hikes",
        "Pharma & Healthcare": "USFDA compliance history (Zero OAI/Warning letters), Domestic formulation share %, R&D pipeline (6-8% of sales)",
        "Automotive & EV": "Volume growth (2W/PV/CV), EV transition readiness, Raw material (commodity) tailwinds, Export market share",
        "Infra & Capital Goods": "Order book-to-bill ratio (> 2.5x), Working capital cycle, Government capex linkage, Operating cash flow",
        "FMCG & Consumption": "Volume-led growth (vs pure pricing), Rural vs Urban demand recovery, Gross margin expansion, Pricing power"
    }

    kpi_focus = sector_kpi_guide.get(sector_name, "Revenue CAGR, Operating margin expansion, ROCE > 18%, Market share gains")

    prompt = f"""
Perform a deep-dive equity analysis for the Indian **{sector_name}** sector focusing on '{focus_theme}'.

Sector-Specific KPIs to Evaluate:
{kpi_focus}

Identify the top {num_recommendations} highest-conviction stocks in this sector with strong multi-year compounding potential.

Output strictly in valid JSON:
```json
[
  {{
    "stock_name": "Company Name",
    "ticker": "SYMBOL",
    "sector_sub_segment": "e.g. Private Bank / Large-cap IT / API Pharma",
    "sector_kpi_scorecard": {{
      "key_kpi_1": "value",
      "key_kpi_2": "value"
    }},
    "competitive_moat": "Why competitors cannot easily replicate this business",
    "growth_outlook_3yr": "Multi-year earnings growth trajectory",
    "actionable_levels": {{
      "buy_zone": "Price range in INR",
      "fair_value_target": "Target in INR",
      "stop_loss": "Stop level in INR"
    }}
  }}
]
```
"""
    return prompt.strip()
