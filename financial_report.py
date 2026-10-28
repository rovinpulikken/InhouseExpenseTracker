"""
financial_report.py
Comprehensive Financial Health Status & Customisable Wealth Report Generator.

Features:
- Pure-Python scoring engine across 5 pillars (0-100 score).
- Deep investment portfolio review & algorithmic advice integration (algo_advisor.py).
- Debt, cash flow, emergency runway, insurance, and tax checklists.
- Fully customisable report generator: users can choose sections, detail level, and notes.
- Export formats:
  * Print-Ready / PDF-Ready HTML (with @media print styling).
  * Multi-sheet Excel workbook (.xlsx via openpyxl).
"""

from typing import Any, Dict, List, Optional
import datetime
import io
import pandas as pd

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    Workbook = None

# Re-use algorithmic advisor rules where possible
try:
    from algo_advisor import build_algo_advice, TIERS
except ImportError:
    build_algo_advice = None
    TIERS = {}


# =====================================================================
# 1. FINANCIAL HEALTH SCORING ENGINE (0 - 100)
# =====================================================================

def compute_financial_health(
    user: Dict[str, Any],
    inv_df: Optional[pd.DataFrame] = None,
    debts_df: Optional[pd.DataFrame] = None,
    income_df: Optional[pd.DataFrame] = None,
    expenses_df: Optional[pd.DataFrame] = None,
    monthly_income: float = 0.0,
    monthly_expenses: float = 0.0,
    liquid_cash: float = 0.0,
) -> Dict[str, Any]:
    """
    Computes a comprehensive financial health assessment across 5 core pillars.
    Each pillar is scored out of 20 points, for a maximum score of 100.
    """
    inv_df = inv_df if inv_df is not None else pd.DataFrame()
    debts_df = debts_df if debts_df is not None else pd.DataFrame()
    income_df = income_df if income_df is not None else pd.DataFrame()
    expenses_df = expenses_df if expenses_df is not None else pd.DataFrame()

    # Asset totals
    tot_invested = float(inv_df["investment_amount"].sum()) if not inv_df.empty and "investment_amount" in inv_df.columns else 0.0
    tot_portfolio = float(inv_df["current_value"].sum()) if not inv_df.empty and "current_value" in inv_df.columns else 0.0
    unrealized_pnl = tot_portfolio - tot_invested
    return_pct = (unrealized_pnl / tot_invested * 100.0) if tot_invested > 0 else 0.0

    # Debt totals
    tot_debt = float(debts_df["outstanding_principal"].sum()) if not debts_df.empty and "outstanding_principal" in debts_df.columns else 0.0
    monthly_emi = float(debts_df["monthly_emi"].sum()) if not debts_df.empty and "monthly_emi" in debts_df.columns else 0.0

    # Net Worth
    total_assets = tot_portfolio + liquid_cash
    net_worth = total_assets - tot_debt

    # Cashflow & Savings Rate
    # Fallback monthly income from income_df if not provided
    if monthly_income <= 0 and not income_df.empty and "amount" in income_df.columns:
        # Sum recurring monthly income or convert annual to monthly
        monthly_income = float(income_df["amount"].sum())
    if monthly_income <= 0:
        # Check user income_range string
        inc_str = str(user.get("income_range", ""))
        if "> ₹50L" in inc_str:
            monthly_income = 450000.0
        elif "₹25L - ₹50L" in inc_str:
            monthly_income = 250000.0
        elif "₹10L - ₹25L" in inc_str:
            monthly_income = 120000.0
        else:
            monthly_income = 75000.0

    if monthly_expenses <= 0 and not expenses_df.empty and "amount" in expenses_df.columns:
        monthly_expenses = float(expenses_df["amount"].sum() / 12.0)
    if monthly_expenses <= 0:
        monthly_expenses = max(20000.0, monthly_income * 0.5)

    savings_amount = max(0.0, monthly_income - monthly_expenses)
    savings_rate = (savings_amount / monthly_income * 100.0) if monthly_income > 0 else 0.0

    # Emergency runway (months)
    # Estimate liquid buffer: liquid_cash or Cash holdings in portfolio
    portfolio_cash = 0.0
    if not inv_df.empty and "investment_type" in inv_df.columns:
        cash_rows = inv_df[inv_df["investment_type"].astype(str).str.contains("Cash|Liquid|Bank|FD|Savings", case=False, na=False)]
        portfolio_cash = float(cash_rows["current_value"].sum()) if not cash_rows.empty else 0.0
    available_liquid = max(liquid_cash, portfolio_cash)
    emergency_runway_months = (available_liquid / monthly_expenses) if monthly_expenses > 0 else 0.0

    # Debt-to-Income (DTI) ratio
    dti_pct = (monthly_emi / monthly_income * 100.0) if monthly_income > 0 else 0.0
    debt_to_asset_pct = (tot_debt / total_assets * 100.0) if total_assets > 0 else (100.0 if tot_debt > 0 else 0.0)

    # -------------------------------------------------------------
    # 5 PILLAR SCORING (0 to 20 pts each)
    # -------------------------------------------------------------

    # Pillar 1: Savings Rate (20 pts)
    if savings_rate >= 35.0:
        score_savings = 20.0
    elif savings_rate >= 25.0:
        score_savings = 16.0
    elif savings_rate >= 15.0:
        score_savings = 12.0
    elif savings_rate >= 5.0:
        score_savings = 7.0
    else:
        score_savings = 3.0

    # Pillar 2: Emergency Runway (20 pts) - Target 6 months
    if emergency_runway_months >= 6.0:
        score_runway = 20.0
    elif emergency_runway_months >= 4.0:
        score_runway = 15.0
    elif emergency_runway_months >= 2.0:
        score_runway = 10.0
    elif emergency_runway_months >= 1.0:
        score_runway = 5.0
    else:
        score_runway = 2.0

    # Pillar 3: Debt Burden / DTI (20 pts)
    if tot_debt == 0.0:
        score_debt = 20.0
    elif dti_pct <= 20.0 and debt_to_asset_pct <= 25.0:
        score_debt = 18.0
    elif dti_pct <= 35.0 and debt_to_asset_pct <= 50.0:
        score_debt = 13.0
    elif dti_pct <= 50.0:
        score_debt = 7.0
    else:
        score_debt = 2.0

    # Pillar 4: Net Worth & Solvency (20 pts)
    if net_worth > 0 and (tot_debt == 0 or total_assets >= 2.5 * tot_debt):
        score_solvency = 20.0
    elif net_worth > 0 and total_assets >= 1.5 * tot_debt:
        score_solvency = 15.0
    elif net_worth > 0:
        score_solvency = 10.0
    elif net_worth == 0:
        score_solvency = 6.0
    else:
        score_solvency = 2.0

    # Pillar 5: Asset Diversification & Investment Discipline (20 pts)
    # Checks number of holdings, asset types, and concentration
    score_invest = 10.0
    if not inv_df.empty:
        types_count = inv_df["investment_type"].nunique() if "investment_type" in inv_df.columns else 1
        holdings_count = len(inv_df)
        if types_count >= 3 and holdings_count >= 5:
            score_invest = 20.0
        elif types_count >= 2 and holdings_count >= 3:
            score_invest = 15.0
        else:
            score_invest = 10.0
    else:
        score_invest = 4.0  # No investments yet

    total_score = round(score_savings + score_runway + score_debt + score_solvency + score_invest, 1)

    if total_score >= 85.0:
        rating = "Excellent"
        rating_color = "#10b981"
        verdict = "Exceptional financial stability with strong capital compounding and low vulnerability."
    elif total_score >= 70.0:
        rating = "Good"
        rating_color = "#3b82f6"
        verdict = "Healthy financial discipline with sound fundamentals; minor optimizations can unlock higher wealth acceleration."
    elif total_score >= 50.0:
        rating = "Fair"
        rating_color = "#f59e0b"
        verdict = "Moderate financial resilience; debt burden, emergency reserves, or savings rate require focused attention."
    else:
        rating = "Needs Action"
        rating_color = "#ef4444"
        verdict = "Immediate restructuring recommended to reduce high debt exposure and establish essential liquidity buffers."

    # Strengths & Priority Areas
    strengths = []
    if savings_rate >= 25.0:
        strengths.append(f"Strong monthly savings rate of {savings_rate:.1f}%")
    if emergency_runway_months >= 5.0:
        strengths.append(f"Robust emergency runway covering {emergency_runway_months:.1f} months of expenses")
    if tot_debt == 0.0:
        strengths.append("Zero outstanding debt liabilities — pristine balance sheet")
    elif dti_pct < 25.0:
        strengths.append(f"Conservative Debt-to-Income ratio of {dti_pct:.1f}%")
    if return_pct > 12.0:
        strengths.append(f"Healthy investment portfolio capital appreciation (+{return_pct:.1f}%)")

    improvement_areas = []
    if emergency_runway_months < 3.0:
        shortfall = max(0.0, (monthly_expenses * 6.0) - available_liquid)
        improvement_areas.append(f"Emergency buffer is below 3 months. Build an additional ₹{shortfall:,.0f} in liquid instruments.")
    if dti_pct > 35.0:
        improvement_areas.append(f"Monthly EMI obligations consume {dti_pct:.1f}% of income; consider prepaying high-interest loans.")
    if savings_rate < 20.0:
        improvement_areas.append(f"Current savings rate of {savings_rate:.1f}% is below the 20% benchmark; audit discretionary expenses.")
    if inv_df.empty:
        improvement_areas.append("No active investment portfolio logged; establish systematic monthly SIPs.")

    # Algorithmic advisor integration
    algo_advice = None
    if build_algo_advice and not inv_df.empty:
        try:
            risk_tol = user.get("risk_tolerance", "Moderate")
            user_age = int(user.get("age", 35))
            algo_advice = build_algo_advice(
                holdings_df=inv_df,
                risk_tolerance=risk_tol,
                age=user_age,
                monthly_sip=max(10000.0, savings_amount * 0.7)
            )
        except Exception:
            algo_advice = None

    return {
        "score": total_score,
        "rating": rating,
        "rating_color": rating_color,
        "verdict": verdict,
        "pillars": {
            "Savings Rate": {"score": score_savings, "max": 20, "val": f"{savings_rate:.1f}%"},
            "Emergency Runway": {"score": score_runway, "max": 20, "val": f"{emergency_runway_months:.1f} mos"},
            "Debt Management": {"score": score_debt, "max": 20, "val": f"{dti_pct:.1f}% DTI"},
            "Net Worth & Solvency": {"score": score_solvency, "max": 20, "val": f"₹{net_worth:,.0f}"},
            "Investment Diversity": {"score": score_invest, "max": 20, "val": f"{len(inv_df)} holdings"},
        },
        "metrics": {
            "total_assets": total_assets,
            "tot_portfolio": tot_portfolio,
            "tot_invested": tot_invested,
            "unrealized_pnl": unrealized_pnl,
            "return_pct": return_pct,
            "tot_debt": tot_debt,
            "monthly_emi": monthly_emi,
            "net_worth": net_worth,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_savings": savings_amount,
            "savings_rate": savings_rate,
            "available_liquid": available_liquid,
            "emergency_runway_months": emergency_runway_months,
            "dti_pct": dti_pct,
            "debt_to_asset_pct": debt_to_asset_pct,
        },
        "strengths": strengths,
        "improvement_areas": improvement_areas,
        "algo_advice": algo_advice,
        "generated_at": datetime.datetime.now().strftime("%d %B %Y, %I:%M %p"),
    }


