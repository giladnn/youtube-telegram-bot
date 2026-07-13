"""Orchestrator for YouTube→Telegram summarizer bot (Unit 3.3).

Ties together all prior units:
- Unit 2.0: YouTube RSS polling (main.py)
- Unit 2.1: Transcript extraction (transcript.py)
- Unit 2.2: Summarization (summarizer.py)
- Unit 3.3: Telegram posting and channel reading (this module)

Daily workflow:
1. Poll YouTube channels for new videos
2. Extract transcript for each video
3. Summarize transcript using Gemini
4. Read latest posts from Telegram channel
5. Format combined digest
6. Post digest to Telegram group
"""

import logging
import os
from typing import List, Dict, Any, Optional

from youtube_telegram_bot.main import main as poll_youtube
from youtube_telegram_bot.transcript import extract_transcript
from youtube_telegram_bot.summarizer import summarize_transcript
from youtube_telegram_bot.telegram_posting import post_digest
from youtube_telegram_bot.telegram_reading import read_channel_posts
from youtube_telegram_bot.message_formatter import format_digest
from youtube_telegram_bot.html_report import (
    archive_summaries,
    generate_html,
    generate_markdown_files,
)
from youtube_telegram_bot.market_data import enrich_tickers

# Setup logging
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_bot(dry_run: bool = False) -> bool:
    """
    Run the complete bot orchestration pipeline.

    Workflow:
    1. Poll YouTube channels for new videos
    2. Extract and summarize each video
    3. Read latest Telegram channel posts
    4. Format combined digest
    5. Post to Telegram group

    Args:
        dry_run: If True, don't actually post to Telegram (for testing)

    Returns:
        True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("Starting YouTube→Telegram bot orchestration")
    if dry_run:
        logger.info("[DRY RUN MODE - No data will be posted]")
    logger.info("=" * 60)

    try:
        # Step 1: Poll YouTube for new videos
        logger.info("Step 1/5: Polling YouTube channels")
        new_videos = poll_youtube()
        logger.info(f"  Found {len(new_videos)} new video(s)")

        # Step 2: Process each video
        logger.info("Step 2/5: Processing videos (extract + summarize)")
        processed_videos = []
        errors = []

        for idx, video in enumerate(new_videos, 1):
            video_id = video.get("id", "unknown")
            title = video.get("title", "Unknown")
            logger.debug(f"  [{idx}/{len(new_videos)}] Processing: {title}")

            try:
                # Extract transcript
                transcript = extract_transcript(video_id)
                if not transcript:
                    logger.warning(f"    ⚠ No transcript available for: {title}")
                    errors.append((video_id, title, "No transcript"))
                    continue

                # Summarize transcript
                summary = summarize_transcript(transcript, title)
                if summary.get("error"):
                    error_msg = summary["error"]
                    logger.warning(f"    ⚠ Summarization error for {title}: {error_msg}")
                    errors.append((video_id, title, error_msg))
                    continue

                # Combine video info with summary
                video_data = {
                    "id": video_id,
                    "title": title,
                    "channel": video.get("channel", ""),
                    "tickers": summary.get("tickers", []),
                    "claim": summary.get("claim", ""),
                    "recommendation": summary.get("recommendation", ""),
                    "risk_flag": summary.get("risk_flag", ""),
                    "tips": summary.get("tips", []),
                    "hebrew_summary": summary.get("hebrew_summary", ""),
                    # Live price + 150-day moving average per ticker
                    "ticker_stats": enrich_tickers(summary.get("tickers", [])),
                }
                processed_videos.append(video_data)
                logger.info(f"    ✓ Processed: {title}")

            except Exception as e:
                logger.error(f"    ✗ Unexpected error processing {title}: {e}")
                errors.append((video_id, title, str(e)))
                continue

        logger.info(f"  Result: {len(processed_videos)} processed, {len(errors)} skipped")
        for _vid, title, error in errors[:3]:  # Log first 3 errors
            logger.debug(f"    Skipped '{title}': {error}")

        # Un-mark videos that must be re-picked-up by the next real run:
        # failed ones (retry), and in dry-run mode ALL new videos —
        # a dry run must never consume a video's "newness"
        unmark_ids = [vid for vid, _t, _e in errors]
        if dry_run:
            unmark_ids = [v.get("id") for v in new_videos]
        if unmark_ids:
            try:
                from youtube_telegram_bot.state import load_state, save_state
                from youtube_telegram_bot.config import STATE_FILE

                state = load_state(STATE_FILE)
                for vid in unmark_ids:
                    state.pop(vid, None)
                save_state(state, STATE_FILE)
                logger.info(f"  Unmarked {len(unmark_ids)} video(s) for next real run")
            except Exception as e:
                logger.warning(f"  ⚠ Could not unmark videos: {e}")

        # Archive summaries, refresh the HTML report + markdown knowledge base
        if processed_videos and not dry_run:
            try:
                archive_summaries(processed_videos)
                generate_html()
                generate_markdown_files()
            except Exception as e:
                logger.warning(f"  ⚠ Failed to update HTML/markdown reports: {e}")

        # Step 3: Read Telegram channel posts (only ones newer than last digest)
        logger.info("Step 3/5: Reading Telegram channel posts")
        from youtube_telegram_bot import telegram_reading
        from youtube_telegram_bot.state import load_state, save_state
        from youtube_telegram_bot.config import STATE_FILE

        state = load_state(STATE_FILE)
        last_post_id = state.get("_honland_last_id", 0)
        channel_posts = read_channel_posts(limit=10, dry_run=dry_run, min_id=last_post_id)
        logger.info(f"  Read {len(channel_posts)} new post(s) since id {last_post_id}")

        # Persist cursor so already-sent posts are never repeated
        new_max_id = telegram_reading.LAST_READ_MAX_ID
        if not dry_run and new_max_id > last_post_id:
            state["_honland_last_id"] = new_max_id
            save_state(state, STATE_FILE)

        # Nothing new anywhere → skip posting (lets the bot run hourly without spam)
        if not processed_videos and not channel_posts:
            logger.info("Nothing new since last digest — skipping post")
            logger.info("=" * 60)
            logger.info("✓ Bot orchestration COMPLETED (no new content)")
            logger.info("=" * 60)
            return True

        # Step 4: Format digest
        logger.info("Step 4/5: Formatting digest message")
        digest_message = format_digest(processed_videos, channel_posts)
        logger.info(f"  Digest size: {len(digest_message)} chars")
        logger.debug(f"  Message preview:\n{digest_message[:200]}...")

        # Step 5: Post to Telegram
        logger.info("Step 5/5: Posting digest to Telegram")
        success = post_digest(digest_message, dry_run=dry_run)

        # Also send the digest to extra private recipients (e.g. אבא),
        # from the user's own account since the bot can't DM them.
        # אבא reads Russian, so his copy is translated first.
        if success and not dry_run:
            from youtube_telegram_bot.telegram_reading import send_message_as_user
            from youtube_telegram_bot.summarizer import translate_to_russian
            send_message_as_user(translate_to_russian(digest_message))

        # Final summary
        logger.info("=" * 60)
        if success:
            logger.info("✓ Bot orchestration COMPLETED SUCCESSFULLY")
        else:
            logger.warning("✗ Bot orchestration completed with errors")
        logger.info("=" * 60)

        return success

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ FATAL ERROR: {e}", exc_info=True)
        logger.error("=" * 60)
        return False


if __name__ == "__main__":
    # Run bot when executed directly
    success = run_bot(dry_run=False)
    exit(0 if success else 1)
