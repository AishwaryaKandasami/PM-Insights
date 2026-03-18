import sqlite3
import sys
sys.path.append('.')
from config.settings import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute('SELECT COUNT(1) FROM bug_clusters')
    bugs = cursor.fetchone()[0]
except Exception:
    bugs = "Table not populated yet"

try:
    cursor.execute('SELECT COUNT(1) FROM feature_clusters')
    features = cursor.fetchone()[0]
except Exception:
    features = "Table not populated yet"

print(f"Bug Clusters: {bugs}")
print(f"Feature Clusters: {features}")
conn.close()
