"""Format digest messages for Telegram — compact, Hebrew-first, skimmable."""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Telegram limits for context
TELEGRAM_MESSAGE_LIMIT = 4096
POST_TRUNCATE_LENGTH = 200
MAX_CHANNEL_POSTS = 5
CLAIM_TRUNCATE_LENGTH = 150

# Human-readable Hebrew labels for source channels
CHANNEL_LABELS = {
    "Micha.Stocks": "מיכה סטוקס",
    "guynatan9": "גיא נתן",
}


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit, appending ellipsis if cut."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _format_video_entry(video: Dict[str, Any]) -> str:
    """
    Format a single video as a compact 2-3 line entry.

    Line 1: bold title
    Line 2: tickers + recommendation on one line
    Line 3: claim (one sentence)
    Line 4: risk flag, only if meaningful

    Args:
        video: Video dictionary with title, tickers, claim, recommendation, risk_flag

    Returns:
        Formatted video entry string
    """
    parts = []

    title = video.get("title", "")
    channel = video.get("channel", "")
    tickers = video.get("tickers", [])
    claim = video.get("claim", "")
    recommendation = video.get("recommendation", "")
    risk_flag = video.get("risk_flag", "")

    source = CHANNEL_LABELS.get(channel, channel)
    if source:
        parts.append(f"🎬 *{source} | {title}*")
    else:
        parts.append(f"🎬 *{title}*")

    # Tickers + recommendation combined into one line
    meta_line = []
    if tickers:
        meta_line.append(" ".join(f"`{t}`" for t in tickers))
    if recommendation:
        meta_line.append(f"📈 {_truncate(recommendation, CLAIM_TRUNCATE_LENGTH)}")
    if meta_line:
        parts.append(" · ".join(meta_line))

    if claim:
        parts.append(f"💬 {_truncate(claim, CLAIM_TRUNCATE_LENGTH)}")

    if risk_flag and risk_flag.lower() not in ("ללא", "none", ""):
        parts.append(f"⚠️ {_truncate(risk_flag, CLAIM_TRUNCATE_LENGTH)}")

    return "\n".join(parts)


def format_digest(videos: List[Dict[str, Any]], channel_posts: List[str]) -> str:
    """
    Format a compact digest combining YouTube videos and Telegram channel posts.

    Empty sections are omitted entirely — no "no new videos" boilerplate.

    Args:
        videos: List of video dicts with title, tickers, claim, recommendation, risk_flag
        channel_posts: List of channel post strings

    Returns:
        Formatted digest message (Telegram-compatible markdown)
    """
    today = datetime.now().strftime("%d.%m")
    lines = [f"📺 *דייג'סט בוקר* · {today}"]

    if videos:
        for video in videos:
            lines.append("")
            lines.append(_format_video_entry(video))

    if channel_posts:
        lines.append("")
        lines.append("📊 *הון לנד | סקירות והחזקות*")
        for post in channel_posts[:MAX_CHANNEL_POSTS]:
            lines.append(f"• {_truncate(post, POST_TRUNCATE_LENGTH)}")

    if not videos and not channel_posts:
        lines.append("אין עדכונים חדשים היום 🤷")

    digest = "\n".join(lines)

    # Warn if message is too long for Telegram
    if len(digest) > TELEGRAM_MESSAGE_LIMIT:
        logger.warning(
            f"Digest message is {len(digest)} chars, exceeds Telegram limit of {TELEGRAM_MESSAGE_LIMIT}"
        )

    return digest
