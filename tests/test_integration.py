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
