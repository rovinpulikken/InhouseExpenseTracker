with open("app.py", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if "def main():" in line:
        pass
    
    # We will inject the sandbox overrides immediately after the database imports
    if "    clear_recovery_otp," in line:
        pass
        
    new_lines.append(line)

    if line.strip() == "from database import (":
        pass

# Actually, the best place to patch is after all the `from database import (...)` finishes.
# Let's find the closing parenthesis for the database imports.
with open("app.py", "r") as f:
    content = f.read()

import_str = """    clear_recovery_otp,
    get_admin_gemini_api_key
)"""

sandbox_injection = """    clear_recovery_otp,
    get_admin_gemini_api_key
)
from sandbox_data import (
    sandbox_get_expenses_df,
    sandbox_get_user_investments_df,
    sandbox_get_budget_status,
    mock_success
)
"""
content = content.replace(import_str, sandbox_injection)

# Now inject the mode override after the authentication block, where current_user is available
# Look for "if st.session_state.get("authenticated"):" and immediately after set the overrides
auth_line = "if st.session_state.get(\"authenticated\"):"
auth_idx = content.find(auth_line)
if auth_idx != -1:
    override_code = """
    if st.session_state.get("is_sandbox_mode", False):
        global get_expenses_df, get_user_investments_df, get_budget_status, insert_expenses, insert_investment, update_investments_df
        get_expenses_df = sandbox_get_expenses_df
        get_user_investments_df = sandbox_get_user_investments_df
        get_budget_status = sandbox_get_budget_status
        insert_expenses = mock_success
        insert_investment = mock_success
        update_investments_df = mock_success
"""
    # Just inject it after the line
    # Actually wait, streamlt reruns from top to bottom, so overriding globals in the middle of the file is fine.
    # Let's insert it right after `current_user = ...` inside the auth block.
    user_line = 'current_user = st.session_state["user_info"]'
    user_idx = content.find(user_line)
    if user_idx != -1:
        insert_pos = user_idx + len(user_line)
        content = content[:insert_pos] + "\n" + override_code + content[insert_pos:]

# Now inject the banner
banner_str = """    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()"""

banner_injection = """    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ----------------------------------------------------
    # Global Sandbox Banner
    if st.session_state.get("is_sandbox_mode", False):
        st.error("🎮 **SANDBOX MODE ACTIVE**: Data is simulated. Your real financial data is safe and hidden.")"""
content = content.replace(banner_str, banner_injection)


# Add a mission banner to the Transactions Dashboard
dash_str = """    if nav_selection == "🏠 Dashboard":
        st.header("🏠 Dashboard Overview")"""
dash_inj = """    if nav_selection == "🏠 Dashboard":
        st.header("🏠 Dashboard Overview")
        if st.session_state.get("is_sandbox_mode", False):
            st.info("🎯 **Sandbox Mission**: Review the simulated expenses below. Try changing the time filter to see how the dashboard updates.")"""
content = content.replace(dash_str, dash_inj)


# Add a mission banner to Budgeting
budget_str = """    elif nav_selection == "🎯 Budgeting":
        st.header("🎯 Budgeting & Goals")"""
budget_inj = """    elif nav_selection == "🎯 Budgeting":
        st.header("🎯 Budgeting & Goals")
        if st.session_state.get("is_sandbox_mode", False):
            st.info("🎯 **Sandbox Mission**: Notice how 'Dining Out' is over budget. Try creating a new budget for 'Rent' to cover the ₹25,000 expense.")"""
content = content.replace(budget_str, budget_inj)


# Add a mission banner to Investments
invest_str = """    elif nav_selection == "📈 Investments":
        st.header("📈 Investment Portfolio")"""
invest_inj = """    elif nav_selection == "📈 Investments":
        st.header("📈 Investment Portfolio")
        if st.session_state.get("is_sandbox_mode", False):
            st.info("🎯 **Sandbox Mission**: Your portfolio contains ₹50k Equity and ₹100k Debt. Try adding a new simulated investment.")"""
content = content.replace(invest_str, invest_inj)


with open("app.py", "w") as f:
    f.write(content)
