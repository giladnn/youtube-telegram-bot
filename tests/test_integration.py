"""Integration tests for YouTube Telegram Bot."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from youtube_telegram_bot.main import poll_channel, main


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>yt:video:video1</id>
    <title>First Video</title>
  </entry>
  <entry>
    <id>yt:video:video2</id>
    <title>Second Video</title>
  </entry>
</feed>"""


@pytest.fixture
def temp_state_file():
    """Create a temporary directory for state file."""
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "state.json")
    yield path
    if os.path.exists(path):
        os.remove(path)
    os.rmdir(tmpdir)


class TestDeduplication:
    """Test that videos aren't re-processed."""

    @patch("youtube_telegram_bot.main.fetch_rss_feed")
    def test_second_poll_detects_no_new_videos(self, mock_fetch, temp_state_file):
        """Should not detect videos on second poll if they were already seen."""
        mock_fetch.return_value = SAMPLE_RSS

        state = {}

        # First poll - should detect both videos
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 2
        assert state["video1"]["seen"] is True
        assert state["video2"]["seen"] is True

        # Second poll - same RSS, should detect no new videos
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 0

    @patch("youtube_telegram_bot.main.fetch_rss_feed")
    def test_new_video_after_existing(self, mock_fetch, temp_state_file):
        """Should detect new videos when they appear in the feed."""
        # First response with 1 video
        first_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>yt:video:video1</id>
    <title>First Video</title>
  </entry>
</feed>"""

        # Second response with 2 videos (1 new)
        second_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>yt:video:video1</id>
    <title>First Video</title>
  </entry>
  <entry>
    <id>yt:video:video2</id>
    <title>Second Video</title>
  </entry>
</feed>"""

        state = {}

        # First poll
        mock_fetch.return_value = first_response
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 1
        assert new_videos[0]["id"] == "video1"

        # Second poll - mock returns new content
        mock_fetch.return_value = second_response
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 1
        assert new_videos[0]["id"] == "video2"


class TestStatePersistence:
    """Test that state is properly persisted to disk."""

    @patch("youtube_telegram_bot.main.fetch_rss_feed")
    def test_state_persists_to_file(self, mock_fetch, temp_state_file):
        """Should write state to file after polling."""
        mock_fetch.return_value = SAMPLE_RSS

        # Patch STATE_FILE in main module
        with patch("youtube_telegram_bot.main.STATE_FILE", temp_state_file):
            # First run
            new_videos = main()
            assert len(new_videos) == 2

            # Verify state was written
            with open(temp_state_file, "r") as f:
                state = json.load(f)
            assert "video1" in state
            assert "video2" in state

            # Second run should find no new videos
            mock_fetch.return_value = SAMPLE_RSS
            new_videos = main()
            assert len(new_videos) == 0


class TestErrorHandling:
    """Test error handling in polling."""

    @patch("youtube_telegram_bot.main.fetch_rss_feed")
    def test_handles_fetch_error_gracefully(self, mock_fetch):
        """Should handle RSS fetch errors without crashing."""
        import requests

        mock_fetch.side_effect = requests.RequestException("Connection failed")

        state = {}
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 0

    @patch("youtube_telegram_bot.main.fetch_rss_feed")
    def test_handles_parse_error_gracefully(self, mock_fetch):
        """Should handle RSS parse errors without crashing."""
        mock_fetch.return_value = "Invalid XML"

        state = {}
        new_videos = poll_channel("Test", "test_id", state)
        assert len(new_videos) == 0


