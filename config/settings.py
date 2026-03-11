import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parents[1]

# Paths
DB_PATH = BASE_DIR / "database" / "pm_insights.db"
RAW_DATA_PATH = BASE_DIR / "data" / "raw"
OUTPUT_PATH = BASE_DIR / "outputs"

# Scraper defaults
DEFAULT_APP_ID = "com.spotify.music"
DEFAULT_MAX_REVIEWS = 10000
DEFAULT_MONTHS_BACK = 3
DEFAULT_LANG = "en"
DEFAULT_COUNTRY = "us"
SCRAPER_BATCH_SIZE = 200
SCRAPER_BASE_DELAY = 2
SCRAPER_MAX_JITTER = 1

# Phase 2 — model config
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_PRO_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "text-embedding-004"

# Token limits
MAX_TOKENS_PER_REVIEW = 512
BATCH_SIZE = 50

# Rate limits
REQUESTS_PER_MINUTE = 15
MIN_DELAY_SECONDS = 4

# Clustering
COSINE_DISTANCE_THRESHOLD = 0.25

# Evaluation thresholds
SEVERITY_DRIFT_THRESHOLD = 0.10
CLUSTER_COUNT_DRIFT_THRESHOLD = 0.20

# API keys / secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

