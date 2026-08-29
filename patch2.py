with open("app.py", "r") as f:
    content = f.read()

user_line = '    current_user = st.session_state["user"]'
user_idx = content.find(user_line)
if user_idx != -1:
    override_code = """
    if st.session_state.get("is_sandbox_mode", False):
        global get_expenses_df, get_user_investments_df, get_budget_status, insert_expenses, insert_investment, update_investments_df, get_debts, get_portfolio_snapshots_deltas
        get_expenses_df = sandbox_get_expenses_df
        get_user_investments_df = sandbox_get_user_investments_df
        get_budget_status = sandbox_get_budget_status
        insert_expenses = mock_success
        insert_investment = mock_success
        update_investments_df = mock_success
"""
    insert_pos = user_idx + len(user_line)
    content = content[:insert_pos] + "\n" + override_code + content[insert_pos:]

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
