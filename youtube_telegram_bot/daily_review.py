"""Daily full review — a comprehensive end-of-day recap of everything collected today.

Unlike the hourly digests (which are incremental and compact), this compiles the
complete day: every video summary in full detail (all tips, full Hebrew summary,
market data) plus all of today's Hon Land posts. Sent to the digest channel and
forwarded (in Russian) to the extra recipient.

Run: python3 -m youtube_telegram_bot.daily_review
"""

import json
import logging
from datetime import datetime
from typing import List

from youtube_telegram_bot.html_report import SUMMARIES_FILE, _load_archive, CHANNEL_LABELS
from youtube_telegram_bot.telegram_posting import post_digest
from youtube_telegram_bot.telegram_reading import read_channel_posts, send_message_as_user
from youtube_telegram_bot.summarizer import translate_to_russian

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Telegram hard limit is 4096; leave headroom for markdown expansion
CHUNK_LIMIT = 3800


def _format_video_full(entry: dict) -> str:
    """One video, full detail — no truncation."""
    lines = []
    source = CHANNEL_LABELS.get(entry.get("channel", ""), entry.get("channel", ""))
    title = entry.get("title", "")
    lines.append(f"🎬 *{source} | {title}*" if source else f"🎬 *{title}*")

    if entry.get("recommendation"):
        lines.append(f"📈 {entry['recommendation']}")

    for ticker, stats in entry.get("ticker_stats", {}).items():
        arrow = "🟢 מעל" if stats.get("above_ma") else "🔴 מתחת"
        line = f"📊 {ticker}: {stats['price']:,} · ממוצע 150: {stats['ma150']:,} ({arrow})"
        analyst = stats.get("analyst")
        if analyst:
            line += f"\n🎯 {analyst['rating']} · יעד {analyst['target_mean']:,} ({analyst['analysts']} אנליסטים)"
        lines.append(line)

    if entry.get("claim"):
        lines.append(f"💬 {entry['claim']}")

    for tip in entry.get("tips", []):
        lines.append(f"💡 {tip}")

    risk = entry.get("risk_flag", "")
    if risk and risk.lower() not in ("ללא", "none", ""):
        lines.append(f"⚠️ {risk}")

    if entry.get("hebrew_summary"):
        lines.append(f"\n📋 {entry['hebrew_summary']}")

    return "\n".join(lines)


def build_daily_review() -> str:
    """Compile the full-day review message from the archive + today's Hon Land posts."""
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_stamp = datetime.now().strftime("%d.%m")

    archive = _load_archive(SUMMARIES_FILE)
    todays_videos = [e for e in archive if e.get("date") == today_iso]

    # All of today's Hon Land posts (fetch a generous window, filter by date prefix)
    posts = read_channel_posts(limit=30)
    todays_posts = [p for p in posts if p.startswith(f"[{today_stamp}]")]

    sections = [f"🌙 *סקירה יומית מלאה* · {today_stamp}"]

    if todays_videos:
        sections.append(f"\n━━━ 📺 סרטונים ({len(todays_videos)}) ━━━")
        for entry in todays_videos:
            sections.append("\n" + _format_video_full(entry))
    else:
        sections.append("\n📺 לא פורסמו סרטונים חדשים היום")

    if todays_posts:
        sections.append(f"\n━━━ 📊 הון לנד | סקירות והחזקות ({len(todays_posts)}) ━━━")
        for p in todays_posts:
            sections.append(f"\n• {p}")
    else:
        sections.append("\n📊 אין פוסטים חדשים היום בהון לנד")

    return "\n".join(sections)


def split_message(text: str, limit: int = CHUNK_LIMIT) -> List[str]:
    """Split a long message into Telegram-sized chunks at line boundaries."""
    if len(text) <= limit:
        return [text]

    chunks, current = [], []
    size = 0
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


def main() -> bool:
    review = build_daily_review()
    chunks = split_message(review)
    logger.info(f"Daily review: {len(review)} chars in {len(chunks)} message(s)")

    ok = True
    for chunk in chunks:
        ok = post_digest(chunk) and ok

    # Russian copy for the extra recipient. Translate the WHOLE review first,
    # then split — Russian runs ~25% longer than Hebrew, so splitting before
    # translation can push chunks past Telegram's 4096-char limit
    russian = translate_to_russian(review)
    for chunk in split_message(russian):
        send_message_as_user(chunk)

    logger.info("✓ Daily review sent" if ok else "✗ Daily review had errors")
    return ok


if __name__ == "__main__":
    exit(0 if main() else 1)
