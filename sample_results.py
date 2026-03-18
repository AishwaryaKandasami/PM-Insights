import sqlite3
import json
import sys
import os

sys.path.append(os.getcwd())
from database.db import get_connection

def get_samples():
    conn = get_connection()
    cursor = conn.cursor()
    
    samples = {}
    
    # Phase 1: Normalized Review
    try:
        row = cursor.execute("""
            SELECT original_text, cleaned_text, is_supported, is_low_quality, detected_language 
            FROM reviews_normalized 
            LIMIT 1
        """).fetchone()
        if row:
            samples['Phase 1: Normalization'] = {
                'original_text': row[0][:200] + "..." if len(row[0]) > 200 else row[0],
                'cleaned_text': row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                'is_supported': row[2],
                'is_low_quality': row[3],
                'language': row[4]
            }
    except Exception as e:
        samples['Phase 1'] = f"Error: {e}"

    # Phase 2: Atom
    try:
        row = cursor.execute("""
            SELECT atom_type, title, description, product_area, severity_signal 
            FROM review_atoms 
            LIMIT 1
        """).fetchone()
        if row:
            samples['Phase 2: Extraction'] = {
                'type': row[0],
                'title': row[1],
                'description': row[2][:200] + "..." if row[2] and len(row[2]) > 200 else row[2],
                'product_area': row[3],
                'severity': row[4]
            }
    except Exception as e:
        samples['Phase 2'] = f"Error: {e}"

    # Phase 3: Bug Cluster
    try:
        row = cursor.execute("""
            SELECT cluster_label, severity, frequency, product_area 
            FROM bug_clusters 
            LIMIT 1
        """).fetchone()
        if row:
            samples['Phase 3: Bug Clustering'] = {
                'label': row[0],
                'severity': row[1],
                'frequency': row[2],
                'product_area': row[3]
            }
    except Exception as e:
        samples['Phase 3 Bug'] = f"Error: {e}"

    # Phase 3: Feature Cluster
    try:
        row = cursor.execute("""
            SELECT cluster_label, frequency, product_area 
            FROM feature_clusters 
            LIMIT 1
        """).fetchone()
        if row:
            samples['Phase 3: Feature Clustering'] = {
                'label': row[0],
                'frequency': row[1],
                'product_area': row[3] if len(row) > 3 else "N/A" # check columns
            }
    except Exception as e:
        samples['Phase 3 Feature'] = f"Error: {e}"

    conn.close()
    
    with open("samples_output.json", "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)
    print("Samples written to samples_output.json")

if __name__ == "__main__":
    get_samples()
