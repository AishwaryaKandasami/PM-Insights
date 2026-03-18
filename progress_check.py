import sqlite3
import sys
sys.path.append('.')
from config.settings import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Count atoms
cursor.execute('SELECT COUNT(1) FROM review_atoms')
atoms = cursor.fetchone()[0]

# 2. Count remaining
cursor.execute('''
    SELECT COUNT(1) FROM reviews_normalized r 
    WHERE is_supported=1 AND is_low_quality=0 AND is_duplicate=0 
    AND NOT EXISTS (SELECT 1 FROM review_atoms a WHERE a.review_id = r.review_id)
''')
remaining = cursor.fetchone()[0]

print(f"Atoms: {atoms}")
print(f"Remaining: {remaining}")
conn.close()
