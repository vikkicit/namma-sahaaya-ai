
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

key = os.getenv("GEMINI_API_KEY")

if not key:
    print("ERROR: GEMINI_API_KEY is missing from .env")
else:
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents="Reply with exactly: Gemini connected"
        )
        print(response.text)
    except Exception as e:
        print(f"API ERROR: {type(e).__name__}: {e}")
