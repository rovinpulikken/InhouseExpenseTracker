# Release Notes

## v1.4.0 (2026-08-12)
- **Feature**: Added a "Find & Remove Duplicate Holdings" tool in the Active Investments tab! Users can now scan their portfolio for exact duplicates and safely delete the redundancies in one click.
- **Feature**: Added automatic AMFI code resolution for Mutual Funds! When importing investments from statements (like Anand Rathi) that only list numeric codes, the system now automatically fetches and saves the official human-readable fund name.
- **Feature**: Replaced raw numeric codes in the Active Investments tracker with their resolved AMFI names.
- **Feature**: Mapped AMFI resolved Mutual Fund sectors/categories directly into the 'Sector / Theme' column in the Active Investment portfolio.
- **Feature**: Implemented user-specific, history-based personal inflation rate logic in the **Personal Expense Predictor**. Users can seamlessly project future expenses weighted by their real category-level spending.
- **Feature**: Added an interactive override field for the inflation rate to let users model "what-if" projection scenarios.

## Newly Added Requirements
- Populated the `sector_segment` database column using Mutual Fund category metadata retrieved from the AMFI lookup tool.
- Added "Personal Expense Predictor" sub-tab under Inflation & CPI Analytics to project future expenses based on a dynamically calculated personalized inflation rate, weighted by the user's historical category spending.
- Added a toggle option in the "Investment & Wealth Planner" to explicitly use the "Networth" (Current Portfolio Valuation) from the Active Investments tab or allow the user to manually override it.
- Realigned the configuration inputs (Age, Networth Toggle, Networth Amount, Monthly Budget) in the "Investment & Wealth Planner" to render cleanly in a single horizontal row.

## [Unreleased]
### Added
- **Gemini AI Integration**: Universal statement parsing using `google-genai` for PDFs, Images, and CSVs.
- **Statement Template**: Expanded the downloadable CSV template to include all 10 investment database fields for seamless non-AI ingestion.
- **API Key Persistence**: Added the ability to securely save the Gemini API key directly to the user profile in the database.
- **Portfolio Filters**: Added a multi-select filter for "Asset Class" in the Active Investment Portfolio detailed view.
- **Investment Schema Update**: Added `description` field for storing Stock Code / Name.

### Fixed
- **Authentication State**: Fixed a `KeyError` related to the `current_user` dictionary in session state.
- **Database Insertion**: Fixed parameter alignment `TypeError` in `insert_investment` after adding the description field.
- **Live Market Tracker**: Fixed `KeyError` when querying missing asset classes.


### Changed
- **UI Navigation**: Renamed the "Budgeting & Targets" tab to "Budgeting & Investments" for clarity.
- **Current Savings Auto-Fill**: The 'Current Total Savings / Corpus' field in the Wealth Planner now automatically fetches and calculates the sum of all your active investments in the portfolio tracker as the default value.

### Added
- **Retirement Planner Engine**: Added a new "Retirement Planner Simulation" module under the Wealth Planner tab. 
- **Dynamic Market Index Returns**: Integrated `yfinance` to allow users to fetch live historical data from major global indices (Nifty 50, BSE Sensex, S&P 500, NASDAQ) to compute the actual historical Average Annual Return (CAGR) dynamically for the last 5, 10, 15, or 20 years.
- **AI Retirement Advisory**: Integrated Gemini AI to cross-reference the user's projected retirement corpus with their *active* holdings portfolio, generating a tailored strategic withdrawal and rebalancing plan.
