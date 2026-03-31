import sqlite3
import pandas as pd
from config.settings import DB_PATH

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM rice_inputs LIMIT 5", conn)
print(df.to_dict('records'))
conn.close()
