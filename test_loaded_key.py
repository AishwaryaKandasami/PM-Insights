import os
import sys
sys.path.append('.')
from dotenv import load_dotenv

# 1. Load without override
load_dotenv()
res1 = os.environ.get("GEMINI_API_KEY")
print("Without Override:", res1[:10] + "..." + res1[-5:] if res1 else "None")

# 2. Load with override
load_dotenv(override=True)
res2 = os.environ.get("GEMINI_API_KEY")
print("With Override:", res2[:10] + "..." + res2[-5:] if res2 else "None")

# 3. Read directly from .env file
try:
    with open('.env', 'r') as f:
        print("File content:", f.read().strip())
except Exception as e:
    print("File read error:", e)
