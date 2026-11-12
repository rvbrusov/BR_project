from types import SimpleNamespace

from orient_new_v3_1 import (
    ROLL_MAGNITUDES_15,
    STAGE3_AIRPLANE_ROLLS,
    OrientationTestV31,
)


def _answer(horizon: int, airplane: int) -> str:
    state = SimpleNamespace(roll=horizon, airplane_roll=airplane)
    return OrientationTestV31.correct_roll_answer(state)


def test_roll_is_measured_relative_to_horizon():
    assert _answer(0, 30) == "Л30"
    assert _answer(15, 30) == "Л15"
    assert _answer(165, 15) == "Л30"


def test_relative_roll_preserves_direction():
    assert _answer(0, -30) == "П30"
    assert _answer(15, -15) == "П30"


def test_zero_roll_is_unsigned_zero():
    assert _answer(0, 0) == "0"
    assert "0" in OrientationTestV31.valid_roll_answers(SimpleNamespace())


def test_signed_or_directional_zero_is_normalized():
    for direction in ("", "+", "-", "Л", "П"):
        state = SimpleNamespace(roll_direction=direction, roll_digits="0")
        assert OrientationTestV31.current_roll_answer(state) == "0"


def test_generator_contains_both_directions_and_only_valid_magnitudes():
    assert any(value > 0 for value in STAGE3_AIRPLANE_ROLLS)
    assert any(value < 0 for value in STAGE3_AIRPLANE_ROLLS)
    assert {abs(value) for value in STAGE3_AIRPLANE_ROLLS} == set(ROLL_MAGNITUDES_15)
