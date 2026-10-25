"""
academy_fallback.py
Database-driven (no AI) fallback for the Financial Academy.

Used when the Gemini service is busy/unavailable:
  * Multiple-choice assessment questions personalised with the user's real figures.
  * Rule-based scoring -> level / persona / summary.
  * Rule-based learning path built from curated resources.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

MAX_QUESTIONS = 5


def _inr(x: float) -> str:
    return f"₹{x:,.0f}"


# ---------------------------------------------------------------------------
# Profile (real figures from the app database)
# ---------------------------------------------------------------------------
def build_user_profile(username: str, family_id: int = 1) -> Dict[str, Any]:
    """Collect the figures used to personalise questions. Never raises."""
    p: Dict[str, Any] = {
        "monthly_income": 0.0, "monthly_expense": 0.0, "top_category": None,
        "top_category_amount": 0.0, "top_category_pct": 0.0, "total_debt": 0.0,
        "portfolio_value": 0.0, "equity_pct": None, "asset_classes": {},
    }
    try:
        from database import get_income_sources_df
        inc = get_income_sources_df(username, family_id, view_mode="All")
        if not inc.empty:
            p["monthly_income"] = float(inc["monthly_equivalent"].sum())
    except Exception:
        pass
    try:
        from database import get_expenses_df
        df = get_expenses_df(username=username, view_mode="Family", family_id=family_id)
        if not df.empty:
            months = max(1, df["expense_date"].dt.to_period("M").nunique())
            p["monthly_expense"] = float(df["amount"].sum()) / months
            cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
            if len(cat):
                p["top_category"] = str(cat.index[0])
                p["top_category_amount"] = float(cat.iloc[0]) / months
                total = float(cat.sum())
                p["top_category_pct"] = 100.0 * float(cat.iloc[0]) / total if total else 0.0
    except Exception:
        pass
    try:
        from database import get_debts
        d = get_debts(family_id)
        if not d.empty:
            p["total_debt"] = float(d["balance_remaining"].sum())
    except Exception:
        pass
    try:
        from database import get_user_investments_df
        inv = get_user_investments_df(username, family_id)
        if not inv.empty:
            by = inv.groupby("asset_class")["current_value"].sum()
            total = float(by.sum())
            p["portfolio_value"] = total
            p["asset_classes"] = {str(k): float(v) for k, v in by.items()}
            if total > 0:
                eq = sum(v for k, v in by.items() if "equity" in str(k).lower() or "stock" in str(k).lower())
                p["equity_pct"] = 100.0 * float(eq) / total
    except Exception:
        pass
    return p


# ---------------------------------------------------------------------------
# Question builders: each returns (text, [(option_label, score 0-2), ...])
# ---------------------------------------------------------------------------
def _q_budget(p):
    if p["top_category"] and p["monthly_expense"] > 0:
        t = (f"Your biggest spending category is **{p['top_category']}** at about "
             f"{_inr(p['top_category_amount'])} a month ({p['top_category_pct']:.0f}% of your expenses). "
             "What is the smartest first move?")
    else:
        t = "One category takes a very large share of your monthly spending. What is the smartest first move?"
    return t, [("Ignore it – spending is spending", 0),
               ("Cut every category by the same percentage", 1),
               ("Review that category, separate needs from wants, and set a monthly cap", 2)]


def _q_savings(p):
    inc, exp = p["monthly_income"], p["monthly_expense"]
    if inc > 0 and exp > 0:
        rate = 100.0 * (inc - exp) / inc
        t = (f"You earn about {_inr(inc)} and spend about {_inr(exp)} a month, a savings rate of "
             f"{rate:.0f}%. What is the best way to improve your savings?")
    else:
        t = "You want to save more each month. What is the best approach?"
    return t, [("Save whatever is left at the end of the month", 1),
               ("Automate a transfer to savings/investments as soon as income arrives", 2),
               ("Wait for a salary hike before starting", 0)]


def _q_emergency(p):
    exp = p["monthly_expense"]
    if exp > 0:
        t = (f"With monthly expenses of about {_inr(exp)}, how large should your emergency fund be?")
        opts = [(f"About 1 month ({_inr(exp)})", 0),
                (f"About 3 months ({_inr(exp * 3)})", 1),
                (f"6 months or more ({_inr(exp * 6)}+), kept in a liquid instrument", 2)]
    else:
        t = "How large should your emergency fund be?"
        opts = [("1 month of expenses", 0), ("3 months of expenses", 1),
                ("6+ months of expenses in a liquid instrument", 2)]
    return t, opts


def _q_debt(p):
    d = p["total_debt"]
    if d > 0:
        t = (f"You have {_inr(d)} of outstanding debt. You also have some spare cash each month. "
             "What should you do?")
    else:
        t = "You have several loans and some spare cash each month. What should you do?"
    return t, [("Ignore the debt and put everything into investments", 0),
               ("Pay off the smallest balance first and ignore interest rates", 1),
               ("Pay minimums on all, then clear the highest-interest debt first", 2)]


def _q_diversify(p):
    eq = p["equity_pct"]
    if eq is not None and p["portfolio_value"] > 0:
        t = (f"Your portfolio is {_inr(p['portfolio_value'])} with about {eq:.0f}% in equity. "
             "What is the best principle for deciding your allocation?")
    else:
        t = "You are starting to invest. What is the best principle for deciding your allocation?"
    return t, [("Put everything in whatever gave the best return last year", 0),
               ("Pick one asset you understand and go all in", 1),
               ("Match the mix of equity/debt/gold to your goals, time horizon and risk comfort", 2)]


def _q_risk(p):
    v = p["portfolio_value"]
    if v > 0:
        t = (f"The market falls 20% and your portfolio of {_inr(v)} drops by about {_inr(v * 0.2)}. "
             "You don't need the money for 10+ years. What do you do?")
    else:
        t = "The market falls 20% and your investments drop sharply. You don't need the money for 10+ years. What do you do?"
    return t, [("Sell everything to stop the losses", 0),
               ("Put in all your remaining savings immediately", 1),
               ("Stay invested, review your allocation, and continue regular SIPs", 2)]


def _q_inflation(p):
    exp = p["monthly_expense"] if p["monthly_expense"] > 0 else 50000.0
    fut = exp * (1.06 ** 10)
    return (f"Your monthly expense is about {_inr(exp)} today. With 6% yearly inflation, "
            "roughly what will the same lifestyle cost per month in 10 years?"), [
        (f"About {_inr(exp * 1.2)}", 1),
        (f"The same {_inr(exp)}", 0),
        (f"About {_inr(fut)}", 2)]


def _q_windfall(p):
    inc = p["monthly_income"]
    amt = _inr(inc) if inc > 0 else "a month's salary"
    return (f"You receive a bonus equal to {amt}. What is the most balanced use?"), [
        ("Put all of it into a single hot stock tip", 0),
        ("Spend it all – you earned it", 1),
        ("Top up emergency fund/clear costly debt, invest a part, and enjoy a small part", 2)]


# id, category, difficulty (1 easy .. 3 hard), builder
QUESTION_BANK = [
    ("budget", "Budgeting", 1, _q_budget),
    ("savings", "Savings", 1, _q_savings),
    ("emergency", "Safety Net", 1, _q_emergency),
    ("debt", "Debt", 2, _q_debt),
    ("diversify", "Investing", 2, _q_diversify),
    ("risk", "Risk Psychology", 2, _q_risk),
    ("inflation", "Long-term Planning", 3, _q_inflation),
    ("windfall", "Money Habits", 3, _q_windfall),
]


# ---------------------------------------------------------------------------
# Session handling (plain dict so it can live in st.session_state)
# ---------------------------------------------------------------------------
def fallback_new_session(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {"profile": profile, "asked": [], "answers": [], "target": 1}


def fallback_next_question(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the next question or None when the assessment is finished."""
    if len(state["answers"]) >= MAX_QUESTIONS:
        return None
    remaining = [q for q in QUESTION_BANK if q[0] not in state["asked"]]
    if not remaining:
        return None
    qid, cat, diff, fn = min(remaining, key=lambda q: (abs(q[2] - state["target"]), QUESTION_BANK.index(q)))
    text, options = fn(state["profile"])
    state["asked"].append(qid)
    return {"id": qid, "category": cat, "difficulty": diff, "text": text,
            "options": [o[0] for o in options], "scores": [o[1] for o in options]}


