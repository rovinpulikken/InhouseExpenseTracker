# Release Notes

## v1.4.0 (2026-08-12)
- **Feature**: Added a "Find & Remove Duplicate Holdings" tool in the Active Investments tab! Users can now scan their portfolio for exact duplicates and safely delete the redundancies in one click.
- **Feature**: Added automatic AMFI code resolution for Mutual Funds! When importing investments from statements (like Anand Rathi) that only list numeric codes, the system now automatically fetches and saves the official human-readable fund name.
- **Feature**: Replaced raw numeric codes in the Active Investments tracker with their resolved AMFI names.
- **Feature**: Mapped AMFI resolved Mutual Fund sectors/categories directly into the 'Sector / Theme' column in the Active Investment portfolio.
- **Feature**: Implemented user-specific, history-based personal inflation rate logic in the **Personal Expense Predictor**. Users can seamlessly project future expenses weighted by their real category-level spending.
- **Feature**: Added an interactive override field for the inflation rate to let users model "what-if" projection scenarios.

## Newly Added Requirements
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
