"""Shared config for Vercel serverless functions."""

import os
from pathlib import Path

# Vercel injects env vars directly — no .env loading needed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
CHAT_MAX_TOKENS = 1500
CHAT_HISTORY_LIMIT = 10

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
POLICY_DEEPDIVE_MAX_TOKENS = 2000
POLICY_MAX_QUESTION_LEN = 1000
POLICY_RATE_LIMIT = 20

# Data directory — try multiple paths for Vercel compatibility
_api_dir = Path(__file__).resolve().parent
_candidates = [
    _api_dir.parent / "public" / "data",      # local dev: api/../public/data
    _api_dir / "public" / "data",              # Vercel includeFiles alongside function
    Path("/var/task/public/data"),              # Vercel absolute path
    Path("/var/task/api/public/data"),          # Vercel function-relative
]

DATA_DIR = next((p for p in _candidates if p.exists()), _candidates[0])
