"""Format digest messages for Telegram with emoji sections."""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Telegram limits for context
TELEGRAM_MESSAGE_LIMIT = 4096
POST_TRUNCATE_LENGTH = 200
MAX_CHANNEL_POSTS = 5


def _format_video_entry(video: Dict[str, Any]) -> str:
    """
    Format a single video entry.

    Args:
        video: Video dictionary with title, tickers, claim, recommendation, risk_flag

    Returns:
        Formatted video entry string
    """
    parts = []

    title = video.get("title", "Unknown")
    tickers = video.get("tickers", [])
    claim = video.get("claim", "")
    recommendation = video.get("recommendation", "")
    risk_flag = video.get("risk_flag", "")

    # Title (bold)
    parts.append(f"*{title}*")

    # Tickers
    ticker_str = ", ".join(tickers) if tickers else "N/A"
    parts.append(f"🎫 Tickers: {ticker_str}")

    # Claim (if present)
    if claim:
        parts.append(f"💬 {claim}")

    # Recommendation (if present)
    if recommendation:
        parts.append(f"📈 Rec: {recommendation}")

    # Risk flag (if present and not empty)
    if risk_flag and risk_flag.lower() not in ("ללא", "none", ""):
        parts.append(f"⚠️ Risk: {risk_flag}")

    return "\n".join(parts)


def format_digest(videos: List[Dict[str, Any]], channel_posts: List[str]) -> str:
    """
    Format a digest message combining YouTube videos and Telegram channel posts.

    Args:
        videos: List of video dicts with title, tickers, claim, recommendation, risk_flag
        channel_posts: List of channel post strings

    Returns:
        Formatted digest message (Telegram-compatible markdown)
    """
    lines = []

    # Header with timestamp context
    lines.append("📺 *Daily Investment Digest*")
    lines.append("(8:00 AM IST)")
    lines.append("")

    # YouTube videos section
    if videos:
        lines.append("📹 *New Videos* ({} video{})".format(
            len(videos), "s" if len(videos) > 1 else ""
        ))
        lines.append("")

        for video in videos:
            lines.append(_format_video_entry(video))
            lines.append("")

    else:
        lines.append("📹 *New Videos*")
        lines.append("No new videos today")
        lines.append("")

    # Channel posts section
    if channel_posts:
        lines.append("💬 *Channel Updates* ({} post{})".format(
            len(channel_posts), "s" if len(channel_posts) > 1 else ""
        ))
        lines.append("")

        for i, post in enumerate(channel_posts[:MAX_CHANNEL_POSTS], 1):
            # Truncate long posts
            post_text = post[:POST_TRUNCATE_LENGTH]
            if len(post) > POST_TRUNCATE_LENGTH:
                post_text += "…"

            lines.append(f"{i}. {post_text}")

        lines.append("")

    else:
        lines.append("💬 *Channel Updates*")
        lines.append("No new posts")
        lines.append("")

    # Footer
    lines.append("_Automated digest • No action required_")

    digest = "\n".join(lines)

    # Warn if message is too long for Telegram
    if len(digest) > TELEGRAM_MESSAGE_LIMIT:
        logger.warning(
            f"Digest message is {len(digest)} chars, exceeds Telegram limit of {TELEGRAM_MESSAGE_LIMIT}"
        )

    return digest
