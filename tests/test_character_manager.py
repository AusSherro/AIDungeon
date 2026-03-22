"""Tests for character CRUD."""
import pytest
import os
from utils.character_manager import (
    register_character, load_character, save_character,
    damage_character, heal_character, CHAR_DIR
)

TEST_USER = "test_user_999"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Clean up test character file
    path = os.path.join(CHAR_DIR, f'{TEST_USER}.json')
    if os.path.exists(path):
        os.remove(path)


def test_register_and_load():
    register_character(TEST_USER, "Test Hero", "Fighter", "Human")
    data = load_character(TEST_USER)
    assert data['name'] == "Test Hero"
    assert data['class'] == "Fighter"


def test_damage_and_heal():
    register_character(TEST_USER, "Test Hero", "Fighter", "Human")
    damage_character(TEST_USER, 5)
    data = load_character(TEST_USER)
    assert data['hp'] == data['max_hp'] - 5
    heal_character(TEST_USER, 3)
    data = load_character(TEST_USER)
    assert data['hp'] == data['max_hp'] - 2


def test_damage_cant_go_below_zero():
    register_character(TEST_USER, "Test Hero", "Fighter", "Human")
    damage_character(TEST_USER, 9999)
    data = load_character(TEST_USER)
    assert data['hp'] == 0


def test_heal_cant_exceed_max():
    register_character(TEST_USER, "Test Hero", "Fighter", "Human")
    max_hp = load_character(TEST_USER)['max_hp']
    heal_character(TEST_USER, 9999)
    data = load_character(TEST_USER)
    assert data['hp'] == max_hp
