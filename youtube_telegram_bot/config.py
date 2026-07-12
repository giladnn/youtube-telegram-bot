"""Configuration for YouTube Telegram Bot."""

import os
from pathlib import Path

# YouTube channel IDs
CHANNELS = {
    "Micha.Stocks": "UCi0TGNL1I3ByW2t3hDJlsmQ",
    "guynatan9": "UCRbPjQKjDkOWKM1TM4-lsqQ",
}

# RSS feed base URL
RSS_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# State file path (default: state.json in current working directory)
STATE_FILE = os.getenv("STATE_FILE", "state.json")

# Logging
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
