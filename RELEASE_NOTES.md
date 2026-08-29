# Release Notes

## v1.7.0 (2026-08-27)
### Added
- **`tax_engine.py` — New Standalone Tax Engine Module**:
  A comprehensive India tax computation engine for FY 2025-26, extracted from `investment_planner.py` and significantly enhanced.
  - **Passive Income Auto-Derivation** (`derive_investment_income`): Scans portfolio holdings and auto-computes annual passive income for RBI FRSB bonds (8.05% p.a., Jan/Jul payments), Sovereign Gold Bonds (2.5% p.a.), Fixed Deposits, Recurring Deposits, NSC, SCSS, PPF (exempt), and equity stock dividends via `yfinance`. PPF/NPS interest correctly marked as Exempt (green badge) and excluded from taxable income.
  - **Capital Gains Parser** (`parse_capital_gains`): Auto-detects and parses LTCG/STCG from uploaded documents — **Zerodha Tax P&L PDF**, **ICICI Direct Capital Gains PDF**, **CAMS/KFintech Consolidated Account Statement PDF**, **IT Dept AIS JSON** download, and a generic PDF fallback. Returns per-category breakdown (equity, equity MF, debt MF, property, other) with correct FY 2025-26 tax rates.
  - **Full Deduction Waterfall** (`compute_deductions`): Old Regime — 80C (PPF, ELSS, LIC, home loan principal, school fees, NSC interest, EPF, tax-saver FD, capped ₹1.5L), 80D (health insurance for self + parents, senior citizen limits ₹50K), 80CCD(1B) NPS (₹50K), 24(b) home loan interest (₹2L), HRA exemption (10(13A), least-of-three calculation, metro/non-metro), Professional Tax (₹2,400), 80TTA/80TTB (savings bank + SCSS interest). New Regime — Standard Deduction (₹75K) + NPS Employer 80CCD(2) + Professional Tax only.
  - **CG Tax Computation** (`compute_cg_tax`): Applies FY 2025-26 rates — Equity LTCG 12.5% above ₹1.25L exempt, Equity STCG 20%, Property LTCG 12.5% (no indexation). Debt MF/property STCG/other correctly added to slab income.
  - **Advance Tax Schedule** (`compute_advance_tax_schedule`): Computes FY 2025-26 quarterly instalments (15 Jun 15%, 15 Sep 45%, 15 Dec 75%, 15 Mar 100%). Shows days-remaining countdown, overdue/paid status. Only generates schedule when net liability > ₹10,000.
  - **Master Compute** (`compute_full_tax`): Combines income sources + passive income (with per-item override) + CG + full deductions → slab tax + CG tax → advance tax schedule + regime comparison + savings opportunities.
- **Database — `tax_deductions` Table**: Persists per-user per-FY deduction inputs (all 80C components, 80D, HRA details, NPS, home loan interest, professional tax, TDS deducted, advance paid). Upsert function with UNIQUE constraint on (username, family_id, financial_year).
- **Database — `capital_gains_entries` Table**: Persists uploaded/manual CG data per user per FY (10 CG categories + source + notes).
- **Database CRUD**: `upsert_tax_deductions`, `get_tax_deductions`, `upsert_capital_gains`, `get_capital_gains`.

### Changed
- **Tax Planner UI (app.py)** — Completely redesigned from a basic single-button calculator to a **4-section workbench** for India users:
  - **Section A — Deductions**: Collapsible form with all deduction inputs. Old Regime shows full 80C/80D/HRA/home loan fields; New Regime shows simplified view. Values auto-saved to DB.
  - **Section B — Passive Income**: Auto-scans portfolio holdings and shows derived income cards (color-coded by taxability). Each entry has an override number input. Refreshes on portfolio changes.
  - **Section C — Capital Gains**: Tabbed panel with Upload (PDF/JSON auto-detection), Manual Entry form, and Saved Data view. Parsed results shown in editable table before saving.
  - **Section D — Tax Summary**: Single "🧮 Calculate Full Tax Liability" button triggers `compute_full_tax`. Shows 5-column KPI row, tax breakdown card, CG tax detail table, income breakdown, deduction breakdown, advance tax instalment schedule, savings opportunities, and "Additional Information Needed" reference panel (Form 16, 26AS, FD interest certificates, home loan statement, rental income, foreign income, etc.).
- Non-India countries continue to use the existing `compute_tax_liability` flow unchanged.

