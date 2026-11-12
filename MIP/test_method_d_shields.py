import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_every_shield_task_uses_one_axis():
    engine = _load("tensor_matrix_test_for_test", "tensor_matrix_test_2026_04_23_v14.py")
    for pockets in (2, 3, 4):
        for _ in range(100):
            _length, _cells, _rules, debug = engine._generate_tensor_once(pockets)
            methods = debug["methods"]
            assert len(methods) == pockets
            assert len(set(methods)) == 1


def test_presented_count_can_exceed_answered_count():
    app = _load("fixed428_for_test", "fixed428_app_2026-04-25_portable_build.py")

    class Dummy:
        result = {
            "tasks": [
                {"difficulty": "max", "correct": True, "elapsed_s": 3.0},
                {"difficulty": "max", "correct": False, "elapsed_s": 4.0},
            ]
        }
        cfg = type("Cfg", (), {
            "normative_cycle_times": {"min": 1.0, "medio": 1.0, "max": 1.0},
            "normative_stage_speed": {},
            "normative_success_coef": 1.0,
        })()
        stage_started_at = {"min": 0.0, "medio": 0.0, "max": 10.0}
        stage_last_answer_at = {"min": 0.0, "medio": 0.0, "max": 17.0}
        stage_started_count = {"min": 0, "medio": 0, "max": 3}
        block_index = 3

    summary = app._fixed428_compute_summary(Dummy())
    assert summary["groups"]["max"]["presented_count"] == 3
    assert summary["groups"]["max"]["answered_count"] == 2
