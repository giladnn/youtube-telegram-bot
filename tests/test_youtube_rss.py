"""Tests for YouTube RSS parsing."""

import pytest
from youtube_telegram_bot.youtube_rss import parse_rss_xml, extract_video_ids


# Sample YouTube RSS XML (minimal structure for testing)
SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <entry>
    <id>yt:video:dQw4w9WgXcQ</id>
    <title>Test Video 1</title>
    <published>2024-01-01T00:00:00+00:00</published>
  </entry>
  <entry>
    <id>yt:video:jNQXAC9IVRw</id>
    <title>Test Video 2</title>
    <published>2024-01-02T00:00:00+00:00</published>
  </entry>
</feed>
"""

MALFORMED_XML = """<?xml version="1.0"?>
<feed>
  <entry>
    <id>yt:video:dQw4w9WgXcQ</id>
"""

EMPTY_FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
"""


class TestParseRssXml:
    """Tests for RSS XML parsing."""

    def test_parse_rss_xml_returns_root_element(self):
        """Should parse valid RSS XML and return root element."""
        root = parse_rss_xml(SAMPLE_RSS_XML)
        assert root is not None
        assert root.tag.endswith("feed")

    def test_parse_rss_xml_raises_on_malformed_xml(self):
        """Should raise exception on malformed XML."""
        with pytest.raises(Exception):
            parse_rss_xml(MALFORMED_XML)

    def test_parse_rss_xml_handles_empty_feed(self):
        """Should handle empty feed without crashing."""
        root = parse_rss_xml(EMPTY_FEED_XML)
        assert root is not None


class TestExtractVideoIds:
    """Tests for video ID extraction."""

    def test_extract_video_ids_from_valid_feed(self):
        """Should extract video IDs from valid RSS feed."""
        root = parse_rss_xml(SAMPLE_RSS_XML)
        videos = extract_video_ids(root)
        assert len(videos) == 2
        assert videos[0]["id"] == "dQw4w9WgXcQ"
        assert videos[1]["id"] == "jNQXAC9IVRw"

    def test_extract_video_ids_includes_title(self):
        """Should extract video IDs with titles."""
        root = parse_rss_xml(SAMPLE_RSS_XML)
        videos = extract_video_ids(root)
        assert videos[0]["title"] == "Test Video 1"
        assert videos[1]["title"] == "Test Video 2"

    def test_extract_video_ids_from_empty_feed(self):
        """Should return empty list for empty feed."""
        root = parse_rss_xml(EMPTY_FEED_XML)
        videos = extract_video_ids(root)
        assert videos == []

    def test_extract_video_ids_returns_list_of_dicts(self):
        """Should return list of dictionaries with id and title."""
        root = parse_rss_xml(SAMPLE_RSS_XML)
        videos = extract_video_ids(root)
        assert isinstance(videos, list)
        for video in videos:
            assert isinstance(video, dict)
            assert "id" in video
            assert "title" in video