## v1.6.2 (2026-08-26)
### Added
- **Income Sources — Inline Edit**: Each income source now has an ✏️ **Edit** button. Clicking it expands an inline edit form directly within the card, pre-populated with the current values (name, type, amount, frequency, notes). Saving calls `update_income_source()` and immediately refreshes the view. Cancelling reverts without changes.
### Changed
- **Income & Tax Planner — Card Grid UI**: Replaced the flat columnar list of income sources with a responsive **3-column card grid**. Each card displays a type icon (💼 🏠 📈 etc.), source name, income type, amount/frequency, monthly and annual equivalents, and optional notes. Actions (Edit / Delete) appear as full-width buttons below each card.
- **Add Income Source — Always Visible**: The "Add New Income Source" form is now persistently visible below the cards (no longer buried inside a collapsed expander).

## v1.6.1 (2026-08-26)
### Fixed
- **Income Deletion Bug in Income & Tax Planner**: Fixed a critical bug where clicking 🗑️ **Delete** on an income source could silently delete *any* income record — including ones that don't belong to the current user/family.
  - **Root Cause**: `delete_income_source` contained an unsafe fallback `DELETE FROM income_sources WHERE id = ?` with no ownership guard. When the primary query (scoped to `family_id`) returned 0 rows, the fallback fired unconditionally by primary key alone, bypassing all access control.
  - **Fix**: Removed the unconstrained fallback. The primary query already handles `NULL family_id` via `OR family_id IS NULL`, so the fallback was redundant and dangerous. If the scoped delete returns 0 rows, the function now correctly returns `False` (no record deleted), and the UI shows an appropriate error.
- **UI Error Feedback on Failed Delete (`app.py`)**: Restored missing `else` branch in the income delete button handler — the UI now displays a visible error message when a delete operation fails instead of silently doing nothing.

### Tests
- **`test_income_source_crud` (`test_app.py`)**: Added a comprehensive CRUD test suite for income sources covering add, fetch, scoped delete by family, unscoped delete (no family_id), and verifying that deleting a non-existent or already-deleted record returns `False`.
- **DB Isolation Fix (`test_app.py`)**: Added environment variable overrides (`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`) and a `get_turso_credentials` stub at test startup to ensure the test suite always runs against a local temp SQLite DB and never touches the production Turso cloud database.

## v1.6.0 (2026-08-26)
### Fixed
- **Income Deletion in Income & Tax Planner**: Fixed an issue where clicking delete on an income source in the Income & Tax Planner would display "Deleted!" but fail to remove the record from the database.
  - **Root Cause 1**: `LibSQLCursorWrapper` checked `res.rows_changed` which was not present on `libsql_client.result.ResultSet` (the attribute name is `rows_affected`). It defaulted to `1`, causing zero-row DML operations to report success falsely. Fixed to properly inspect `rows_affected` and default to `0` when no rows are modified.
  - **Root Cause 2**: `delete_income_source`, `delete_debt`, and `delete_savings_goal` failed to match rows when `family_id` was `None` (e.g. Super Admin / Global scope) or when rows had `NULL` `family_id`. Updated the SQL queries to handle `(family_id = ? OR family_id IS NULL)` with fallback deletion by primary key `id`.
  - Added unit test suite `test_income_source_crud` to prevent regressions.

## v1.5.9 (2026-08-21)
### Changed
- **Smart Advisor Context Input**: Added an optional text area in the "Smart Advisor & Tax Planner" tab. Users can now enter specific goals, life events, or questions (e.g., "I want to buy a house in 2 years") which are passed directly to the Gemini AI to generate highly personalized rebalancing and new money deployment advice.
- **Detailed Action Plan**: The Smart Advisor now automatically generates and displays a step-by-step roadmap detailing exactly *how* the specific goals will be achieved, complete with expected outcomes. This plan is now prominently displayed at the top of the results to avoid scrolling.
- **Trend Signals UI Tweak**: To save space and prioritize AI advice, the "Live Trend Signals" for equity holdings are now collapsed inside an expander by default.
- **Credit Card Bill Payments Ignored**: Instructed the AI statement parser to automatically skip credit card bill payments/settlements (typically appearing as "CR" entries for "Payment Received" or "Auto Debit"). These are debt settlements, not genuine income or expenses, and dropping them prevents double-counting. Also added a programmatic post-processing safety net to drop rows with payment-related keywords.
- **File Import Duplicate Detection**: Added a feature in the "File Import & Quick Add" tab to automatically flag newly imported transactions that match an existing record's Date and Amount, allowing you to uncheck and skip duplicates easily.
- **Bulk Duplicate Cleanup**: Added a new "🕵️ Detect Duplicates" sub-tab under "Edit & Delete Existing" to scan your entire database for redundant expense records (matching Date + Amount) and safely delete them in bulk.
## v1.5.8 (2026-08-19)
### Fixed
- **`StreamlitAPIException` on Statement Review (take 2)**: `DateColumn` in Streamlit on Python 3.14 rejects `object`-dtype columns of `datetime.date` objects even after `.dt.date` coercion. Fix: replaced `DateColumn` with `TextColumn("Date (YYYY-MM-DD)")` and store dates as ISO strings via `.dt.strftime("%Y-%m-%d")`. Also coerces `description`, `transaction_type`, `category` to clean strings to prevent any `SelectboxColumn` type errors.

