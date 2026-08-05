"""Hon Land-only feed bot — relays new Hon Land posts to a dedicated group.

This is a second, independent bot: different bot token, different destination,
and crucially its own read cursor. It shares nothing mutable with the main
digest bot, so both can run on their own schedules without stealing each
other's unread posts.

Unlike the main digest (which truncates posts to keep the combined message
skimmable), this relays each post in full — that's the whole point of a
dedicated feed.

Run: python3 -m youtube_telegram_bot.honland_bot
"""

import logging
import os
from datetime import datetime
from typing import List

from youtube_telegram_bot import telegram_reading
from youtube_telegram_bot.config import STATE_FILE
from youtube_telegram_bot.state import load_state, save_state
from youtube_telegram_bot.telegram_posting import post_digest
from youtube_telegram_bot.telegram_reading import read_channel_posts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Second bot's own credentials and destination
HONLAND_BOT_TOKEN = os.getenv("HONLAND_BOT_TOKEN", "")
HONLAND_CHAT_ID = os.getenv("HONLAND_CHAT_ID", "")

# Separate cursor key — must NOT be the main bot's "_honland_last_id",
# otherwise whichever bot runs first would consume the other's posts
CURSOR_KEY = "_honland_feed_last_id"

# Telegram caps messages at 4096; leave headroom for markdown
CHUNK_LIMIT = 3800

# How many posts to pull per run when catching up
READ_LIMIT = 20


def split_message(text: str, limit: int = CHUNK_LIMIT) -> List[str]:
    """Split a long message into Telegram-sized chunks at line boundaries."""
    if len(text) <= limit:
        return [text]

    chunks, current, size = [], [], 0
    for line in text.split("\n"):
        if size + len(line) + 1 > limit and current:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))

    total = len(chunks)
    return [f"({i}/{total})\n{c}" if total > 1 else c for i, c in enumerate(chunks, 1)]


def format_feed(posts: List[str]) -> str:
    """Format new Hon Land posts as a standalone feed message, full text."""
    today = datetime.now().strftime("%d.%m")
    header = f"📊 *הון לנד | סקירות והחזקות* · {today}"

    # Newest last reads more naturally in a chat feed
    body = "\n\n➖➖➖\n\n".join(reversed(posts))
    return f"{header}\n\n{body}"


def run(dry_run: bool = False) -> bool:
    """
    Relay any Hon Land posts newer than this bot's cursor.

    Returns True on success (including "nothing new"), False on failure.
    """
    logger.info("=" * 60)
    logger.info("Hon Land feed bot starting")
    logger.info("=" * 60)

    if not dry_run and not (HONLAND_BOT_TOKEN and HONLAND_CHAT_ID):
        logger.error(
            "HONLAND_BOT_TOKEN / HONLAND_CHAT_ID not set — "
            "create the bot via BotFather and add both to .env"
        )
        return False

    state = load_state(STATE_FILE)
    last_id = state.get(CURSOR_KEY, 0)

    posts = read_channel_posts(limit=READ_LIMIT, dry_run=dry_run, min_id=last_id)
    logger.info(f"Found {len(posts)} new post(s) since id {last_id}")

    if not posts:
        logger.info("✓ Nothing new — no message sent")
        return True

    message = format_feed(posts)
    chunks = split_message(message)
    logger.info(f"Sending {len(message)} chars in {len(chunks)} message(s)")

    ok = True
    for chunk in chunks:
        ok = post_digest(
            chunk,
            dry_run=dry_run,
            token=HONLAND_BOT_TOKEN,
            chat_id=HONLAND_CHAT_ID,
        ) and ok

    # Advance the cursor only after a successful send, so a failed run
    # retries the same posts next time instead of dropping them
    new_max_id = telegram_reading.LAST_READ_MAX_ID
    if ok and not dry_run and new_max_id > last_id:
        state[CURSOR_KEY] = new_max_id
        save_state(state, STATE_FILE)
        logger.info(f"Cursor advanced to {new_max_id}")

    logger.info("✓ Hon Land feed sent" if ok else "✗ Hon Land feed had errors")
    return ok


if __name__ == "__main__":
    exit(0 if run() else 1)
