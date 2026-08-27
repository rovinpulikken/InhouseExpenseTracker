"""
tax_engine.py — Enhanced India Income & Tax Planner Engine (FY 2025-26)

Provides:
  1. Passive income auto-derivation from investment holdings
     (FRSB bonds, SGB, FD, equity dividends via yfinance, MF IDCW)
  2. Capital gains document parsing
     (Zerodha Tax P&L PDF, ICICI Direct CG PDF, CAMS/KFintech CAS PDF,
      IT Dept AIS JSON, manual entry fallback)
  3. Full India deduction waterfall (80C, 80D, HRA, 24b, NPS, 80TTA, professional tax)
  4. Regime comparison (New vs Old) with complete deductions
  5. Advance tax quarterly instalment schedule
"""

import re
import datetime
import io
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ─── RBI / Statutory Rates (hardcoded, updated quarterly) ────────────────────
FRSB_RATE: float = 0.0805           # 8.05% p.a. (Jul–Dec 2025)
FRSB_RATE_EFFECTIVE: str = "Jul 2025"
FRSB_PAYMENT_MONTHS: Tuple[int, int] = (1, 7)   # January and July

SGB_COUPON_RATE: float = 0.025      # 2.5% p.a. semi-annual
SGB_PAYMENT_MONTHS: Tuple[int, int] = (1, 7)

DEFAULT_FD_RATE: float = 0.070
DEFAULT_RD_RATE: float = 0.068
NSC_RATE: float = 0.0724            # Q1 2025
SCSS_RATE: float = 0.082            # Q1 2025
PPF_RATE: float = 0.071             # Q1 2025
EPF_RATE: float = 0.0815            # FY 2024-25 (EPFO declared)

SAVINGS_INTEREST_80TTA_EXEMPT: float = 10_000.0

# ─── CG Tax Rates (post-Budget 2024, FY 2025-26) ─────────────────────────────
LTCG_EQUITY_EXEMPT: float = 125_000.0
LTCG_EQUITY_RATE: float = 0.125
STCG_EQUITY_RATE: float = 0.20
LTCG_PROPERTY_RATE: float = 0.125

# ─── Advance Tax Due Dates (FY 2025-26) ──────────────────────────────────────
ADVANCE_TAX_SCHEDULE: List[Dict[str, Any]] = [
    {"instalment": "1st",  "due_date": datetime.date(2025, 6, 15),  "cumulative_pct": 0.15},
    {"instalment": "2nd",  "due_date": datetime.date(2025, 9, 15),  "cumulative_pct": 0.45},
    {"instalment": "3rd",  "due_date": datetime.date(2025, 12, 15), "cumulative_pct": 0.75},
    {"instalment": "4th",  "due_date": datetime.date(2026, 3, 15),  "cumulative_pct": 1.00},
]

# ─── Investment-type keyword sets (match against investment_type column values) ─
# These match via substring: if any keyword is contained in the investment_type string
_FRSB_KEYWORDS   = {"frsb", "floating rate savings bond", "rbi savings bond", "goi savings bond", "rbi frsb"}
_SGB_KEYWORDS    = {"sgb", "sovereign gold bond", "gold bond"}
_FD_KEYWORDS     = {"fixed deposit", "fd", "term deposit", "bank fd", "fixed deposits"}
_RD_KEYWORDS     = {"recurring deposit", "rd"}
_PPF_KEYWORDS    = {"ppf", "public provident fund"}
_NSC_KEYWORDS    = {"nsc", "national savings certificate"}
_SCSS_KEYWORDS   = {"scss", "senior citizen savings scheme"}
_EPF_KEYWORDS    = {"epf", "epfo", "employee provident fund", "vpf", "provident fund"}
_EQUITY_KEYWORDS = {"equity", "stock", "share", "nse", "bse", "equity (stocks)"}

# ─── Income-source type keywords (for scanning income_sources table entries) ───
_FRSB_INCOME_KEYWORDS = {"frsb", "floating rate", "rbi bond", "rbi savings", "goi bond", "savings bond"}
_PPF_INCOME_KEYWORDS  = {"ppf", "public provident fund"}
_EPF_INCOME_KEYWORDS  = {"epf", "epfo", "provident fund", "vpf"}
_FD_INCOME_KEYWORDS   = {"fixed deposit", "fd interest", "term deposit", "bank interest"}
_SCSS_INCOME_KEYWORDS = {"scss", "senior citizen savings"}
_NSC_INCOME_KEYWORDS  = {"nsc", "national savings cert"}


def _itype_matches(investment_type: str, keywords: set) -> bool:
    t = investment_type.lower().strip()
    return any(k in t for k in keywords)