## v1.5.7 (2026-08-19)
### Fixed
- **`StreamlitAPIException` on Statement Review (`st.data_editor`)**: `DateColumn` requires `datetime.date` objects but Gemini returns date strings (e.g. `"2026-01-01"`). Added type coercion in `app.py` before storing parsed data in session state: `date` column is coerced via `pd.to_datetime().dt.date` (invalid dates fall back to today), `amount` via `pd.to_numeric()` (invalid values default to `0.0`).

## v1.5.6 (2026-08-19)
### Fixed
- **Statement Parse 400 INVALID_ARGUMENT — Definitive Fix**: `inline_data` (base64 PDF upload) returns 400 for this API key tier regardless of model — even `gemini-3.5-flash-lite` fails with real-sized PDFs. Root cause: PDF multimodal via `inline_data` requires a higher-tier API key. **Fix**: `_call_gemini_rest` now pre-extracts all file content to plain text before calling the API (pdfplumber for PDFs: full text + structured table rows; pandas for Excel; UTF-8 decode for CSV). Text-only approach is model-agnostic, key-tier-agnostic, and confirmed working end-to-end with live API test.

## v1.5.5 (2026-08-19)
### Fixed
- **Gemini Model Migration (RCA)**: Root cause: This API key is a "new user" key — Google deprecated `gemini-2.5-flash` AND `gemini-2.5-flash-lite` for new-user keys (both return HTTP 404). Verified live via the models API that `gemini-3.5-flash` returns HTTP 200 for this key. All 10 AI call sites in `categorizer.py`, `statement_parser.py`, `ocr_engine.py`, `investment_planner.py`, and `example_stock_recommender.py` are now updated to `gemini-3.5-flash`.

## v1.5.4 (2026-08-18)
### Added
- **Smart Statement Import**: Added AI-powered Bank and Credit Card Statement Import. The system now uses Google Gemini Vision to read any unstructured Bank or Credit Card Statement (PDF, CSV, or Excel), intelligently extracts dates, descriptions, amounts, determines if it's an Income or Expense, and automatically categorizes it.
- **Unified Transaction Ledger**: Updated the `expenses` database table schema to include a `transaction_type` column to support both 'Expense' and 'Income' entries in the same place without breaking backward compatibility for existing expense charts.
- **Interactive Review UI**: Revamped the "File Import & Quick Add" section. When you upload a PDF or CSV statement, it will process it using AI and present an interactive spreadsheet (`st.data_editor`) for you to review and confirm the AI's predicted categories or amounts before saving to the database.

