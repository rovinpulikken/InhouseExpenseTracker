"""
algo_advisor.py
Risk-Budgeted Core-Satellite algorithmic advisor (Indian markets).

Pure-python engine (testable without Streamlit):
    build_algo_advice(holdings_df, risk_tolerance, age, monthly_sip, regime) -> dict
    fetch_market_regime() -> dict            (yfinance, fails soft)
    evaluate_regime(regime, tier) -> dict    (pure rules)
and a Streamlit renderer:
    render_algo_advisor(inv_df, current_user, monthly_sip)

Tiers
  Low       9-10%   Debt 65 / Gold 15 / Large-cap 20
  Moderate  10-12%  Equity 50 (Large 35 + Flexi 15) / Debt&Arb 35 / Gold 15
  High      12-15%  Equity 75 (Large 40 + Factor 20 + Mid/Small 15) / Gold 10 / Cash 15
Rules
  * Rebalance when any sleeve drifts > 5% (and review at least semi-annually)
  * Low: freeze equity buying if Nifty is >10% below its 52-week peak
  * Moderate: halve equity inflow (park in arbitrage) when Nifty < 200 DMA
  * High: crash deployment - 5% of portfolio from the cash bucket per 3% fall once the
    market has dropped 7-10% in a short window
  * Volatility guardrail: India VIX spike -> shift part of Mid/Small into liquid/arbitrage
"""
from typing import Any, Dict, List, Optional

DRIFT_BAND = 5.0            # % drift that triggers a rebalance
VIX_CAUTION = 18.0
VIX_SPIKE = 22.0
VIX_SHIFT_FRACTION = 0.25   # share of Mid/Small moved to liquid/arbitrage on a VIX spike
FREEZE_DRAWDOWN = 10.0      # Low tier: freeze equity buys if Nifty is this far below peak
FLASH_DROP = 7.0            # High tier: flash correction threshold (% in ~10 sessions)
TRANCHE_STEP = 3.0          # % market fall per deployment tranche
TRANCHE_SIZE = 5.0          # % of portfolio deployed per tranche
CONCENTRATION_LIMIT = 15.0  # % of portfolio in one holding

LARGE, FLEXI, FACTOR, MIDSMALL = "Large-Cap / Index", "Flexi / Multi-Cap", "Factor / Momentum", "Mid / Small Cap"
DEBT, GOLD, CASH, EXCLUDED = "Debt & Arbitrage", "Gold", "Liquid / Cash", "Excluded"
EQUITY_SLEEVES = (LARGE, FLEXI, FACTOR, MIDSMALL)
SLEEVES = (LARGE, FLEXI, FACTOR, MIDSMALL, DEBT, GOLD, CASH)

TIERS: Dict[str, Dict[str, Any]] = {
    "Low": {
        "target_return": "9% – 10%",
        "objective": "Capital preservation with a small kicker over FDs; minimal drawdowns.",
        "weights": {DEBT: 65.0, GOLD: 15.0, LARGE: 20.0},
        "rule": "Zero equity buying on deep drops (>10% below peak) until the market recovers.",
    },
    "Moderate": {
        "target_return": "10% – 12%",
        "objective": "Balanced accumulation that absorbs shocks via large-caps and tactical debt.",
        "weights": {LARGE: 35.0, FLEXI: 15.0, DEBT: 35.0, GOLD: 15.0},
        "rule": "200-DMA trend filter: below it, equity inflow is halved and parked in arbitrage funds.",
    },
    "High": {
        "target_return": "12% – 15%",
        "objective": "Aggressive compounding that harnesses volatility; outperform over full cycles.",
        "weights": {LARGE: 40.0, FACTOR: 20.0, MIDSMALL: 15.0, GOLD: 10.0, CASH: 15.0},
        "rule": "Dip deployment: 5% of portfolio from the cash bucket per 3% fall after a 7–10% flash correction.",
    },
}

RISK_TO_TIER = {"Conservative": "Low", "Moderate": "Moderate", "Aggressive": "High"}

INSTRUMENTS = {
    LARGE: "Nifty 50 index fund / ETF (low-cost, large-cap core)",
    FLEXI: "Flexi/multi-cap fund with quality-momentum filters",
    FACTOR: "Nifty200 Momentum 30 or Nifty100 Low Volatility 30 index fund",
    MIDSMALL: "Midcap/smallcap fund or index filtered for high RoCE and low debt-to-equity",
    DEBT: "Target-maturity G-Sec/SDL index fund, high-credit corporate bond fund, arbitrage / short-duration debt fund",
    GOLD: "Sovereign Gold Bond (secondary market) or Gold ETF",
    CASH: "Liquid fund (opportunity reserve for dips)",
}