def _parse_rate_from_description(desc: str) -> Optional[float]:
    if not desc:
        return None
    patterns = [
        r"(\d+\.?\d*)\s*%\s*p\.?a\.?",
        r"@\s*(\d+\.?\d*)\s*%",
        r"rate[:\s]+(\d+\.?\d*)\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, desc, re.IGNORECASE)
        if m:
            try:
                rate = float(m.group(1))
                if 1.0 <= rate <= 20.0:
                    return rate / 100.0
            except ValueError:
                continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. PASSIVE INCOME AUTO-DERIVATION
# ─────────────────────────────────────────────────────────────────────────────

def derive_investment_income(
    holdings_df: pd.DataFrame,
    income_sources_df: Optional[pd.DataFrame] = None,
) -> List[Dict[str, Any]]:
    """
    Scan portfolio holdings AND income sources and return auto-computed passive income entries.
    - holdings_df: investments table DataFrame
    - income_sources_df: income_sources table DataFrame (optional, for FRSB/EPF stored as income)
    """
    if holdings_df is None or holdings_df.empty:
        holdings_df = pd.DataFrame()

    entries: List[Dict[str, Any]] = []
    seen_names: set = set()  # avoid double-counting

    # ── SCAN PORTFOLIO HOLDINGS ──────────────────────────────────────────────
    for _, row in holdings_df.iterrows():
        itype    = str(row.get("investment_type", "")).strip()
        desc     = str(row.get("description", "")).strip()
        name     = str(row.get("resolved_name", "") or row.get("platform", "")).strip()
        invested = float(row.get("investment_amount", 0.0))
        units    = float(row.get("units", 0.0))

        match_text = f"{itype} {name} {desc}"

        if _itype_matches(match_text, _FRSB_KEYWORDS):
            annual = round(invested * FRSB_RATE, 2)
            label = name or "RBI FRSB Bond"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Fully Taxable (Other Sources)",
                "payment_months": list(FRSB_PAYMENT_MONTHS),
                "notes": f"RBI FRSB rate {FRSB_RATE*100:.2f}% p.a. (effective {FRSB_RATE_EFFECTIVE}). Semi-annual Jan & Jul.",
                "derivation_method": "RBI declared rate",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _SGB_KEYWORDS):
            annual = round(invested * SGB_COUPON_RATE, 2)
            label = name or "Sovereign Gold Bond"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Fully Taxable (Other Sources)",
                "payment_months": list(SGB_PAYMENT_MONTHS),
                "notes": "SGB coupon 2.5% p.a. on issue price. Semi-annual Jan & Jul. Redemption gains after 8 yrs are exempt.",
                "derivation_method": "Statutory SGB coupon",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _FD_KEYWORDS):
            rate = _parse_rate_from_description(desc) or DEFAULT_FD_RATE
            annual = round(invested * rate, 2)
            label = name or "Fixed Deposit"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Fully Taxable (Other Sources). TDS @10% by bank.",
                "payment_months": None,
                "notes": f"Rate: {rate*100:.1f}% p.a. {'(from description)' if _parse_rate_from_description(desc) else '(estimate — add rate in Description field)'}",
                "derivation_method": "Rate from description or 7% default",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _RD_KEYWORDS):
            rate = _parse_rate_from_description(desc) or DEFAULT_RD_RATE
            annual = round(invested * rate, 2)
            label = name or "Recurring Deposit"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Fully Taxable (Other Sources). TDS @10% by bank.",
                "payment_months": None,
                "notes": f"Rate: {rate*100:.1f}% p.a. (estimate)",
                "derivation_method": "Rate from description or 6.8% default",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _NSC_KEYWORDS):
            annual = round(invested * NSC_RATE, 2)
            label = name or "NSC"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Taxable; re-invested interest qualifies as 80C each year",
                "payment_months": None,
                "notes": f"NSC rate {NSC_RATE*100:.2f}% p.a. Interest deemed re-invested, counts toward 80C.",
                "derivation_method": "Current NSC rate (Q1 2025)",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _SCSS_KEYWORDS):
            annual = round(invested * SCSS_RATE, 2)
            label = name or "SCSS"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income",
                "annual_amount": annual,
                "taxability": "Fully Taxable. 80TTB exemption ₹50K for senior citizens.",
                "payment_months": [3, 6, 9, 12],
                "notes": f"SCSS rate {SCSS_RATE*100:.1f}% p.a. (Q1 2025). Quarterly payments.",
                "derivation_method": "Current SCSS rate",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _PPF_KEYWORDS):
            annual = round(invested * PPF_RATE, 2)
            label = name or "PPF"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income (Exempt)",
                "annual_amount": annual,
                "taxability": "EXEMPT u/s 10(11) — EEE. Not added to taxable income.",
                "payment_months": [3],
                "notes": f"PPF rate {PPF_RATE*100:.1f}% p.a. Credited 31 Mar. Completely tax-free.",
                "derivation_method": "Current PPF rate",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(match_text, _EPF_KEYWORDS):
            # EPF interest is exempt up to 2.5L contribution per year (employer+employee)
            annual = round(invested * EPF_RATE, 2)
            label = name or "EPF / EPFO"
            entries.append({
                "source_name": label,
                "income_type": "Interest Income (Exempt up to threshold)",
                "annual_amount": annual,
                "taxability": "EXEMPT u/s 10(12) up to ₹2.5L contribution p.a. Taxable above that threshold.",
                "payment_months": [3],
                "notes": f"EPF interest rate {EPF_RATE*100:.2f}% p.a. (FY 2024-25). Credited Mar 31. Ensure own+employer contribution ≤ ₹2.5L to keep exempt.",
                "derivation_method": "Current EPFO declared rate",
                "override_allowed": True,
            })
            seen_names.add(label.lower())

        elif _itype_matches(itype, _EQUITY_KEYWORDS) and units > 0:
            ticker = str(row.get("platform", "")).strip()
            div_per_unit = _fetch_equity_dividend(ticker)
            annual = round(units * div_per_unit, 2)
            if annual > 0:
                label = name or ticker
                entries.append({
                    "source_name": label,
                    "income_type": "Dividend Income",
                    "annual_amount": annual,
                    "taxability": "Fully Taxable (Other Sources). TDS @10% if > ₹5,000 from one company.",
                    "payment_months": None,
                    "notes": f"Based on last 12-month declared dividends for {ticker}. Verify with dividend warrants.",
                    "derivation_method": "yfinance last-12m dividends",
                    "override_allowed": True,
                })
                seen_names.add(label.lower())

    # ── SCAN INCOME SOURCES for items that carry taxable interest/EPF income ─
    # (Some users enter FRSB, EPFO, FD interest directly as income sources
    #  rather than as portfolio holdings)
    if income_sources_df is not None and not income_sources_df.empty:
        for _, row in income_sources_df.iterrows():
            sname  = str(row.get("source_name", "")).strip()
            itype  = str(row.get("income_type", "")).strip()
            amount = float(row.get("amount", 0.0))
            freq   = str(row.get("frequency", "Monthly")).strip()

            # Convert to annual
            freq_mult = {"Monthly": 12, "Quarterly": 4, "Half-Yearly": 2, "Annual": 1, "One-Time": 1}
            annual_amt = amount * freq_mult.get(freq, 12)

            name_lower = sname.lower()
            itype_lower = itype.lower()

            # Skip if already captured from portfolio
            if name_lower in seen_names:
                continue

            # FRSB in income sources
            if any(k in name_lower or k in itype_lower for k in _FRSB_INCOME_KEYWORDS):
                entries.append({
                    "source_name": sname or "RBI FRSB Bond (Income)",
                    "income_type": "Interest Income",
                    "annual_amount": annual_amt,
                    "taxability": "Fully Taxable (Other Sources)",
                    "payment_months": list(FRSB_PAYMENT_MONTHS),
                    "notes": f"From income sources. RBI FRSB current rate {FRSB_RATE*100:.2f}% p.a. — actual interest may differ if entered at coupon.",
                    "derivation_method": "Income source entry (FRSB detected)",
                    "override_allowed": True,
                })
                seen_names.add(name_lower)

            # PPF in income sources
            elif any(k in name_lower or k in itype_lower for k in _PPF_INCOME_KEYWORDS):
                entries.append({
                    "source_name": sname or "PPF (Income)",
                    "income_type": "Interest Income (Exempt)",
                    "annual_amount": annual_amt,
                    "taxability": "EXEMPT u/s 10(11) — EEE.",
                    "payment_months": [3],
                    "notes": f"From income sources. PPF interest rate {PPF_RATE*100:.1f}% p.a. completely tax-free.",
                    "derivation_method": "Income source entry (PPF detected)",
                    "override_allowed": True,
                })
                seen_names.add(name_lower)

            # EPF / EPFO in income sources
            elif any(k in name_lower or k in itype_lower for k in _EPF_INCOME_KEYWORDS):
                entries.append({
                    "source_name": sname or "EPF / EPFO",
                    "income_type": "Interest Income (Exempt up to threshold)",
                    "annual_amount": annual_amt,
                    "taxability": "EXEMPT u/s 10(12) up to ₹2.5L contribution p.a. Taxable above that threshold.",
                    "payment_months": [3],
                    "notes": "From income sources. EPF interest is credited in March. Taxable only if own contribution > ₹2.5L p.a.",
                    "derivation_method": "Income source entry (EPF/EPFO detected)",
                    "override_allowed": True,
                })
                seen_names.add(name_lower)

            # FD interest entered as income source
            elif any(k in name_lower or k in itype_lower for k in _FD_INCOME_KEYWORDS):
                entries.append({
                    "source_name": sname or "FD Interest",
                    "income_type": "Interest Income",
                    "annual_amount": annual_amt,
                    "taxability": "Fully Taxable (Other Sources). TDS @10% by bank.",
                    "payment_months": None,
                    "notes": "From income sources. Verify against bank interest certificate.",
                    "derivation_method": "Income source entry (FD interest detected)",
                    "override_allowed": True,
                })
                seen_names.add(name_lower)

            # SCSS interest entered as income source
            elif any(k in name_lower or k in itype_lower for k in _SCSS_INCOME_KEYWORDS):
                entries.append({
                    "source_name": sname or "SCSS Interest",
                    "income_type": "Interest Income",
                    "annual_amount": annual_amt,
                    "taxability": "Fully Taxable. 80TTB exemption ₹50K for senior citizens.",
                    "payment_months": [3, 6, 9, 12],
                    "notes": "From income sources. SCSS interest is paid quarterly.",
                    "derivation_method": "Income source entry (SCSS detected)",
                    "override_allowed": True,
                })
                seen_names.add(name_lower)

    # Deduplicate entries (aggregate amounts for exact same source_name and income_type)
    dedup_dict = {}
    for e in entries:
        key = (e["source_name"], e["income_type"])
        if key in dedup_dict:
            dedup_dict[key]["annual_amount"] = round(dedup_dict[key]["annual_amount"] + e["annual_amount"], 2)
            if dedup_dict[key]["notes"] != e["notes"]:
                dedup_dict[key]["notes"] += f" | {e['notes']}"
        else:
            dedup_dict[key] = dict(e)
            
    return list(dedup_dict.values())


