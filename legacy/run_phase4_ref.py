import sys
import os

sys.path.append(os.getcwd())
from agent.artifact_orchestrator import run_artifacts

def main():
    # Use the run_id from our previous analysis
    run_id = "20260309041447_516de1cc"
    print(f"Starting Phase 4 for run_id: {run_id}")
    
    try:
        result = run_artifacts(run_id)
        print("\n✅ Phase 4 completed successfully!")
        print("\nArtifact Generation Summary:")
        print(f"  - Bug Triage Rows: {result.get('triage_rows')}")
        print(f"  - Bug Triage CSV: {result.get('triage_csv')}")
        print(f"  - Feature Request Rows: {result.get('feature_rows')}")
        print(f"  - Feature Request CSV: {result.get('feature_csv')}")
        print(f"  - RICE Input Rows: {result.get('rice_rows')}")
        print(f"  - RICE Input CSV: {result.get('rice_csv')}")
        print(f"  - Executive Summary MD: {result.get('summary_md')}")
        
    except Exception as e:
        print(f"\n❌ Phase 4 Artifact Generation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
