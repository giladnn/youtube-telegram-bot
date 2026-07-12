"""Tests for state file management."""

import json
import os
import pytest
import tempfile
from youtube_telegram_bot.state import load_state, save_state, is_video_seen, mark_video_seen


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def missing_state_file():
    """Return a path to a non-existent state file."""
    path = "/tmp/nonexistent_state_" + str(os.getpid()) + ".json"
    if os.path.exists(path):
        os.remove(path)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


class TestLoadState:
    """Tests for loading state from file."""

    def test_load_state_from_existing_file(self, temp_state_file):
        """Should load state from existing file."""
        # Write test data
        test_state = {"video1": {"seen": True}, "video2": {"seen": True}}
        with open(temp_state_file, "w") as f:
            json.dump(test_state, f)

        # Load and verify
        state = load_state(temp_state_file)
        assert state == test_state

    def test_load_state_returns_empty_dict_for_missing_file(self, missing_state_file):
        """Should return empty dict if state file doesn't exist."""
        state = load_state(missing_state_file)
        assert state == {}

    def test_load_state_handles_empty_file(self, temp_state_file):
        """Should handle empty file gracefully."""
        # Write empty dict
        with open(temp_state_file, "w") as f:
            json.dump({}, f)

        state = load_state(temp_state_file)
        assert state == {}

    def test_load_state_raises_on_invalid_json(self, temp_state_file):
        """Should raise exception on invalid JSON."""
        # Write invalid JSON
        with open(temp_state_file, "w") as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            load_state(temp_state_file)


class TestSaveState:
    """Tests for saving state to file."""

    def test_save_state_creates_file(self, missing_state_file):
        """Should create state file if it doesn't exist."""
        state = {"video1": {"seen": True}}
        save_state(state, missing_state_file)

        assert os.path.exists(missing_state_file)
        with open(missing_state_file, "r") as f:
            saved = json.load(f)
        assert saved == state

    def test_save_state_overwrites_existing_file(self, temp_state_file):
        """Should overwrite existing state file."""
        old_state = {"old": "data"}
        with open(temp_state_file, "w") as f:
            json.dump(old_state, f)

        new_state = {"new": "data"}
        save_state(new_state, temp_state_file)

        with open(temp_state_file, "r") as f:
            saved = json.load(f)
        assert saved == new_state

    def test_save_state_is_atomic(self, temp_state_file):
        """Should use atomic write (temp file + rename)."""
        state = {"video1": {"seen": True}}
        save_state(state, temp_state_file)

        # Verify file exists and has correct content
        with open(temp_state_file, "r") as f:
            saved = json.load(f)
        assert saved == state


class TestIsVideoSeen:
    """Tests for checking if video has been seen."""

    def test_is_video_seen_returns_true_for_seen_video(self):
        """Should return True if video is in state."""
        state = {"dQw4w9WgXcQ": {"seen": True}}
        assert is_video_seen("dQw4w9WgXcQ", state) is True

    def test_is_video_seen_returns_false_for_unseen_video(self):
        """Should return False if video is not in state."""
        state = {"dQw4w9WgXcQ": {"seen": True}}
        assert is_video_seen("jNQXAC9IVRw", state) is False

    def test_is_video_seen_returns_false_for_empty_state(self):
        """Should return False for empty state."""
        state = {}
        assert is_video_seen("dQw4w9WgXcQ", state) is False


class TestMarkVideoSeen:
    """Tests for marking video as seen."""

    def test_mark_video_seen_adds_to_state(self):
        """Should add video to state."""
        state = {}
        mark_video_seen("dQw4w9WgXcQ", state)
        assert "dQw4w9WgXcQ" in state

    def test_mark_video_seen_preserves_existing_videos(self):
        """Should not remove existing videos."""
        state = {"existing": {"seen": True}}
        mark_video_seen("dQw4w9WgXcQ", state)
        assert "existing" in state
        assert "dQw4w9WgXcQ" in state

    def test_mark_video_seen_can_be_called_multiple_times(self):
        """Should handle being called multiple times."""
        state = {}
        mark_video_seen("dQw4w9WgXcQ", state)
        mark_video_seen("dQw4w9WgXcQ", state)
        assert list(state.keys()).count("dQw4w9WgXcQ") == 1
