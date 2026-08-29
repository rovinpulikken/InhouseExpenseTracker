"""
academy_assessment.py
AI-driven psychometric assessment for the Financial Academy.
"""
import os
import json
from typing import List, Dict, Any

def get_gemini_client():
    try:
        from google import genai
    except ImportError:
        return None
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    
    if api_key:
        return genai.Client(api_key=api_key)
    return None

def generate_next_assessment_question(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Given the chat history of the assessment, generates the next situational question 
    or finalizes the assessment.
    chat_history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    client = get_gemini_client()
    if not client:
        return {"error": "Google Gemini API Key is missing. Please configure it in Settings."}
        
    system_prompt = """
    You are an expert Financial Assessor and Psychometric Profiler.
    Your goal is to assess the user's financial competence (Beginner, Intermediate, Advanced) 
    through a series of dynamic, scenario-based questions.
    
    Conduct a maximum of 3-5 questions. Adapt the difficulty based on previous answers.
    Cover budgeting, debt management, investment (FDs, MFs, Equity), and risk psychology.
    
    Format your response EXACTLY as a JSON object:
    If asking the next question (status: question):
    {
        "status": "question",
        "question_text": "The scenario and question here..."
    }
    
    If the assessment is finished (status: complete):
    {
        "status": "complete",
        "final_score": "Beginner|Intermediate|Advanced",
        "persona": "A short catchy title e.g. 'The Cautious Saver'",
        "summary": "A brief explanation of their strengths and weaknesses."
    }
    """
    
    prompt = system_prompt + "\n\nChat History:\n" + json.dumps(chat_history)
    
    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        if response and response.text:
            cleaned = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": "Failed to generate response"}
