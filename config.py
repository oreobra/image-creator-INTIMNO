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

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN is not set in .env")