### Fixed
- **Mutual Fund display in Smart Advisor**: Fixed an issue where Mutual Funds (especially those tracked via AMFI scheme codes like "103819") would display "N/A" for their ticker and price because Yahoo Finance does not support AMFI codes. The Advisor now correctly identifies Mutual Funds, skips the Yahoo Finance technical trend check (which causes the N/A), calculates their current price directly from the portfolio's active NAV, and passes them to the AI for fundamental advice.
- **Enhanced Ticker Display**: Smart Advisor now combines the stock/fund code and the actual resolved name in the UI, displaying it as `103819 ("Fund Name")` for much better readability.
- **Personalized Mutual Fund Signals**: Instead of showing generic advice or returning API errors for mutual funds, the Smart Advisor now calculates a personalized performance signal (Strong Hold, Hold, Caution, Reduce) based directly on your Absolute Return % (unrealized gains) for that specific fund.
- **Blended Stock Analysis**: Expanded the personal return logic to individual stock holdings as well. Stock signals are now a powerful blend of your *Personal Return* (Absolute Return %) and *Technical Signals* (SMA crossovers and momentum from Yahoo Finance), giving you a holistic "Buy/Hold/Reduce" recommendation.
- **Grouped Portfolio Summary**: Added a brand new "Grouped Holdings Summary" section to the Active Investments tab. Your investments are now cleanly bucketed into Mutual Funds, Stocks, and Other Investments (EPFO, Real Estate, etc.) in expandable folders. Mutual funds are further broken down into separate tables for Large Cap, Mid Cap, Small Cap, and Multi Cap, displaying exact group totals and Unrealized Gains directly on the headers.
## v1.5.3 (2026-08-17)
### Added
- **Strict Stock Recommendation Logic**: Injected a highly structured, forensic-focused AI system prompt (`BASE_STOCK_SYSTEM_PROMPT`) into the Smart Advisor's core engine. The AI now acts as a Senior Equity Research Analyst & Quantitative Portfolio Strategist, enforcing strict forensic checks (avoiding high promoter pledge, auditor red flags, debt traps) and providing realistic valuation targets before making any recommendations for rebalancing or new money deployment. The prompt automatically adapts to the user's selected country.
## v1.5.2 (2026-08-17)
### Added
- **Full Portfolio Review**: The Smart Advisor now loops through all equity holdings in the portfolio (removed the previous 5-stock limit) to provide live Buy/Hold/Sell trend signals and strength scores for the entire equity portfolio.
- **Sector & Segment Analysis**: Integrated a portfolio-wide sector breakdown into the Smart Advisor. The Gemini AI engine now analyzes the current macroeconomic environment against the user's specific sector allocation and outputs actionable segment recommendations (which sectors to Buy, Hold, or Sell).
- **Progress UI Update**: Added a warning to the loading spinner in the Rebalance tab indicating that fetching live signals for all holdings may take 30-45 seconds.
## v1.5.1 (2026-08-17) — Hotfix
### Fixed
- **Turso connection fallback bug (critical)**: `get_connection()` was silently falling back to local SQLite on Streamlit Cloud because an `ImportError` on `libsql_experimental` was stored as the failure reason and blocked the `libsql_client` (HTTP mode) fallback from running. Fixed the fallback chain so `ImportError` on `libsql_experimental` is treated as "driver not installed, try next" and `libsql_client` is always attempted before giving up and falling back to SQLite. This caused the Streamlit Cloud deployment to read/write an empty local database instead of the Turso cloud DB, making all user data appear missing.

## v1.5.0 (2026-08-17)
### Added
- **Smart Investment Advisor (new sub-tab)**: Added a new "💡 Smart Advisor & Tax Planner" 5th sub-tab under Wealth & Planning with three inner tabs:
  - **🔄 Rebalance My Portfolio**: Computes current vs target asset allocation by risk profile (Conservative / Moderate / Aggressive), shows drift table with Buy/Hold/Reduce actions, fetches live yfinance trend signals (20-SMA vs 50-SMA Golden/Death Cross, 200-SMA position, 30-day momentum) for equity holdings, and generates Gemini AI-powered rebalancing recommendations with specific fund names.
  - **💰 Deploy New Money**: Accepts a lump-sum or SIP amount and generates categorised instrument suggestions (Equity, Debt, Gold, Tax-Saving) personalised by risk profile and country (India / US / UAE / UK / SG / Other), with Gemini AI narrative summary. Country selection is editable inline and synced to user profile.
  - **🧾 Income & Tax Planner**: Full income source manager (add/delete with frequency normalisation to monthly equivalent), income breakdown bar chart, and a country-aware tax liability calculator supporting India Old/New Regime (FY 2024-25 slabs, 87A rebate, 80C auto-detection from holdings, LTCG 12.5% check), US Single Filer (2024 brackets), and UAE/No-Tax countries. Surfaces personalised tax-saving opportunities.
