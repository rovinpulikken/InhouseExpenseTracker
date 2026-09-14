"""
academy_assessment.py
AI-driven psychometric assessment for the Financial Academy.
"""
import os
import json
from typing import List, Dict, Any

def get_gemini_client(api_key=None):
    try:
        from google import genai
    except ImportError:
        return None
        
    if not api_key:
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

def generate_next_assessment_question(chat_history: List[Dict[str, str]], api_key: str = "") -> Dict[str, Any]:
    """
    Given the chat history of the assessment, generates the next situational question 
    or finalizes the assessment.
    chat_history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    client = get_gemini_client(api_key)
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
        import time
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt
                )
                break
            except Exception as api_err:
                if "503" in str(api_err) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise api_err
                
        if response and response.text:
            cleaned = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
    except Exception as e:
        return {"error": f"⚠️ Gemini API Error (after {max_retries} attempts): {str(e)}"}
    
    return {"error": "Failed to generate response"}

def generate_ai_learning_path(user_context: Dict[str, Any], api_key: str = "") -> Dict[str, Any]:
    """
    Generates a personalized structured syllabus based on the user's financial context, 
    location preference, investment interests, and knowledge level.
    """
    client = get_gemini_client(api_key)
    if not client:
        return {"error": "⚠️ Google Gemini API Key is missing. Please configure it in Settings to generate a personalized learning path."}
        
    system_prompt = """
    You are an expert Financial Educator building a tailor-made, structured investment course for a user.
    
    You will receive the user's profile, including:
    - Financial data (Income, Debt, Current Investments)
    - Knowledge Level (Beginner, Intermediate, Advanced)
    - Location Preference (Local/Domestic, International, or Both)
    - Specific Investment Interests (e.g., Traditional, Mutual Funds, Stocks, Alternate, Property)
    
    IMPORTANT RULES FOR LINKS:
    To avoid broken video links, do NOT generate direct YouTube video IDs.
    Instead, generate YouTube search queries like this:
    https://www.youtube.com/results?search_query=your+search+keywords
    
    For articles, you may link to well-known domains like Investopedia or Zerodha Varsity.
    
    YOUR OUTPUT MUST BE EXACTLY VALID JSON. DO NOT WRAP IN MARKDOWN BLOCKS LIKE ```json.
    
    Structure your JSON response as follows:
    {
        "course_title": "A catchy title for the personalized course",
        "summary": "A 2-3 paragraph summary of what they should focus on, taking into account their knowledge level, debt (if any), and chosen location preference.",
        "modules": [
            {
                "module_name": "Name of the topic (e.g., 'Mastering Mutual Funds' or 'Real Estate Fundamentals')",
                "description": "Brief explanation of what this module covers and why it fits their profile.",
                "resources": [
                    {
                        "title": "Resource Title (e.g., 'Index Funds vs Active Funds')",
                        "url": "https://...",
                        "type": "Video" or "Article" or "Course"
                    }
                ]
            }
        ]
    }
    
    Create one module for each of the user's specified investment interests. Also, create a foundational module if they have high debt or are beginners.
    Ensure suggestions align with their location preference (e.g., if 'Local (India)', suggest domestic instruments; if 'International', suggest US/Global stocks/funds).
    """
    
    prompt = system_prompt + "\n\nUser Context:\n" + json.dumps(user_context, indent=2)
    
    try:
        import time
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt
                )
                break
            except Exception as api_err:
                if "503" in str(api_err) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise api_err
                
        if response and response.text:
            cleaned = response.text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {"error": "⚠️ AI generated malformed JSON. Please try again."}
    except Exception as e:
        return {"error": f"⚠️ Failed to generate learning path (Gemini API Error after {max_retries} attempts): {str(e)}"}
    
    return {"error": "⚠️ Failed to generate response from AI."}
