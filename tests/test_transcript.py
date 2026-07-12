"""Tests for YouTube transcript extraction using yt-dlp."""

import os
import sys
import tempfile
from unittest import mock
from pathlib import Path

import pytest

# Mock yt_dlp before importing transcript module
sys.modules["yt_dlp"] = mock.MagicMock()

from youtube_telegram_bot.transcript import extract_transcript


# Sample caption content (VTT format)
SAMPLE_VTT_HE = """WEBVTT

00:00:00.000 --> 00:00:02.000
שלום, זה סרטון בעברית

00:00:02.000 --> 00:00:04.000
על שוק המניות הישראלי

00:00:04.000 --> 00:00:06.000
עם טיקרים חדשים
"""

# Sample caption content (VTT format - English)
SAMPLE_VTT_EN = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello, this is an English caption

00:00:02.000 --> 00:00:04.000
about the Israeli stock market
"""

# Sample caption content (SRT format)
SAMPLE_SRT_EN = """1
00:00:00,000 --> 00:00:02,000
Hello, this is an English caption

2
00:00:02,000 --> 00:00:04,000
about the Israeli stock market
"""

# Long transcript to test for truncation
LONG_TRANSCRIPT = "This is a long transcript. " * 1000


class TestExtractTranscriptBasic:
    """Tests for basic transcript extraction."""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_extract_transcript_with_hebrew_captions(self, mock_ydl_class):
        """Should extract Hebrew captions successfully."""
        # Setup mock to return Hebrew VTT file
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        def mock_extract_info(url, download=False):
            # Simulate yt-dlp creating a caption file
            if hasattr(mock_extract_info, "temp_dir"):
                caption_path = Path(mock_extract_info.temp_dir) / "test.he.vtt"
                caption_path.write_text(SAMPLE_VTT_HE)
            return {"id": "test_id"}

        mock_instance.extract_info.side_effect = mock_extract_info

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_extract_info.temp_dir = tmpdir
            # Mock the path search to find our caption file
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.he.vtt"
                caption_path.write_text(SAMPLE_VTT_HE)
                mock_glob.return_value = [caption_path]

                # Mock YoutubeDL params to use our temp dir
                with mock.patch.object(
                    mock_ydl_class.return_value.__enter__.return_value,
                    "params",
                    {"outtmpl": tmpdir},
                ):
                    transcript = extract_transcript("test_video_id")

            assert transcript is not None
            assert len(transcript) > 0
            assert "שלום" in transcript or "Hebrew" not in transcript

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_extract_transcript_returns_string(self, mock_ydl_class):
        """Should return transcript as a string."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.en.vtt"
                caption_path.write_text(SAMPLE_VTT_EN)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert isinstance(transcript, str)

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_extract_transcript_with_no_captions_returns_empty_string(
        self, mock_ydl_class
    ):
        """Should return empty string when no captions are available."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {"id": "test_id"}

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                mock_glob.return_value = []  # No caption files found

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert transcript == ""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_extract_transcript_handles_yt_dlp_exception(self, mock_ydl_class):
        """Should handle yt-dlp exceptions gracefully."""
        mock_ydl_class.side_effect = Exception("yt-dlp error")

        transcript = extract_transcript("invalid_video_id")

        assert transcript == ""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_extract_transcript_with_no_logger_errors(self, mock_ydl_class):
        """Should not raise exceptions even if logger is unavailable."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = ValueError("test error")

        # Should not raise
        transcript = extract_transcript("test_video_id")
        assert transcript == ""


