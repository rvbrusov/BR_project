import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _load_fixed428():
    name = "fixed428_method_c_for_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "fixed428_app_2026-04-25_portable_build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_integral_uses_stage_value_that_already_applied_error_norm():
    app = _load_fixed428()
    payload = {
        "summary": {
            "stages": {
                "1": {"t_value": 0.8, "gamma_count": 0.5, "t_avg_cycle_s": 4.0},
                "2": {"t_value": 1.2, "gamma_count": 0.0, "t_avg_cycle_s": 8.0},
                "3": {"t_value": 0.6, "gamma_count": 0.25, "t_avg_cycle_s": 16.0},
            }
        }
    }
    assert app._fixed428_method_c_result_values(None, payload) == [0.8, 1.2, 0.6]


def test_integral_never_emits_negative_value():
    app = _load_fixed428()
    payload = {"summary": {"stages": {str(i): {"t_value": -1} for i in range(1, 4)}}}
    assert app._fixed428_method_c_result_values(None, payload) == [0.0, 0.0, 0.0]