# ---------------------------------------------------------------------------
# Profile -> tier
# ---------------------------------------------------------------------------
def select_tier(risk_tolerance: str = "Moderate", age: Optional[int] = None, override: Optional[str] = None):
    """Return (tier, reason). Age guardrails cap risk for older investors."""
    if override in TIERS:
        return override, "Selected manually."
    tier = RISK_TO_TIER.get(risk_tolerance or "Moderate", "Moderate")
    reason = f"Mapped from your risk profile ({risk_tolerance or 'Moderate'})."
    try:
        a = int(age) if age else None
    except Exception:
        a = None
    if a is not None:
        if a >= 70 and tier != "Low":
            return "Low", f"Capped to Low because of age {a} (capital preservation)."
        if a >= 60 and tier == "High":
            return "Moderate", f"Capped to Moderate because of age {a}."
    return tier, reason


# ---------------------------------------------------------------------------
# Holding classification
# ---------------------------------------------------------------------------
_DEBT_KEYS = ("epf", "ppf", "nsc", "kvp", "fixed deposit", "recurring", "debt", "gilt", "g-sec", "gsec",
              "bond", "target maturity", "sdl", "arbitrage", "fd")
_CASH_KEYS = ("liquid", "overnight", "money market", "cash", "savings")
_EXCLUDED_KEYS = ("real estate", "property", "land", "plot", "flat", "apartment", "house", "villa", "startup")


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def classify_holding(row: Dict[str, Any]) -> str:
    itype = _clean_str(row.get("investment_type")).lower()
    name = " ".join(_clean_str(row.get(k)) for k in ("description", "resolved_name", "sector_segment")).lower()
    text = (itype + " " + name).strip()
    mc = _clean_str(row.get("market_cap")).lower()

    if any(k in text for k in _EXCLUDED_KEYS):
        return EXCLUDED
    if "gold" in text or "sgb" in text:
        return GOLD
    if any(k in text for k in _CASH_KEYS) and "equity" not in itype and "stock" not in itype:
        return CASH
    if "arbitrage" in text:
        return DEBT
    is_equity_type = ("equity" in itype or "stock" in itype or "mutual" in itype or "structured" in itype)
    if not is_equity_type and any(k in text for k in _DEBT_KEYS):
        return DEBT
    # equity-like from here
    if any(k in text for k in ("momentum", "low vol", "lowvol", "alpha", "factor")):
        return FACTOR
    if "small" in mc or "mid" in mc or any(k in name for k in ("midcap", "mid cap", "smallcap", "small cap")):
        return MIDSMALL
    if "flexi" in name or "multi" in name:
        return FLEXI
    if "large" in mc or any(k in name for k in ("nifty 50", "nifty50", "sensex", "bluechip", "blue chip",
                                                "large cap", "largecap", "index")):
        return LARGE
    if is_equity_type:
        return FLEXI
    if any(k in text for k in _DEBT_KEYS):
        return DEBT
    return EXCLUDED


def _holding_name(row: Dict[str, Any]) -> str:
    desc = _clean_str(row.get("description"))
    res = _clean_str(row.get("resolved_name"))
    itype = _clean_str(row.get("investment_type")) or "Holding"
    if res and desc and res.lower() != desc.lower():
        return f"{res} ({desc})"
    return res or desc or itype


# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------
def fetch_market_regime() -> Dict[str, Any]:
    """Nifty 50 trend / drawdown / flash-drop and India VIX. Fails soft with None values."""
    out: Dict[str, Any] = {"available": False, "nifty": None, "dma200": None, "peak_52w": None,
                           "drawdown_pct": None, "drop_10d_pct": None, "vix": None}
    try:
        import yfinance as yf
        data = yf.download("^NSEI", period="1y", progress=False, auto_adjust=True)
        if data is not None and not data.empty:
            close = data["Close"].squeeze().dropna()
            if len(close) >= 20:
                last = float(close.iloc[-1])
                out["nifty"] = last
                out["dma200"] = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
                peak = float(close.max())
                out["peak_52w"] = peak
                out["drawdown_pct"] = (peak - last) / peak * 100.0 if peak else None
                recent_peak = float(close.iloc[-10:].max())
                out["drop_10d_pct"] = (recent_peak - last) / recent_peak * 100.0 if recent_peak else None
                out["available"] = True
    except Exception as e:
        print(f"Nifty fetch error: {e}")
    try:
        import yfinance as yf
        v = yf.download("^INDIAVIX", period="1mo", progress=False, auto_adjust=True)
        if v is not None and not v.empty:
            out["vix"] = float(v["Close"].squeeze().dropna().iloc[-1])
            out["available"] = True
    except Exception as e:
        print(f"VIX fetch error: {e}")
    return out


