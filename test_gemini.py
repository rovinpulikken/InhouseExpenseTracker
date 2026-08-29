import os
import sys
try:
    from google import genai
except ImportError:
    print("google-genai not installed")
    sys.exit(1)

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    # Try reading from secrets.toml
    try:
        import toml
        with open(".streamlit/secrets.toml", "r") as f:
            secrets = toml.load(f)
            api_key = secrets.get("GEMINI_API_KEY", "")
    except Exception as e:
        pass

if not api_key:
    print("No API key found")
    sys.exit(1)

client = genai.Client(api_key=api_key)
try:
    models = client.models.list()
    for m in models:
        print(m.name)
except Exception as e:
    print(f"Error: {e}")
