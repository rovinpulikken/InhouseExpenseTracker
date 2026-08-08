# Release Notes

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
