"""State file management for tracking seen videos.

State is stored as a JSON file with structure:
{
    "VIDEO_ID_1": {"seen": True},
    "VIDEO_ID_2": {"seen": True},
    ...
}
"""

import json
import os
import tempfile
from typing import Dict, Any


def load_state(state_file: str) -> Dict[str, Any]:
    """
    Load state from JSON file.

    Args:
        state_file: Path to state.json file

    Returns:
        Dictionary of state data. Empty dict if file doesn't exist.

    Raises:
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not os.path.exists(state_file):
        return {}

    with open(state_file, "r") as f:
        return json.load(f)


def save_state(state: Dict[str, Any], state_file: str) -> None:
    """
    Save state to JSON file atomically.

    Uses atomic write pattern to prevent corruption:
    1. Write to temporary file in same directory
    2. Rename temp file to target path (atomic on POSIX)

    Args:
        state: Dictionary to save
        state_file: Path where state.json should be written
    """
    state_dir = os.path.dirname(state_file) or "."

    # Write to temp file first
    with tempfile.NamedTemporaryFile(
        mode="w", dir=state_dir, delete=False, suffix=".json"
    ) as tmp:
        json.dump(state, tmp)
        tmp_path = tmp.name

    # Atomic rename
    os.replace(tmp_path, state_file)


def is_video_seen(video_id: str, state: Dict[str, Any]) -> bool:
    """
    Check if a video has been seen before.

    Args:
        video_id: YouTube video ID
        state: Current state dictionary

    Returns:
        True if video_id is in state, False otherwise
    """
    return video_id in state


def mark_video_seen(video_id: str, state: Dict[str, Any]) -> None:
    """
    Mark a video as seen in the state.

    Modifies the state dictionary in place.

    Args:
        video_id: YouTube video ID
        state: Current state dictionary (modified in place)
    """
    state[video_id] = {"seen": True}
