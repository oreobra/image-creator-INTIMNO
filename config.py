import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")

# Replicate model identifiers
# ANALYSIS_MODEL (Sonnet) — used only where creative/analytical quality directly drives image quality:
#   composing the actual generation prompts (reference/describe/style).
# FAST_MODEL (Haiku) — used for short, low-stakes text tasks: panties count/material read-off,
#   short prop descriptions, feedback summarization. Same request shape as ANALYSIS_MODEL, much cheaper.
ANALYSIS_MODEL = "anthropic/claude-4-sonnet"
FAST_MODEL = "anthropic/claude-4.5-haiku"
GENERATION_MODEL = "google/nano-banana-pro"

# Persistent storage for learned feedback notes (mount a volume onto its parent dir)
NOTES_FILE_PATH: str = os.getenv("NOTES_FILE_PATH", "/app/data/feedback_notes.json")
MAX_FEEDBACK_NOTES: int = int(os.getenv("MAX_FEEDBACK_NOTES", "20"))

# Catalog (Google Sheets CSV export — public, no auth required)
CATALOG_SHEET_URL: str = os.getenv(
    "CATALOG_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1-8tNEZAbCycpJvjKATQgMvvTcG8P4cA6AT_D9jg-gW0/export?format=csv&gid=0",
)
CATALOG_CACHE_PATH: str = os.getenv("CATALOG_CACHE_PATH", "/app/data/catalog_cache.json")
CATALOG_REFRESH_INTERVAL_DAYS: int = int(os.getenv("CATALOG_REFRESH_INTERVAL_DAYS", "7"))

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN is not set in .env")
