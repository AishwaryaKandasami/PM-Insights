import sys
sys.path.append('.')
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def test_model(name):
    print(f"Testing {name}...")
    try:
        model = genai.GenerativeModel(name)
        res = model.generate_content("Say 'OK' if working and you can see this.")
        print(f"[{name}] SUCCESS: {res.text.strip()}")
        return True
    except Exception as e:
        print(f"[{name}] FAILED: {e}")
        return False

test_model('gemini-1.5-pro')
test_model('gemini-1.5-flash')
