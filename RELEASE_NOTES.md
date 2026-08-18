# Release Notes

## v1.5.4 (2026-08-18)
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
