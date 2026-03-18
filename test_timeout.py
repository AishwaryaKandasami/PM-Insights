import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-2.5-flash')
try:
    response = model.generate_content(
        "Hello", 
        request_options={"timeout": 30}
    )
    print("SUCCESS: request_options is supported!")
    print(response.text)
except Exception as e:
    print(f"ERROR: request_options failed: {e}")