def _fetch_equity_dividend(ticker: str) -> float:
    """Fetch last 12m declared dividends per share using yfinance. Returns 0.0 on error."""
    try:
        import yfinance as yf
        t = ticker.strip()
        if t and "." not in t:
            t = t + ".NS"
        hist = yf.Ticker(t).dividends
        if hist is None or hist.empty:
            return 0.0
        cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=12)
        recent = hist[hist.index >= cutoff]
        return float(recent.sum()) if not recent.empty else 0.0
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. CAPITAL GAINS PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _empty_cg() -> Dict[str, Any]:
    return {
        "equity_ltcg": 0.0, "equity_stcg": 0.0,
        "equity_mf_ltcg": 0.0, "equity_mf_stcg": 0.0,
        "debt_mf_ltcg": 0.0, "debt_mf_stcg": 0.0,
        "property_ltcg": 0.0, "property_stcg": 0.0,
        "other_ltcg": 0.0, "other_stcg": 0.0,
        "source": "manual", "raw_rows": [],
        "parse_errors": [],
        "total_ltcg": 0.0, "total_stcg": 0.0,
        "slab_income_addition": 0.0,
    }


def _sum_totals(r: Dict[str, Any]) -> Dict[str, Any]:
    r["total_ltcg"] = round(r["equity_ltcg"] + r["equity_mf_ltcg"] +
                            r["debt_mf_ltcg"] + r["property_ltcg"] + r["other_ltcg"], 2)
    r["total_stcg"] = round(r["equity_stcg"] + r["equity_mf_stcg"] +
                            r["debt_mf_stcg"] + r["property_stcg"] + r["other_stcg"], 2)
    r["slab_income_addition"] = round(r["debt_mf_ltcg"] + r["debt_mf_stcg"] +
                                      r["property_stcg"] + r["other_ltcg"] + r["other_stcg"], 2)
    return r


