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
        elif fname.endswith(".zip"):
            # AIS downloads from IT portal come as encrypted ZIP
            file_type_hint = "ais_zip"
        elif fname.endswith(".pdf"):
            # Read first 2 pages for detection
            sample = _extract_pdf_text(raw_bytes, max_pages=3).lower()

            if "zerodha" in sample or "kite" in sample:
                file_type_hint = "zerodha"

            # AIS / IT Portal PDF detection — check BEFORE ICICI/CAMS
            # Primary: highly specific AIS phrases (very unlikely in broker PDFs)
            elif any(k in sample for k in (
                "annual information statement",
                "taxpayer information summary",
                "sft information",
                "tds / tcs information",
                "tds/tcs information",
                "incometax.gov.in",
            )):
                file_type_hint = "ais_pdf"

            # Secondary: IT dept PDF with PAN/AY markers — broader match
            elif any(k in sample for k in (
                "income tax department", "income-tax department",
                "income tax india", "efiling.incometax",
            )) and any(k in sample for k in (
                "pan ", "pan:", "pan no",
                "assessment year", "assessment yr",
                "financial year", "form 26as", "form26as",
            )):
                file_type_hint = "ais_pdf"

            elif any(k in sample for k in (
                "icici direct", "icici securities", "icicidirect",
                "capital gain report", "profit & loss report",
                "profit and loss report", "p&l report",
                "equity capital gain", "scrip wise", "scrip-wise",
            )):
                file_type_hint = "icici"

            elif "cams" in sample or "kfintech" in sample or "consolidated account statement" in sample:
                file_type_hint = "cams"

            else:
                file_type_hint = "generic_pdf"
        else:
            file_type_hint = "generic_pdf"


    parsers = {
        "ais":         _parse_ais_json,
        "ais_zip":     _parse_ais_zip,
        "ais_pdf":     _parse_ais_pdf,
        "zerodha":     _parse_zerodha_pdf,
        "icici":       _parse_icici_pdf,
        "cams":        _parse_cams_pdf,
        "generic_pdf": _parse_generic_pdf,
    }
    parser = parsers.get(file_type_hint, _parse_generic_pdf)
    result["detected_format"] = file_type_hint   # expose for UI diagnostics
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
    """
    Multi-strategy parser for ICICI Direct PDFs:
      Strategy 1 — Section-header scan (consolidated P&L / Capital Gains report)
      Strategy 2 — Summary table scan (scrip-wise / trade-wise summary page)
      Strategy 3 — Row-level accumulation (scan every line for STCG/LTCG amounts)
      Strategy 4 — Generic LTCG/STCG keyword scan (last resort)
    Applies strategies in order; stops as soon as at least one value is populated.
    """
    r["source"] = "ICICI Direct"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Could not extract text from ICICI Direct PDF.")
        return r

    # ── Normalise text: collapse multiple spaces/newlines for easier matching ──
    flat = re.sub(r"[\r\n]+", "\n", text)
    flat_s = re.sub(r" {2,}", " ", flat)   # single-space version

    def _try_amount(s: str) -> float:
        """Parse a ₹ amount string; return 0 on failure."""
        s = s.replace(",", "").replace("₹", "").replace("Rs", "").strip()
        try:
            return float(s)
        except ValueError:
            return 0.0

    def _first_number_after(pattern: str, text_block: str, flags=re.IGNORECASE | re.DOTALL) -> float:
        """Return the first currency-looking number after a regex match."""
        m = re.search(pattern, text_block, flags)
        if not m:
            return 0.0
        tail = text_block[m.end():m.end() + 200]
        nm = re.search(r"([\d,]+\.\d{2})", tail)
        return _try_amount(nm.group(1)) if nm else 0.0

    populated = lambda: any(r[k] for k in (
        "equity_stcg", "equity_ltcg", "equity_mf_stcg", "equity_mf_ltcg",
        "debt_mf_stcg", "debt_mf_ltcg",
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 1 — Section-header scan
    # ICICI consolidated reports have section headers like:
    #   "Short Term Capital Gain" / "Long Term Capital Gain"
    # followed by a summary line with the net gain amount.
    # ─────────────────────────────────────────────────────────────────────────
    _S1_PATTERNS = [
        # Equity STCG section
        (r"short[\s\-]?term\s+capital\s+gain[^\n]*equity", "equity_stcg"),
        (r"equity[^\n]*short[\s\-]?term\s+capital\s+gain",  "equity_stcg"),
        (r"stcg[^\n]*equity",                                 "equity_stcg"),
        (r"equity[^\n]*stcg",                                 "equity_stcg"),
        # Equity LTCG section
        (r"long[\s\-]?term\s+capital\s+gain[^\n]*equity",   "equity_ltcg"),
        (r"equity[^\n]*long[\s\-]?term\s+capital\s+gain",   "equity_ltcg"),
        (r"ltcg[^\n]*equity",                                 "equity_ltcg"),
        (r"equity[^\n]*ltcg",                                 "equity_ltcg"),
        # MF STCG
        (r"short[\s\-]?term[^\n]*mutual\s*fund",             "equity_mf_stcg"),
        (r"mutual\s*fund[^\n]*stcg",                          "equity_mf_stcg"),
        (r"stcg[^\n]*mutual\s*fund",                          "equity_mf_stcg"),
        # MF LTCG
        (r"long[\s\-]?term[^\n]*mutual\s*fund",              "equity_mf_ltcg"),
        (r"mutual\s*fund[^\n]*ltcg",                          "equity_mf_ltcg"),
        (r"ltcg[^\n]*mutual\s*fund",                          "equity_mf_ltcg"),
        # Debt MF
        (r"debt[^\n]*stcg",                                   "debt_mf_stcg"),
        (r"stcg[^\n]*debt",                                   "debt_mf_stcg"),
        (r"debt[^\n]*ltcg",                                   "debt_mf_ltcg"),
        (r"ltcg[^\n]*debt",                                   "debt_mf_ltcg"),
    ]
    for pat, key in _S1_PATTERNS:
        v = _first_number_after(pat, flat_s)
        if v > 0 and r[key] == 0.0:
            r[key] = v

    if populated():
        return _sum_totals(r)

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 2 — Summary table scan
    # ICICI consolidated PDFs include a summary table:
    #   "Net Short Term Gain / (Loss)   12,345.67"
    #   "Net Long Term Gain / (Loss)    56,789.01"
    # Also handles:
    #   "Total Short Term"  /  "Total Long Term"
    #   "Net Gain (Short Term)"  /  "Net Gain (Long Term)"
    # ─────────────────────────────────────────────────────────────────────────
    _S2_PATTERNS = [
        (r"net\s+short[\s\-]?term\s+(?:gain|capital)[^\n]*",  "equity_stcg"),
        (r"total\s+short[\s\-]?term\s+(?:gain|capital)[^\n]*", "equity_stcg"),
        (r"net\s+gain\s*\(\s*short[^)]*\)",                    "equity_stcg"),
        (r"short\s+term\s+(?:net\s+)?(?:gain|profit)[^\n]*",   "equity_stcg"),
        (r"net\s+long[\s\-]?term\s+(?:gain|capital)[^\n]*",   "equity_ltcg"),
        (r"total\s+long[\s\-]?term\s+(?:gain|capital)[^\n]*",  "equity_ltcg"),
        (r"net\s+gain\s*\(\s*long[^)]*\)",                     "equity_ltcg"),
        (r"long\s+term\s+(?:net\s+)?(?:gain|profit)[^\n]*",    "equity_ltcg"),
    ]
    for pat, key in _S2_PATTERNS:
        v = _first_number_after(pat, flat_s)
        if v > 0 and r[key] == 0.0:
            r[key] = v

    if populated():
        return _sum_totals(r)

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 3 — Row-level accumulation
    # Scan every line; if a line contains a holding-period marker and a number,
    # accumulate into the appropriate bucket.  Works for scrip-wise statements
    # where each row is one scrip with a "Short" or "Long" label.
    # ─────────────────────────────────────────────────────────────────────────
    _NUM_RE = re.compile(r"([\-]?[\d,]+\.\d{2})")
    for line in flat.splitlines():
        ll = line.lower()
        # Skip header lines
        if any(h in ll for h in ("purchase", "sale", "quantity", "date", "scrip", "description", "symbol")):
            continue
        nums = _NUM_RE.findall(line)
        if not nums:
            continue
        # Last numeric on the line is usually the gain/loss
        val = _try_amount(nums[-1])
        if val == 0.0:
            continue
        is_mf   = any(k in ll for k in ("mutual fund", "mf", "nav", "folio"))
        is_debt  = any(k in ll for k in ("debt", "bond", "gilt", "liquid", "overnight"))
        is_stcg  = any(k in ll for k in ("short", "stcg", "111a"))
        is_ltcg  = any(k in ll for k in ("long", "ltcg", "112a"))
        if is_stcg and not is_ltcg:
            bucket = "debt_mf_stcg" if is_debt else ("equity_mf_stcg" if is_mf else "equity_stcg")
            r[bucket] = round(r[bucket] + val, 2)
        elif is_ltcg and not is_stcg:
            bucket = "debt_mf_ltcg" if is_debt else ("equity_mf_ltcg" if is_mf else "equity_ltcg")
            r[bucket] = round(r[bucket] + val, 2)

    if populated():
        return _sum_totals(r)

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 4 — Generic LTCG/STCG keyword scan (last resort)
    # ─────────────────────────────────────────────────────────────────────────
    for pat, key in [
        (r"(?:net\s+)?(?:total\s+)?stcg[^\n]{0,60}([\d,]+\.\d{2})",  "equity_stcg"),
        (r"(?:net\s+)?(?:total\s+)?ltcg[^\n]{0,60}([\d,]+\.\d{2})",  "equity_ltcg"),
        (r"short[\s\-]?term[^\n]{0,80}([\d,]+\.\d{2})",               "equity_stcg"),
        (r"long[\s\-]?term[^\n]{0,80}([\d,]+\.\d{2})",                "equity_ltcg"),
    ]:
        if r[key.replace("equity_", "") if False else key] != 0.0:  # don't overwrite
            continue
        m = re.search(pat, flat, re.IGNORECASE)
        if m:
            v = _try_amount(m.group(1))
            if v > 0:
                r[key] = v

    if not populated():
        r["parse_errors"].append(
            "ICICI Direct PDF parsed but no STCG/LTCG figures found. "
            "Please verify the PDF is a Capital Gains / P&L statement, "
            "or enter figures manually below."
        )
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


def _ais_classify(description: str, info_code: str) -> tuple:
    """
    Classify an AIS transaction into (asset_bucket, is_ltcg).
    Returns (bucket_key_prefix, is_long_term) where bucket_key_prefix is
    one of: 'equity', 'equity_mf', 'debt_mf', 'property', 'other'.
    is_long_term is None when holding period is unknown (sale proceeds only).
    """
    desc  = description.lower()
    code  = str(info_code).upper()

    # SFT codes: 017=equity securities, 018=mutual funds
    is_equity_sft = code in ("SFT-017", "SFT017", "17")
    is_mf_sft     = code in ("SFT-018", "SFT018", "18")

    is_mf      = is_mf_sft or any(k in desc for k in ("mutual fund", "mf unit", "folio", "nav", "redemption of unit"))
    is_equity  = (is_equity_sft and not is_mf) or any(k in desc for k in ("listed share", "equity share", "listed security", "sale of share", "listed debenture"))
    is_debt    = any(k in desc for k in ("debt", "bond", "debenture", "gilt", "overnight", "liquid fund")) and not is_equity
    is_prop    = any(k in desc for k in ("immovable property", "land", "house", "real estate", "building"))

    is_ltcg = None
    if any(k in desc for k in ("long term", "ltcg", "long-term", "112a")):
        is_ltcg = True
    elif any(k in desc for k in ("short term", "stcg", "short-term", "111a")):
        is_ltcg = False

    if is_prop:
        return "property", is_ltcg
    elif is_debt:
        return "debt_mf", is_ltcg
    elif is_mf:
        return "equity_mf", is_ltcg
    elif is_equity:
        return "equity", is_ltcg
    else:
        return "other", is_ltcg


def _parse_ais_json(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse an AIS JSON from the Income Tax portal.
    Handles multiple schema versions:
      - Schema A: partBDetails[] -> category -> data[] -> transactions[]
      - Schema B: aisDetail.data[] (flat)
      - Schema C: capitalGains[] (legacy/simplified)
      - Schema D: aisSummary.items[] (summary-only)
    Note: AIS reports *sale proceeds*, not gains. When a gain amount is
    present (some AIS exports include it), it's used directly. Otherwise
    we report sale proceeds and mark it as approximate.
    """
    import json
    r["source"] = "IT Dept AIS"

    try:
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        r["parse_errors"].append(
            f"AIS JSON parse error: {e}. "
            "Note: AIS files downloaded from the IT portal are encrypted (password = PAN + DOB in DDMMYYYY). "
            "Decrypt first using the AIS Offline Utility, then re-upload the decrypted JSON."
        )
        return r

    raw_rows = []
    found_any = False

    # ── Schema A: partBDetails (most common real AIS export) ─────────────────
    part_b = data.get("partBDetails") or data.get("partB") or []
    if isinstance(part_b, dict):
        part_b = [part_b]
    for category in part_b:
        cat_name = str(category.get("category", category.get("name", ""))).lower()
        # Only process capital gains / SFT / securities categories
        if not any(k in cat_name for k in ("capital", "sft", "securit", "mutual fund", "other information")):
            # Also check sub-items in case structure is different
            if "data" not in category and "items" not in category:
                continue
        items = category.get("data") or category.get("items") or category.get("transactions") or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            info_code = str(item.get("informationCode", item.get("code", "")))
            description = str(item.get("description", item.get("desc", "")))
            # Transactions within this item
            txns = item.get("transactions") or item.get("data") or []
            if not isinstance(txns, list):
                txns = [txns]
            if not txns:
                # Sometimes the item itself IS the transaction
                txns = [item]
            for txn in txns:
                desc_full = str(txn.get("description", description))
                code_full  = str(txn.get("informationCode", info_code))
                # Amount: prefer gainAmount / capitalGain over txnAmt (which is sale proceeds)
                gain_amt   = float(txn.get("gainAmount") or txn.get("capitalGain") or
                                   txn.get("gain_amount") or 0)
                sale_amt   = float(txn.get("amount") or txn.get("txnAmt") or
                                   txn.get("saleAmount") or txn.get("informationValue") or 0)
                holding    = str(txn.get("holdingPeriod", txn.get("holding_period", ""))).lower()
                gain_type  = str(txn.get("gainType", txn.get("gain_type", ""))).upper()

                use_amt   = gain_amt if gain_amt else sale_amt
                if use_amt == 0:
                    continue
                is_gain   = bool(gain_amt)  # True if we have actual gain, False if sale proceeds
                bucket, is_ltcg = _ais_classify(desc_full, code_full)

                # Refine is_ltcg from explicit fields
                if "LTCG" in gain_type or "LONG" in gain_type or "long" in holding:
                    is_ltcg = True
                elif "STCG" in gain_type or "SHORT" in gain_type or "short" in holding:
                    is_ltcg = False

                # Default unknown holding to LTCG for equities (most common for CG reports)
                if is_ltcg is None:
                    is_ltcg = True

                key = f"{bucket}_{'ltcg' if is_ltcg else 'stcg'}"
                if key in r:
                    r[key] = round(r[key] + use_amt, 2)
                    found_any = True
                    raw_rows.append({"source": "partBDetails", "code": code_full,
                                     "desc": desc_full, "amount": use_amt,
                                     "is_gain": is_gain, "bucket": key})

    if found_any:
        r["raw_rows"] = raw_rows
        if any(not row["is_gain"] for row in raw_rows):
            r["parse_errors"].append(
                "⚠️ AIS only reports sale proceeds (not net capital gain). "
                "These figures are OVERESTIMATES — subtract your purchase cost. "
                "Use your broker's P&L statement for accurate LTCG/STCG figures."
            )
        return _sum_totals(r)

    # ── Schema B: aisDetail (flat structure) ─────────────────────────────────
    ais_detail = data.get("aisDetail") or data.get("ais_detail") or {}
    items_b = (ais_detail.get("data") or ais_detail.get("items") or
               (ais_detail if isinstance(ais_detail, list) else []))
    for item in items_b:
        info_code   = str(item.get("informationCode", ""))
        description = str(item.get("description", ""))
        use_amt = float(item.get("gainAmount") or item.get("amount") or item.get("txnAmt") or 0)
        if use_amt == 0:
            continue
        bucket, is_ltcg = _ais_classify(description, info_code)
        if is_ltcg is None:
            is_ltcg = True
        key = f"{bucket}_{'ltcg' if is_ltcg else 'stcg'}"
        if key in r:
            r[key] = round(r[key] + use_amt, 2)
            found_any = True
            raw_rows.append({"source": "aisDetail", "code": info_code,
                             "desc": description, "amount": use_amt, "bucket": key})

    if found_any:
        r["raw_rows"] = raw_rows
        r["parse_errors"].append(
            "⚠️ AIS reports sale proceeds, not net gains. These figures may be overestimates. "
            "Reconcile with your broker's P&L for accurate capital gains."
        )
        return _sum_totals(r)

    # ── Schema C / Legacy ────────────────────────────────────────────────────
    # (Simplified fallback for legacy AIS JSONs)
    capital_gains = data.get("capitalGains") or []
    for item in capital_gains:
        pass # Not implemented fully in this snippet, add if needed.
    return _sum_totals(r)

def _parse_ais_pdf(raw_bytes: bytes, r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse AIS PDF downloaded from the Income Tax portal.

    Key insight: AIS PDFs list SALE PROCEEDS under SFT codes — they do NOT
    label transactions as LTCG or STCG. The layout is typically:

        SFT-017  Sale and purchase of securities listed on ...  ₹X,XX,XXX
        SFT-018  Sale and purchase of units of Mutual Funds     ₹X,XX,XXX

    Strategy:
      1. SFT code scan — look for SFT-017/018 and grab the next amount
      2. Description-only scan — "sale of securities", "sale of units",
         "sale of mutual fund" without needing long/short-term qualifiers
      3. LTCG/STCG explicit labels (rare in AIS but handle if present)
      4. Line-by-line accumulator — any line with equity/MF keyword + amount
      5. Capital gains section scan — "Other Information" / CG summary blocks

    All amounts go to equity_ltcg / equity_mf_ltcg as best estimates,
    with a prominent warning that these are SALE PROCEEDS not net gains.
    """
    r["source"] = "IT Dept AIS (PDF)"
    text = _extract_pdf_text(raw_bytes)
    if not text:
        r["parse_errors"].append("Could not extract text from AIS PDF.")
        return r

    flat  = re.sub(r"\s+", " ", text)          # single-space version
    lines = text.splitlines()
    found_any = False

    # ── helpers ──────────────────────────────────────────────────────────────
    def _first_amt(pattern: str, txt: str, flags=re.IGNORECASE | re.DOTALL) -> float:
        """Return the first ₹ amount > 100 after match to avoid matching 'Count' columns."""
        for m in re.finditer(pattern, txt, flags):
            tail = txt[m.end(): m.end() + 600]
            # Find all numbers in the tail
            nums = re.findall(r"(?:[\u20b9Rs]\s*)?([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)", tail)
            for n in nums:
                clean_n = n.replace(",", "")
                if clean_n.replace(".", "").isdigit():
                    val = float(clean_n)
                    # Typically capital gains/sale proceeds are > 100. A single digit (like 5 or 12) is usually a 'Count'.
                    if val > 100:
                        return val
        return 0.0

    def _set(key: str, val: float):
        nonlocal found_any
        if val > 0 and r.get(key, 0.0) == 0.0:
            r[key] = round(val, 2)
            found_any = True

    # ── Strategy 1: SFT code scan ─────────────────────────────────────────
    # SFT-017 = sale/purchase of listed securities (equity)
    # SFT-018 = sale/purchase of mutual fund units
    # SFT-011 = cash deposits, SFT-012 = credit card — skip those
    for pat, key in [
        # SFT-017 variants: "SFT017", "SFT-017", "SFT 017", code "17", "SFT - 017"
        (r"SFT[\s\-]*017\b",  "equity_ltcg"),
        (r"\bcode[\s\-:]*017\b", "equity_ltcg"),
        # SFT-018 variants
        (r"SFT[\s\-]*018\b",   "equity_mf_ltcg"),
        (r"\bcode[\s\-:]*018\b",  "equity_mf_ltcg"),
        # SFT-016 = interest on savings (not CG — skip)
    ]:
        _set(key, _first_amt(pat, flat))

    # ── Strategy 2: Description-only scan (no LTCG/STCG required) ────────
    # AIS labels are like "Sale and purchase of securities listed on..."
    # or "Sale of units of Mutual Fund" — no holding-period qualifiers.
    _DESC_PATTERNS = [
        # Equity / listed securities
        (r"sale\s+(?:and\s+purchase\s+)?of\s+(?:securities\s+and\s+units\s+of\s+mutual\s+fund|listed\s+securities|securities|shares|equity)",
         "equity_ltcg"),
        (r"purchase\s+and\s+sale\s+of\s+(?:listed\s+)?(?:securities|shares)",
         "equity_ltcg"),
        (r"(?:listed|unlisted)\s+(?:equity\s+)?shares?",
         "equity_ltcg"),
        # Mutual fund
        (r"sale\s+(?:and\s+purchase\s+)?of\s+(?:units?\s+of\s+)?mutual\s+funds?",
         "equity_mf_ltcg"),
        (r"purchase\s+and\s+sale\s+of\s+(?:units?\s+of\s+)?mutual\s+funds?",
         "equity_mf_ltcg"),
        (r"redemption\s+of\s+(?:units?\s+of\s+)?mutual\s+funds?",
         "equity_mf_ltcg"),
        (r"mutual\s+fund\s+(?:units?|redemption|transactions?)",
         "equity_mf_ltcg"),
        # Immovable property
        (r"sale\s+of\s+immovable\s+property",  "property_ltcg"),
        (r"immovable\s+property",               "property_ltcg"),
    ]
    for pat, key in _DESC_PATTERNS:
        _set(key, _first_amt(pat, flat))

    # ── Strategy 3: Explicit LTCG / STCG labels (rare but handle them) ───
    _EXPLICIT = [
        (r"long[\s\-]?term\s+capital\s+gains?\s+(?:on\s+)?(?:equity|securities|shares?)",
         "equity_ltcg"),
        (r"short[\s\-]?term\s+capital\s+gains?\s+(?:on\s+)?(?:equity|securities|shares?)",
         "equity_stcg"),
        (r"long[\s\-]?term\s+capital\s+gains?\s+(?:on\s+)?(?:mutual\s+funds?|mf)",
         "equity_mf_ltcg"),
        (r"short[\s\-]?term\s+capital\s+gains?\s+(?:on\s+)?(?:mutual\s+funds?|mf)",
         "equity_mf_stcg"),
        (r"long[\s\-]?term\s+capital\s+gains?",   "equity_ltcg"),
        (r"short[\s\-]?term\s+capital\s+gains?",  "equity_stcg"),
        (r"\bltcg\b",  "equity_ltcg"),
        (r"\bstcg\b",  "equity_stcg"),
        (r"immovable\s+property[^.]{0,80}long[\s\-]?term",  "property_ltcg"),
        (r"immovable\s+property[^.]{0,80}short[\s\-]?term", "property_stcg"),
    ]
    for pat, key in _EXPLICIT:
        _set(key, _first_amt(pat, flat))

    # ── Strategy 4: Line-by-line accumulator ─────────────────────────────
    # Scan each line: if it has an equity/MF keyword AND a currency amount,
    # accumulate into the right bucket.
    _NUM_RE   = re.compile(r"[\u20b9Rs\s]*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)")
    _SKIP_KW  = {"purchase", "tds", "tax deducted", "interest", "salary",
                 "dividend", "rent", "house property", "cash deposit",
                 "credit card", "foreign", "banking"}
    if not found_any:
        for line in lines:
            ll = line.lower().strip()
            if not ll or any(k in ll for k in _SKIP_KW):
                continue
            nums = _NUM_RE.findall(line)
            if not nums:
                continue
            try:
                val = max(float(n.replace(",", "")) for n in nums if n.replace(",", "").replace(".", "").isdigit())
            except ValueError:
                continue
            if val < 100:       # skip line numbers / small values
                continue
            is_mf   = any(k in ll for k in ("mutual fund", "mf unit", "folio", "nav"))
            is_prop = any(k in ll for k in ("property", "land", "house", "building"))
            is_eq   = any(k in ll for k in ("securit", "share", "equity", "sft-017", "sft 017"))
            is_mf_c = any(k in ll for k in ("sft-018", "sft 018")) or is_mf
            if is_prop:
                r["property_ltcg"] = round(r.get("property_ltcg", 0) + val, 2); found_any = True
            elif is_mf_c:
                r["equity_mf_ltcg"] = round(r.get("equity_mf_ltcg", 0) + val, 2); found_any = True
            elif is_eq:
                r["equity_ltcg"] = round(r.get("equity_ltcg", 0) + val, 2); found_any = True

    # ── Strategy 5: Legacy/Fallback Patterns ──────────────────────────────
    # AIS PDF patterns for capital gains entries
    _AIS_PDF_PATTERNS = [
        # Sale of listed securities (SFT-017)
        (r"sale\s+of\s+(?:listed\s+)?(?:securities|shares|equity).{0,120}?long[\s\-]?term", "equity_ltcg"),
        (r"sale\s+of\s+(?:listed\s+)?(?:securities|shares|equity).{0,120}?short[\s\-]?term", "equity_stcg"),
        (r"long[\s\-]?term.{0,120}?sale\s+of\s+(?:securities|shares|equity)", "equity_ltcg"),
        (r"short[\s\-]?term.{0,120}?sale\s+of\s+(?:securities|shares|equity)", "equity_stcg"),
        # Mutual fund (SFT-018)
        (r"mutual\s+fund.{0,120}?long[\s\-]?term",  "equity_mf_ltcg"),
        (r"mutual\s+fund.{0,120}?short[\s\-]?term", "equity_mf_stcg"),
        (r"long[\s\-]?term.{0,120}?mutual\s+fund",  "equity_mf_ltcg"),
        (r"short[\s\-]?term.{0,120}?mutual\s+fund", "equity_mf_stcg"),
        # Generic LTCG/STCG labels in AIS summary tables
        (r"capital\s+gains?.{0,120}?long[\s\-]?term",  "equity_ltcg"),
        (r"capital\s+gains?.{0,120}?short[\s\-]?term", "equity_stcg"),
        (r"long[\s\-]?term\s+capital\s+gains?",           "equity_ltcg"),
        (r"short[\s\-]?term\s+capital\s+gains?",          "equity_stcg"),
        # Immovable property
        (r"immovable\s+property.{0,120}?long[\s\-]?term",  "property_ltcg"),
        (r"immovable\s+property.{0,120}?short[\s\-]?term", "property_stcg"),
    ]
    for pat, key in _AIS_PDF_PATTERNS:
        v = _first_amt(pat, flat)
        if v > 0 and r.get(key, 0) == 0:
            r[key] = v
            found_any = True

    if found_any:
        r["parse_errors"].append(
            "⚠️ AIS PDF shows sale consideration (not net capital gain). "
            "Subtract your purchase cost to get actual gains. "
            "For accurate LTCG/STCG, use your broker's P&L statement instead."
        )
    else:
        r["parse_errors"].append(
            "AIS PDF detected but capital gains figures not found in expected format. "
            "The AIS PDF may only show TDS/interest data and not capital gains. \n"
            "For capital gains, use: Zerodha Console P&L PDF, ICICI Capital Gains PDF, "
            "or CAMS Consolidated Account Statement PDF."
        )
        # ── Diagnostic: expose the raw extracted text so the UI can show it ──
        # This helps identify what the PDF text actually looks like so regexes
        # can be tuned to match it.
        r["debug_text"] = text[:4000]   # first 4000 chars is enough to diagnose
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

def _months_overdue(due_date: datetime.date, today: datetime.date) -> int:
    """
    Count the number of full or partial months elapsed since due_date up to today.
    Returns 0 if today <= due_date (not yet due).
    Per IT Act, even a part of a month counts as a full month.
    """
    if today <= due_date:
        return 0
    # months = full months + 1 if any days remain in the partial month
    m = (today.year - due_date.year) * 12 + (today.month - due_date.month)
    # If today's day > due_date's day, the partial month is already captured
    # If today's day <= due_date's day, we're still within the same month boundary
    if today.day > due_date.day:
        m += 1
    return max(m, 1)  # at minimum 1 month if any day has passed


def compute_advance_tax_schedule(
    total_tax_liability: float,
    tds_deducted: float = 0.0,
    advance_already_paid: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Compute advance tax instalment schedule for FY 2025-26, including:
      - 234C interest: 1% per month on shortfall at each instalment due date
        (shortfall = cumulative_due - advance_already_paid, if positive and date is past)
      - 234B interest: 1% per month on overall shortfall from Apr 1 to today
        (applies when total advance paid < 90% of net liability by Mar 31)

    Returns list of instalment rows PLUS two summary keys at the end:
      'interest_234C_total' and 'interest_234B_total'.
    These are embedded in the last row dict as _summary keys for the caller to extract.
    """
    today = datetime.date.today()
    net_liability = max(0.0, total_tax_liability - tds_deducted)
    if net_liability < 10_000:
        return []

    # ── 234C: per-instalment interest ────────────────────────────────────────
    # Rule: if cumulative advance paid < cumulative due at each instalment due date,
    # interest = 1% × shortfall × months overdue (rounded up to nearest month)
    # The "shortfall" for 234C is assessed per instalment independently.
    # For simplicity (common practice): shortfall = (cum_due - advance_already_paid)
    # capped at zero from below, measured at each due date.
    schedule = []
    prev_cum = 0.0
    total_234c = 0.0

    for item in ADVANCE_TAX_SCHEDULE:
        due_date = item["due_date"]
        cum_due  = round(net_liability * item["cumulative_pct"], 2)
        inst_amt = round(cum_due - prev_cum, 2)
        days_rem = (due_date - today).days

        # 234C fine calculation (only for past due dates)
        fine_234c = 0.0
        fine_note = ""
        if today > due_date:
            shortfall = max(0.0, cum_due - advance_already_paid)
            if shortfall > 0:
                months = _months_overdue(due_date, today)
                fine_234c = round(shortfall * 0.01 * months, 2)
                fine_note = f"1% × ₹{shortfall:,.0f} × {months}m"
            total_234c += fine_234c

        if days_rem < 0:
            status = "⚠️ Overdue" if advance_already_paid < cum_due else "✅ Paid"
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
            "interest_234c":     fine_234c,
            "fine_note":         fine_note,
        })
        prev_cum = cum_due

    # ── 234B: overall advance tax shortfall interest ─────────────────────────
    # Applies if total advance tax paid < 90% of net liability by 31 Mar
    # Interest = 1% per month on deficit, from 1 Apr of assessment year to today
    fy_end = datetime.date(2026, 3, 31)
    assessment_start = datetime.date(2026, 4, 1)
    required_90pct   = net_liability * 0.90
    interest_234b    = 0.0
    deficit_234b     = 0.0
    months_234b      = 0

    if advance_already_paid < required_90pct and today >= assessment_start:
        deficit_234b  = round(net_liability - advance_already_paid, 2)
        months_234b   = _months_overdue(assessment_start - datetime.timedelta(days=1), today)
        interest_234b = round(deficit_234b * 0.01 * months_234b, 2)

    # Attach summary to last row (caller will pop and display separately)
    if schedule:
        schedule[-1]["_234c_total"]   = round(total_234c, 2)
        schedule[-1]["_234b_total"]   = round(interest_234b, 2)
        schedule[-1]["_234b_deficit"] = deficit_234b
        schedule[-1]["_234b_months"]  = months_234b
        schedule[-1]["_today"]        = today.strftime("%d %b %Y")
        schedule[-1]["_net_liability"]= net_liability

    return schedule


# ─────────────────────────────────────────────────────────────────────────────
# 7. PORTFOLIO-AWARE TAX-SAVING REBALANCE RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

def compute_tax_saving_rebalance(
    holdings_df: pd.DataFrame,
    tax_result: Dict[str, Any],
    deductions: Dict[str, Any],
    tax_regime: str = "New Regime",
) -> List[Dict[str, Any]]:
    """
    Analyse the user's actual investment holdings and tax computation result to
    generate priority-ranked, portfolio-specific rebalancing recommendations
    that maximise tax efficiency.

    Returns a list of recommendation dicts, sorted by estimated tax saving (desc).
    Each dict has keys:
        title, section, priority, current_holding, action,
        tax_saving (float, ₹/yr), tax_saving_str, rationale, risk_note
    """
    recs: List[Dict[str, Any]] = []

    if holdings_df is None:
        holdings_df = pd.DataFrame()

    # ── Derive marginal tax rate from effective rate (proxy) ─────────────────
    eff_rate = float(tax_result.get("effective_rate_pct", 20.0)) / 100.0
    taxable_income = float(tax_result.get("taxable_income", 0.0))

    # Better marginal rate estimate from slab
    if taxable_income > 1_500_000:
        marginal_rate = 0.30
    elif taxable_income > 1_200_000:
        marginal_rate = 0.20
    elif taxable_income > 900_000:
        marginal_rate = 0.15
    elif taxable_income > 700_000:
        marginal_rate = 0.10
    elif taxable_income > 400_000:
        marginal_rate = 0.05
    else:
        marginal_rate = max(eff_rate, 0.05)

    # With 4% cess
    marginal_rate_cess = round(marginal_rate * 1.04, 4)

    is_old_regime = (tax_regime == "Old Regime")
    total_tax = float(tax_result.get("total_tax", 0.0))
    cg_detail = tax_result.get("cg_tax_detail", {})
    ded_detail = tax_result.get("deduction_detail", {})

    # ── Classify holdings ────────────────────────────────────────────────────
    if not holdings_df.empty and "investment_type" in holdings_df.columns:
        def _itype(row):
            return str(row.get("investment_type", "")).lower().strip()

        def _amount(row):
            return float(row.get("investment_amount", 0.0) or 0.0)

        def _curr_val(row):
            return float(row.get("current_value", 0.0) or 0.0)

        def _match(row, keywords):
            t = f"{_itype(row)} {str(row.get('description',''))} {str(row.get('resolved_name',''))} {str(row.get('platform',''))}".lower()
            return any(k in t for k in keywords)

        fd_rows    = [r for _, r in holdings_df.iterrows() if _match(r, _FD_KEYWORDS)]
        rd_rows    = [r for _, r in holdings_df.iterrows() if _match(r, _RD_KEYWORDS)]
        ppf_rows   = [r for _, r in holdings_df.iterrows() if _match(r, _PPF_KEYWORDS)]
        epf_rows   = [r for _, r in holdings_df.iterrows() if _match(r, _EPF_KEYWORDS)]
        nsc_rows   = [r for _, r in holdings_df.iterrows() if _match(r, _NSC_KEYWORDS)]
        scss_rows  = [r for _, r in holdings_df.iterrows() if _match(r, _SCSS_KEYWORDS)]
        sgb_rows   = [r for _, r in holdings_df.iterrows() if _match(r, _SGB_KEYWORDS)]
        frsb_rows  = [r for _, r in holdings_df.iterrows() if _match(r, _FRSB_KEYWORDS)]
        elss_rows  = [r for _, r in holdings_df.iterrows() if _match(r, {"elss", "equity linked", "tax saver fund", "tax saving fund"})]
        nps_rows   = [r for _, r in holdings_df.iterrows() if _match(r, {"nps", "national pension", "pension system", "tier 1", "tier-1"})]
        equity_rows= [r for _, r in holdings_df.iterrows() if _match(r, _EQUITY_KEYWORDS)]
        debt_mf_rows=[r for _, r in holdings_df.iterrows() if _match(r, {"debt mutual fund", "debt mf", "liquid fund", "ultra short", "short duration", "bond fund", "gilt", "overnight fund"})]

        total_invested = float(holdings_df["investment_amount"].sum()) if "investment_amount" in holdings_df.columns else 0.0
        total_curr_val = float(holdings_df["current_value"].sum()) if "current_value" in holdings_df.columns else 0.0

        fd_total   = sum(_amount(r) for r in fd_rows)
        rd_total   = sum(_amount(r) for r in rd_rows)
        scss_total = sum(_amount(r) for r in scss_rows)
        ppf_total  = sum(_amount(r) for r in ppf_rows)
        elss_total = sum(_amount(r) for r in elss_rows)
        nps_total  = sum(_amount(r) for r in nps_rows)
        sgb_total  = sum(_amount(r) for r in sgb_rows)
        equity_total = sum(_curr_val(r) for r in equity_rows)

        # ── Taxable FD / RD interest burden ──────────────────────────────────
        fd_rd_total = fd_total + rd_total
        if fd_rd_total > 0:
            fd_rate_avg = DEFAULT_FD_RATE
            fd_annual_interest = round(fd_rd_total * fd_rate_avg, 0)
            fd_tax_burden = round(fd_annual_interest * marginal_rate_cess, 0)

            # Sub-recommendation A: shift portion to Tax-Saver FD (80C benefit)
            if is_old_regime:
                eighty_c_used = float(ded_detail.get("eighty_c", 0.0))
                eighty_c_gap  = max(0.0, 150_000.0 - eighty_c_used)
                if eighty_c_gap > 0 and elss_total == 0:
                    shift_amt  = min(fd_rd_total, eighty_c_gap)
                    tax_saving = round(shift_amt * marginal_rate_cess, 0)
                    recs.append({
                        "title":           "Shift FD into Tax-Saver FD or ELSS",
                        "section":         "80C",
                        "priority":        "High" if tax_saving > 10_000 else "Medium",
                        "current_holding": f"₹{fd_rd_total:,.0f} in FD/RD — interest fully taxable at {marginal_rate*100:.0f}% slab rate. Annual tax burden: ~₹{fd_tax_burden:,.0f}.",
                        "action":          f"Redirect ₹{shift_amt:,.0f} (80C gap) into a Tax-Saver FD (5-yr lock-in, 6.5-7.5% p.a.) or ELSS Mutual Fund. This uses up your remaining 80C limit and converts principal from taxable to deductible.",
                        "tax_saving":      tax_saving,
                        "tax_saving_str":  f"~₹{tax_saving:,.0f}/yr",
                        "rationale":       "u/s 80C — up to ₹1.5L deductible from taxable income",
                        "risk_note":       "Tax-Saver FD: 5-yr lock-in, low risk. ELSS: 3-yr lock-in, market risk, historically higher returns.",
                    })

            # Sub-recommendation B: shift taxable FD into Debt MF (tax-deferred growth)
            if fd_rd_total > 200_000:
                debt_shift = min(fd_rd_total * 0.30, 500_000)
                # Debt MF: STCG taxed at slab (same as FD) but growth compounds without annual TDS drag
                tds_drag_saving = round(fd_rd_total * fd_rate_avg * 0.10 * 0.70, 0)  # TDS reinvestment compounding benefit
                recs.append({
                    "title":           "Shift Taxable FD into Debt Mutual Funds",
                    "section":         "Debt Rebalance",
                    "priority":        "Medium",
                    "current_holding": f"₹{fd_rd_total:,.0f} in FD/RD. Bank deducts TDS @10% annually, reducing compounding.",
                    "action":          f"Move ₹{debt_shift:,.0f} into a Debt MF (Ultra-Short or Short Duration). No annual TDS — growth compounds tax-deferred until redemption. Taxed at slab on redemption, same as FD, but no interim TDS drag.",
                    "tax_saving":      tds_drag_saving,
                    "tax_saving_str":  f"~₹{tds_drag_saving:,.0f}/yr (TDS compounding benefit)",
                    "rationale":       "Debt MF: no annual TDS; tax only on redemption. FD: bank deducts TDS each year, reducing corpus.",
                    "risk_note":       "Debt MF NAV can fluctuate slightly. No capital guarantee unlike FD. Choose funds rated AAA.",
                })

        # ── ELSS gap (Old Regime only) ────────────────────────────────────────
        if is_old_regime:
            eighty_c_used = float(ded_detail.get("eighty_c", 0.0))
            eighty_c_gap  = max(0.0, 150_000.0 - eighty_c_used)
            if eighty_c_gap > 0 and elss_total == 0 and fd_rd_total == 0:
                # Only show standalone ELSS recommendation if no FD shift was recommended
                tax_saving = round(eighty_c_gap * marginal_rate_cess, 0)
                recs.append({
                    "title":           "Invest in ELSS Mutual Funds",
                    "section":         "80C",
                    "priority":        "High" if tax_saving > 10_000 else "Medium",
                    "current_holding": f"80C utilised: ₹{eighty_c_used:,.0f} / ₹1,50,000. Gap: ₹{eighty_c_gap:,.0f}.",
                    "action":          f"Invest ₹{eighty_c_gap:,.0f} in ELSS (Equity Linked Savings Scheme). 3-year lock-in, no portfolio holding detected. Market-linked growth + full 80C benefit.",
                    "tax_saving":      tax_saving,
                    "tax_saving_str":  f"~₹{tax_saving:,.0f}/yr",
                    "rationale":       "u/s 80C — deductible up to ₹1.5L. ELSS has shortest lock-in among 80C options.",
                    "risk_note":       "Equity market risk. 3-year lock-in per SIP instalment. Recommend SIP rather than lumpsum.",
                })

        # ── PPF: EEE instrument not in portfolio ─────────────────────────────
        if ppf_total == 0 and is_old_regime:
            eighty_c_used = float(ded_detail.get("eighty_c", 0.0))
            ppf_room = max(0.0, min(150_000.0 - eighty_c_used, 150_000.0))
            if ppf_room > 0:
                tax_saving = round(ppf_room * marginal_rate_cess, 0)
                recs.append({
                    "title":           "Open / Top-Up PPF Account",
                    "section":         "80C (EEE)",
                    "priority":        "High" if tax_saving > 8_000 else "Medium",
                    "current_holding": "No PPF investment detected in your portfolio.",
                    "action":          f"Invest up to ₹{ppf_room:,.0f} in PPF. PPF is EEE — contribution deductible u/s 80C, interest earned is tax-free u/s 10(11), maturity proceeds are tax-free.",
                    "tax_saving":      tax_saving,
                    "tax_saving_str":  f"~₹{tax_saving:,.0f}/yr",
                    "rationale":       "EEE instrument — Exempt-Exempt-Exempt. Current PPF rate 7.1% p.a., fully tax-free.",
                    "risk_note":       "15-year lock-in (partial withdrawal from year 7). Sovereign-backed, zero default risk.",
                })

        # ── NPS 80CCD(1B): ₹50K extra deduction ─────────────────────────────
        if is_old_regime:
            nps_1b_used = float(deductions.get("nps_80ccd_1b", 0.0))
            nps_gap = max(0.0, 50_000.0 - nps_1b_used)
            if nps_gap > 0 and nps_total == 0:
                tax_saving = round(nps_gap * marginal_rate_cess, 0)
                recs.append({
                    "title":           "Invest in NPS Tier-1 (80CCD(1B))",
                    "section":         "80CCD(1B)",
                    "priority":        "High" if tax_saving > 5_000 else "Medium",
                    "current_holding": f"No NPS Tier-1 detected. 80CCD(1B) used: ₹{nps_1b_used:,.0f} / ₹50,000.",
                    "action":          f"Invest ₹{nps_gap:,.0f} in NPS Tier-1. This is OVER AND ABOVE the ₹1.5L 80C limit — an additional exclusive deduction. Choose Aggressive (75% equity) or Moderate (50% equity) allocation.",
                    "tax_saving":      tax_saving,
                    "tax_saving_str":  f"~₹{tax_saving:,.0f}/yr",
                    "rationale":       "u/s 80CCD(1B) — exclusive ₹50K deduction, not part of 80C. Reduces taxable income directly.",
                    "risk_note":       "Partial lock-in until age 60. On exit, 60% lumpsum is tax-free; 40% must be used to buy annuity (taxable). Market-linked returns.",
                })

        # ── LTCG Harvesting: annual reset ────────────────────────────────────
        taxable_equity_ltcg = float(cg_detail.get("taxable_equity_ltcg", 0.0))
        total_equity_ltcg   = float(cg_detail.get("total_equity_ltcg", 0.0))
        if taxable_equity_ltcg > 0:
            ltcg_tax = float(cg_detail.get("tax_equity_ltcg", 0.0))
            # Harvesting saves the LTCG tax by resetting cost base
            recs.append({
                "title":           "LTCG Harvesting — Reset Cost Base",
                "section":         "LTCG Harvesting",
                "priority":        "High" if ltcg_tax > 5_000 else "Medium",
                "current_holding": f"Taxable Equity LTCG: ₹{taxable_equity_ltcg:,.0f} (above ₹1.25L exempt). Generating tax of ~₹{ltcg_tax:,.0f}.",
                "action":          "Book gains in equity/equity MF positions at fiscal year-end (Feb–Mar). Re-enter the same position immediately. This resets your cost base to current price, so future LTCG starts fresh from ₹0. Use the annual ₹1.25L exemption every year.",
                "tax_saving":      ltcg_tax,
                "tax_saving_str":  f"~₹{ltcg_tax:,.0f}/yr",
                "rationale":       "Equity LTCG exempt up to ₹1.25L per year u/s 112A. Annual harvesting prevents accumulation of taxable gains.",
                "risk_note":       "Re-entry has market timing risk (price may move between sell and buy). Best done for long-term core holdings. STT applicable on each transaction.",
            })

        # ── STCG → Hold to qualify for LTCG ─────────────────────────────────
        equity_stcg = float((tax_result.get("cg_tax_detail") or {}).get("equity_stcg", 0.0))
        if equity_stcg == 0:
            # Try from saved CG data passed in context
            pass
        stcg_tax = float(cg_detail.get("tax_equity_stcg", 0.0))
        if stcg_tax > 0:
            # STCG rate 20% vs LTCG 12.5% — holding > 1 yr saves the diff
            stcg_to_ltcg_saving = round(float(cg_detail.get("taxable_equity_stcg", 0.0)) * (0.20 - 0.125), 0)
            if stcg_to_ltcg_saving > 500:
                recs.append({
                    "title":           "Hold Short-Term Positions to Qualify for LTCG",
                    "section":         "LTCG vs STCG",
                    "priority":        "Medium",
                    "current_holding": f"Equity STCG taxed @ 20% (+ cess). Estimated STCG tax: ~₹{stcg_tax:,.0f}.",
                    "action":          "Identify equity / equity MF positions held < 12 months. Defer sale past the 1-year mark to convert STCG (20%) into LTCG (12.5%). Review your portfolio holding periods in broker console before booking profits.",
                    "tax_saving":      stcg_to_ltcg_saving,
                    "tax_saving_str":  f"~₹{stcg_to_ltcg_saving:,.0f}/yr",
                    "rationale":       "STCG rate u/s 111A = 20% + cess. LTCG rate u/s 112A = 12.5% + cess (above ₹1.25L). Holding > 365 days cuts rate by 7.5 ppts.",
                    "risk_note":       "Market risk during holding period. Use stop-losses. Do not hold just for tax if fundamentals deteriorate.",
                })

        # ── SCSS / RD over-allocation in taxable debt ────────────────────────
        if scss_total > 500_000:
            scss_interest = round(scss_total * SCSS_RATE, 0)
            scss_tax      = round(scss_interest * marginal_rate_cess, 0)
            redirect_amt  = scss_total * 0.20
            recs.append({
                "title":           "Diversify Away from SCSS (Reduce Taxable Interest)",
                "section":         "Debt Rebalance",
                "priority":        "Low",
                "current_holding": f"₹{scss_total:,.0f} in SCSS @ {SCSS_RATE*100:.1f}% p.a. Annual interest ~₹{scss_interest:,.0f}, tax drag ~₹{scss_tax:,.0f}/yr.",
                "action":          f"On maturity / partial withdrawal, redirect ₹{redirect_amt:,.0f} into SGB (Sovereign Gold Bond). SGB coupon (2.5%) is taxable but redemption gain after 8 yrs is fully exempt u/s 47(viic). Also consider PPF for EEE benefits.",
                "tax_saving":      round(redirect_amt * (SCSS_RATE - 0.025) * marginal_rate_cess, 0),
                "tax_saving_str":  f"Reduces taxable interest by ~₹{round(redirect_amt * (SCSS_RATE - 0.025), 0):,.0f}/yr",
                "rationale":       "SGB redemption (after 8 yrs) fully exempt u/s 47(viic). SCSS interest is fully taxable, with 80TTB exemption of only ₹50K for seniors.",
                "risk_note":       "SCSS is sovereign-backed and ideal for seniors. This is only for excess allocation. SGB has 8-yr lock-in; secondary market liquidity is limited.",
            })

        # ── Health Insurance (80D) gap ────────────────────────────────────────
        if is_old_regime:
            hi_self = float(deductions.get("health_ins_self", 0.0))
            if hi_self == 0:
                tax_saving_80d = round(25_000 * marginal_rate_cess, 0)
                recs.append({
                    "title":           "Buy Health Insurance — Claim 80D Deduction",
                    "section":         "80D",
                    "priority":        "High",
                    "current_holding": "No health insurance premium entered in your deductions.",
                    "action":          "Purchase a health insurance policy for self & family. Premium up to ₹25,000 (₹50,000 for senior citizens) is deductible u/s 80D. Choose a ₹10L+ family floater.",
                    "tax_saving":      tax_saving_80d,
                    "tax_saving_str":  f"~₹{tax_saving_80d:,.0f}/yr",
                    "rationale":       "u/s 80D — health insurance premium deductible. Self+family: ₹25K; parents: additional ₹25K (₹50K if senior).",
                    "risk_note":       "This is financial planning, not just tax — medical inflation in India runs at 12–15% p.a.",
                })

        # ── SGB: no gold allocation in portfolio ─────────────────────────────
        if sgb_total == 0 and equity_total > 500_000:
            gold_target = round(equity_total * 0.10, 0)
            recs.append({
                "title":           "Add Sovereign Gold Bond (SGB) for Tax-Free Gold Exposure",
                "section":         "Gold / Diversification",
                "priority":        "Low",
                "current_holding": f"No SGB detected. Equity portfolio: ₹{equity_total:,.0f}. No gold allocation.",
                "action":          f"Invest ~₹{gold_target:,.0f} (10% of equity) in SGB. You earn 2.5% p.a. taxable coupon + gold price appreciation. Redemption gain after 8 years is completely tax-free u/s 47(viic).",
                "tax_saving":      0.0,
                "tax_saving_str":  "Redemption gain fully exempt after 8 yrs",
                "rationale":       "SGB capital gains on redemption: 100% exempt u/s 47(viic). Physical gold/gold MF: LTCG at 12.5% after 2 yrs.",
                "risk_note":       "Gold price is volatile. SGB has 8-yr lock-in (exit window every 6 months from year 5). Not recommended if you may need liquidity.",
            })

        # ── High FD % of portfolio warning ───────────────────────────────────
        if total_invested > 0 and fd_rd_total / max(total_invested, 1) > 0.35:
            fd_pct = fd_rd_total / total_invested * 100
            excess_fd = fd_rd_total - total_invested * 0.25
            excess_tax = round(excess_fd * DEFAULT_FD_RATE * marginal_rate_cess, 0)
            recs.append({
                "title":           "Reduce FD Over-Concentration",
                "section":         "Portfolio Rebalance",
                "priority":        "Medium",
                "current_holding": f"FD/RD = {fd_pct:.0f}% of portfolio (₹{fd_rd_total:,.0f}). Recommended ceiling: 25%.",
                "action":          f"Redeploy ₹{excess_fd:,.0f} excess FD into PPF (80C/EEE), ELSS (80C/equity growth), or Debt MF (tax-deferred). This shifts income from annually-taxed interest to tax-deferred or exempt growth.",
                "tax_saving":      excess_tax,
                "tax_saving_str":  f"~₹{excess_tax:,.0f}/yr on excess portion",
                "rationale":       "FD interest is taxable as 'Other Sources' every year (accrual basis). Optimal fixed-income allocation: 20-25% of portfolio.",
                "risk_note":       "Only redeploy on maturity to avoid premature withdrawal penalties. Build ₹3–6 month emergency fund in FD/liquid fund first.",
            })

    else:
        # No holdings — generic recommendations
        if is_old_regime:
            recs.append({
                "title":           "Add Investments to Unlock Full 80C Benefit",
                "section":         "80C",
                "priority":        "High",
                "current_holding": "No portfolio holdings found.",
                "action":          "Invest ₹1,50,000 in PPF, ELSS, or Tax-Saver FD to claim full 80C deduction.",
                "tax_saving":      round(150_000 * marginal_rate_cess, 0),
                "tax_saving_str":  f"~₹{round(150_000 * marginal_rate_cess, 0):,.0f}/yr",
                "rationale":       "u/s 80C — ₹1.5L deductible from taxable income.",
                "risk_note":       "Choose instrument based on risk appetite and liquidity needs.",
            })

    # ── Sort by tax saving descending, then priority ──────────────────────────
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    recs.sort(key=lambda x: (-x["tax_saving"], priority_order.get(x["priority"], 3)))

    # Deduplicate by title
    seen_titles: set = set()
    deduped = []
    for r in recs:
        if r["title"] not in seen_titles:
            deduped.append(r)
            seen_titles.add(r["title"])

    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# 8. MASTER COMPUTE
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
