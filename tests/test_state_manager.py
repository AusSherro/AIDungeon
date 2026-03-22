"""Tests for state persistence."""
import pytest
import os
import json
from utils.state_manager import load_state, save_state, STATE_DIR

TEST_ID = "test_channel_999"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Clean up test files
    path = os.path.join(STATE_DIR, f'{TEST_ID}.json')
    if os.path.exists(path):
        os.remove(path)
    corrupted = path + ".corrupted"
    if os.path.exists(corrupted):
        os.remove(corrupted)


def test_load_missing_state_returns_defaults():
    state = load_state(TEST_ID)
    assert state["campaign_title"] == ""
    assert state["players"] == []


def test_save_and_load_roundtrip():
    state = load_state(TEST_ID)
    state["campaign_title"] = "Test Campaign"
    save_state(TEST_ID, state)
    loaded = load_state(TEST_ID)
    assert loaded["campaign_title"] == "Test Campaign"


def test_corrupted_file_recovery():
    path = os.path.join(STATE_DIR, f'{TEST_ID}.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write("{invalid json!!")
    state = load_state(TEST_ID)
    assert state["campaign_title"] == ""  # Should return defaults
    assert os.path.exists(path + ".corrupted")  # Should rename bad file
