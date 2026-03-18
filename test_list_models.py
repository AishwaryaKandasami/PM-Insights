import sys
sys.path.append('.')
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

try:
    print("Listing models...")
    for m in genai.list_models():
        print(f"Model: {m.name} | Display: {m.display_name}")
except Exception as e:
    print("Failed to list models:", e)