def fallback_record_answer(state: Dict[str, Any], question: Dict[str, Any], option_idx: int) -> None:
    score = int(question["scores"][option_idx])
    state["answers"].append({"id": question["id"], "category": question["category"], "score": score})
    if score == 2:
        state["target"] = min(3, state["target"] + 1)
    elif score == 0:
        state["target"] = max(1, state["target"] - 1)


_PERSONAS = {
    "Beginner": "The Curious Starter",
    "Intermediate": "The Balanced Planner",
    "Advanced": "The Confident Strategist",
}


def fallback_result(state: Dict[str, Any]) -> Dict[str, Any]:
    ans = state["answers"]
    mx = 2 * len(ans) or 1
    ratio = sum(a["score"] for a in ans) / mx
    level = "Beginner" if ratio < 0.4 else ("Intermediate" if ratio < 0.75 else "Advanced")
    strong = [a["category"] for a in ans if a["score"] == 2]
    weak = [a["category"] for a in ans if a["score"] == 0]
    parts = [f"You scored {sum(a['score'] for a in ans)} out of {mx} on questions based on your own finances."]
    if strong:
        parts.append("Strengths: " + ", ".join(strong) + ".")
    if weak:
        parts.append("Focus areas: " + ", ".join(weak) + ".")
    if not weak:
        parts.append("Keep reviewing your plan regularly as your income and goals change.")
    return {"status": "complete", "final_score": level, "persona": _PERSONAS[level],
            "summary": " ".join(parts), "source": "database", "weak_areas": weak}


