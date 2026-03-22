"""Tests for AI tag parsing."""
from utils.tag_parser import parse_all_tags, strip_tags


def test_combat_tag():
    tags = parse_all_tags("[COMBAT: 3 goblins, 1 hobgoblin]")
    assert len(tags.combat) == 1
    assert "goblin" in tags.combat[0]['enemies'].lower()


def test_combat_tag_no_space():
    tags = parse_all_tags("[COMBAT:3 goblins]")
    assert len(tags.combat) == 1


def test_combat_tag_lowercase():
    tags = parse_all_tags("[combat: 2 wolves]")
    assert len(tags.combat) == 1


def test_quest_tag():
    tags = parse_all_tags('[QUEST: name="Rescue the Princess", type=rescue]')
    assert len(tags.quests) == 1


def test_strip_tags():
    text = "The goblins attack! [COMBAT: 3 goblins] Roll for initiative!"
    clean = strip_tags(text)
    assert "[COMBAT" not in clean
    assert "goblins attack" in clean


def test_multiple_tags():
    text = "[WEATHER: rain] The sky darkens. [LIGHTING: dim]"
    tags = parse_all_tags(text)
    assert len(tags.weather) == 1
    assert len(tags.lighting) == 1


def test_no_tags():
    tags = parse_all_tags("Just a regular sentence with no tags.")
    assert not tags.has_any()
