"""Main entry point for YouTube Telegram Bot.

Usage:
    python -m youtube_telegram_bot.main
"""

import logging
import requests
from typing import List, Dict, Any

from youtube_telegram_bot.config import CHANNELS, RSS_FEED_URL, STATE_FILE, DEBUG
from youtube_telegram_bot.youtube_rss import parse_rss_xml, extract_video_ids
from youtube_telegram_bot.state import (
    load_state,
    save_state,
    is_video_seen,
    mark_video_seen,
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_rss_feed(channel_id: str) -> str:
    """
    Fetch YouTube RSS feed for a channel.

    Args:
        channel_id: YouTube channel ID

    Returns:
        Raw RSS XML content

    Raises:
        requests.RequestException: If RSS fetch fails
    """
    url = RSS_FEED_URL.format(channel_id=channel_id)
    logger.debug(f"Fetching RSS from {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def _detect_new_videos(
    videos: List[Dict[str, str]], state: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Detect which videos are new (not in state).

    Marks detected videos as seen in the state.

    Args:
        videos: List of videos from RSS feed
        state: Current state dictionary (modified in place)

    Returns:
        List of new videos only
    """
    new_videos = []
    for video in videos:
        video_id = video["id"]
        if not is_video_seen(video_id, state):
            new_videos.append(video)
            mark_video_seen(video_id, state)
    return new_videos


def poll_channel(
    channel_name: str, channel_id: str, state: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Poll a single YouTube channel for new videos.

    Args:
        channel_name: Human-readable channel name
        channel_id: YouTube channel ID
        state: Current state dictionary (modified in place)

    Returns:
        List of new videos detected
    """
    new_videos = []
    try:
        rss_content = fetch_rss_feed(channel_id)
        root = parse_rss_xml(rss_content)
        videos = extract_video_ids(root)
        logger.info(f"Channel {channel_name}: Found {len(videos)} videos")

        new_videos = _detect_new_videos(videos, state)
        for video in new_videos:
            video["channel"] = channel_name
            logger.info(f"New video: {video['title']} ({video['id']})")

    except requests.RequestException as e:
        logger.error(f"Failed to fetch RSS for {channel_name}: {e}")
    except Exception as e:
        logger.error(f"Error processing {channel_name}: {e}")

    return new_videos


def main() -> List[Dict[str, str]]:
    """
    Main polling loop.

    Polls all configured YouTube channels for new videos,
    detects videos not yet seen, and updates state.

    Returns:
        List of all new videos detected across all channels
    """
    logger.info("Starting YouTube polling")

    # Load current state
    state = load_state(STATE_FILE)
    logger.debug(f"Loaded state with {len(state)} seen videos")

    all_new_videos = []

    # Poll each channel
    for channel_name, channel_id in CHANNELS.items():
        logger.info(f"Polling channel: {channel_name}")
        new_videos = poll_channel(channel_name, channel_id, state)
        all_new_videos.extend(new_videos)

    # Save updated state
    save_state(state, STATE_FILE)
    logger.debug(f"Saved state with {len(state)} total seen videos")

    # Log summary
    logger.info(f"Polling complete. Found {len(all_new_videos)} new videos")

    return all_new_videos


if __name__ == "__main__":
    main()
