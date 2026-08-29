import streamlit as st
from academy_assessment import generate_next_assessment_question

def render_financial_academy_tab():
    st.header("🎓 Financial Academy")
    st.markdown("Level up your financial knowledge and master the InhouseExpenseTracker.")
    
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
                    response = generate_next_assessment_question(st.session_state.academy_chat_history)
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
                    response = generate_next_assessment_question(st.session_state.academy_chat_history)
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
        
        st.markdown("### YouTube Playlists")
        st.markdown("- [Zerodha Varsity: Stock Market Basics](https://zerodha.com/varsity/)")
        st.markdown("- [Personal Finance for Beginners](https://www.youtube.com)")
        
        st.markdown("### Udemy & Coursera")
        st.markdown("- [Financial Planning Essentials (Coursera)](https://www.coursera.org)")
        st.markdown("- [Investing 101 (Udemy)](https://www.udemy.com)")