# =====================================================================
# 2. PRINT-READY / PDF-READY HTML REPORT GENERATOR
# =====================================================================

def generate_html_report(
    user: Dict[str, Any],
    health_data: Dict[str, Any],
    inv_df: Optional[pd.DataFrame] = None,
    debts_df: Optional[pd.DataFrame] = None,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Renders a comprehensive, print-optimized HTML report with modern styling.
    Supports user customization for which sections to include.
    """
    options = options or {}
    sections = options.get("sections", [
        "executive_summary",
        "net_worth_balance_sheet",
        "investments_audit",
        "debt_schedule",
        "cashflow_emergency",
        "actionable_recommendations"
    ])
    custom_title = options.get("title", "Comprehensive Financial Health & Wealth Audit Report")
    custom_note = options.get("custom_note", "")
    include_holding_details = options.get("include_holding_details", True)

    m = health_data["metrics"]
    p = health_data["pillars"]
    algo = health_data.get("algo_advice") or {}

    user_name = user.get("full_name") or user.get("username", "Valued Client")
    user_age = user.get("age", "N/A")
    risk_tol = user.get("risk_tolerance", "Moderate")

    html_parts = []

    # Head and CSS
    html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{custom_title} - {user_name}</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #f8fafc;
        color: #1e293b;
        line-height: 1.5;
        font-size: 14px;
        padding: 30px;
    }}
    .container {{
        max-width: 1000px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        padding: 40px;
        border: 1px solid #e2e8f0;
    }}
    .report-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 2px solid #0f172a;
        padding-bottom: 24px;
        margin-bottom: 30px;
    }}
    .brand-title {{
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
    }}
    .brand-subtitle {{
        font-size: 13px;
        color: #64748b;
        margin-top: 4px;
    }}
    .meta-box {{
        text-align: right;
        font-size: 12px;
        color: #475569;
    }}
    .meta-box strong {{
        color: #0f172a;
    }}
    .section-card {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 24px;
        margin-bottom: 24px;
    }}
    .section-title {{
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 8px;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 20px;
    }}
    .kpi-box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
    }}
    .kpi-label {{
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .kpi-value {{
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 4px;
    }}
    .kpi-sub {{
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
    }}
    
    /* Health Score Hero */
    .hero-score-box {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 28px;
    }}
    .score-circle {{
        text-align: center;
        min-width: 140px;
    }}
    .score-number {{
        font-size: 48px;
        font-weight: 800;
        line-height: 1;
        color: {health_data['rating_color']};
    }}
    .score-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.1);
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-top: 6px;
        color: {health_data['rating_color']};
    }}
    .score-info {{
        padding-left: 24px;
    }}
    .score-verdict {{
        font-size: 15px;
        color: #cbd5e1;
        margin-top: 6px;
        line-height: 1.5;
    }}
    
    /* Progress Bars */
    .pillar-row {{
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        font-size: 13px;
    }}
    .pillar-name {{
        width: 180px;
        font-weight: 600;
        color: #334155;
    }}
    .pillar-bar-wrap {{
        flex: 1;
        height: 10px;
        background: #e2e8f0;
        border-radius: 6px;
        overflow: hidden;
        margin: 0 16px;
    }}
    .pillar-bar {{
        height: 100%;
        background: #3b82f6;
        border-radius: 6px;
    }}
    .pillar-val {{
        width: 80px;
        text-align: right;
        font-weight: 700;
        color: #0f172a;
    }}
    
    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        margin-top: 10px;
    }}
    th {{
        background: #f1f5f9;
        color: #475569;
        font-weight: 600;
        text-align: left;
        padding: 10px 12px;
        border-bottom: 1px solid #cbd5e1;
    }}
    td {{
        padding: 10px 12px;
        border-bottom: 1px solid #f1f5f9;
        color: #334155;
    }}
    tr:nth-child(even) td {{
        background: #fafafa;
    }}
    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .badge-hold {{ background: #e0f2fe; color: #0369a1; }}
    .badge-buy {{ background: #dcfce7; color: #15803d; }}
    .badge-trim {{ background: #fee2e2; color: #b91c1c; }}
    .badge-review {{ background: #fef3c7; color: #b45309; }}
    
    /* Lists */
    .bullet-list {{
        list-style: none;
        padding-left: 0;
    }}
    .bullet-list li {{
        position: relative;
        padding-left: 20px;
        margin-bottom: 8px;
        font-size: 13px;
        color: #334155;
    }}
    .bullet-list li::before {{
        content: "•";
        position: absolute;
        left: 6px;
        color: #3b82f6;
        font-weight: bold;
    }}
    
    .print-btn {{
        background: #0f172a;
        color: #ffffff;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    .print-btn:hover {{
        background: #1e293b;
    }}
    
    @media print {{
        body {{ background: #ffffff; padding: 0; }}
        .container {{ box-shadow: none; border: none; padding: 0; width: 100%; max-width: 100%; }}
        .no-print {{ display: none !important; }}
        .section-card {{ break-inside: avoid; border: 1px solid #cbd5e1; margin-bottom: 20px; }}
        .hero-score-box {{ break-inside: avoid; background: #0f172a !important; -webkit-print-color-adjust: exact; }}
    }}
</style>
</head>
<body>

<div class="container">
    <div class="no-print" style="display:flex; justify-content:flex-end; margin-bottom: 20px;">
        <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>

    <!-- HEADER -->
    <div class="report-header">
        <div>
            <div class="brand-title">FinCompass · Financial Health Audit</div>
            <div class="brand-subtitle">{custom_title}</div>
            {f'<div style="margin-top:6px; font-size:12px; color:#475569; font-style:italic;">Note: {custom_note}</div>' if custom_note else ''}
        </div>
        <div class="meta-box">
            <div>Client: <strong>{user_name}</strong> (Age: {user_age})</div>
            <div>Risk Profile: <strong>{risk_tol}</strong></div>
            <div>Audit Date: <strong>{health_data['generated_at']}</strong></div>
        </div>
    </div>
""")

    # 1. EXECUTIVE SUMMARY & SCORE
    if "executive_summary" in sections:
        html_parts.append(f"""
    <!-- HERO SCORE -->
    <div class="hero-score-box">
        <div class="score-circle">
            <div class="score-number">{health_data['score']:.0f}</div>
            <div style="font-size:11px; color:#94a3b8; text-transform:uppercase;">Score out of 100</div>
            <div class="score-badge">{health_data['rating']}</div>
        </div>
        <div class="score-info">
            <h3 style="font-size:18px; font-weight:700;">Financial Health Summary</h3>
            <p class="score-verdict">{health_data['verdict']}</p>
        </div>
    </div>

    <!-- 5 PILLARS DETAIL -->
    <div class="section-card">
        <div class="section-title">📊 5-Pillar Financial Health Breakdown</div>
""")
        for name, p_data in p.items():
            pct = (p_data["score"] / p_data["max"]) * 100.0
            html_parts.append(f"""
        <div class="pillar-row">
            <div class="pillar-name">{name} ({p_data['val']})</div>
            <div class="pillar-bar-wrap">
                <div class="pillar-bar" style="width: {pct:.0f}%;"></div>
            </div>
            <div class="pillar-val">{p_data['score']:.0f} / {p_data['max']}</div>
        </div>
""")
        html_parts.append("""    </div>""")

    # 2. NET WORTH BALANCE SHEET
    if "net_worth_balance_sheet" in sections:
        html_parts.append(f"""
    <div class="section-card">
        <div class="section-title">💰 Net Worth & Wealth Balance Sheet</div>
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-label">Total Assets</div>
                <div class="kpi-value" style="color:#10b981;">₹{m['total_assets']:,.0f}</div>
                <div class="kpi-sub">Portfolio + Liquid Cash</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Total Liabilities</div>
                <div class="kpi-value" style="color:#ef4444;">₹{m['tot_debt']:,.0f}</div>
                <div class="kpi-sub">Outstanding Loans & EMIs</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Net Worth</div>
                <div class="kpi-value" style="color:#0f172a;">₹{m['net_worth']:,.0f}</div>
                <div class="kpi-sub">Assets − Liabilities</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Monthly Savings Rate</div>
                <div class="kpi-value" style="color:#3b82f6;">{m['savings_rate']:.1f}%</div>
                <div class="kpi-sub">₹{m['monthly_savings']:,.0f} saved / mo</div>
            </div>
        </div>
    </div>
""")

    # 3. INVESTMENT PORTFOLIO AUDIT
    if "investments_audit" in sections and inv_df is not None and not inv_df.empty:
        html_parts.append(f"""
    <div class="section-card">
        <div class="section-title">📈 Investment Portfolio & Holdings Review</div>
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-label">Portfolio Value</div>
                <div class="kpi-value">₹{m['tot_portfolio']:,.0f}</div>
                <div class="kpi-sub">₹{m['tot_invested']:,.0f} invested</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Unrealised Returns</div>
                <div class="kpi-value" style="color:{'#10b981' if m['unrealized_pnl'] >= 0 else '#ef4444'};">
                    {'+' if m['unrealized_pnl'] >= 0 else ''}₹{m['unrealized_pnl']:,.0f}
                </div>
                <div class="kpi-sub">{m['return_pct']:+.1f}% overall return</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Holdings Count</div>
                <div class="kpi-value">{len(inv_df)}</div>
                <div class="kpi-sub">Across asset classes</div>
            </div>
        </div>
""")
        # If algorithmic advisor results are available
        if algo:
            tier_name = algo.get("tier", "Moderate")
            summary_text = algo.get("summary", "")
            html_parts.append(f"""
        <div style="background:#f1f5f9; padding:12px 16px; border-radius:6px; margin-bottom:16px;">
            <div style="font-weight:700; color:#0f172a; font-size:13px;">🧠 Algorithmic Model Recommendation ({tier_name} Tier)</div>
            <div style="font-size:12px; color:#475569; margin-top:4px;">{summary_text}</div>
        </div>
""")

        if include_holding_details:
            html_parts.append("""
        <table>
            <thead>
                <tr>
                    <th>Asset Name / Ticker</th>
                    <th>Type / Sleeve</th>
                    <th style="text-align:right;">Invested (₹)</th>
                    <th style="text-align:right;">Current (₹)</th>
                    <th style="text-align:right;">Return</th>
                    <th style="text-align:center;">Action</th>
                </tr>
            </thead>
            <tbody>
""")
            decisions = algo.get("decisions", [])
            dec_map = {d["holding"]: d for d in decisions} if decisions else {}

            for _, row in inv_df.iterrows():
                h_name = str(row.get("description") or row.get("resolved_name") or row.get("platform") or "Holding")
                h_type = str(row.get("investment_type") or "Equity")
                h_inv = float(row.get("investment_amount", 0.0))
                h_cur = float(row.get("current_value", 0.0))
                h_ret = ((h_cur - h_inv) / h_inv * 100.0) if h_inv > 0 else 0.0

                dec_info = dec_map.get(h_name, {})
                action = dec_info.get("action", "HOLD")
                action_badge = f'<span class="badge badge-{action.lower()}">{action}</span>'

                html_parts.append(f"""
                <tr>
                    <td><strong>{h_name}</strong></td>
                    <td>{h_type}</td>
                    <td style="text-align:right;">₹{h_inv:,.0f}</td>
                    <td style="text-align:right;">₹{h_cur:,.0f}</td>
                    <td style="text-align:right; color:{'#10b981' if h_ret >= 0 else '#ef4444'}; font-weight:600;">{h_ret:+.1f}%</td>
                    <td style="text-align:center;">{action_badge}</td>
                </tr>
""")
            html_parts.append("""
            </tbody>
        </table>
""")
        html_parts.append("""    </div>""")

    # 4. DEBT & LIABILITIES
    if "debt_schedule" in sections:
        html_parts.append(f"""
    <div class="section-card">
        <div class="section-title">🏦 Debt & Liabilities Audit</div>
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-label">Total Debt</div>
                <div class="kpi-value" style="color:#ef4444;">₹{m['tot_debt']:,.0f}</div>
                <div class="kpi-sub">{len(debts_df) if debts_df is not None and not debts_df.empty else 0} active loans</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Monthly EMI Burden</div>
                <div class="kpi-value">₹{m['monthly_emi']:,.0f}</div>
                <div class="kpi-sub">{m['dti_pct']:.1f}% of income (DTI)</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Debt-to-Asset</div>
                <div class="kpi-value">{m['debt_to_asset_pct']:.1f}%</div>
                <div class="kpi-sub">Benchmark: &lt; 30%</div>
            </div>
        </div>
""")
        if debts_df is not None and not debts_df.empty:
            html_parts.append("""
        <table>
            <thead>
                <tr>
                    <th>Loan / Facility Name</th>
                    <th>Category</th>
                    <th style="text-align:right;">Outstanding (₹)</th>
                    <th style="text-align:right;">Interest Rate</th>
                    <th style="text-align:right;">Monthly EMI</th>
                </tr>
            </thead>
            <tbody>
""")
            for _, d_row in debts_df.iterrows():
                d_name = str(d_row.get("debt_name", "Loan"))
                d_cat = str(d_row.get("debt_category", "Personal"))
                d_out = float(d_row.get("outstanding_principal", 0.0))
                d_rate = float(d_row.get("interest_rate", 0.0))
                d_emi = float(d_row.get("monthly_emi", 0.0))
                html_parts.append(f"""
                <tr>
                    <td><strong>{d_name}</strong></td>
                    <td>{d_cat}</td>
                    <td style="text-align:right; font-weight:600; color:#ef4444;">₹{d_out:,.0f}</td>
                    <td style="text-align:right;">{d_rate:.1f}%</td>
                    <td style="text-align:right;">₹{d_emi:,.0f}</td>
                </tr>
""")
            html_parts.append("""
            </tbody>
        </table>
""")
        else:
            html_parts.append("""<p style="color:#10b981; font-weight:600; font-size:13px;">✅ Congratulations! You have no outstanding debt liabilities logged.</p>""")
        html_parts.append("""    </div>""")

    # 5. CASH FLOW & EMERGENCY RUNWAY
    if "cashflow_emergency" in sections:
        html_parts.append(f"""
    <div class="section-card">
        <div class="section-title">💵 Cash Flow & Emergency Runway</div>
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-label">Monthly Inflow</div>
                <div class="kpi-value">₹{m['monthly_income']:,.0f}</div>
                <div class="kpi-sub">Total Take-Home</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Monthly Outflow</div>
                <div class="kpi-value">₹{m['monthly_expenses']:,.0f}</div>
                <div class="kpi-sub">Living Expenses + EMIs</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Liquid Reserves</div>
                <div class="kpi-value">₹{m['available_liquid']:,.0f}</div>
                <div class="kpi-sub">Cash & Liquid Funds</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Emergency Runway</div>
                <div class="kpi-value" style="color:{'#10b981' if m['emergency_runway_months'] >= 6.0 else '#f59e0b'};">
                    {m['emergency_runway_months']:.1f} Months
                </div>
                <div class="kpi-sub">Recommended: 6.0 Mos</div>
            </div>
        </div>
    </div>
""")

    # 6. ACTIONABLE RECOMMENDATIONS & TAX CHECKLIST
    if "actionable_recommendations" in sections:
        html_parts.append("""
    <div class="section-card">
        <div class="section-title">💡 Strategic Wealth & Tax Action Plan</div>
        
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4 style="font-size:13px; font-weight:700; color:#10b981; margin-bottom:10px;">🌟 Key Financial Strengths</h4>
                <ul class="bullet-list">
""")
        if health_data["strengths"]:
            for s in health_data["strengths"]:
                html_parts.append(f"<li>{s}</li>")
        else:
            html_parts.append("<li>Baseline profile established; ready for structured financial optimization.</li>")

        html_parts.append("""
                </ul>
            </div>
            <div>
                <h4 style="font-size:13px; font-weight:700; color:#ef4444; margin-bottom:10px;">⚡ High-Priority Improvement Areas</h4>
                <ul class="bullet-list">
""")
        if health_data["improvement_areas"]:
            for imp in health_data["improvement_areas"]:
                html_parts.append(f"<li>{imp}</li>")
        else:
            html_parts.append("<li>All core financial metrics meet or exceed optimal benchmark standards!</li>")

        html_parts.append(f"""
                </ul>
            </div>
        </div>

        <div style="margin-top:20px; padding-top:16px; border-top:1px solid #f1f5f9;">
            <h4 style="font-size:13px; font-weight:700; color:#0f172a; margin-bottom:10px;">🛡️ Protection & Tax Optimization Checklist</h4>
            <ul class="bullet-list">
                <li><strong>Tax Harvesting (LTCG):</strong> Utilize the ₹1.25 Lakh annual long-term capital gains tax-free exemption threshold on listed equities.</li>
                <li><strong>Sec 80C & 80D:</strong> Ensure ₹1.5 Lakh 80C limit (PPF, ELSS, EPF) and ₹25k/₹50k 80D health insurance deductions are fully maximized.</li>
                <li><strong>Term Insurance Rule:</strong> Maintain pure term life insurance coverage equal to 10x–15x your annual income (₹{(m['monthly_income']*12*12):,.0f} benchmark).</li>
                <li><strong>Comprehensive Health Cover:</strong> Base policy of ₹10L + Super Top-up of ₹25L–₹50L for the household to insulate investments against medical contingencies.</li>
            </ul>
        </div>
    </div>
""")

    # FOOTER
    html_parts.append("""
    <div style="margin-top: 30px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px;">
        Generated by FinCompass Wealth Intelligence Engine · Confidential & Privileged Personal Financial Report
    </div>
</div>

</body>
</html>
""")

    return "".join(html_parts)


