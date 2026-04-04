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

# Data directory — api/data/ is bundled with the serverless function
DATA_DIR = Path(__file__).resolve().parent / "data"
