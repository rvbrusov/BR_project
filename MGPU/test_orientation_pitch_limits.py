import aviatest_v2
from orient_new_v3_1 import STAGE3_PITCH_VALUES_15


def test_standalone_stage3_excludes_vertical_pitch_endpoints():
    assert -90 not in STAGE3_PITCH_VALUES_15
    assert 90 not in STAGE3_PITCH_VALUES_15
    assert min(STAGE3_PITCH_VALUES_15) == -75
    assert max(STAGE3_PITCH_VALUES_15) == 75


def test_aviatest_stage3_rejects_vertical_pitch_endpoints():
    style = aviatest_v2._AviatestOrientationStyle
    stage3 = object.__new__(style)
    stage3.final_stage_number = 3
    answers = style.valid_pitch_answers(stage3)
    assert "-90" not in answers
    assert "+90" not in answers
    assert "-75" in answers
    assert "+75" in answers


def test_aviatest_stage2_keeps_existing_endpoints():
    style = aviatest_v2._AviatestOrientationStyle
    stage2 = object.__new__(style)
    stage2.final_stage_number = 2
    answers = style.valid_pitch_answers(stage2)
    assert "-90" in answers
    assert "+90" in answers
