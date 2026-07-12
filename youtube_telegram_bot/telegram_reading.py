"""Telegram channel reading using Telethon (MTProto) client."""

import logging
import os
from typing import List, Optional

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    TelegramClient = None
    SessionPasswordNeededError = None

logger = logging.getLogger(__name__)

# Telethon configuration
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "hon_land")  # Channel username
TELETHON_SESSION_FILE = os.getenv("TELETHON_SESSION_FILE", "telethon_session.session")


def read_channel_posts(
    limit: int = 5,
    channel_id: Optional[str] = None,
    dry_run: bool = False,
) -> List[str]:
    """
    Read latest posts from a Telegram channel using Telethon.

    Args:
        limit: Maximum number of posts to read (default: 5)
        channel_id: Telegram channel ID or username (uses env var if None)
        dry_run: If True, return mock data (for testing)

    Returns:
        List of post text strings
    """
    if dry_run:
        logger.info("DRY RUN: Returning mock channel posts")
        return [
            "Mock post 1: TEVA stock news",
            "Mock post 2: Market update",
        ]

    if TelegramClient is None:
        logger.error("Telethon library not installed")
        return []

    channel_id = channel_id or TELEGRAM_CHANNEL_ID

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.error("TELEGRAM_API_ID or TELEGRAM_API_HASH not set")
        return []

    try:
        # Create Telethon client
        client = TelegramClient(
            TELETHON_SESSION_FILE,
            int(TELEGRAM_API_ID),
            TELEGRAM_API_HASH,
        )

        # Connect (will reuse session if it exists)
        with client:
            posts = []

            try:
                # Get channel entity
                entity = client.get_entity(channel_id)
                logger.debug(f"Connected to channel: {entity.title if hasattr(entity, 'title') else channel_id}")

                # Fetch latest messages
                messages = client.get_messages(entity, limit=limit)

                # Extract text from messages
                for message in messages:
                    if message.text:
                        posts.append(message.text)

                logger.info(f"Read {len(posts)} posts from {channel_id}")
                return posts

            except Exception as e:
                logger.error(f"Error fetching messages from {channel_id}: {e}")
                return []

    except Exception as e:
        logger.error(f"Failed to connect to Telegram: {e}", exc_info=True)
        return []
