"""YouTube RSS feed parsing and video extraction."""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any

# Atom namespace used by YouTube RSS feeds
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def parse_rss_xml(xml_content: str) -> ET.Element:
    """
    Parse YouTube RSS XML content.

    Args:
        xml_content: Raw XML string from YouTube RSS feed

    Returns:
        Root XML Element

    Raises:
        xml.etree.ElementTree.ParseError: If XML is malformed
    """
    return ET.fromstring(xml_content)


def _extract_video_id_from_yt_id(yt_id_text: str) -> str:
    """
    Extract video ID from YouTube's yt:video:ID format.

    Args:
        yt_id_text: Full ID text in format "yt:video:dQw4w9WgXcQ"

    Returns:
        Video ID portion only
    """
    return yt_id_text.split(":")[-1]


def extract_video_ids(root: ET.Element) -> List[Dict[str, str]]:
    """
    Extract video IDs and titles from parsed RSS XML.

    Each entry in the RSS feed contains:
    - <id>yt:video:{VIDEO_ID}</id>
    - <title>{VIDEO_TITLE}</title>

    Args:
        root: Root XML Element from parse_rss_xml()

    Returns:
        List of dicts with 'id' and 'title' keys
    """
    videos = []

    for entry in root.findall("atom:entry", ATOM_NS):
        id_elem = entry.find("atom:id", ATOM_NS)
        if id_elem is None or not id_elem.text:
            continue

        video_id = _extract_video_id_from_yt_id(id_elem.text)
        title_elem = entry.find("atom:title", ATOM_NS)
        title = title_elem.text if title_elem is not None else "Unknown"

        # Publish time lets a multi-channel backlog be ordered newest-first
        published_elem = entry.find("atom:published", ATOM_NS)
        published = published_elem.text if published_elem is not None else ""

        videos.append({"id": video_id, "title": title, "published": published})

    return videos