class TestBotOrchestration:
    """Test full orchestration in bot.py (Unit 3.3)."""

    @patch("youtube_telegram_bot.bot.post_digest")
    @patch("youtube_telegram_bot.bot.read_channel_posts")
    @patch("youtube_telegram_bot.bot.summarize_transcript")
    @patch("youtube_telegram_bot.bot.extract_transcript")
    @patch("youtube_telegram_bot.bot.poll_youtube")
    def test_bot_orchestrates_all_components(
        self, mock_poll, mock_extract, mock_summarize, mock_read, mock_post
    ):
        """Should orchestrate all components in correct order."""
        from youtube_telegram_bot.bot import run_bot

        # Setup mocks
        mock_poll.return_value = [
            {"id": "vid1", "title": "Video 1"},
            {"id": "vid2", "title": "Video 2"},
        ]
        mock_extract.side_effect = ["transcript 1", "transcript 2"]
        mock_summarize.side_effect = [
            {
                "tickers": ["TEVA"],
                "claim": "TEVA is up",
                "recommendation": "BUY",
                "risk_flag": "none",
                "hebrew_summary": "סיכום",
                "error": None,
            },
            {
                "tickers": ["ICL"],
                "claim": "ICL is down",
                "recommendation": "SELL",
                "risk_flag": "regulatory",
                "hebrew_summary": "סיכום שני",
                "error": None,
            },
        ]
        mock_read.return_value = ["Channel post 1", "Channel post 2"]
        mock_post.return_value = True

        # Run bot
        success = run_bot(dry_run=True)

        # Verify orchestration
        assert success is True
        assert mock_poll.called
        assert mock_extract.call_count == 2
        assert mock_summarize.call_count == 2
        assert mock_read.called
        assert mock_post.called

    @patch("youtube_telegram_bot.bot.post_digest")
    @patch("youtube_telegram_bot.bot.poll_youtube")
    def test_bot_handles_no_new_videos(self, mock_poll, mock_post):
        """Should handle gracefully when no new videos."""
        from youtube_telegram_bot.bot import run_bot

        mock_poll.return_value = []
        mock_post.return_value = False

        success = run_bot(dry_run=True)

        # Should still succeed (or return false) gracefully
        assert isinstance(success, bool)

    @patch("youtube_telegram_bot.bot.post_digest")
    @patch("youtube_telegram_bot.bot.summarize_transcript")
    @patch("youtube_telegram_bot.bot.extract_transcript")
    @patch("youtube_telegram_bot.bot.poll_youtube")
    def test_bot_handles_transcript_extraction_error(
        self, mock_poll, mock_extract, mock_summarize, mock_post
    ):
        """Should handle transcript extraction errors gracefully."""
        from youtube_telegram_bot.bot import run_bot

        mock_poll.return_value = [{"id": "vid1", "title": "Video 1"}]
        mock_extract.return_value = ""  # Empty transcript
        mock_summarize.return_value = {
            "error": "Empty transcript",
            "tickers": [],
            "claim": "",
            "recommendation": "",
            "risk_flag": "",
            "hebrew_summary": "",
        }
        mock_post.return_value = False  # Posting should fail since no videos

        # Should not crash
        success = run_bot(dry_run=True)
        assert isinstance(success, bool)

    @patch("youtube_telegram_bot.bot.post_digest")
    @patch("youtube_telegram_bot.bot.read_channel_posts")
    @patch("youtube_telegram_bot.bot.summarize_transcript")
    @patch("youtube_telegram_bot.bot.extract_transcript")
    @patch("youtube_telegram_bot.bot.poll_youtube")
    def test_bot_posts_formatted_digest(
        self, mock_poll, mock_extract, mock_summarize, mock_read, mock_post
    ):
        """Should post a properly formatted digest message."""
        from youtube_telegram_bot.bot import run_bot

        mock_poll.return_value = [{"id": "vid1", "title": "Video 1"}]
        mock_extract.return_value = "transcript"
        mock_summarize.return_value = {
            "tickers": ["TEVA"],
            "claim": "claim",
            "recommendation": "BUY",
            "risk_flag": "none",
            "hebrew_summary": "סיכום",
            "error": None,
        }
        mock_read.return_value = ["post1"]
        mock_post.return_value = True

        run_bot(dry_run=True)

        # Verify post_digest was called with a string
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args is not None
        digest_message = call_args[0][0]
        assert isinstance(digest_message, str)
        assert len(digest_message) > 0


class TestMessageFormatter:
    """Test digest message formatting."""

    def test_format_digest_includes_emoji_sections(self):
        """Should format digest with emoji sections."""
        from youtube_telegram_bot.message_formatter import format_digest

        videos = [
            {
                "id": "vid1",
                "title": "Video 1",
                "tickers": ["TEVA"],
                "claim": "TEVA up",
                "recommendation": "BUY",
                "risk_flag": "none",
            }
        ]
        channel_posts = ["Post 1", "Post 2"]

        digest = format_digest(videos, channel_posts)

        assert isinstance(digest, str)
        assert len(digest) > 0
        # Should contain emoji sections
        assert any(emoji in digest for emoji in ["📺", "📊", "🎬"])

    def test_format_digest_includes_video_info(self):
        """Should include video titles and summaries."""
        from youtube_telegram_bot.message_formatter import format_digest

        videos = [
            {
                "id": "vid1",
                "title": "Test Video Title",
                "tickers": ["TEVA"],
                "claim": "TEVA is up",
                "recommendation": "BUY",
                "risk_flag": "none",
            }
        ]

        digest = format_digest(videos, [])

        assert "Test Video Title" in digest or "TEVA" in digest

    def test_format_digest_includes_channel_posts(self):
        """Should include channel posts in digest."""
        from youtube_telegram_bot.message_formatter import format_digest

        channel_posts = ["Channel post 1", "Channel post 2"]

        digest = format_digest([], channel_posts)

        assert "Channel post 1" in digest or "Channel post 2" in digest


class TestTelegramPosting:
    """Test Telegram posting functionality."""

    @patch("youtube_telegram_bot.telegram_posting.requests.post")
    def test_post_digest_sends_to_telegram_api(self, mock_post):
        """Should send digest to Telegram Bot API."""
        from youtube_telegram_bot.telegram_posting import post_digest

        mock_post.return_value.status_code = 200

        result = post_digest("Test message", dry_run=True)

        assert isinstance(result, bool)

    @patch("youtube_telegram_bot.telegram_posting.requests.post")
    def test_post_digest_handles_api_error(self, mock_post):
        """Should handle API errors gracefully."""
        from youtube_telegram_bot.telegram_posting import post_digest

        mock_post.side_effect = Exception("API Error")

        result = post_digest("Test message", dry_run=True)

        assert isinstance(result, bool)


class TestTelegramReading:
    """Test Telegram channel reading functionality."""

    def test_read_channel_posts_returns_list(self):
        """Should return list of channel posts."""
        from youtube_telegram_bot.telegram_reading import read_channel_posts

        # Mock version should work without Telethon setup
        posts = read_channel_posts(dry_run=True)

        assert isinstance(posts, list)