- **Income Sources DB Table**: New `income_sources` table auto-migrated in `init_db()`. CRUD functions: `add_income_source`, `get_income_sources_df`, `delete_income_source`, `update_income_source`. Supports family/private visibility scope.
- **Advisory Disclaimer Banner**: Prominent amber warning on the new advisor tab clarifying all recommendations are informational only based on technical indicators.
- **`fetch_stock_trend_signal()`**: New function in `investment_planner.py` using yfinance to compute SMA crossover, long-term trend, and 30-day momentum signals. Returns signal label (Strong Buy / Buy / Hold / Reduce / Caution) with strength score 0–100.
- **`generate_rebalance_advice()`**, **`generate_new_money_advice()`**, **`compute_tax_liability()`**: Three new advisory engine functions with Gemini AI primary and rule-based fallback.
- **Country-editable inline**: Country of residence can now be updated directly from within the Advisor tab (synced to user profile) instead of only from Settings.

## v1.4.1 (2026-08-17)
### Added
- **Turso DB Health Check**: Added `check_turso_connection()` in `database.py` that probes the remote Turso database with a live `SELECT 1` query at startup (once per session).
- **Connection Warning Banner**: If Turso credentials are configured but the remote database is unreachable, a prominent red warning banner is shown at the top of the app on every page. The banner details the exact failure reason and informs the user that the app has fallen back to local SQLite (data will not sync to the cloud).

### Fixed
- **`get_connection()` exception handling**: Separated `ImportError`/`ModuleNotFoundError` from generic `Exception` so driver-missing errors are distinguished from network/auth failures.
- **Fallback reason capture**: `get_connection()` now records the failure reason in `_turso_fallback_reason` module variable instead of silently printing to stdout.
- **Import hygiene**: `check_turso_connection` is now properly exported from `database.py` and imported in `app.py`.

## v1.4.0 (2026-08-12)
- **Feature**: Added a "Find & Remove Duplicate Holdings" tool in the Active Investments tab! Users can now scan their portfolio for exact duplicates and safely delete the redundancies in one click.
- **Feature**: Added automatic AMFI code resolution for Mutual Funds! When importing investments from statements (like Anand Rathi) that only list numeric codes, the system now automatically fetches and saves the official human-readable fund name.
- **Feature**: Replaced raw numeric codes in the Active Investments tracker with their resolved AMFI names.
- **Feature**: Mapped AMFI resolved Mutual Fund sectors/categories directly into the 'Sector / Theme' column in the Active Investment portfolio.
- **Feature**: Implemented user-specific, history-based personal inflation rate logic in the **Personal Expense Predictor**. Users can seamlessly project future expenses weighted by their real category-level spending.
- **Feature**: Added an interactive override field for the inflation rate to let users model "what-if" projection scenarios.

