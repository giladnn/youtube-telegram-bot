"""Configuration for YouTube Telegram Bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (parent of this package)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# YouTube channel IDs
CHANNELS = {
    "Micha.Stocks": "UCSxjNbPriyBh9RNl_QNSAtw",
    "guynatan9": "UCJww92D4haH3uolAWiLIFRw",
}

# RSS feed base URL
RSS_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# State file path (default: state.json in current working directory)
STATE_FILE = os.getenv("STATE_FILE", "state.json")

# Logging
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
