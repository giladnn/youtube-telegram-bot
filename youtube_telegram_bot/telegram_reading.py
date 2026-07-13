"""Telegram channel reading using Telethon (MTProto) client."""

import logging
import os
from typing import List, Optional

try:
    from telethon.sync import TelegramClient
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    TelegramClient = None
    SessionPasswordNeededError = None

logger = logging.getLogger(__name__)

# Telethon configuration
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "-1002007708028")  # Hon Land chat ID
TELETHON_SESSION_FILE = os.getenv("TELETHON_SESSION_FILE", "telethon_session.session")

# Newest message id seen by the last read_channel_posts call (cursor for dedup)
LAST_READ_MAX_ID = 0

# Extra digest recipient (private chat), messaged from the user's own account
TELEGRAM_FORWARD_TO = os.getenv("TELEGRAM_FORWARD_TO", "")


def send_message_as_user(text: str, target_id: Optional[int] = None) -> bool:
    """
    Send a message from the user's own Telegram account (Telethon session).

    Used to forward the digest to additional private recipients the bot
    cannot reach (a bot can only DM users who /start-ed it first).

    Args:
        text: Message text to send
        target_id: Recipient user/chat id (defaults to TELEGRAM_FORWARD_TO)

    Returns:
        True if sent, False otherwise
    """
    if TelegramClient is None:
        return False

    target = int(target_id or TELEGRAM_FORWARD_TO or 0)
    if not target:
        return False

    try:
        client = TelegramClient(
            TELETHON_SESSION_FILE, int(TELEGRAM_API_ID), TELEGRAM_API_HASH
        )
        client.connect()
        # Never trigger an interactive login from an automated run
        if not client.is_user_authorized():
            logger.error("Telethon session not authorized — cannot forward digest")
            client.disconnect()
            return False
        with client:
            client.send_message(target, text)
        logger.info(f"Forwarded digest to user {target} (as personal account)")
        return True
    except Exception as e:
        logger.error(f"Failed to forward digest to {target}: {e}")
        return False


def read_channel_posts(
    limit: int = 5,
    channel_id: Optional[str] = None,
    dry_run: bool = False,
    min_id: int = 0,
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

        # Connect (reuses session if it exists; first run sends a login code
        # to the user's Telegram app and prompts for it in the terminal)
        client.start(phone=TELEGRAM_PHONE)
        with client:
            posts = []

            try:
                # Numeric IDs (e.g. -1002007708028) must be passed as int
                entity_ref = int(channel_id) if str(channel_id).lstrip("-").isdigit() else channel_id
                entity = client.get_entity(entity_ref)
                logger.debug(f"Connected to channel: {entity.title if hasattr(entity, 'title') else channel_id}")

                # Fetch latest messages
                # min_id > 0 fetches only messages newer than that id
                messages = client.get_messages(entity, limit=limit, min_id=min_id)

                # Track newest message id so callers can persist a cursor
                global LAST_READ_MAX_ID
                LAST_READ_MAX_ID = max((m.id for m in messages), default=min_id)

                # Extract text from messages, prefixed with post date
                for message in messages:
                    if message.text:
                        stamp = message.date.strftime("%d.%m") if message.date else ""
                        posts.append(f"[{stamp}] {message.text}" if stamp else message.text)

                logger.info(f"Read {len(posts)} posts from {channel_id}")
                return posts

            except Exception as e:
                logger.error(f"Error fetching messages from {channel_id}: {e}")
                return []

    except Exception as e:
        logger.error(f"Failed to connect to Telegram: {e}", exc_info=True)
        return []
