import sys
import sqlite3
sys.path.append('.')

from config.settings import DB_PATH
from agent.clustering_orchestrator import run_clustering

def get_latest_run_id():
    """Fetch the breakdown run_id that has the most atoms loaded."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Find run_id with the most atoms, or the most recent pipeline run
    cursor.execute('''
        SELECT run_id 
        FROM pipeline_runs 
        ORDER BY started_at DESC LIMIT 1
    ''')
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

if __name__ == "__main__":
    run_id = get_latest_run_id()
    if not run_id:
        print("No run_id found with extracted atoms!")
        sys.exit(1)
        
    print(f"Starting Phase 3: Adaptive Clustering for Run ID: {run_id}")
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        results = run_clustering(run_id)
        print("\n--- Clustering Complete ---")
        print(f"Bug Clusters: {results.get('bug_clusters')} ({results.get('bug_flagged')} flagged)")
        print(f"Feature Clusters: {results.get('feature_clusters')} ({results.get('feature_flagged')} flagged)")
    except Exception as e:
         print(f"Clustering failed: {e}")
