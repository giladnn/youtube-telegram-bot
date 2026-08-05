"""YouTube Telegram Bot - Israeli market intelligence summarizer."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root so credentials are available no matter
# which module is imported first
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

__version__ = "0.1.0"
