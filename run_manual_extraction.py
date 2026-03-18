import sys
import logging
from agent.orchestrator import run_extraction

# Configure logging to print everything to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

RUN_ID = "20260309041447_516de1cc"

print(f"Starting manual extraction for {RUN_ID}...")
try:
    # run_extraction will process all remaining or usable reviews
    # sample_limit=None uses the full set
    result = run_extraction(RUN_ID, sample_limit=None)
    print("\nExtraction Success Summary:")
    print(result)
except Exception as e:
    print(f"\nExtraction CRASHED with error: {e}")
    sys.exit(1)