# =====================================================================
# 3. MULTI-SHEET EXCEL WORKBOOK GENERATOR (.xlsx)
# =====================================================================

def generate_excel_report(
    user: Dict[str, Any],
    health_data: Dict[str, Any],
    inv_df: Optional[pd.DataFrame] = None,
    debts_df: Optional[pd.DataFrame] = None,
    options: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generates a structured, professional multi-tab Excel workbook (.xlsx).
    """
    options = options or {}
    sections = options.get("sections", [
        "executive_summary",
        "net_worth_balance_sheet",
        "investments_audit",
        "debt_schedule",
        "actionable_recommendations"
    ])
    custom_title = options.get("title", "Financial Health Report")
    m = health_data["metrics"]
    user_name = user.get("full_name") or user.get("username", "Client")

    if not HAS_OPENPYXL:
        lines = []
        lines.append(f"{custom_title}")
        lines.append(f"Client: {user_name}, Date: {health_data['generated_at']}")
        lines.append(f"Score: {health_data['score']}/100, Rating: {health_data['rating']}")
        lines.append("")
        lines.append("METRIC,VALUE,BENCHMARK")
        lines.append(f"Total Assets,₹{m['total_assets']:,.0f},Portfolio + Liquid")
        lines.append(f"Total Debt,₹{m['tot_debt']:,.0f},Outstanding Loans")
        lines.append(f"Net Worth,₹{m['net_worth']:,.0f},Assets - Liabilities")
        lines.append(f"Savings Rate,{m['savings_rate']:.1f}%,Target: >= 20%")
        lines.append(f"Emergency Runway,{m['emergency_runway_months']:.1f} Mos,Target: >= 6 Mos")
        if "investments_audit" in sections and inv_df is not None and not inv_df.empty:
            lines.append("")
            lines.append("HOLDING,TYPE,INVESTED,CURRENT")
            for _, r in inv_df.iterrows():
                h_name = str(r.get("description") or r.get("resolved_name") or "Holding")
                lines.append(f'"{h_name}",{r.get("investment_type","Equity")},{r.get("investment_amount",0)},{r.get("current_value",0)}')
        return "\n".join(lines).encode("utf-8")

    wb = Workbook()
    # remove default sheet
    wb.remove(wb.active)

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    kpi_val_font = Font(name="Calibri", size=13, bold=True, color="0369A1")

    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    m = health_data["metrics"]
    user_name = user.get("full_name") or user.get("username", "Client")

    # SHEET 1: Executive Summary & Health Score
    if "executive_summary" in sections or "net_worth_balance_sheet" in sections:
        ws1 = wb.create_sheet(title="Executive Summary")
        ws1.append([custom_title])
        ws1.append([f"Client: {user_name}", f"Date: {health_data['generated_at']}"])
        ws1.append([])

        ws1.cell(row=1, column=1).font = title_font
        ws1.cell(row=2, column=1).font = bold_font

        # Score & Rating Box
        ws1.append(["OVERALL FINANCIAL HEALTH SCORE", health_data["score"], "out of 100", f"Rating: {health_data['rating']}"])
        ws1.append(["Verdict", health_data["verdict"]])
        ws1.append([])

        # KPI Summary Table
        ws1.append(["Key Financial Metric", "Value", "Benchmark / Notes"])
        ws1.append(["Total Assets", m["total_assets"], "Portfolio + Liquid Cash"])
        ws1.append(["Total Liabilities", m["tot_debt"], "Outstanding Loans & EMIs"])
        ws1.append(["Net Worth", m["net_worth"], "Total Assets − Liabilities"])
        ws1.append(["Monthly Savings Rate", f"{m['savings_rate']:.1f}%", "Target: ≥ 20%"])
        ws1.append(["Monthly Inflow", m["monthly_income"], "Take-Home Income"])
        ws1.append(["Monthly Expenses", m["monthly_expenses"], "Living Expenses + EMIs"])
        ws1.append(["Emergency Runway", f"{m['emergency_runway_months']:.1f} Months", "Target: ≥ 6 Months"])
        ws1.append(["Debt-to-Income (DTI)", f"{m['dti_pct']:.1f}%", "Target: < 30%"])
        ws1.append([])

        # Style Table Header
        for col_idx in range(1, 4):
            c = ws1.cell(row=7, column=col_idx)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="left")

        # Format Currency Cells
        for r in [8, 9, 10, 12, 13]:
            ws1.cell(row=r, column=2).number_format = '₹#,##0'

    # SHEET 2: Investments & Holdings Audit
    if "investments_audit" in sections and inv_df is not None and not inv_df.empty:
        ws2 = wb.create_sheet(title="Investments Audit")
        ws2.append(["Investment Portfolio & Holdings Review"])
        ws2.append([f"Total Value: ₹{m['tot_portfolio']:,.0f}", f"Unrealized Gain: ₹{m['unrealized_pnl']:,.0f} ({m['return_pct']:+.1f}%)"])
        ws2.append([])

        ws2.cell(row=1, column=1).font = title_font
        ws2.cell(row=2, column=1).font = bold_font

        headers = ["Holding / Asset Name", "Asset Type", "Invested Amount", "Current Value", "Unrealized P&L", "Return %", "Action"]
        ws2.append(headers)

        for col_idx in range(1, len(headers) + 1):
            c = ws2.cell(row=4, column=col_idx)
            c.fill = header_fill
            c.font = header_font

        algo = health_data.get("algo_advice") or {}
        dec_map = {d["holding"]: d for d in algo.get("decisions", [])}

        curr_row = 5
        for _, r in inv_df.iterrows():
            name = str(r.get("description") or r.get("resolved_name") or r.get("platform") or "Holding")
            atype = str(r.get("investment_type") or "Equity")
            inv_amt = float(r.get("investment_amount", 0.0))
            cur_amt = float(r.get("current_value", 0.0))
            pnl = cur_amt - inv_amt
            ret = (pnl / inv_amt * 100.0) if inv_amt > 0 else 0.0
            act = dec_map.get(name, {}).get("action", "HOLD")

            ws2.append([name, atype, inv_amt, cur_amt, pnl, f"{ret:+.1f}%", act])

            ws2.cell(row=curr_row, column=3).number_format = '₹#,##0'
            ws2.cell(row=curr_row, column=4).number_format = '₹#,##0'
            ws2.cell(row=curr_row, column=5).number_format = '₹#,##0'
            curr_row += 1

    # SHEET 3: Debts & Liabilities Schedule
    if "debt_schedule" in sections:
        ws3 = wb.create_sheet(title="Debts & Liabilities")
        ws3.append(["Debt Schedule & Liabilities Audit"])
        ws3.append([f"Total Debt: ₹{m['tot_debt']:,.0f}", f"Monthly EMI: ₹{m['monthly_emi']:,.0f}"])
        ws3.append([])

        ws3.cell(row=1, column=1).font = title_font
        ws3.cell(row=2, column=1).font = bold_font

        d_headers = ["Debt / Facility Name", "Category", "Outstanding Principal", "Interest Rate (%)", "Monthly EMI", "Tenure (Mos)"]
        ws3.append(d_headers)

        for col_idx in range(1, len(d_headers) + 1):
            c = ws3.cell(row=4, column=col_idx)
            c.fill = header_fill
            c.font = header_font

        curr_d_row = 5
        if debts_df is not None and not debts_df.empty:
            for _, dr in debts_df.iterrows():
                ws3.append([
                    str(dr.get("debt_name", "Loan")),
                    str(dr.get("debt_category", "Personal")),
                    float(dr.get("outstanding_principal", 0.0)),
                    float(dr.get("interest_rate", 0.0)),
                    float(dr.get("monthly_emi", 0.0)),
                    int(dr.get("tenure_months", 0)) if pd.notnull(dr.get("tenure_months")) else 0,
                ])
                ws3.cell(row=curr_d_row, column=3).number_format = '₹#,##0'
                ws3.cell(row=curr_d_row, column=5).number_format = '₹#,##0'
                curr_d_row += 1
        else:
            ws3.append(["No active debts logged", "-", 0, 0, 0, 0])

    # SHEET 4: Recommendations & Suggestions
    if "actionable_recommendations" in sections:
        ws4 = wb.create_sheet(title="Action Plan & Tax")
        ws4.append(["Strategic Action Plan & Recommendations"])
        ws4.append([])
        ws4.cell(row=1, column=1).font = title_font

        ws4.append(["Category", "Recommendation / Suggestion", "Priority / Benchmark"])
        for col_idx in range(1, 4):
            c = ws4.cell(row=3, column=col_idx)
            c.fill = header_fill
            c.font = header_font

        rec_rows = [
            ("Emergency Buffer", f"Build liquid reserves to cover 6 months (Target: ₹{(m['monthly_expenses']*6):,.0f})", "High"),
            ("Debt Optimization", "Pay off high-interest personal loans / credit card balances first (Avalanche Method)", "High"),
            ("Tax Planning", "Maximize ₹1.5L Sec 80C and ₹25k/₹50k Sec 80D health insurance deductions", "Medium"),
            ("Capital Gains", "Utilize ₹1.25L annual LTCG tax-free exemption threshold on listed equities", "Medium"),
            ("Life Insurance", f"Term cover target of 10x–15x annual income (Benchmark: ₹{(m['monthly_income']*12*12):,.0f})", "High"),
            ("Portfolio Rebalance", "Review and trim asset class sleeves that have drifted > 5% from target weights", "Medium"),
        ]
        for r in rec_rows:
            ws4.append(list(r))

    # Auto-adjust column widths across all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# =====================================================================
# 4. STREAMLIT UI RENDERER
# =====================================================================

def render_financial_health_report_ui(
    current_user: Dict[str, Any],
    inv_df: Optional[pd.DataFrame] = None,
    debts_df: Optional[pd.DataFrame] = None,
    income_df: Optional[pd.DataFrame] = None,
    expenses_df: Optional[pd.DataFrame] = None,
    monthly_income: float = 0.0,
    monthly_expenses: float = 0.0,
    liquid_cash: float = 0.0,
):
    """
    Renders the Financial Health Status card, report customization controls,
    and download buttons (Print-ready HTML/PDF & Excel .xlsx).
    """
    import streamlit as st
    import streamlit.components.v1 as components

    health_data = compute_financial_health(
        user=current_user,
        inv_df=inv_df,
        debts_df=debts_df,
        income_df=income_df,
        expenses_df=expenses_df,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        liquid_cash=liquid_cash,
    )

    m = health_data["metrics"]
    score = health_data["score"]
    rating = health_data["rating"]
    rating_color = health_data["rating_color"]
    today_str = datetime.date.today().strftime("%Y%m%d")
    clean_user = (current_user.get("username") or "user").replace(" ", "_")

    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <h3 style="color:#ffffff; margin:0 0 4px 0; font-size:1.3rem;">📑 Financial Health Status & Custom Wealth Audit Report</h3>
                <p style="color:#94a3b8; font-size:0.88rem; margin:0;">
                    Instant 360° diagnostic across net worth, investments, debt burden, cash flow runway, and tax optimization.
                </p>
            </div>
            <div style="text-align:right;">
                <span style="font-size:2rem; font-weight:800; color:""" + rating_color + f""";">{score:.0f}</span>
                <span style="color:#64748b; font-size:0.9rem;"> / 100</span>
                <div style="display:inline-block; margin-left:10px; background:rgba(255,255,255,0.1); padding:4px 10px; border-radius:14px; font-size:0.8rem; font-weight:700; color:""" + rating_color + f""";">
                    {rating}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mini metric cards
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Net Worth", f"₹{m['net_worth']:,.0f}", help="Total Assets (Portfolio + Liquid) minus Liabilities")
    with mc2:
        st.metric("Portfolio Value", f"₹{m['tot_portfolio']:,.0f}", f"{m['return_pct']:+.1f}% P&L")
    with mc3:
        st.metric("Total Debt", f"₹{m['tot_debt']:,.0f}", f"DTI: {m['dti_pct']:.1f}%")
    with mc4:
        st.metric("Emergency Runway", f"{m['emergency_runway_months']:.1f} Months", f"Savings: {m['savings_rate']:.0f}%")

    # Customization Controls Expander
    with st.expander("⚙️ Customise What to Include in Your Report", expanded=False):
        st.caption("Select specific sections, detail level, and add a personal goal/note to generate a tailored report.")
        
        c_col1, c_col2 = st.columns([1.4, 1])
        with c_col1:
            st.markdown("##### 📌 Select Report Sections")
            inc_exec = st.checkbox("Executive Summary & 5-Pillar Health Score (0–100)", value=True, key="rep_sec_exec")
            inc_nw = st.checkbox("Net Worth & Wealth Balance Sheet (Assets vs Liabilities)", value=True, key="rep_sec_nw")
            inc_inv = st.checkbox("Investment Portfolio Review & Holdings Audit", value=True, key="rep_sec_inv")
            inc_debt = st.checkbox("Debt & Liabilities Amortization Schedule", value=True, key="rep_sec_debt")
            inc_cash = st.checkbox("Cash Flow, Monthly Burn & Emergency Runway", value=True, key="rep_sec_cash")
            inc_sugg = st.checkbox("Algorithmic Rebalancing, Tax & Insurance Suggestions", value=True, key="rep_sec_sugg")
            
        with c_col2:
            st.markdown("##### 📝 Formatting & Personalization")
            custom_title = st.text_input("Report Title", value="Comprehensive Financial Health & Wealth Audit Report", key="rep_title")
            inc_holding_details = st.checkbox("Include Individual Holding Rows in Table", value=True, key="rep_inc_rows")
            custom_note = st.text_area("Personal Goal / Note for Report Cover", value="", placeholder="e.g. Annual financial health check preparing for home purchase in 2027.", key="rep_note")

    # Build chosen sections list
    chosen_sections = []
    if inc_exec: chosen_sections.append("executive_summary")
    if inc_nw: chosen_sections.append("net_worth_balance_sheet")
    if inc_inv: chosen_sections.append("investments_audit")
    if inc_debt: chosen_sections.append("debt_schedule")
    if inc_cash: chosen_sections.append("cashflow_emergency")
    if inc_sugg: chosen_sections.append("actionable_recommendations")

    report_options = {
        "title": custom_title,
        "custom_note": custom_note,
        "sections": chosen_sections,
        "include_holding_details": inc_holding_details,
    }

    # Generate documents
    html_report = generate_html_report(
        user=current_user,
        health_data=health_data,
        inv_df=inv_df,
        debts_df=debts_df,
        options=report_options
    )

    excel_report = generate_excel_report(
        user=current_user,
        health_data=health_data,
        inv_df=inv_df,
        debts_df=debts_df,
        options=report_options
    )

    # Action buttons for download & preview
    st.markdown("##### 📥 Download Customised Report")
    d1, d2, d3 = st.columns([1.2, 1.2, 1])
    with d1:
        st.download_button(
            label="🖨️ Download Print-Ready HTML / PDF",
            data=html_report,
            file_name=f"Financial_Health_Report_{clean_user}_{today_str}.html",
            mime="text/html",
            type="primary",
            use_container_width=True,
            help="Download as HTML. Open in any browser and press Ctrl+P / Cmd+P to print or save directly as a clean PDF."
        )
    with d2:
        st.download_button(
            label="📊 Download Excel Workbook (.xlsx)",
            data=excel_report,
            file_name=f"Financial_Health_Report_{clean_user}_{today_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True,
            help="Download multi-tab formatted Excel sheet with KPI summaries, holdings audit, and debt schedule."
        )
    with d3:
        show_preview = st.toggle("👁️ Preview Report", value=False, key="rep_toggle_preview")

    if show_preview:
        st.markdown("#### 📄 In-App Report Live Preview")
        components.html(html_report, height=700, scrolling=True)