def _extract_pdf_text(raw_bytes: bytes, max_pages: int = 999) -> str:
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""


def _parse_amount(s: str) -> float:
    s = s.strip().replace(",", "").replace("\u20b9", "").replace("Rs", "").replace("INR", "").strip()
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return 0.0


def parse_capital_gains(uploaded_file, file_type_hint: str = "auto") -> Dict[str, Any]:
    """
    Parse a capital gains document (Zerodha/ICICI/CAMS/AIS/generic PDF) and return
    structured CG breakdown.
    """
    result = _empty_cg()
    if uploaded_file is None:
        return result

    fname = getattr(uploaded_file, "name", "").lower()

    # Read bytes
    if hasattr(uploaded_file, "read"):
        raw_bytes = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    else:
        raw_bytes = bytes(uploaded_file)

    if file_type_hint == "auto":
        if fname.endswith(".json"):
            file_type_hint = "ais"
        elif fname.endswith(".pdf"):
            sample = _extract_pdf_text(raw_bytes, max_pages=1).lower()
            if "zerodha" in sample or "kite" in sample:
                file_type_hint = "zerodha"
            elif "icici direct" in sample or "icici securities" in sample:
                file_type_hint = "icici"
            elif "cams" in sample or "kfintech" in sample or "consolidated account statement" in sample:
                file_type_hint = "cams"
            else:
                file_type_hint = "generic_pdf"
        else:
            file_type_hint = "generic_pdf"

    parsers = {
        "ais":         _parse_ais_json,
        "zerodha":     _parse_zerodha_pdf,
        "icici":       _parse_icici_pdf,
        "cams":        _parse_cams_pdf,
        "generic_pdf": _parse_generic_pdf,
    }
    parser = parsers.get(file_type_hint, _parse_generic_pdf)
    return parser(raw_bytes, result)


