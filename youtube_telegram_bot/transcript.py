"""YouTube transcript extraction using youtube-transcript-api (primary) + yt-dlp fallback."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None  # Fallback to yt-dlp

try:
    import yt_dlp
except ImportError:
    yt_dlp = None  # Fallback disabled if neither library available


logger = logging.getLogger(__name__)

# Language preference order for captions
# NOTE: YouTube uses the legacy ISO code "iw" for Hebrew auto-captions
PREFERRED_LANGUAGES = ["iw", "he", "en"]

# Supported caption file extensions
CAPTION_EXTENSIONS = ("*.vtt", "*.srt")


def _parse_caption_file(file_path: Path) -> str:
    """
    Parse caption file (VTT or SRT format) and extract text only.

    Strips out timing information and formatting, leaving only the caption text.

    Args:
        file_path: Path to the caption file

    Returns:
        Extracted text from captions (one line per caption), empty string on error
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read caption file {file_path}: {e}")
        return ""

    # Extract only text lines, filtering out formatting and timing
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()

        # Skip empty lines and headers
        if not stripped:
            continue
        if stripped == "WEBVTT":
            continue

        # Skip timing lines (contain "-->")
        if "-->" in stripped:
            continue

        # Skip SRT sequence numbers (lines that are purely numeric)
        if stripped.isdigit():
            continue

        # Keep actual caption text
        lines.append(line)

    return "\n".join(lines).strip()


def _find_caption_file(temp_dir: str) -> Optional[Path]:
    """
    Find the best caption file in temp directory by language preference.

    Searches for VTT or SRT files and ranks them by language preference
    (Hebrew preferred over English over others).

    Args:
        temp_dir: Temporary directory path containing caption files

    Returns:
        Path to selected caption file, or None if no captions found
    """
    temp_path = Path(temp_dir)

    # Find all caption files
    caption_files = []
    for extension in CAPTION_EXTENSIONS:
        caption_files.extend(temp_path.glob(extension))

    if not caption_files:
        return None

    # Sort by language preference
    def get_language_priority(file_path: Path) -> int:
        """Return priority score (lower is better)."""
        name = file_path.name
        for i, lang in enumerate(PREFERRED_LANGUAGES):
            if f".{lang}." in name or f".{lang}-" in name:
                return i
        # Unknown language gets lowest priority
        return len(PREFERRED_LANGUAGES)

    caption_files.sort(key=get_language_priority)
    return caption_files[0]


def _extract_via_transcript_api(video_id: str) -> str:
    """
    Extract transcript using youtube-transcript-api (lightweight, no auth).

    Attempts Hebrew first, then English. Faster than yt-dlp but only works
    for videos with available transcripts (manual or pre-cached auto-captions).

    Args:
        video_id: YouTube video ID

    Returns:
        Transcript text or empty string if unavailable/failed
    """
    if YouTubeTranscriptApi is None:
        return ""

    try:
        # v1.x API: instantiate and fetch with language preference list
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=PREFERRED_LANGUAGES)
        # Snippets are objects with .text in v1.x, dicts in 0.x
        text = " ".join(
            s.text if hasattr(s, "text") else s["text"] for s in transcript
        )
        logger.info(f"Extracted transcript via API for {video_id} ({len(text)} chars)")
        return text
    except Exception as e:
        logger.debug(f"youtube-transcript-api unavailable for {video_id}: {e}")
        return ""


def _extract_via_ytdlp(video_id: str) -> str:
    """
    Extract transcript using yt-dlp (fallback, slower but more robust).

    Args:
        video_id: YouTube video ID

    Returns:
        Transcript text or empty string if unavailable/failed
    """
    if yt_dlp is None:
        logger.warning("yt-dlp not installed")
        return ""

    # Create temporary directory for caption extraction (auto-cleaned up)
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Configure yt-dlp to extract captions only
            ydl_opts = {
                "skip_download": True,  # Critical: do not download video
                "writesubtitles": True,  # Download manually added captions
                "writeautomaticsub": True,  # Download auto-generated captions
                "subtitleslangs": PREFERRED_LANGUAGES,
                "outtmpl": os.path.join(temp_dir, "%(title)s"),
                "quiet": True,
                "no_warnings": True,
            }

            # Extract captions from video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                ydl.extract_info(video_url, download=False)

            # Locate the best caption file by language preference
            caption_file = _find_caption_file(temp_dir)
            if caption_file is None:
                logger.debug(f"No captions found for video {video_id}")
                return ""

            # Parse and return transcript text
            transcript = _parse_caption_file(caption_file)
            return transcript

        except Exception as e:
            logger.debug(f"yt-dlp fallback failed for {video_id}: {e}")
            return ""


def extract_transcript(video_id: str) -> str:
    """
    Extract transcript from YouTube video using youtube-transcript-api (primary) + yt-dlp fallback.

    Attempts to extract captions in order of preference (Hebrew, then English).
    Returns empty string if no captions are available or if extraction fails.

    Uses lightweight youtube-transcript-api first (fast, no auth, no download).
    Falls back to yt-dlp if transcript API doesn't work (handles edge cases).

    Args:
        video_id: YouTube video ID

    Returns:
        Transcript text as string, or empty string if unavailable or on error
    """
    # Try lightweight API first
    transcript = _extract_via_transcript_api(video_id)
    if transcript:
        return transcript

    # Fallback to yt-dlp if API doesn't work
    transcript = _extract_via_ytdlp(video_id)
    return transcript