# ---------------------------------------------------------------------------
# Learning path fallback
# ---------------------------------------------------------------------------
def _yt(q: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(q)


_TOPIC_MODULES = {
    "Traditional": ("Safe Savings: FDs, PPF & Small Savings",
                    "Understand guaranteed-return instruments, tax treatment and where they fit.",
                    [("PPF & FD explained", _yt("PPF vs fixed deposit explained India"), "Video"),
                     ("Fixed Deposit basics", "https://www.investopedia.com/terms/f/fixed-deposit.asp", "Article")]),
    "Mutual Funds": ("Mastering Mutual Funds",
                     "Learn SIPs, index vs active funds, expense ratios and asset allocation.",
                     [("Zerodha Varsity: Mutual Funds", "https://zerodha.com/varsity/module/mutual-funds/", "Course"),
                      ("Index funds vs active funds", _yt("index funds vs active funds India"), "Video")]),
    "Direct Stocks": ("Direct Stocks Fundamentals",
                      "Read financial statements, value a business and manage position risk.",
                      [("Zerodha Varsity: Fundamental Analysis", "https://zerodha.com/varsity/module/fundamental-analysis/", "Course"),
                       ("How to analyse a stock", _yt("how to analyse a stock fundamental analysis"), "Video")]),
    "Alternate": ("Alternate Investments: P2P, REITs & Gold",
                  "Know the risks, liquidity and taxation of non-traditional assets.",
                  [("REITs explained", "https://www.investopedia.com/terms/r/reit.asp", "Article"),
                   ("Gold as an investment", _yt("sovereign gold bond vs gold ETF"), "Video")]),
    "Real Estate": ("Real Estate / Property Fundamentals",
                    "Evaluate rental yield, leverage and the real cost of owning property.",
                    [("Real estate investing basics", "https://www.investopedia.com/terms/r/realestate.asp", "Article"),
                     ("Rent vs buy in India", _yt("rent vs buy house India calculation"), "Video")]),
}


def fallback_learning_path(user_context: Dict[str, Any]) -> Dict[str, Any]:
    level = user_context.get("knowledge_level", "Beginner")
    loc = user_context.get("location_preference", "Local / Domestic")
    interests = user_context.get("investment_interests") or []
    income = float(user_context.get("total_monthly_income") or 0)
    debt = float(user_context.get("total_debt") or 0)
    inv = user_context.get("investments_by_asset_class")

    modules: List[Dict[str, Any]] = []
    if level == "Beginner" or (debt > 0 and income > 0 and debt > 6 * income):
        modules.append({
            "module_name": "Money Foundations: Budgeting, Emergency Fund & Debt",
            "description": "Build a budget, a 6-month emergency fund and a plan to clear costly debt before investing more.",
            "resources": [
                {"title": "Personal finance for beginners", "url": _yt("personal finance for beginners India"), "type": "Video"},
                {"title": "Zerodha Varsity: Personal Finance", "url": "https://zerodha.com/varsity/module/personal-finance/", "type": "Course"}]})
    for interest in interests:
        for key, (name, desc, res) in _TOPIC_MODULES.items():
            if key.lower() in interest.lower():
                modules.append({"module_name": name, "description": desc,
                                "resources": [{"title": t, "url": u, "type": ty} for t, u, ty in res]})
                break
    if loc in ("International", "Both"):
        modules.append({
            "module_name": "Investing Globally",
            "description": "Understand currency risk, LRS limits and tax on foreign investments.",
            "resources": [
                {"title": "Investing in US stocks from India", "url": _yt("invest in US stocks from India LRS tax"), "type": "Video"},
                {"title": "Global diversification", "url": "https://www.investopedia.com/terms/i/international-diversification.asp", "type": "Article"}]})

    facts = []
    if income > 0:
        facts.append(f"monthly income of about {_inr(income)}")
    if debt > 0:
        facts.append(f"outstanding debt of {_inr(debt)}")
    if isinstance(inv, dict) and inv:
        facts.append(f"investments of {_inr(sum(inv.values()))} across {len(inv)} asset class(es)")
    summary = (f"This {level.lower()}-level course follows your selected interests ({loc.lower()}). "
               + (("Based on your data you have " + ", ".join(facts) + ". ") if facts else "")
               + "It was built from curated resources because the AI service was busy; "
                 "regenerate later for a fully AI-personalised plan.")
    return {"course_title": f"Your {level} Investing Course", "summary": summary,
            "modules": modules, "source": "database"}
