import sqlite3
import pandas as pd
import sys
import os

sys.path.append(os.getcwd())
from database.db import get_connection

def check_table_counts():
    conn = get_connection()
    cursor = conn.cursor()
    
    tables_to_check = [
        'raw_reviews',
        'reviews_normalized',
        'review_atoms',
        'bug_clusters',
        'feature_clusters',
        'triage_matrix',
        'feature_requests',
        'dashboard_metrics',
        'rice_inputs',
        'pipeline_runs'
    ]
    
    output = []
    output.append("--- Table Counts ---")
    for table in tables_to_check:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            output.append(f"{table}: {count}")
        except Exception as e:
            output.append(f"{table}: ERROR ({e})")
            
    output.append("\n--- Pipeline Runs ---")
    try:
        runs = pd.read_sql("SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5", conn)
        output.append(runs.to_string())
    except Exception as e:
        output.append(f"Error reading pipeline_runs: {e}")

    output.append("\n--- Sample Atoms ---")
    try:
        atoms = pd.read_sql("SELECT * FROM review_atoms LIMIT 3", conn)
        output.append(atoms.to_string())
    except Exception as e:
         output.append(f"Error reading review_atoms: {e}")
         
    output.append("\n--- Sample Bug Clusters ---")
    try:
        clusters = pd.read_sql("SELECT * FROM bug_clusters LIMIT 3", conn)
        output.append(clusters.to_string())
    except Exception as e:
         output.append(f"Error reading bug_clusters: {e}")
         
    output.append("\n--- Sample Feature Clusters ---")
    try:
        clusters = pd.read_sql("SELECT * FROM feature_clusters LIMIT 3", conn)
        output.append(clusters.to_string())
    except Exception as e:
         output.append(f"Error reading feature_clusters: {e}")

    conn.close()
    
    with open("check_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Results written to check_results.txt")

if __name__ == "__main__":
    check_table_counts()
