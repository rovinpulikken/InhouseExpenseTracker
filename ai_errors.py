"""
ai_errors.py
Turns raw Gemini / Google API exceptions into short, user-friendly messages.
"""


def friendly_gemini_error(err, attempts: int = 0) -> str:
    """Return a human-readable message for a Gemini API exception (never leaks raw JSON)."""
    raw = str(err or "")
    low = raw.lower()
    tried = f" (tried {attempts} times)" if attempts and attempts > 1 else ""

    if "503" in raw or "unavailable" in low or "high demand" in low or "overloaded" in low:
        return ("⏳ The AI service is very busy right now" + tried +
                ". This is usually temporary — please wait a minute and try again.")
    if "429" in raw or "resource_exhausted" in low or "quota" in low or "rate limit" in low:
        return ("🚦 The AI usage limit has been reached for now. "
                "Please wait a little while and try again, or check your Gemini API key quota in Settings.")
    if ("api key" in low and ("invalid" in low or "not valid" in low)) or "api_key_invalid" in low \
            or "401" in raw or "403" in raw or "permission_denied" in low or "unauthenticated" in low:
        return ("🔑 The AI service rejected the API key. "
                "Please check your Gemini API key in Settings.")
    if "deadline" in low or "timed out" in low or "timeout" in low or "504" in raw:
        return "⌛ The AI service took too long to respond. Please try again in a moment."
    if "connection" in low or "network" in low or "name resolution" in low or "unreachable" in low:
        return "📡 Could not reach the AI service. Please check your internet connection and try again."
    if "safety" in low or "blocked" in low:
        return "🛡️ The AI could not respond to this request. Please rephrase and try again."
    return "⚠️ Something went wrong while contacting the AI service. Please try again shortly."