def _parse_zerodha_pdf(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    r["source"] = "Zerodha"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Could not extract text from Zerodha PDF.")
        return r

    # Total STCG / LTCG from Zerodha summary
    stcg_m = re.search(r"(?:total\s+)?short[\s\-]?term.*?([\d,]+\.?\d*)", text, re.IGNORECASE)
    ltcg_m = re.search(r"(?:total\s+)?long[\s\-]?term.*?([\d,]+\.?\d*)", text, re.IGNORECASE)
    eq_stcg_m = re.search(r"equity.*?stcg.*?([\d,]+\.?\d*)", text, re.IGNORECASE | re.DOTALL)
    eq_ltcg_m = re.search(r"equity.*?ltcg.*?([\d,]+\.?\d*)", text, re.IGNORECASE | re.DOTALL)
    mf_stcg_m = re.search(r"mutual\s*fund.*?stcg.*?([\d,]+\.?\d*)", text, re.IGNORECASE | re.DOTALL)
    mf_ltcg_m = re.search(r"mutual\s*fund.*?ltcg.*?([\d,]+\.?\d*)", text, re.IGNORECASE | re.DOTALL)

    if eq_stcg_m:
        r["equity_stcg"] = max(0.0, _parse_amount(eq_stcg_m.group(1)))
    elif stcg_m:
        r["equity_stcg"] = max(0.0, _parse_amount(stcg_m.group(1)))
    if eq_ltcg_m:
        r["equity_ltcg"] = max(0.0, _parse_amount(eq_ltcg_m.group(1)))
    elif ltcg_m:
        r["equity_ltcg"] = max(0.0, _parse_amount(ltcg_m.group(1)))
    if mf_stcg_m:
        r["equity_mf_stcg"] = max(0.0, _parse_amount(mf_stcg_m.group(1)))
    if mf_ltcg_m:
        r["equity_mf_ltcg"] = max(0.0, _parse_amount(mf_ltcg_m.group(1)))

    return _sum_totals(r)


def _parse_icici_pdf(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    r["source"] = "ICICI Direct"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Could not extract text from ICICI Direct PDF.")
        return r

    for pat, key in [
        (r"stcg.*?total.*?([\d,]+\.?\d*)", "equity_stcg"),
        (r"ltcg.*?total.*?([\d,]+\.?\d*)", "equity_ltcg"),
        (r"mutual\s*fund.*?stcg.*?([\d,]+\.?\d*)", "equity_mf_stcg"),
        (r"mutual\s*fund.*?ltcg.*?([\d,]+\.?\d*)", "equity_mf_ltcg"),
    ]:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            r[key] = max(0.0, _parse_amount(m.group(1)))
    return _sum_totals(r)


def _parse_cams_pdf(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    r["source"] = "CAMS / KFintech CAS"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Could not extract text from CAMS CAS PDF.")
        return r

    for pat, key in [
        (r"equity.*?ltcg.*?([\d,]+\.?\d*)", "equity_mf_ltcg"),
        (r"equity.*?stcg.*?([\d,]+\.?\d*)", "equity_mf_stcg"),
        (r"debt.*?ltcg.*?([\d,]+\.?\d*)", "debt_mf_ltcg"),
        (r"debt.*?stcg.*?([\d,]+\.?\d*)", "debt_mf_stcg"),
    ]:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            r[key] = max(0.0, _parse_amount(m.group(1)))
    return _sum_totals(r)


def _parse_ais_json(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    import json
    r["source"] = "IT Dept AIS"
    try:
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        r["parse_errors"].append(f"AIS JSON parse error: {e}")
        return r

    cg_list = (data.get("capitalGains") or
               data.get("annualInformationStatement", {}).get("capitalGains") or [])

    raw_rows = []
    for entry in cg_list:
        asset  = str(entry.get("assetType", entry.get("asset_type", ""))).lower()
        gain_t = str(entry.get("gainType", entry.get("gain_type", ""))).upper()
        amount = float(entry.get("amount", entry.get("gainAmount", 0)) or 0)
        raw_rows.append({"asset": asset, "gain_type": gain_t, "amount": amount})

        is_ltcg   = "LTCG" in gain_t
        is_equity = "equity" in asset and "mutual" not in asset and "fund" not in asset
        is_mf     = "mutual fund" in asset or ("equity" in asset and "fund" in asset)
        is_debt   = "debt" in asset or "bond" in asset
        is_prop   = "property" in asset or "land" in asset or "house" in asset

        if is_equity:
            r["equity_ltcg" if is_ltcg else "equity_stcg"] += amount
        elif is_mf:
            r["equity_mf_ltcg" if is_ltcg else "equity_mf_stcg"] += amount
        elif is_debt:
            r["debt_mf_ltcg" if is_ltcg else "debt_mf_stcg"] += amount
        elif is_prop:
            r["property_ltcg" if is_ltcg else "property_stcg"] += amount
        else:
            r["other_ltcg" if is_ltcg else "other_stcg"] += amount

    r["raw_rows"] = raw_rows
    for k in ["equity_ltcg","equity_stcg","equity_mf_ltcg","equity_mf_stcg",
              "debt_mf_ltcg","debt_mf_stcg","property_ltcg","property_stcg","other_ltcg","other_stcg"]:
        r[k] = round(r[k], 2)
    return _sum_totals(r)


def _parse_generic_pdf(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    r["source"] = "Generic PDF"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Cannot extract text. Use manual entry below.")
        return r
    for pat, key in [
        (r"(?:total\s+)?ltcg.*?([\d,]+\.?\d*)", "equity_ltcg"),
        (r"(?:total\s+)?stcg.*?([\d,]+\.?\d*)", "equity_stcg"),
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            r[key] = max(0.0, _parse_amount(m.group(1)))
    if not any([r["equity_ltcg"], r["equity_stcg"]]):
        r["parse_errors"].append("Unrecognised format. Figures not auto-extracted. Use manual entry.")
    return _sum_totals(r)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DEDUCTION WATERFALL
# ─────────────────────────────────────────────────────────────────────────────

def compute_deductions(deductions: Dict[str, Any], gross_salary: float, tax_regime: str) -> Dict[str, Any]:
    """Compute all applicable India deductions. Returns detail dict + total_deduction."""
    d = deductions
    regime_is_new = (tax_regime == "New Regime")
    age = int(d.get("age", 35))
    is_senior = age >= 60
    result: Dict[str, Any] = {}

    std_ded = 75_000.0 if regime_is_new else 50_000.0
    result["standard_deduction"] = std_ded

    if regime_is_new:
        result["professional_tax"]    = min(float(d.get("professional_tax", 0)), 2_400.0)
        result["nps_80ccd_1b"]        = 0.0
        result["nps_employer_80ccd2"] = min(float(d.get("nps_employer_80ccd2", 0)), gross_salary * 0.10)
        result["total_deduction"]     = round(result["standard_deduction"] +
                                              result["professional_tax"] +
                                              result["nps_employer_80ccd2"], 2)
        result["regime_note"] = "New Regime: Standard Deduction + NPS Employer (80CCD2) + Professional Tax."
        return result

    # Old Regime — full waterfall
    eighty_c_components = {
        "PPF":               float(d.get("ppf_contribution", 0)),
        "ELSS":              float(d.get("elss_investment", 0)),
        "LIC Premium":       float(d.get("lic_premium", 0)),
        "Home Loan Principal": float(d.get("home_loan_principal", 0)),
        "School Fees":       float(d.get("school_fees", 0)),
        "NSC Interest":      float(d.get("nsc_interest_reinvested", 0)),
        "EPF":               float(d.get("epf_contribution", 0)),
        "Tax-saver FD":      float(d.get("tax_saver_fd", 0)),
    }
    eighty_c_total = min(sum(eighty_c_components.values()), 150_000.0)
    result["eighty_c_components"] = eighty_c_components
    result["eighty_c"] = round(eighty_c_total, 2)

    self_limit    = 50_000.0 if is_senior else 25_000.0
    parents_limit = 50_000.0 if d.get("parents_senior", False) else 25_000.0
    eighty_d = (min(float(d.get("health_ins_self", 0)), self_limit) +
                min(float(d.get("health_ins_parents", 0)), parents_limit))
    result["eighty_d"]          = round(eighty_d, 2)
    result["eighty_d_self_cap"] = self_limit
    result["eighty_d_par_cap"]  = parents_limit

    nps_1b = min(float(d.get("nps_80ccd_1b", 0)), 50_000.0)
    result["nps_80ccd_1b"] = round(nps_1b, 2)

    hl_interest = min(float(d.get("home_loan_interest", 0)), 200_000.0)
    result["home_loan_interest_24b"] = round(hl_interest, 2)

    hra_exempt = 0.0
    hra_received = float(d.get("hra_received", 0))
    rent_paid    = float(d.get("rent_paid", 0))
    basic_salary = float(d.get("hra_basic_salary", gross_salary * 0.40))
    if hra_received > 0 and rent_paid > 0:
        metro_factor = 0.50 if d.get("metro_city", True) else 0.40
        hra_exempt = min(
            hra_received,
            basic_salary * metro_factor,
            max(0, rent_paid - basic_salary * 0.10)
        )
    result["hra_exemption"] = round(hra_exempt, 2)

    prof_tax = min(float(d.get("professional_tax", 0)), 2_400.0)
    result["professional_tax"] = round(prof_tax, 2)

    sb_interest   = float(d.get("savings_bank_interest", 0))
    scss_interest = float(d.get("scss_interest", 0))
    if is_senior:
        tta_ttb = min(sb_interest + scss_interest, 50_000.0)
        result["tta_ttb_label"] = "80TTB (Senior Citizen)"
    else:
        tta_ttb = min(sb_interest, 10_000.0)
        result["tta_ttb_label"] = "80TTA"
    result["tta_ttb"] = round(tta_ttb, 2)

    nps_employer = min(float(d.get("nps_employer_80ccd2", 0)), gross_salary * 0.10)
    result["nps_employer_80ccd2"] = round(nps_employer, 2)

    result["total_deduction"] = round(
        std_ded + eighty_c_total + eighty_d + nps_1b +
        hl_interest + hra_exempt + prof_tax + tta_ttb + nps_employer, 2
    )
    result["regime_note"] = "Old Regime: Full deduction waterfall applied."
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. CG TAX
# ─────────────────────────────────────────────────────────────────────────────

def compute_cg_tax(cg_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute CG tax from structured CG data. FY 2025-26 rates."""
    total_eq_ltcg = float(cg_data.get("equity_ltcg", 0)) + float(cg_data.get("equity_mf_ltcg", 0))
    taxable_eq_ltcg = max(0.0, total_eq_ltcg - LTCG_EQUITY_EXEMPT)
    tax_eq_ltcg = round(taxable_eq_ltcg * LTCG_EQUITY_RATE * 1.04, 2)

    total_eq_stcg = float(cg_data.get("equity_stcg", 0)) + float(cg_data.get("equity_mf_stcg", 0))
    tax_eq_stcg = round(total_eq_stcg * STCG_EQUITY_RATE * 1.04, 2)

    prop_ltcg = float(cg_data.get("property_ltcg", 0))
    tax_prop_ltcg = round(prop_ltcg * LTCG_PROPERTY_RATE * 1.04, 2)

    slab_addition = float(cg_data.get("slab_income_addition", 0))
    total_cg_tax = round(tax_eq_ltcg + tax_eq_stcg + tax_prop_ltcg, 2)

    return {
        "total_equity_ltcg":   round(total_eq_ltcg, 2),
        "ltcg_exempt":         min(total_eq_ltcg, LTCG_EQUITY_EXEMPT),
        "taxable_equity_ltcg": round(taxable_eq_ltcg, 2),
        "tax_equity_ltcg":     tax_eq_ltcg,
        "total_equity_stcg":   round(total_eq_stcg, 2),
        "tax_equity_stcg":     tax_eq_stcg,
        "property_ltcg":       prop_ltcg,
        "tax_property_ltcg":   tax_prop_ltcg,
        "slab_income_addition": slab_addition,
        "total_cg_tax":        total_cg_tax,
        "notes": {
            "equity_ltcg_rate":   "12.5% on gains above ₹1.25L (+ 4% cess)",
            "equity_stcg_rate":   "20% (+ 4% cess)",
            "property_ltcg_rate": "12.5% without indexation (+ 4% cess)",
            "debt_note":          "Debt MF / bond gains taxed at slab rate — added to income",
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. SLAB TAX HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def india_new_regime_tax(taxable_income: float) -> float:
    """New Regime FY 2025-26 (income after std deduction). Includes 4% cess."""
    income = max(0.0, taxable_income)
    slabs = [(300_000, 0.00), (400_000, 0.05), (300_000, 0.10),
             (300_000, 0.15), (300_000, 0.20), (float("inf"), 0.30)]
    tax = 0.0; rem = income
    for lim, rate in slabs:
        chunk = min(rem, lim); tax += chunk * rate; rem -= chunk
        if rem <= 0: break
    if income <= 700_000:
        tax = 0.0
    return round(tax * 1.04, 2)


def india_old_regime_tax(taxable_income: float) -> float:
    """Old Regime FY 2024-25 (income after all deductions). Includes 4% cess."""
    income = max(0.0, taxable_income)
    slabs = [(250_000, 0.00), (250_000, 0.05), (250_000, 0.20), (float("inf"), 0.30)]
    tax = 0.0; rem = income
    for lim, rate in slabs:
        chunk = min(rem, lim); tax += chunk * rate; rem -= chunk
        if rem <= 0: break
    if income <= 500_000:
        tax = 0.0
    return round(tax * 1.04, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 6. ADVANCE TAX SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def compute_advance_tax_schedule(
    total_tax_liability: float,
    tds_deducted: float = 0.0,
    advance_already_paid: float = 0.0,
) -> List[Dict[str, Any]]:
    """Compute advance tax instalment schedule for FY 2025-26."""
    today = datetime.date.today()
    net_liability = max(0.0, total_tax_liability - tds_deducted)
    if net_liability < 10_000:
        return []

    schedule = []
    prev_cum = 0.0
    cumulative_paid = advance_already_paid

    for item in ADVANCE_TAX_SCHEDULE:
        due_date = item["due_date"]
        cum_due  = round(net_liability * item["cumulative_pct"], 2)
        inst_amt = round(cum_due - prev_cum, 2)
        days_rem = (due_date - today).days

        if days_rem < 0:
            status = "⚠️ Overdue" if cumulative_paid < cum_due else "✅ Paid"
        elif days_rem == 0:
            status = "🔔 Due Today"
        else:
            status = f"🕐 {days_rem} days left"

        schedule.append({
            "instalment":        item["instalment"],
            "due_date":          due_date.strftime("%d %b %Y"),
            "cumulative_pct":    f"{item['cumulative_pct']*100:.0f}%",
            "cumulative_due":    cum_due,
            "instalment_amount": inst_amt,
            "status":            status,
            "days_remaining":    days_rem,
        })
        prev_cum = cum_due

    return schedule


# ─────────────────────────────────────────────────────────────────────────────
# 7. MASTER COMPUTE
# ─────────────────────────────────────────────────────────────────────────────

def compute_full_tax(
    income_sources_df: pd.DataFrame,
    passive_income_entries: List[Dict[str, Any]],
    passive_overrides: Dict[int, float],
    cg_data: Dict[str, Any],
    deductions: Dict[str, Any],
    tds_deducted: float = 0.0,
    advance_paid: float = 0.0,
    tax_regime: str = "New Regime",
) -> Dict[str, Any]:
    """Master tax computation: income + passive income + CG + deductions → full result."""

    gross_salary = 0.0
    income_breakdown = []
    
    # Collect passive income sources to avoid double counting them in slab income
    passive_source_names = {p["source_name"].lower() for p in passive_income_entries}
    
    if income_sources_df is not None and not income_sources_df.empty:
        for _, row in income_sources_df.iterrows():
            sname = str(row.get("source_name", "")).strip()
            # If this income was already extracted into passive_income_entries (like FRSB/EPF), skip it here
            if sname.lower() in passive_source_names:
                continue
                
            annual = float(row.get("monthly_equivalent", 0.0)) * 12.0
            gross_salary += annual
            income_breakdown.append({
                "source": sname,
                "type":   row["income_type"],
                "annual": round(annual, 2),
                "taxability": "Slab",
            })

    other_income_taxable = 0.0
    exempt_income = 0.0
    passive_breakdown = []
    for idx, entry in enumerate(passive_income_entries):
        amount = passive_overrides.get(idx, entry["annual_amount"])
        is_exempt = "EXEMPT" in entry.get("taxability", "").upper()
        if is_exempt:
            exempt_income += amount
        else:
            other_income_taxable += amount
        passive_breakdown.append({
            "source":     entry["source_name"],
            "type":       entry["income_type"],
            "annual":     round(amount, 2),
            "taxability": entry.get("taxability", ""),
        })

    cg_slab_addition = float((cg_data or {}).get("slab_income_addition", 0.0))
    total_slab_income = gross_salary + other_income_taxable + cg_slab_addition

    ded_result = compute_deductions(deductions, gross_salary, tax_regime)
    total_deduction = ded_result["total_deduction"]
    taxable_income  = max(0.0, total_slab_income - total_deduction)

    if tax_regime == "New Regime":
        slab_tax = india_new_regime_tax(taxable_income)
        old_ded  = compute_deductions(deductions, gross_salary, "Old Regime")
        compare_taxable = max(0.0, total_slab_income - old_ded["total_deduction"])
        compare_tax     = india_old_regime_tax(compare_taxable)
    else:
        slab_tax = india_old_regime_tax(taxable_income)
        new_taxable  = max(0.0, total_slab_income - 75_000.0)
        compare_tax  = india_new_regime_tax(new_taxable)
        compare_taxable = new_taxable

    cg_tax_result = compute_cg_tax(cg_data) if cg_data else {"total_cg_tax": 0.0}
    cg_tax        = float(cg_tax_result.get("total_cg_tax", 0.0))
    total_tax     = round(slab_tax + cg_tax, 2)
    balance_due   = round(max(0.0, total_tax - tds_deducted - advance_paid), 2)
    eff_rate      = round((total_tax / max(1.0, total_slab_income)) * 100, 2)
    adv_schedule  = compute_advance_tax_schedule(total_tax, tds_deducted, advance_paid)

    # Savings opportunities
    opp: List[Dict[str, str]] = []
    regime_is_new = (tax_regime == "New Regime")
    if regime_is_new and compare_tax < slab_tax:
        opp.append({"opportunity": "Consider Old Regime",
                    "detail": f"Old Regime tax ₹{compare_tax:,.0f} < New Regime ₹{slab_tax:,.0f}. Potential saving: ₹{slab_tax-compare_tax:,.0f}."})
    if not regime_is_new:
        eighty_c_used = ded_result.get("eighty_c", 0.0)
        gap = max(0.0, 150_000 - eighty_c_used)
        if gap > 0:
            opp.append({"opportunity": "Maximize 80C",
                        "detail": f"₹{gap:,.0f} unused in 80C. Invest in PPF/ELSS/VPF to save up to ₹{gap*0.30:,.0f}."})
        if float(deductions.get("nps_80ccd_1b", 0)) < 50_000:
            gap_nps = 50_000 - float(deductions.get("nps_80ccd_1b", 0))
            opp.append({"opportunity": "NPS 80CCD(1B)",
                        "detail": f"₹{gap_nps:,.0f} remaining in NPS 80CCD(1B) limit. Invest to save ~₹{gap_nps*0.30:,.0f}."})
    if cg_tax_result.get("taxable_equity_ltcg", 0) > 0:
        opp.append({"opportunity": "LTCG Harvesting",
                    "detail": f"Taxable LTCG ₹{cg_tax_result['taxable_equity_ltcg']:,.0f}. Harvest losses to offset gains."})
    if float(deductions.get("health_ins_self", 0)) == 0:
        opp.append({"opportunity": "Health Insurance (80D)",
                    "detail": "No health insurance entered. Up to ₹25,000 deductible (₹50,000 for seniors)."})
    if not regime_is_new and float(deductions.get("home_loan_interest", 0)) == 0:
        opp.append({"opportunity": "Home Loan Interest 24(b)",
                    "detail": "If you have a home loan on self-occupied property, up to ₹2L interest is deductible."})

    return {
        "gross_slab_income":     round(total_slab_income, 2),
        "total_deduction":       round(total_deduction, 2),
        "taxable_income":        round(taxable_income, 2),
        "slab_tax":              slab_tax,
        "cg_tax":                cg_tax,
        "total_tax":             total_tax,
        "tds_deducted":          tds_deducted,
        "advance_paid":          advance_paid,
        "balance_due":           balance_due,
        "effective_rate_pct":    eff_rate,
        "compare_tax":           compare_tax,
        "compare_regime":        "Old Regime" if regime_is_new else "New Regime",
        "compare_taxable":       round(compare_taxable, 2),
        "deduction_detail":      ded_result,
        "cg_tax_detail":         cg_tax_result,
        "income_breakdown":      income_breakdown,
        "passive_breakdown":     passive_breakdown,
        "exempt_income":         round(exempt_income, 2),
        "advance_tax_schedule":  adv_schedule,
        "savings_opportunities": opp,
        "frsb_rate":             FRSB_RATE,
        "frsb_rate_effective":   FRSB_RATE_EFFECTIVE,
    }
