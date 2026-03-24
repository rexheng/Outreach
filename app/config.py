import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
GPKG_PATH = BASE_DIR / "master_lsoa.gpkg"
GPKG_LAYER = "master_lsoa"
RISK_CONFIG_PATH = BASE_DIR / "risk_config.yaml"

# Geometry simplification tolerance (degrees, after reprojection to 4326)
SIMPLIFY_TOLERANCE = 0.0005

# Columns to include in GeoJSON properties (beyond CNI fields)
DISPLAY_COLUMNS = [
    "lsoa_code",
    "lsoa_name",
    "Local Authority District name (2019)",
    "imd_score",
    "pop_density_2021",
    "total_16plus",
    "samhi_index_2022",
    "health_bad_or_very_bad_pct",
    "disability_rate_pct",
    "unpaid_care_rate_pct",
]

# Chat / LLM settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHAT_MODEL = "gemini-2.5-flash"
CHAT_MAX_TOKENS = 1500
CHAT_HISTORY_LIMIT = 10

# Policy recommendation settings
POLICY_MODEL = CHAT_MODEL  # reuse same Gemini model
POLICY_PRECOMPUTE_TEMP = 0.3
POLICY_DEEPDIVE_TEMP = 0.7
POLICY_MAX_TOKENS = 4096
POLICY_DEEPDIVE_MAX_TOKENS = 2000
POLICY_RATE_LIMIT = 20  # requests per hour per IP
POLICY_MAX_QUESTION_LEN = 1000
POLICY_SIGNALS_PATH = BASE_DIR / "policy_signals.json"
POLICY_RECS_PATH = BASE_DIR / "policy_recommendations.json"
