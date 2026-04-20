import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")

# Replicate model identifiers
ANALYSIS_MODEL = "anthropic/claude-4-sonnet"
GENERATION_MODEL = "google/nano-banana-pro"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN is not set in .env")
