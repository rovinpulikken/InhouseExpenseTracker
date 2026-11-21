"""
First-Time User Onboarding & Navigation Help System for FinCompass.

Implements a 4-layer progressive help architecture:
  Layer 1: 4-step interactive Welcome Tour modal (@st.dialog) on first login
  Layer 2: Live "Getting Started" checklist on Home (auto-checked from real data)
  Layer 3: Contextual per-page `❓ Guide` popover in every page header
  Layer 4: Searchable "Where do I find...?" Navigation Guide (@st.dialog)
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

import database
import data_layer


# ---------------------------------------------------------------------------
# LAYER 3 METADATA: CONTEXTUAL PER-PAGE HELP GUIDES (ALL 12 PAGES)
# ---------------------------------------------------------------------------
PAGE_HELP_GUIDES: Dict[str, Dict[str, Any]] = {
    "home": {
        "title": "Home Dashboard",
        "summary": "Your daily financial pulse — cash flow, urgent alerts, recent spending, and net worth in one view.",
        "sections": [
            ("Top Quick-Bar", "Jump in 1 tap to Home, Transactions, Budgets, Insights, Reports, Portfolio, or ➕ Add."),
            ("Scope Bar", "Switch Family/Private view, Financial Year, or use ◀ ▶ arrows to browse months."),
            ("Needs Attention", "Automatically surfaces categories over 80% budget or holdings hitting stop-loss/targets."),
        ],
        "tip": "Tap ➕ Add anytime to log an expense or income in under 5 seconds.",
    },
    "transactions": {
        "title": "Transactions",
        "summary": "Your complete ledger of expenses and income, plus bulk statement upload and cleanup tools.",
        "sections": [
            ("📅 Ledger", "Browse recent transactions as clean cards, filter by type/category, or toggle ✏️ Edit / Bulk Entry."),
            ("📤 Import", "Upload bank or credit card CSV, Excel, or PDF statements (or sync via IMAP email)."),
            ("🧹 Clean up", "Auto-categorize uncategorized rows with ML and scan for duplicate imports."),
        ],
        "tip": "Uploading a bank PDF? Save your default PDF password once in Settings → Integrations.",
    },
    "budgets": {
        "title": "Budgets & Goals",
        "summary": "Track category spending limits and long-term savings goals side by side.",
        "sections": [
            ("🎯 Budgets", "Shows over-budget categories first. Click ✏️ Edit Budget Allocations for a single fast table with 3 smart presets."),
            ("🏆 Goals", "Track target corpus, saved amount, and progress bars for major milestones."),
        ],
        "tip": "Start fast with the 50/30/20 or Match Last FY preset inside Edit Budget Allocations.",
    },
    "insights": {
        "title": "Insights & Analytics",
        "summary": "Deep visual analytics on where your money goes, multi-month trends, anomalies, and personal inflation.",
        "sections": [
            ("📊 Overview", "Category breakdown and visual spending hierarchy for your active scope."),
            ("📈 Trends", "Switch between Monthly, Quarterly, and Half-Yearly cash-flow trajectories."),
            ("🚨 Alerts", "Detects sudden category spending surges and runs AI rationalization tips."),
            ("📉 Inflation", "Measures your household's personal lifestyle inflation over time."),
        ],
        "tip": "Use the Scope Bar's FY selector to compare an entire financial year at once.",
    },
    "reports": {
        "title": "Reports & Statements",
        "summary": "Central hub for print-ready PDF/HTML statements, formatted Excel workbooks, and raw CSV backups.",
        "sections": [
            ("📄 Statements", "Generate Monthly Statement, FY Summary, Portfolio Valuation, Tax Summary, and Debt Schedule on demand."),
            ("🩺 Health Report", "Run a 5-pillar Financial Health Audit (0–100 score) with customisable PDF & multi-tab Excel output."),
            ("📦 Exports", "One-click raw CSV downloads for Transactions, Holdings, Loans, and Income Sources."),
        ],
        "tip": "Open any downloaded HTML statement in your browser and press Print → Save as PDF for crisp A4 pages.",
    },
    "portfolio": {
        "title": "Investment Portfolio",
        "summary": "Track equity, mutual funds, FDs, gold, and NPS with live valuations and rebalancing guidance.",
        "sections": [
            ("💼 Holdings", "View holdings, import Zerodha/Groww/CAMS statements, refresh live prices, or edit inline."),
            ("🥧 Allocation", "Visualize exposure by Asset Type, Market Cap, Sector/Theme, or Broker Platform."),
            ("🧭 Advisor", "Algorithmic Core-Satellite review (BUY/HOLD/TRIM) plus your AI Portfolio Strategist chat."),
            ("🎯 SIP Planner", "Plan monthly SIP allocations tailored to your risk profile and surplus."),
        ],
        "tip": "Add your free Gemini API key in Settings → Integrations to unlock AI portfolio Q&A.",
    },
    "loans": {
        "title": "Loans & EMIs",
        "summary": "Monitor active loans, interest burden, and simulate how prepayments shave years off your debt.",
        "sections": [
            ("🏦 Active Loans", "Track outstanding principal, interest rates, monthly EMI, and remaining tenure."),
            ("🔮 Payoff Simulator", "Compare Snowball vs Avalanche strategies and test extra monthly or lump-sum prepayments."),
        ],
        "tip": "Even 1 extra EMI per year on a Home Loan can cut 3–4 years off total tenure.",
    },
    "tax": {
        "title": "Tax & Income (India)",
        "summary": "Guided 4-step India income tax workspace comparing Old vs New Regime.",
        "sections": [
            ("💵 1. Income", "Log recurring salary, rental, freelance, and interest/dividend income."),
            ("📋 2. Deductions", "Enter Section 80C, 80D, HRA, NPS 80CCD(1B), and Home Loan interest."),
            ("📈 3. Capital Gains", "Compute STCG and LTCG taxes across equity, debt, and property."),
            ("🧮 4. Tax Summary", "Compare Old vs New Regime liability, advance tax dates, and download a Tax Summary."),
        ],
        "tip": "Follow steps 1 → 4 in order; your calculated summary also becomes downloadable in Reports.",
    },
    "retirement": {
        "title": "Retirement Planner",
        "summary": "Model financial independence (FIRE) corpus, post-retirement inflation, and milestone cash flows.",
        "sections": [
            ("Option A (Guided)", "Use your current expenses, retirement age, expected returns, and inflation sliders."),
            ("Option B (Natural Text)", "Describe life milestones in plain English (e.g. 'retire at 55, kids college in 2034')."),
            ("Saved Runs", "Save and compare multiple retirement scenarios over time."),
        ],
        "tip": "Set your Date of Birth in Settings → Profile so your current age stays auto-calculated.",
    },
    "academy": {
        "title": "Financial Academy",
        "summary": "Interactive personal finance lessons, readiness quizzes, and hands-on practice missions.",
        "sections": [
            ("Learning Paths", "Short modules covering budgeting, asset allocation, tax planning, and debt mastery."),
            ("Sandbox Mode", "Practice freely with simulated data without touching your real household records."),
        ],
        "tip": "Exit Sandbox Mode anytime from the top banner or Settings → Profile.",
    },
    "settings": {
        "title": "Settings & Preferences",
        "summary": "Manage your profile, AI/email integrations, password security, family members, and backups.",
        "sections": [
            ("👤 Profile", "Update full name, DOB, risk tolerance, and replay the Welcome Tour or Checklist."),
            ("🔌 Integrations", "Configure Gemini API key, IMAP statement sync, and default PDF password."),
            ("🔒 Security", "Update login password and recovery email / security question."),
            ("🏠 Family", "Copy your Family Join Code to invite household members."),
            ("💾 Data", "Check cloud sync status and manage workspace data."),
        ],
        "tip": "Share your Family Join Code from Settings → Family so family members can join on sign-up.",
    },
    "admin": {
        "title": "Admin Console",
        "summary": "Household user administration and raw database inspection (Admin / Super Admin only).",
        "sections": [
            ("👥 Users & Roles", "Create users, update roles, and manage member profiles."),
            ("🗄️ Raw DB Log", "Inspect and edit raw database records directly with column safeguards."),
        ],
        "tip": "Super Admins can switch between households using the top dropdown in the left sidebar.",
    },
}


# ---------------------------------------------------------------------------
# LAYER 4 METADATA: SEARCHABLE "WHERE DO I FIND...?" DIRECTORY
# ---------------------------------------------------------------------------
INTENT_DIRECTORY: List[Dict[str, Any]] = [
    # Daily Money
    {
        "group": "📌 Daily Money",
        "task": "Log a single expense or income",
        "cta": "➕ Open Quick Add",
        "action": "add_tx",
        "page": "home",
        "sub_tab": None,
        "keywords": "add expense income bill entry log spend quick new transaction",
    },
    {
        "group": "📌 Daily Money",
        "task": "Upload bank or credit card CSV / Excel / PDF statement",
        "cta": "📤 Go to Import →",
        "action": "navigate",
        "page": "transactions",
        "sub_tab": "📤 Import",
        "keywords": "upload import bank statement hdfc icici sbi axis pdf csv excel credit card imap",
    },
    {
        "group": "📌 Daily Money",
        "task": "View, search, edit, or delete past transactions",
        "cta": "📅 Go to Ledger →",
        "action": "navigate",
        "page": "transactions",
        "sub_tab": "📅 Ledger",
        "keywords": "ledger history edit delete modify search filter monthly transactions bulk",
    },
    {
        "group": "📌 Daily Money",
        "task": "Auto-categorize expenses or remove duplicate imports",
        "cta": "🧹 Go to Clean up →",
        "action": "navigate",
        "page": "transactions",
        "sub_tab": "🧹 Clean up",
        "keywords": "duplicate duplicates clean ml categorize uncategorized fix",
    },
    {
        "group": "📌 Daily Money",
        "task": "Set monthly category budgets & savings goals",
        "cta": "🎯 Go to Budgets →",
        "action": "navigate",
        "page": "budgets",
        "sub_tab": "🎯 Budgets",
        "keywords": "budget limit monthly spending allocation 50/30/20 goals target savings",
    },
    # Reports & Insights
    {
        "group": "📊 Reports & Insights",
        "task": "Download Monthly, FY, Portfolio, Debt, or Tax PDF/Excel",
        "cta": "📄 Open Statements →",
        "action": "navigate",
        "page": "reports",
        "sub_tab": "📄 Statements",
        "keywords": "report pdf excel download statement monthly annual fy export print",
    },
    {
        "group": "📊 Reports & Insights",
        "task": "Check 5-pillar Financial Health Score & Audit",
        "cta": "🩺 Health Report →",
        "action": "navigate",
        "page": "reports",
        "sub_tab": "🩺 Health Report",
        "keywords": "health score audit net worth solvency runway dti report",
    },
    {
        "group": "📊 Reports & Insights",
        "task": "Spot unusual spending spikes & inflation trends",
        "cta": "🚨 Go to Alerts →",
        "action": "navigate",
        "page": "insights",
        "sub_tab": "🚨 Alerts",
        "keywords": "surge spike anomaly alert inflation trends analytics charts",
    },
    {
        "group": "📊 Reports & Insights",
        "task": "Download raw CSV backups of all datasets",
        "cta": "📦 Raw Exports →",
        "action": "navigate",
        "page": "reports",
        "sub_tab": "📦 Exports",
        "keywords": "csv backup export raw data download",
    },
    # Wealth, Tax & Planning
    {
        "group": "📈 Wealth, Tax & Planning",
        "task": "Track stocks, mutual funds, FDs, gold, or import CAMS/broker files",
        "cta": "💼 Go to Portfolio →",
        "action": "navigate",
        "page": "portfolio",
        "sub_tab": "💼 Holdings",
        "keywords": "portfolio stocks mutual fund mf zerodha groww cams fd gold holdings nav",
    },
    {
        "group": "📈 Wealth, Tax & Planning",
        "task": "Get AI & algorithmic rebalance advice or plan monthly SIPs",
        "cta": "🧭 Portfolio Advisor →",
        "action": "navigate",
        "page": "portfolio",
        "sub_tab": "🧭 Advisor",
        "keywords": "advisor ai chat rebalance buy trim hold sip planner allocation",
    },
    {
        "group": "📈 Wealth, Tax & Planning",
        "task": "Track loans/EMIs or simulate early debt payoff",
        "cta": "🔮 Payoff Simulator →",
        "action": "navigate",
        "page": "loans",
        "sub_tab": "🔮 Payoff Simulator",
        "keywords": "loan emi home car debt prepayment snowball avalanche payoff simulator",
    },
    {
        "group": "📈 Wealth, Tax & Planning",
        "task": "Add salary/income sources & compare Old vs New India Tax Regime",
        "cta": "🧾 Tax & Income →",
        "action": "navigate",
        "page": "tax",
        "sub_tab": "💵 Income",
        "keywords": "salary income tax 80c 80d hra nps capital gains stcg ltcg regime itr",
    },
    {
        "group": "📈 Wealth, Tax & Planning",
        "task": "Build a retirement / FIRE corpus roadmap",
        "cta": "🏖️ Retirement →",
        "action": "navigate",
        "page": "retirement",
        "sub_tab": None,
        "keywords": "retirement fire corpus pension milestones future plan",
    },
    # Account & Family
    {
        "group": "⚙️ Account & Family",
        "task": "Invite family members / copy Family Join Code",
        "cta": "🏠 Family Setup →",
        "action": "navigate",
        "page": "settings",
        "sub_tab": "🏠 Family",
        "keywords": "family invite join code member spouse household",
    },
    {
        "group": "⚙️ Account & Family",
        "task": "Configure Gemini AI key, email sync, or PDF password",
        "cta": "🔌 Integrations →",
        "action": "navigate",
        "page": "settings",
        "sub_tab": "🔌 Integrations",
        "keywords": "gemini api key ai email imap pdf password integration settings",
    },
]


# ---------------------------------------------------------------------------
# PURE HELPERS (UNIT-TESTABLE WITHOUT STREAMLIT RUNTIME)
# ---------------------------------------------------------------------------
def filter_intent_directory(query: str) -> List[Dict[str, Any]]:
    """Filter INTENT_DIRECTORY entries by case-insensitive token match."""
    q = (query or "").strip().lower()
    if not q:
        return list(INTENT_DIRECTORY)
    tokens = [tok for tok in q.split() if tok]
    matches = []
    for item in INTENT_DIRECTORY:
        haystack = f"{item['group']} {item['task']} {item['cta']} {item['keywords']}".lower()
        if all(tok in haystack for tok in tokens):
            matches.append(item)
    return matches


def compute_checklist_steps(
    current_user: Dict[str, Any],
    all_tx_df: Optional[pd.DataFrame],
    income_df: Optional[pd.DataFrame],
    budget_df: Optional[pd.DataFrame],
    inv_df: Optional[pd.DataFrame],
    debts_df: Optional[pd.DataFrame],
    report_generated: bool = False,
) -> Dict[str, Any]:
    """
    Compute the 5-step Getting Started checklist status directly from already-loaded
    DataFrames (zero extra DB queries).
    """
    has_logged_income = False
    if all_tx_df is not None and not all_tx_df.empty and "transaction_type" in all_tx_df.columns:
        has_logged_income = bool(
            (all_tx_df["transaction_type"].fillna("").astype(str).str.strip().str.title() == "Income").any()
        )
    has_income = (income_df is not None and not income_df.empty) or has_logged_income
    has_tx = all_tx_df is not None and not all_tx_df.empty
    has_budget = False
    if budget_df is not None and not budget_df.empty and "Annual_Budget" in budget_df.columns:
        has_budget = bool((pd.to_numeric(budget_df["Annual_Budget"], errors="coerce").fillna(0.0) > 0).any())
    has_wealth_or_debt = (inv_df is not None and not inv_df.empty) or (debts_df is not None and not debts_df.empty)
    has_profile_or_report = bool(report_generated) or bool(str(current_user.get("dob") or "").strip())

    steps = [
        {
            "id": "income",
            "label": "Set your monthly income or salary",
            "done": has_income,
            "cta": "Add Income →",
            "action": "navigate",
            "page": "tax",
            "sub_tab": "💵 Income",
        },
        {
            "id": "transaction",
            "label": "Log or import your first transaction",
            "done": has_tx,
            "cta": "➕ Add First",
            "action": "add_tx",
            "page": "transactions",
            "sub_tab": "📅 Ledger",
        },
        {
            "id": "budget",
            "label": "Set monthly spending budgets",
            "done": has_budget,
            "cta": "Set Budgets →",
            "action": "navigate",
            "page": "budgets",
            "sub_tab": "🎯 Budgets",
            "extra_state": {"bud_edit_mode": True},
        },
        {
            "id": "wealth",
            "label": "Add an investment holding or active loan",
            "done": has_wealth_or_debt,
            "cta": "Open Portfolio →",
            "action": "navigate",
            "page": "portfolio",
            "sub_tab": "💼 Holdings",
        },
        {
            "id": "report",
            "label": "Complete profile DOB or generate a statement",
            "done": has_profile_or_report,
            "cta": "Open Reports →",
            "action": "navigate",
            "page": "reports",
            "sub_tab": "📄 Statements",
        },
    ]

    completed = sum(1 for s in steps if s["done"])
    total = len(steps)
    pct = int(round((completed / total) * 100)) if total else 0
    first_pending_id = next((s["id"] for s in steps if not s["done"]), None)
    return {
        "steps": steps,
        "completed": completed,
        "total": total,
        "pct": pct,
        "all_done": completed == total,
        "next_step_id": first_pending_id,
    }


def _mark_onboarding_state(
    current_user: Dict[str, Any],
    tour_completed: Optional[bool] = None,
    checklist_dismissed: Optional[bool] = None,
) -> None:
    """Persist onboarding state to DB and mirror immediately in session_state."""
    uname = current_user.get("username")
    if uname:
        database.update_user_onboarding_state(
            uname,
            tour_completed=tour_completed,
            checklist_dismissed=checklist_dismissed,
        )
    if "user" in st.session_state:
        if tour_completed is not None:
            st.session_state["user"]["onboarding_completed"] = 1 if tour_completed else 0
        if checklist_dismissed is not None:
            st.session_state["user"]["onboarding_checklist_dismissed"] = 1 if checklist_dismissed else 0


# ---------------------------------------------------------------------------
# LAYER 1: 4-STEP INTERACTIVE WELCOME TOUR (@st.dialog)
# ---------------------------------------------------------------------------
@st.dialog("🧭 Welcome to FinCompass", width="large")
def open_welcome_tour_dialog(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
    """4-step interactive first-time tour with visual map and instant starting paths."""
    import ui  # Local import avoids circular import at module load

    step = int(st.session_state.get("_tour_step", 1))
    step = max(1, min(4, step))
    total_steps = 4

    # Step indicator dots
    dots_html = "".join(
        f'<span class="fc-tour-dot {"active" if i == step else ("done" if i < step else "")}"></span>'
        for i in range(1, total_steps + 1)
    )
    st.markdown(
        f"""
        <div class="fc-tour-progress">
            <div class="fc-tour-dots">{dots_html}</div>
            <div class="fc-tour-step-lbl">Step {step} of {total_steps}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if step == 1:
        st.markdown("#### Your money, organized into 4 simple zones")
        st.caption("Open the left sidebar anytime (☰ on mobile) to jump between these four sections:")
        st.markdown(
            """
            <div class="fc-tour-grid">
                <div class="fc-tour-card" style="border-left:3px solid #38bdf8;">
                    <div class="fc-tour-card-title">📌 Track <span class="fc-badge fc-badge-info">Daily</span></div>
                    <div class="fc-tour-card-desc"><b>Home</b>, <b>Transactions</b>, and <b>Budgets &amp; Goals</b> for everyday cash flow.</div>
                </div>
                <div class="fc-tour-card" style="border-left:3px solid #a855f7;">
                    <div class="fc-tour-card-title">📊 Analyze</div>
                    <div class="fc-tour-card-desc"><b>Insights</b> (trends, surges, inflation) and <b>Reports</b> (6 printable PDF/Excel statements).</div>
                </div>
                <div class="fc-tour-card" style="border-left:3px solid #34d399;">
                    <div class="fc-tour-card-title">📈 Grow</div>
                    <div class="fc-tour-card-desc"><b>Portfolio</b> (stocks, MFs, AI advisor, SIPs) and <b>Loans &amp; EMIs</b> payoff simulator.</div>
                </div>
                <div class="fc-tour-card" style="border-left:3px solid #f59e0b;">
                    <div class="fc-tour-card-title">🧭 Plan</div>
                    <div class="fc-tour-card-desc"><b>Tax &amp; Income</b> (India Old vs New Regime) and <b>Retirement</b> corpus planner.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif step == 2:
        st.markdown("#### Two bars keep everything 1 tap away")
        st.markdown(
            """
            <div class="fc-tour-card" style="border-left:3px solid #38bdf8; margin-bottom:10px;">
                <div class="fc-tour-card-title">⚡ Top Quick-Navigation Bar</div>
                <div class="fc-tour-card-desc">
                    Always visible at the top of the screen: <b>🏠 Home</b> · <b>💸 Transactions</b> · <b>🎯 Budgets</b> · <b>📊 Insights</b> · <b>📑 Reports</b> · <b>📈 Portfolio</b> · <b>➕ Add</b>.
                </div>
            </div>
            <div class="fc-tour-card" style="border-left:3px solid #34d399; margin-bottom:10px;">
                <div class="fc-tour-card-title">🎛️ Unified Scope Bar</div>
                <div class="fc-tour-card-desc">
                    Right below the top bar, pick <b>🏠 Family / 🔒 Private / 🌐 All</b>, choose a <b>Financial Year</b>, and tap <b>◀ ▶</b> to flip months. Your selection stays synced across every page.
                </div>
            </div>
            <div class="fc-tour-card" style="border-left:3px solid #a855f7;">
                <div class="fc-tour-card-title">❓ Contextual Help on Every Page</div>
                <div class="fc-tour-card-desc">
                    Tap <b>❓ Guide</b> in any page header for quick tips, or <b>❓ Navigation Guide</b> in the sidebar to search <i>"Where do I find...?"</i>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif step == 3:
        st.markdown("#### Three fast ways to bring in your data")
        st.markdown(
            """
            <div class="fc-tour-card" style="border-left:3px solid #38bdf8; margin-bottom:10px;">
                <div class="fc-tour-card-title">1. ➕ Quick-Add (5 seconds)</div>
                <div class="fc-tour-card-desc">Tap <b>➕ Add</b> from the top bar or sidebar to log a single expense or income — auto-categorized as you type.</div>
            </div>
            <div class="fc-tour-card" style="border-left:3px solid #f59e0b; margin-bottom:10px;">
                <div class="fc-tour-card-title">2. 📤 Bank &amp; Card Statements</div>
                <div class="fc-tour-card-desc">Go to <b>Transactions → Import</b> to upload CSV, Excel, or password-protected PDF bank statements in seconds.</div>
            </div>
            <div class="fc-tour-card" style="border-left:3px solid #34d399;">
                <div class="fc-tour-card-title">3. 💼 Investment Imports</div>
                <div class="fc-tour-card-desc">Go to <b>Portfolio → Holdings</b> to import Zerodha, Groww, or CAMS statements — or add FDs, gold, and stocks manually.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("#### You're all set! How would you like to start?")
        st.caption("Pick an option below — you can replay this tour anytime from the sidebar's ❓ Navigation Guide.")

        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("➕ Log My First Transaction", type="primary", use_container_width=True, key="tour_cta_add"):
                _mark_onboarding_state(current_user, tour_completed=True)
                st.session_state["_tour_step"] = 1
                st.session_state["_tour_keep_open"] = False
                st.session_state["_reopen_add_tx"] = True
                st.rerun()
        with c_b:
            if st.button("🎮 Explore with Sample Data", use_container_width=True, key="tour_cta_sandbox"):
                _mark_onboarding_state(current_user, tour_completed=True)
                st.session_state["_tour_step"] = 1
                st.session_state["_tour_keep_open"] = False
                st.session_state["is_sandbox_mode"] = True
                data_layer.invalidate_data_cache()
                st.rerun()

        if st.button("🏠 Go straight to Home Dashboard", use_container_width=True, key="tour_cta_home"):
            _mark_onboarding_state(current_user, tour_completed=True)
            st.session_state["_tour_step"] = 1
            st.session_state["_tour_keep_open"] = False
            st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    nav_l, nav_m, nav_r = st.columns([1.2, 1, 1.2])
    with nav_l:
        if step > 1:
            if st.button("← Back", use_container_width=True, key="tour_btn_back"):
                st.session_state["_tour_step"] = step - 1
                st.session_state["_tour_keep_open"] = True
                st.rerun()
        else:
            if st.button("Skip Tour", use_container_width=True, key="tour_btn_skip_1"):
                _mark_onboarding_state(current_user, tour_completed=True)
                st.session_state["_tour_step"] = 1
                st.session_state["_tour_keep_open"] = False
                st.rerun()
    with nav_m:
        if step > 1 and step < total_steps:
            if st.button("Skip", use_container_width=True, key="tour_btn_skip_mid"):
                _mark_onboarding_state(current_user, tour_completed=True)
                st.session_state["_tour_step"] = 1
                st.session_state["_tour_keep_open"] = False
                st.rerun()
    with nav_r:
        if step < total_steps:
            if st.button("Next →", type="primary", use_container_width=True, key="tour_btn_next"):
                st.session_state["_tour_step"] = step + 1
                st.session_state["_tour_keep_open"] = True
                st.rerun()


# ---------------------------------------------------------------------------
# LAYER 4: SEARCHABLE "WHERE DO I FIND...?" NAVIGATION GUIDE (@st.dialog)
# ---------------------------------------------------------------------------
@st.dialog("🧭 FinCompass Navigation Guide", width="large")
def open_navigation_guide_dialog(current_user: Dict[str, Any], user_family_id: Optional[int]) -> None:
    """Searchable intent-to-page directory with 1-click deep links, Replay Tour & Sample Data toggle."""
    import ui

    q = st.text_input(
        "What would you like to do?",
        placeholder="Search e.g. 'upload pdf', 'budget', 'tax', 'SIP', 'family', 'loan'...",
        key="nav_guide_search",
    )
    matches = filter_intent_directory(q)

    if not matches:
        st.info("No matching tasks found. Try keywords like **pdf**, **budget**, **tax**, **portfolio**, or **family**.")
    else:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in matches:
            grouped.setdefault(item["group"], []).append(item)

        for grp_name, items in grouped.items():
            st.markdown(f"**{grp_name}**")
            for idx, item in enumerate(items):
                c_txt, c_btn = st.columns([2.6, 1.3])
                with c_txt:
                    st.markdown(
                        f"<div style='padding-top:6px; font-size:0.9rem; color:#e2e8f0;'>• {item['task']}</div>",
                        unsafe_allow_html=True,
                    )
                with c_btn:
                    if st.button(item["cta"], key=f"ng_btn_{item['page']}_{idx}_{grp_name[:4]}", use_container_width=True):
                        if item["action"] == "add_tx":
                            st.session_state["_reopen_add_tx"] = True
                            st.rerun()
                        else:
                            ui.navigate_to(item["page"], sub_tab=item.get("sub_tab"))
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    f1, f2 = st.columns(2)
    with f1:
        if st.button("🎬 Replay Welcome Tour", use_container_width=True, key="ng_replay_tour"):
            st.session_state["_tour_step"] = 1
            st.session_state["_tour_keep_open"] = True
            st.rerun()
    with f2:
        in_sb = data_layer.is_sandbox_mode()
        sb_lbl = "🚪 Exit Sample Data Mode" if in_sb else "🎮 Try Sample Data Mode"
        if st.button(sb_lbl, use_container_width=True, key="ng_toggle_sandbox"):
            st.session_state["is_sandbox_mode"] = not in_sb
            data_layer.invalidate_data_cache()
            st.rerun()


# ---------------------------------------------------------------------------
# LAYER 2: LIVE "GETTING STARTED" CHECKLIST CARD ON HOME
# ---------------------------------------------------------------------------
def render_getting_started_checklist(
    current_user: Dict[str, Any],
    user_family_id: Optional[int],
    all_tx_df: Optional[pd.DataFrame],
    income_df: Optional[pd.DataFrame],
    budget_df: Optional[pd.DataFrame],
    inv_df: Optional[pd.DataFrame],
    debts_df: Optional[pd.DataFrame],
) -> None:
    """
    Render the auto-checked 5-step Getting Started checklist on Home.
    Hidden if dismissed by the user or while in Sandbox Mode.
    """
    import ui

    if data_layer.is_sandbox_mode():
        return
    if int(current_user.get("onboarding_checklist_dismissed") or 0) == 1:
        return

    report_gen = bool(
        st.session_state.get("_rep_monthly_cache")
        or st.session_state.get("_rep_fy_cache")
        or st.session_state.get("_health_report_bundle")
    )
    status = compute_checklist_steps(
        current_user=current_user,
        all_tx_df=all_tx_df,
        income_df=income_df,
        budget_df=budget_df,
        inv_df=inv_df,
        debts_df=debts_df,
        report_generated=report_gen,
    )

    if status["all_done"]:
        c_done, c_dim = st.columns([4.5, 1])
        with c_done:
            st.markdown(
                """
                <div class="fc-card" style="border-left:4px solid #10b981; padding:11px 14px; margin-bottom:10px;">
                    🎉 <b>Setup Complete!</b> You've configured income, transactions, budgets, wealth, and profile/reports.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_dim:
            if st.button("Dismiss", key="gs_dismiss_complete", use_container_width=True):
                _mark_onboarding_state(current_user, checklist_dismissed=True)
                st.rerun()
        return

    with st.container(border=True):
        h_left, h_right = st.columns([4.2, 1])
        with h_left:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                    <div style="font-size:1.0rem; font-weight:800; color:#f8fafc;">🚀 Get Started with FinCompass</div>
                    <span class="fc-badge fc-badge-info">{status['completed']} of {status['total']} done ({status['pct']}%)</span>
                </div>
                <div class="fc-bar-track" style="margin-top:8px;">
                    <div class="fc-bar-fill" style="width:{status['pct']}%; background:linear-gradient(90deg,#38bdf8,#34d399);"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with h_right:
            if st.button("Hide", key="gs_hide_btn", use_container_width=True, help="Hide checklist (can be restored in Settings)"):
                _mark_onboarding_state(current_user, checklist_dismissed=True)
                st.rerun()

        for idx, step in enumerate(status["steps"], start=1):
            is_next = (step["id"] == status["next_step_id"])
            icon = "✅" if step["done"] else ("🔵" if is_next else "⚪")
            txt_style = "color:#64748b; text-decoration:line-through;" if step["done"] else ("color:#f8fafc; font-weight:700;" if is_next else "color:#cbd5e1;")

            r_txt, r_act = st.columns([3.6, 1.3])
            with r_txt:
                st.markdown(
                    f"<div style='padding:6px 0; font-size:0.9rem; {txt_style}'>{icon} &nbsp;{idx}. {step['label']}</div>",
                    unsafe_allow_html=True,
                )
            with r_act:
                if step["done"]:
                    st.markdown("<div style='padding:6px 0; text-align:right; font-size:0.8rem; color:#34d399; font-weight:600;'>Done</div>", unsafe_allow_html=True)
                else:
                    if st.button(
                        step["cta"],
                        key=f"gs_step_{step['id']}",
                        type="primary" if is_next else "secondary",
                        use_container_width=True,
                    ):
                        if step["action"] == "add_tx":
                            ui.open_add_transaction_dialog(current_user, user_family_id)
                        else:
                            ui.navigate_to(
                                step["page"],
                                sub_tab=step.get("sub_tab"),
                                extra_state=step.get("extra_state"),
                            )


# ---------------------------------------------------------------------------
# LAYER 3: CONTEXTUAL PER-PAGE `❓ Guide` POPOVER
# ---------------------------------------------------------------------------
def render_page_help_popover(page_key: str) -> None:
    """Render a compact `❓ Guide` popover tailored to the active page."""
    guide = PAGE_HELP_GUIDES.get(page_key)
    if not guide:
        return
    with st.popover("❓ Guide", use_container_width=True):
        st.markdown(f"**💡 {guide['title']}**")
        st.caption(guide["summary"])
        for sec_name, sec_desc in guide.get("sections", []):
            st.markdown(f"- **{sec_name}:** {sec_desc}")
        if guide.get("tip"):
            st.info(f"**Tip:** {guide['tip']}")
        if st.button("🧭 Open Full Navigation Guide", key=f"pop_open_ng_{page_key}", use_container_width=True):
            st.session_state["_open_nav_guide"] = True
            st.rerun()