def evaluate_regime(regime: Optional[Dict[str, Any]], tier: str) -> Dict[str, Any]:
    """Apply the tier's trigger rules to market data. Returns flags + human-readable signals."""
    r = regime or {}
    res = {"freeze_equity": False, "halve_equity": False, "deploy_tranches": 0,
           "vix_shift": False, "signals": [], "available": bool(r.get("available"))}
    if not res["available"]:
        res["signals"].append("ℹ️ Live market data unavailable — allocation advice shown without trigger overlays.")
        return res

    dd, nifty, dma, vix, drop = (r.get("drawdown_pct"), r.get("nifty"), r.get("dma200"),
                                 r.get("vix"), r.get("drop_10d_pct"))
    if nifty is not None:
        line = f"Nifty 50 at {nifty:,.0f}"
        if dma:
            line += f" ({'above' if nifty >= dma else 'below'} 200-DMA {dma:,.0f})"
        if dd is not None:
            line += f", {dd:.1f}% below 52-week peak"
        res["signals"].append("📈 " + line + ".")

    if tier == "Low" and dd is not None and dd > FREEZE_DRAWDOWN:
        res["freeze_equity"] = True
        res["signals"].append(f"🧊 Downside trigger: Nifty is {dd:.1f}% below peak (> {FREEZE_DRAWDOWN:.0f}%). "
                              "Equity buying is FROZEN; add to debt/gold instead.")
    if tier == "Moderate" and nifty is not None and dma and nifty < dma:
        res["halve_equity"] = True
        res["signals"].append("📉 Trend filter: Nifty is below its 200-DMA. Equity inflow is HALVED; "
                              "park the rest in arbitrage funds until it crosses back above.")
    if tier == "High" and drop is not None and drop >= FLASH_DROP:
        n = max(1, int(drop // TRANCHE_STEP))
        res["deploy_tranches"] = n
        res["signals"].append(f"⚡ Flash correction: Nifty fell {drop:.1f}% in ~10 sessions. Deploy {n} tranche(s) "
                              f"of {TRANCHE_SIZE:.0f}% of your portfolio from the cash bucket into quality equity.")
    if vix is not None:
        if vix >= VIX_SPIKE:
            res["vix_shift"] = tier in ("High",)
            res["signals"].append(f"🌪️ India VIX {vix:.1f} (spike ≥ {VIX_SPIKE:.0f}). "
                                  + ("Shift 25% of Mid/Small caps into liquid/arbitrage funds." if tier == "High"
                                     else "Avoid adding to volatile mid/small caps."))
        elif vix >= VIX_CAUTION:
            res["signals"].append(f"⚠️ India VIX {vix:.1f} is elevated — stagger purchases.")
        else:
            res["signals"].append(f"✅ India VIX {vix:.1f} — calm volatility regime.")
    return res


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
def _fmt(v: float) -> str:
    v = float(v)
    if abs(v) >= 1e7:
        return f"₹{v / 1e7:.2f} Cr"
    if abs(v) >= 1e5:
        return f"₹{v / 1e5:.2f} L"
    return f"₹{v:,.0f}"


def build_algo_advice(holdings_df, risk_tolerance: str = "Moderate", age: Optional[int] = None,
                      monthly_sip: float = 0.0, regime: Optional[Dict[str, Any]] = None,
                      tier_override: Optional[str] = None) -> Dict[str, Any]:
    tier, tier_reason = select_tier(risk_tolerance, age, tier_override)
    cfg = TIERS[tier]
    weights = cfg["weights"]
    reg = evaluate_regime(regime, tier)

    if holdings_df is None or len(holdings_df) == 0:
        return {"error": "No holdings found. Add your investments to get algorithmic advice.", "tier": tier}

    rows: List[Dict[str, Any]] = []
    for rec in holdings_df.to_dict("records"):
        rec = dict(rec)
        rec["sleeve"] = classify_holding(rec)
        rec["value"] = float(rec.get("current_value") or 0.0)
        rec["ret"] = float(rec.get("returns_pct") or 0.0)
        rows.append(rec)

    excluded_value = sum(r["value"] for r in rows if r["sleeve"] == EXCLUDED)
    inv_rows = [r for r in rows if r["sleeve"] != EXCLUDED]
    total = sum(r["value"] for r in inv_rows)
    if total <= 0:
        return {"error": "Investable portfolio value is zero. Update current values first.", "tier": tier}

    cur_val = {s: 0.0 for s in SLEEVES}
    for r in inv_rows:
        cur_val[r["sleeve"]] += r["value"]

    sleeve_rows = []
    for s in SLEEVES:
        cur = cur_val[s] / total * 100.0
        tgt = weights.get(s, 0.0)
        drift = cur - tgt
        if drift > DRIFT_BAND:
            action = "SELL / TRIM"
        elif drift < -DRIFT_BAND:
            action = "BUY"
        else:
            action = "HOLD"
        if tgt == 0 and cur_val[s] == 0:
            continue
        sleeve_rows.append({"Sleeve": s, "Current %": round(cur, 1), "Target %": tgt, "Drift %": round(drift, 1),
                            "Action": action, "Amount": abs(drift) / 100.0 * total if action != "HOLD" else 0.0})
    drift_by = {x["Sleeve"]: x for x in sleeve_rows}

    # --- holding-level decisions -------------------------------------------------
    trim_budget = {s: (drift_by[s]["Amount"] if s in drift_by and drift_by[s]["Action"] == "SELL / TRIM" else 0.0)
                   for s in SLEEVES}
    hold_actions: List[Dict[str, Any]] = []
    for r in sorted(inv_rows, key=lambda x: x["ret"]):          # weakest performers are trimmed first
        s = r["sleeve"]
        weight = r["value"] / total * 100.0
        action, reason, amount = "HOLD", "Sleeve within target band.", 0.0
        if trim_budget[s] > 0:
            amount = min(r["value"], trim_budget[s])
            trim_budget[s] -= amount
            action = "SELL / TRIM"
            reason = f"{s} is overweight by {drift_by[s]['Drift %']:.1f}% — rebalance to target (weakest performers first)."
        if reg["vix_shift"] and s == MIDSMALL:
            vix_amt = r["value"] * VIX_SHIFT_FRACTION
            if vix_amt > amount:
                amount = vix_amt
                action = "SELL / TRIM"
                reason = "VIX spike guardrail: move 25% of Mid/Small cap into liquid/arbitrage."
        if weight > CONCENTRATION_LIMIT and s in EQUITY_SLEEVES:
            excess = r["value"] - CONCENTRATION_LIMIT / 100.0 * total
            if excess > amount:
                amount = excess
                action = "SELL / TRIM"
                reason = f"Concentration: {weight:.1f}% of portfolio in one holding (limit {CONCENTRATION_LIMIT:.0f}%)."
        if action == "HOLD" and s in EQUITY_SLEEVES and r["ret"] <= -15:
            action, reason = "REVIEW", f"Down {abs(r['ret']):.1f}% — check fundamentals / switch to an index fund."
        elif action == "HOLD" and r["ret"] > 15:
            reason = f"Within target band; strong return (+{r['ret']:.1f}%)."
        hold_actions.append({"Holding": _holding_name(r), "Sleeve": s, "Value": r["value"],
                             "Weight %": round(weight, 1), "Return %": round(r["ret"], 1),
                             "Action": action, "Amount": amount, "Reason": reason})
    hold_actions.sort(key=lambda x: -x["Value"])
    for r in rows:
        if r["sleeve"] == EXCLUDED:
            hold_actions.append({"Holding": _holding_name(r), "Sleeve": EXCLUDED, "Value": r["value"],
                                 "Weight %": 0.0, "Return %": round(r["ret"], 1), "Action": "HOLD", "Amount": 0.0,
                                 "Reason": "Real estate / startup — outside the algorithm's liquid universe."})

    # --- buy list with regime overlays --------------------------------------------
    buys: List[Dict[str, Any]] = []
    for x in sleeve_rows:
        if x["Action"] != "BUY":
            continue
        s, amt = x["Sleeve"], x["Amount"]
        note = ""
        if s in EQUITY_SLEEVES:
            if reg["freeze_equity"]:
                buys.append({"Sleeve": s, "Amount": 0.0, "Instrument": INSTRUMENTS[s],
                             "Note": f"FROZEN (Nifty >{FREEZE_DRAWDOWN:.0f}% below peak). Revisit on recovery."})
                continue
            if reg["halve_equity"]:
                buys.append({"Sleeve": s, "Amount": amt / 2.0, "Instrument": INSTRUMENTS[s],
                             "Note": f"Halved (below 200-DMA); park {_fmt(amt / 2.0)} in an arbitrage fund meanwhile."})
                continue
        if s == CASH and reg["deploy_tranches"]:
            note = "Cash is the dip-deployment reserve — build it, then use the crash rule."
        buys.append({"Sleeve": s, "Amount": amt, "Instrument": INSTRUMENTS[s], "Note": note})

    if reg["deploy_tranches"]:
        avail = cur_val[CASH]
        want = reg["deploy_tranches"] * TRANCHE_SIZE / 100.0 * total
        deploy = min(avail, want)
        buys.append({"Sleeve": "Crash deployment", "Amount": deploy,
                     "Instrument": INSTRUMENTS[LARGE] + " / quality equity",
                     "Note": (f"{reg['deploy_tranches']} tranche(s) × {TRANCHE_SIZE:.0f}% from cash"
                              + ("" if deploy >= want else f" (limited to available cash {_fmt(avail)})"))})

    # --- monthly SIP routing --------------------------------------------------------
    sip_plan: List[Dict[str, Any]] = []
    if monthly_sip and monthly_sip > 0:
        under = {x["Sleeve"]: -x["Drift %"] for x in sleeve_rows if x["Drift %"] < 0}
        base = under if under else {s: w for s, w in weights.items()}
        tot_b = sum(base.values()) or 1.0
        alloc = {s: monthly_sip * v / tot_b for s, v in base.items()}
        redirect = 0.0
        for s in list(alloc):
            if s in EQUITY_SLEEVES and reg["freeze_equity"]:
                redirect += alloc[s]; alloc[s] = 0.0
            elif s in EQUITY_SLEEVES and reg["halve_equity"]:
                redirect += alloc[s] / 2.0; alloc[s] /= 2.0
        if redirect:
            alloc[DEBT] = alloc.get(DEBT, 0.0) + redirect
        for s, v in alloc.items():
            if v > 0:
                sip_plan.append({"Sleeve": s, "Monthly ₹": v, "Instrument": INSTRUMENTS[s]})

    # --- executive summary ------------------------------------------------------------
    sells = [h for h in hold_actions if h["Action"] == "SELL / TRIM" and h["Amount"] > 0]
    reviews = [h for h in hold_actions if h["Action"] == "REVIEW"]
    n_hold = sum(1 for h in hold_actions if h["Action"] == "HOLD")
    need_rebalance = any(x["Action"] != "HOLD" for x in sleeve_rows)
    equity_now = sum(cur_val[s] for s in EQUITY_SLEEVES) / total * 100.0
    equity_tgt = sum(w for s, w in weights.items() if s in EQUITY_SLEEVES)
    if need_rebalance:
        headline = "⚖️ Rebalance recommended"
    elif reg["freeze_equity"] or reg["halve_equity"] or reg["deploy_tranches"] or reg["vix_shift"]:
        headline = "🚦 Portfolio on target — market triggers active"
    else:
        headline = "✅ Portfolio on track — hold and keep investing"

    lines = [
        f"**{headline}.** Based on your profile you are on the **{tier}-risk** algorithm "
        f"(target return {cfg['target_return']}; {tier_reason}).",
        f"Your investable portfolio is **{_fmt(total)}** with **{equity_now:.0f}% equity** against a target of "
        f"**{equity_tgt:.0f}%**."
        + (f" ({_fmt(excluded_value)} of real estate/startup holdings is excluded.)" if excluded_value else ""),
    ]
    if sells:
        tot_sell = sum(h["Amount"] for h in sells)
        lines.append(f"**SELL / TRIM:** {_fmt(tot_sell)} across {len(sells)} holding(s) — e.g. "
                     + ", ".join(f"{h['Holding']} ({_fmt(h['Amount'])})" for h in sells[:3]) + ".")
    real_buys = [b for b in buys if b["Amount"] > 0]
    if real_buys:
        lines.append("**BUY:** " + "; ".join(f"{b['Sleeve']} ({_fmt(b['Amount'])})" for b in real_buys[:4]) + ".")
    frozen = [b for b in buys if b["Amount"] == 0]
    if frozen:
        lines.append("**BUY (deferred):** " + ", ".join(b["Sleeve"] for b in frozen) + " — equity buying is frozen by the downside trigger.")
    if reviews:
        lines.append("**REVIEW:** " + ", ".join(h["Holding"] for h in reviews[:3]) + " (deep losses).")
    lines.append(f"**HOLD:** {n_hold} holding(s) stay as they are.")
    if reg["signals"]:
        lines.append("**Market overlay:** " + " ".join(s.split(' ', 1)[1] if ' ' in s else s for s in reg["signals"][:3]))
    if monthly_sip and sip_plan:
        top = max(sip_plan, key=lambda x: x["Monthly ₹"])
        lines.append(f"**Monthly SIP {_fmt(monthly_sip)}:** route mostly to {top['Sleeve']} ({_fmt(top['Monthly ₹'])}).")

    return {"tier": tier, "tier_reason": tier_reason, "config": cfg, "total_value": total,
            "excluded_value": excluded_value, "sleeve_rows": sleeve_rows, "holding_actions": hold_actions,
            "buys": buys, "sip_plan": sip_plan, "regime": reg, "headline": headline,
            "summary_lines": lines, "need_rebalance": need_rebalance}


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
def render_algo_advisor(inv_df, current_user: Dict[str, Any], monthly_sip: float = 0.0) -> None:
    import streamlit as st
    import pandas as pd

    st.markdown("#### 🧮 Algorithmic Advisor — Risk-Budgeted Core-Satellite")
    if inv_df is None or inv_df.empty:
        st.info("Add holdings to get an algorithmic Hold / Buy / Sell summary.")
        return

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached_regime():
        return fetch_market_regime()

    c1, c2 = st.columns([2, 1])
    with c1:
        choice = st.selectbox("Algorithm tier",
                              ["Auto (from my profile)", "Low (9–10%)", "Moderate (10–12%)", "High (12–15%)"],
                              key="algo_tier_choice")
    with c2:
        st.caption(f"Profile: risk **{current_user.get('risk_tolerance', 'Moderate')}**, "
                   f"age **{current_user.get('age', '—')}**")
    override = None if choice.startswith("Auto") else choice.split(" ")[0]

    with st.spinner("Reading Nifty 50 trend & India VIX..."):
        regime = _cached_regime()
    res = build_algo_advice(inv_df, current_user.get("risk_tolerance", "Moderate"), current_user.get("age"),
                            monthly_sip, regime, override)
    if "error" in res:
        st.warning(res["error"])
        return

    # Executive summary
    st.markdown("##### 📋 Executive Summary")
    box = st.container(border=True)
    for ln in res["summary_lines"]:
        box.markdown(ln)
    cfg = res["config"]
    st.caption(f"**{res['tier']} tier** — {cfg['objective']}  Key trigger: {cfg['rule']}")

    t_alloc, t_hold, t_buy, t_mkt = st.tabs(["⚖️ Allocation Drift", "💼 Holding Actions", "🛒 Buy List & SIP", "🌐 Market Triggers"])
    badge = {"BUY": "🟢 BUY", "SELL / TRIM": "🔴 SELL / TRIM", "HOLD": "⚪ HOLD", "REVIEW": "🟠 REVIEW"}
    with t_alloc:
        df = pd.DataFrame(res["sleeve_rows"])
        df["Action"] = df["Action"].map(badge)
        df["Amount"] = df["Amount"].apply(lambda v: _fmt(v) if v else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Rebalance when any sleeve drifts more than {DRIFT_BAND:.0f}% (and review at least every 6 months).")
    with t_hold:
        h = pd.DataFrame(res["holding_actions"])
        h["Action"] = h["Action"].map(badge)
        h["Value"] = h["Value"].apply(_fmt)
        h["Amount"] = h["Amount"].apply(lambda v: _fmt(v) if v else "—")
        st.dataframe(h, use_container_width=True, hide_index=True)
    with t_buy:
        if res["buys"]:
            b = pd.DataFrame(res["buys"])
            b["Amount"] = b["Amount"].apply(lambda v: _fmt(v) if v else "—")
            st.dataframe(b, use_container_width=True, hide_index=True)
        else:
            st.success("No purchases needed to reach target weights.")
        if res["sip_plan"]:
            st.markdown("**Monthly SIP routing**")
            s = pd.DataFrame(res["sip_plan"])
            s["Monthly ₹"] = s["Monthly ₹"].apply(_fmt)
            st.dataframe(s, use_container_width=True, hide_index=True)
    with t_mkt:
        for sig in res["regime"]["signals"]:
            st.markdown(f"- {sig}")
    st.caption("⚠️ Rule-based model output for education — not SEBI-registered investment advice. "
               "Instruments are categories, not specific recommendations.")
