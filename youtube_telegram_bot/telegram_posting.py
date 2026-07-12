"""Telegram Bot API wrapper for posting digests to chat."""

import logging
import os
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# Telegram Bot API configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003772028678")  # "Morning digest" channel
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_API_TIMEOUT = 10


def _validate_prerequisites() -> Optional[str]:
    """
    Validate that all prerequisites for posting are met.

    Returns:
        Error message if validation fails, None if all checks pass
    """
    if not TELEGRAM_BOT_TOKEN:
        return "TELEGRAM_BOT_TOKEN not set in environment"

    if requests is None:
        return "requests library not installed"

    if not TELEGRAM_CHAT_ID:
        return "TELEGRAM_CHAT_ID not set in environment"

    return None


def post_digest(digest_message: str, dry_run: bool = False) -> bool:
    """
    Post a digest message to Telegram group chat.

    Args:
        digest_message: Formatted digest message to post
        dry_run: If True, don't actually post (for testing)

    Returns:
        True if successful, False otherwise
    """
    if not digest_message or not digest_message.strip():
        logger.warning("Empty digest message, not posting")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would post {len(digest_message)} chars to Telegram chat {TELEGRAM_CHAT_ID}")
        return True

    # Validate prerequisites
    validation_error = _validate_prerequisites()
    if validation_error:
        logger.error(validation_error)
        return False

    try:
        url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": digest_message,
            "parse_mode": "Markdown",
        }

        logger.debug(f"Posting {len(digest_message)} chars to Telegram")
        response = requests.post(
            url,
            json=payload,
            timeout=TELEGRAM_API_TIMEOUT,
        )

        # Check for API errors
        if response.status_code != 200:
            error_msg = f"Telegram API returned {response.status_code}"
            try:
                error_json = response.json()
                if "description" in error_json:
                    error_msg = error_json["description"]
            except Exception:
                pass

            logger.error(f"Failed to post to Telegram: {error_msg}")
            return False

        logger.info(f"Successfully posted digest to Telegram (chat {TELEGRAM_CHAT_ID})")
        return True

    except requests.Timeout:
        logger.error("Telegram API request timed out")
        return False
    except requests.ConnectionError:
        logger.error("Connection error when posting to Telegram")
        return False
    except requests.RequestException as e:
        logger.error(f"Telegram API request failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error posting to Telegram: {e}", exc_info=True)
        return False
