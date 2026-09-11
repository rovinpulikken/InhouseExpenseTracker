import streamlit as st
from academy_assessment import generate_next_assessment_question

def render_financial_academy_tab(api_key=""):
    st.header("🎓 Financial Academy")
    st.markdown("Level up your financial knowledge and master FinCompass.")
    
    # Session state for academy
    if "academy_chat_history" not in st.session_state:
        st.session_state.academy_chat_history = []
    if "academy_status" not in st.session_state:
        st.session_state.academy_status = "not_started"
    if "academy_persona" not in st.session_state:
        st.session_state.academy_persona = None
        
    tabs = st.tabs(["📝 AI Assessment", "🎮 Sandbox Simulator", "📚 Library & Courses"])
    
    with tabs[0]:
        st.subheader("Financial Health Check")
        st.markdown("Let's assess your current financial knowledge through a quick conversational scenario.")
        
        if st.session_state.academy_status == "not_started":
            if st.button("Start Assessment"):
                st.session_state.academy_chat_history = []
                st.session_state.academy_status = "in_progress"
                with st.spinner("Generating first scenario..."):
                    response = generate_next_assessment_question(st.session_state.academy_chat_history, api_key)
                    if "error" in response:
                        st.error(response["error"])
                        st.session_state.academy_status = "not_started"
                    else:
                        st.session_state.academy_chat_history.append({"role": "assistant", "content": response.get("question_text", "Ready?")})
                        st.rerun()
                
        elif st.session_state.academy_status == "in_progress":
            for msg in st.session_state.academy_chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
            user_input = st.chat_input("Your response...")
            if user_input:
                st.session_state.academy_chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.write(user_input)
                    
                with st.spinner("Analyzing..."):
                    response = generate_next_assessment_question(st.session_state.academy_chat_history, api_key)
                    if "error" in response:
                        st.error(response["error"])
                    elif response.get("status") == "complete":
                        st.session_state.academy_status = "completed"
                        st.session_state.academy_persona = response
                        st.rerun()
                    else:
                        question_text = response.get("question_text", "Please continue.")
                        st.session_state.academy_chat_history.append({"role": "assistant", "content": question_text})
                        st.rerun()
                        
        elif st.session_state.academy_status == "completed":
            st.success("🎉 Assessment Completed!")
            persona = st.session_state.academy_persona
            if persona:
                st.metric("Level Assessed", persona.get("final_score", "Unknown"))
                st.markdown(f"**Your Persona:** {persona.get('persona', '')}")
                st.info(persona.get("summary", ""))
            
            if st.button("Retake Assessment"):
                st.session_state.academy_status = "not_started"
                st.rerun()
                
    with tabs[1]:
        st.subheader("Sandbox Simulator")
        st.markdown("Practice your skills using fake simulated data without affecting your real finances.")
        
        is_sandbox = st.session_state.get("is_sandbox_mode", False)
        
        if is_sandbox:
            st.warning("⚠️ You are currently in SANDBOX MODE. Data shown on other tabs is simulated.")
            if st.button("Exit Sandbox Mode"):
                st.session_state.is_sandbox_mode = False
                st.rerun()
                
            st.markdown("### Active Missions")
            st.info("**Mission 1 (Beginner):** Fix the monthly deficit by adjusting the budget.")
            st.info("**Mission 2 (Intermediate):** Allocate ₹50,000 into a mix of FDs and Equity.")
        else:
            st.success("You are in LIVE mode viewing your real data.")
            if st.button("Enter Sandbox Mode"):
                st.session_state.is_sandbox_mode = True
                st.rerun()
                
    with tabs[2]:
        st.subheader("Library & Further Studies")
        st.markdown("Expand your knowledge with curated resources based on your level.")
        
        # Build user context
        user_context = {}
        if "user" in st.session_state:
            user = st.session_state["user"]
            user_context["username"] = user.get("username")
            family_id = user.get("family_id", 1)
            
            try:
                from database import get_income_sources_df, get_debts, get_user_investments_df
                inc_df = get_income_sources_df(user["username"], family_id, view_mode="All")
                user_context["total_monthly_income"] = inc_df["monthly_equivalent"].sum() if not inc_df.empty else 0
                
                debts_df = get_debts(family_id)
                user_context["total_debt"] = debts_df["balance_remaining"].sum() if not debts_df.empty else 0
                
                inv_df = get_user_investments_df(user["username"], family_id)
                if not inv_df.empty:
                    user_context["investments_by_asset_class"] = inv_df.groupby("asset_class")["current_value"].sum().to_dict()
                else:
                    user_context["investments_by_asset_class"] = "No investments found"
            except Exception as e:
                user_context["error"] = "Could not fetch detailed financial profile."
                
        if st.button("✨ Generate Personalized Learning Path", type="primary", use_container_width=True):
            with st.spinner("Analyzing your profile and finding the best resources..."):
                from academy_assessment import generate_ai_learning_path
                learning_path = generate_ai_learning_path(user_context, api_key)
                st.session_state.academy_learning_path = learning_path
                
        if "academy_learning_path" in st.session_state:
            st.markdown("### 🎯 Your Personalized AI Learning Path")
            st.markdown(st.session_state.academy_learning_path)
            st.markdown("---")
            
        with st.expander("General Curated Resources", expanded=("academy_learning_path" not in st.session_state)):
            st.markdown("### YouTube Playlists")
            st.markdown("- [Zerodha Varsity: Stock Market Basics](https://zerodha.com/varsity/)")
            st.markdown("- [Personal Finance for Beginners](https://www.youtube.com)")
            
            st.markdown("### Udemy & Coursera")
            st.markdown("- [Financial Planning Essentials (Coursera)](https://www.coursera.org)")
            st.markdown("- [Investing 101 (Udemy)](https://www.udemy.com)")