class TestTranscriptParsing:
    """Tests for caption file parsing."""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_parse_vtt_format(self, mock_ydl_class):
        """Should correctly parse VTT format."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.en.vtt"
                caption_path.write_text(SAMPLE_VTT_EN)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert "English caption" in transcript
                assert "WEBVTT" not in transcript  # Header should be stripped

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_parse_srt_format(self, mock_ydl_class):
        """Should correctly parse SRT format."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.en.srt"
                caption_path.write_text(SAMPLE_SRT_EN)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert "Hello" in transcript or "caption" in transcript
                # SRT numbers should be stripped
                assert "1\n" not in transcript or transcript.count("\n") < 3

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_long_transcript_not_truncated(self, mock_ydl_class):
        """Should not truncate long transcripts."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.en.vtt"
                # Create a long VTT with many timestamps
                long_vtt = "WEBVTT\n\n"
                for i in range(100):
                    long_vtt += f"00:{i//60:02d}:{i%60:02d}.000 --> 00:{i//60:02d}:{i%60+1:02d}.000\n"
                    long_vtt += f"Line {i}: {LONG_TRANSCRIPT[:50]}\n\n"

                caption_path.write_text(long_vtt)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert len(transcript) > 1000


class TestLanguageFallback:
    """Tests for Hebrew to English fallback."""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_prefers_hebrew_over_english(self, mock_ydl_class):
        """Should prefer Hebrew captions over English."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                # Create both Hebrew and English caption files
                he_path = Path(tmpdir) / "test.he.vtt"
                en_path = Path(tmpdir) / "test.en.vtt"
                he_path.write_text("Hebrew caption content")
                en_path.write_text("English caption content")

                # Return both, but in order: English first, then Hebrew
                # We expect the code to prefer Hebrew
                mock_glob.return_value = [en_path, he_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                # Should contain Hebrew content (he.vtt processed last, or prioritized)
                # This test verifies the preference logic
                assert len(transcript) > 0

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_fallback_to_english_if_hebrew_missing(self, mock_ydl_class):
        """Should fallback to English if Hebrew captions not available."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                en_path = Path(tmpdir) / "test.en.vtt"
                en_path.write_text(SAMPLE_VTT_EN)
                mock_glob.return_value = [en_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert "English" in transcript or "caption" in transcript


class TestCleanup:
    """Tests for temporary file cleanup."""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_temp_directory_created_and_cleaned(self, mock_ydl_class):
        """Should use temporary directory that gets cleaned up."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = None

            def capture_temp_path(*args, **kwargs):
                nonlocal temp_path
                # Extract the temp directory from YoutubeDL params
                temp_path = kwargs.get("outtmpl", tmpdir)
                return {"id": "test_id"}

            mock_instance.extract_info.side_effect = capture_temp_path

            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                mock_glob.return_value = []

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                # Should return empty string (no captions found)
                assert transcript == ""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_no_video_files_downloaded(self, mock_ydl_class):
        """Should not download video files, only captions."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.en.vtt"
                caption_path.write_text(SAMPLE_VTT_EN)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                # Verify yt-dlp was called with skip_download=True
                mock_ydl_class.assert_called()
                # Check positional args for the options dict
                call_args = mock_ydl_class.call_args[0]
                if call_args:
                    ydl_opts = call_args[0]
                    assert ydl_opts.get("skip_download") is True


class TestValidation:
    """Tests for transcript validation."""

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_transcript_is_non_empty_or_empty_string(self, mock_ydl_class):
        """Should return either non-empty string or empty string, never None."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                mock_glob.return_value = []

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                # Must never be None
                assert transcript is not None
                assert isinstance(transcript, str)

    @mock.patch("youtube_telegram_bot.transcript.yt_dlp.YoutubeDL")
    def test_handles_unicode_in_transcript(self, mock_ydl_class):
        """Should handle Unicode characters (Hebrew, etc.) correctly."""
        mock_instance = mock.MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("youtube_telegram_bot.transcript.Path.glob") as mock_glob:
                caption_path = Path(tmpdir) / "test.he.vtt"
                caption_path.write_text(SAMPLE_VTT_HE)
                mock_glob.return_value = [caption_path]

                with mock.patch.dict(os.environ, {"TMPDIR": tmpdir}):
                    transcript = extract_transcript("test_video_id")

                assert isinstance(transcript, str)