## Newly Added Requirements
- Added **Goal-Based Savings** tracking under the Budget Planner for creating specific savings targets (e.g. Child's Education) with progress bars and contribution logging.
- Added **Debt Payoff Simulator** to the "Debt & Liabilities" tab with Snowflake simulation logic for Avalanche and Snowball payoff strategies.
- Added Portfolio Sync History to track historical portfolio growth over multiple time frames (Since Last Sync, Weekly, Monthly, Yearly).
- Implemented `portfolio_snapshots` table to automatically record total portfolio valuation when the user syncs live prices.
- Populated the `sector_segment` database column using Mutual Fund category metadata retrieved from the AMFI lookup tool.
- Added "Personal Expense Predictor" sub-tab under Inflation & CPI Analytics to project future expenses based on a dynamically calculated personalized inflation rate, weighted by the user's historical category spending.
- Added a toggle option in the "Investment & Wealth Planner" to explicitly use the "Networth" (Current Portfolio Valuation) from the Active Investments tab or allow the user to manually override it.
- Realigned the configuration inputs (Age, Networth Toggle, Networth Amount, Monthly Budget) in the "Investment & Wealth Planner" to render cleanly in a single horizontal row.
- Renamed "Monthly Budget" label in the Investment and Wealth Planner to "Monthly recurring Investments".
- Added support for factoring in multiple one-time expenses (like child's education or house downpayment) and additional ongoing monthly recurring expenses (like medical costs) directly into the Retirement Simulation model to dynamically reduce the final retirement corpus.

## [Unreleased]
### Added
- **Debt & Liabilities Management**: Added a new comprehensive module under "Wealth & Planning" to track active debts, loans, and liabilities. Users can now input their outstanding principal, interest rate, tenure, and monthly EMI.
- **Debt Auto-Sync**: The system now automatically synchronizes the Monthly EMI for new debts directly into the Category Budget Planner as a fixed expense.
- **Debt Portfolio & Payments**: Added a tracking view to monitor principal paid vs. outstanding, along with a dedicated "Log Payment" feature to record principal and interest payments over time.
- **Debt Dashboards**: Added a "Total Active Debt" consolidated KPI to the Main Dashboard and a detailed "Total Debt & Liabilities Overview" to the Debt tab.
- **Gemini AI Integration**: Universal statement parsing using `google-genai` for PDFs, Images, and CSVs.
- **Extended Profile**: Added new demographic and financial fields (Sex, Date of Birth, Address, City, State, Country, Income Range, Occupation, Marital Status, Risk Tolerance) to the database schema and created a comprehensive User Profile editor in the Settings & Admin tab.
- **Income-Driven Budgeting**: Added a "Monthly Expected Income" field to the Category Budget Planner. The "Insurance & Investments" budget is now dynamically locked to equal `Income - Sum(Other Expenses)`. Auto-allocation now strictly reserves 20% for Insurance & Investments, distributing the remainder proportionally to other expenses. Added a deficit warning if expenses exceed income.

### Fixed
- **Page Layout & Scrolling**: Fixed an issue where the top KPI dashboard blocks occupied the entire screen height when navigating to other tabs, eliminating the need for constant scrolling.
- **Profile Form**: Allowed Date of Birth field to select years going back to 1900.

### Changed
- **UI Navigation & Layout**: Consolidated the main dashboard KPIs (Household Expenses Overview and Personal Wealth & Profile) into two side-by-side structured container boxes (`.dashboard-box`) inside the Dashboard page overview tab rather than rendering them globally on every single page navigation.
- **Responsive Layout**: Designed custom CSS and media query rules for the consolidated boxes to stack vertically on mobile screens for optimal mobile navigation.
- **Statement Template**: Expanded the downloadable CSV template to include all 10 investment database fields for seamless non-AI ingestion.
- **API Key Persistence**: Added the ability to securely save the Gemini API key directly to the user profile in the database.
- **Portfolio Filters**: Added a multi-select filter for "Asset Class" in the Active Investment Portfolio detailed view.
- **Investment Schema Update**: Added `description` field for storing Stock Code / Name.
- **User Profile Updates**: Added `age` column to the user database schema for persistence and introduced a dedicated User Profile editor in the Settings & Admin tab to allow users to update it.

### Fixed
- **Dashboard Crash**: Fixed a `NameError` caused by missing expense dataframe initialization in the Dashboard view.
- **App Crash**: Fixed an `AttributeError` on `datetime.now()` caused by incorrect datetime module usage during dashboard initialization.
- **Authentication State**: Fixed a `KeyError` related to the `current_user` dictionary in session state.
- **Database Insertion**: Fixed parameter alignment `TypeError` in `insert_investment` after adding the description field.
- **Live Market Tracker**: Fixed `KeyError` when querying missing asset classes.
- **Retirement Simulator**: Fixed a `TypeError` when processing empty cells in the one-time expenses data editor.
- **Navigation Tabs Crash**: Fixed a `NameError` causing crashes by restoring missing sidebar navigation `elif` blocks for "Insights & Analytics", "Wealth & Planning", and "Settings & Admin" sections.
- **Admin Tab Crash**: Fixed a `NameError` for `tab_admin` in the Settings & Admin section by replacing the deprecated tab reference with proper role-based access control checks (`is_super_admin` / "Admin").
- **Settings & Admin Content**: Fixed an issue where the "Data Export" and "Admin" tabs were incorrectly rendering inside the "Wealth & Planning" section by adding the missing `elif nav_selection == "⚙️ Settings & Admin":` block.


### Changed
- **UI Navigation**: Renamed the "Budgeting & Targets" tab to "Budgeting & Investments" for clarity.
- **Sidebar Layout**: Moved the primary navigation menu to the absolute top of the sidebar. Moved the "Storage Engine" and "Sign Out" button to the bottom of the sidebar, below the navigation menu, and increased the Storage Engine font size by 2px.
- **Dashboard Layout**: Restructured the Top KPI dashboard into two cleanly aligned thematic rows (Household Expenses Overview and Personal Wealth & Profile), expanding the visible metrics to include dynamically calculated Networth and User Age.
- **Current Savings Auto-Fill**: The 'Current Total Savings / Corpus' field in the Wealth Planner now automatically fetches and calculates the sum of all your active investments in the portfolio tracker as the default value.

### Added
- **Retirement Planner Engine**: Added a new "Retirement Planner Simulation" module under the Wealth Planner tab. 
- **Dynamic Market Index Returns**: Integrated `yfinance` to allow users to fetch live historical data from major global indices (Nifty 50, BSE Sensex, S&P 500, NASDAQ) to compute the actual historical Average Annual Return (CAGR) dynamically for the last 5, 10, 15, or 20 years.
- **AI Retirement Advisory**: Integrated Gemini AI to cross-reference the user's projected retirement corpus with their *active* holdings portfolio, generating a tailored strategic withdrawal and rebalancing plan.
- Fixed an issue where the user's age was not persistently saving when updated from the Wealth Planner dashboard.

- **Defects Fixed:** Fixed UI issue where the 'Detect Duplicates' tab was hidden when there were no expenses in the currently selected Financial Year. The tab is now always visible and queries all financial years.

- **Newly Added Requirements:** Implemented a 'Smart Select' feature in the 'Detect Duplicates' tab that automatically pre-selects all redundant duplicates for deletion, saving the user from clicking them individually while safely keeping one original record.

## Password Recovery Updates
- **Feature**: Added a complete Forgot Password flow using either Email OTP or a Security Question.
- **Requirement**: Made Email setup mandatory for existing users upon login to ensure account recovery is always possible.
- **Profile Management**: Users can now update their Email Address and Security Question/Answer directly in their Profile Settings.

### Fixed
- **Portfolio Analytics**: Fixed an issue in the "Historical Growth (vs Live Market)" section where a decrease in portfolio value was incorrectly displayed in green instead of red.

### Fixed
- **AI Integration**: Fixed an issue where Gemini AI features (like Portfolio Suggestions) silently failed and fell back to rule-based generation due to an invalid model name (`gemini-3.5-flash-lite`). Updated all AI endpoints to correctly use `gemini-1.5-flash`.

- **Gemini AI Portfolio Review Enhancement**: 
  - Integrated User Profile (Age, Income, Risk Tolerance), Active Debts, and Savings Goals context into the AI engine.
  - Upgraded the AI model to `gemini-1.5-pro` for deeper financial reasoning.
  - Instructed the AI to adopt a SEBI RIA persona and strictly adhere to Indian tax codes.
  - Implemented Gemini Structured Outputs (JSON Schema via Pydantic) to ensure the AI's response perfectly maps to the UI, eliminating formatting crashes.

### Bug Fixes
- **Income Sources:** Fixed an issue where deleting an income source in "Personal View" mode would silently fail due to a missing family_id fallback.

### Fixed
- **Passive Income UI & Calculation**: Fixed a defect where duplicate portfolio investments (e.g. two EPF entries under the same bank) were displayed multiple times in the Tax Planner Section B. Entries are now correctly deduplicated and aggregated by source name and income type.
- **Tax Double Counting**: Fixed an issue where auto-derived passive income sources (like FRSB bonds or EPF entered in the Income Sources tab) were double-counted in both standard Gross Salary and Passive Income calculations. 
- **Keyword Matching**: Fixed an issue where an income source named 'Public Provident Fund' was incorrectly parsed as EPF instead of PPF due to keyword overlap.
- **FRSB Parsing**: Fixed an issue where FRSB bonds were not recognized by the income tax calculator if categorized under generic investment types like 'Alternative Asset'. The parser now checks the name and description fields for FRSB and other fixed-income keywords.

### Added
- **Financial Academy Module**: Added a new main navigation tab called "🎓 Financial Academy" targeted at beginner and medium competence users.
- **AI Assessment Engine**: Built a dynamic, conversational AI assessment (`academy_assessment.py`) using Gemini 1.5 Pro to evaluate users' financial competence (budgeting, debt, investments) and assign personalized personas.
- **Sandbox Simulator Interface**: Created the UI structure for an interactive Sandbox Mode to allow users to practice budgeting and rebalancing using simulated dummy data.
- **Curated Learning Library**: Added a "Library & Courses" sub-tab featuring recommended YouTube playlists, Coursera, and Udemy courses for continued financial education.

### Fixed
- **Admin User Creation**: Fixed a `TypeError` crash that occurred when an Admin attempted to register a new household member account while in the "Personal" view mode (where `family_id` was internally set to `None`). The new user now correctly inherits the Admin's family ID as a fallback.
