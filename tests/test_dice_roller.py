"""Tests for the dice roller — the simplest, most testable module."""
import pytest
from utils.dice_roller import roll_dice, parse_dice


def test_basic_roll():
    total, rolls, modifier = roll_dice("1d20")
    assert 1 <= total <= 20
    assert len(rolls) == 1
    assert modifier == 0


def test_multiple_dice():
    total, rolls, modifier = roll_dice("3d6")
    assert 3 <= total <= 18
    assert len(rolls) == 3


def test_modifier():
    total, rolls, modifier = roll_dice("1d20+5")
    assert 6 <= total <= 25
    assert modifier == 5


def test_negative_modifier():
    total, rolls, modifier = roll_dice("1d20-2")
    assert -1 <= total <= 18
    assert modifier == -2


def test_d100():
    total, rolls, modifier = roll_dice("1d100")
    assert 1 <= total <= 100


def test_parse_dice_basic():
    num, sides, mod = parse_dice("2d6+3")
    assert num == 2
    assert sides == 6
    assert mod == 3
