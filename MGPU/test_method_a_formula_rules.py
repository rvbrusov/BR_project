from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def _load_app_module():
    source = Path(__file__).with_name("fixed427_app_2026-04-25_portable_build.py")
    module_name = "_method_a_formula_test_app"
    spec = importlib.util.spec_from_file_location(module_name, source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


APP = _load_app_module()


def _owner():
    config = APP.load_config(Path(__file__).with_name("method_a_config.json"))
    return type("Owner", (), {"cfg": config})()


def test_current_radius_is_clamped_to_target_for_entropy() -> None:
    assert APP._fixed260_axis_s(2.0, 3.0, 18.0, True) == 0.0
    assert APP._fixed260_axis_s(3.0, 3.0, 18.0, True) == 0.0
    assert math.isclose(APP._fixed260_axis_s(10.0, 3.0, 18.0, True), 7.0 / 15.0)
    assert APP._fixed260_axis_s(18.0, 3.0, 18.0, True) == 1.0


def test_gamma_uses_mean_entropy_and_permissible_error() -> None:
    s_norm = APP._fixed260_stage_s_norm(_owner(), 1)
    assert math.isclose(s_norm, 0.28)

    mean_entropy, gamma = APP._fixed427_success_gamma(0.0, 40.0, s_norm)
    assert mean_entropy == 0.0
    assert math.isclose(gamma, 1.0 / 0.72)

    mean_entropy, gamma = APP._fixed427_success_gamma(0.28 * 40.0, 40.0, s_norm)
    assert math.isclose(mean_entropy, 0.28)
    assert math.isclose(gamma, 1.0)

    mean_entropy, gamma = APP._fixed427_success_gamma(40.0, 40.0, s_norm)
    assert mean_entropy == 1.0
    assert gamma == 0.0


def test_limits_and_setting_names_match_document() -> None:
    owner = _owner()
    assert math.isclose(APP._fixed200_stage_y_lim_per_sec(owner, 1) * 40.0, 28.0)
    expected_n_dop = owner.cfg.n_dop_x_for_150s * 40.0 / 150.0
    assert math.isclose(APP._fixed260_stage_n_dop_t(owner, 1, 40.0), expected_n_dop)

    metadata = APP.RESEARCH_FIELD_META["A"]
    assert "Допустимая ошибка" in metadata["s_norm_x"]["label"]
    assert "150" in metadata["n_dop_x_for_150s"]["label"]
    assert "XY" in metadata["y_lim_xy_per_sec"]["label"]

    groups = APP._get_research_section_groups("A", APP.MethodAConfig)
    visible = {field_name for _title, field_names in groups for field_name in field_names}
    assert {"s_norm_x", "y_lim_x_per_sec", "y_lim_xy_per_sec", "n_dop_x_for_150s", "v_norm_x_cm_s"} <= visible
    assert "n_dop_x_for_180s" not in visible
    assert "stage1_v_norm_x_cm_s" not in visible


def test_final_report_uses_document_gamma_and_separate_stage_limit() -> None:
    owner = _owner()
    report = APP.StageReport(stage_no=1, active_axes="X")
    report.real_time_s = 40.0
    report.sum_error = 0.28 * 40.0
    report.crashes = 0
    report.second_metrics = []
    report._fixed209_lambda_sum = 20.0

    result = APP._fixed260_finalize_stage_report(owner, report, 40.0, 0.0, 0.0)

    assert math.isclose(result.entropy_h, 0.28)
    assert math.isclose(result.success_gamma, 1.0)
    assert math.isclose(result.s_norm_value, 0.28)
    assert math.isclose(result.y_lim_per_sec, 0.7)
    assert math.isclose(result.error_limit_formula_value, 28.0)
    assert result.tracking_error_current_avg_raw == 0.0
    assert math.isclose(result.tracking_error_current_avg, result.tracking_error_target)


def test_current_speed_uses_signed_positions_and_real_interval() -> None:
    # Crossing the centre from -1 to +1 cm is 2 cm of movement, not zero.
    assert math.isclose(APP._fixed428_current_speed(1.0, -1.0, 0.5), 4.0)
    assert APP._fixed428_current_speed(1.0, 1.0, 0.5) == 0.0
    assert APP._fixed428_current_speed(1.0, -1.0, 0.0) == 0.0
    assert APP._fixed428_control_speed(3.0, 5.0) == -2.0


def test_n_avar_keeps_fractional_limit_and_uses_allotted_time() -> None:
    owner = _owner()
    owner.cfg.n_dop_x_for_150s = 40.0
    owner.cfg.n_dop_x_for_180s = 40.0
    report = APP.StageReport(stage_no=1, active_axes="X")
    report.real_time_s = 20.0
    report.stage_time_limit_used_s = 40.0
    report.sum_error = 5.6
    report.crashes = 1
    report.second_metrics = []
    report._fixed209_lambda_sum = 10.0

    result = APP._fixed260_finalize_stage_report(owner, report, 20.0, 0.0, 0.0)

    expected_n_dop_t = 40.0 * 40.0 / 150.0
    assert math.isclose(result.crash_limit_doc, expected_n_dop_t)
    assert math.isclose(result.crash_coeff_n_avar, 1.0 - 1.0 / expected_n_dop_t)
    assert math.isclose(result.v_avg, 10.0 / 40.0)
    assert math.isclose(result.entropy_h, 5.6 / 40.0)


def test_axis_snapshot_keeps_x_and_y_settings_independent() -> None:
    owner = _owner()
    owner.stage_defs = {2: {"x": True, "y": True, "z": False}}
    owner.cfg.r_goal_x_cm = 3.0
    owner.cfg.r_crash_x_cm = 18.0
    owner.cfg.r_goal_y_cm = 4.0
    owner.cfg.r_crash_y_cm = 20.0
    state = APP.DriftState(x_px=owner.cfg.px_per_cm * 5.0, y_px=owner.cfg.px_per_cm * 6.0)

    snap = APP._fixed200_axis_snapshot(owner, state, 2)

    assert snap["goal_x"] == 3.0
    assert snap["crash_x"] == 18.0
    assert snap["goal_y"] == 4.0
    assert snap["crash_y"] == 20.0


def test_crash_zone_uses_independent_xy_radii_and_z_crash_angle() -> None:
    owner = _owner()
    owner.stage_defs = {
        2: {"x": True, "y": True, "z": False},
        3: {"x": True, "y": True, "z": True},
    }
    owner.cfg.r_crash_x_cm = 18.0
    owner.cfg.r_crash_y_cm = 20.0
    owner.cfg.r_crash_z_deg = 90.0
    owner.cfg.work_roll_deg = 90.0

    inside = APP.DriftState(
        x_px=owner.cfg.px_per_cm * 10.0,
        y_px=owner.cfg.px_per_cm * 10.0,
        roll_deg=89.0,
    )
    assert not APP._fixed293_method_a_in_crash_zone(owner, inside, 3)

    on_xy_boundary = APP.DriftState(x_px=owner.cfg.px_per_cm * 18.0, y_px=0.0)
    assert APP._fixed293_method_a_in_crash_zone(owner, on_xy_boundary, 2)

    on_z_boundary = APP.DriftState(x_px=0.0, y_px=0.0, roll_deg=90.0)
    assert APP._fixed293_method_a_in_crash_zone(owner, on_z_boundary, 3)
