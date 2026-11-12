import json
from pathlib import Path

import aviatest_v2


class JsonStore:
    def __init__(self, path: Path):
        self.path = path

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data):
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_v2_results_are_not_shifted_again_on_restart(tmp_path):
    path = tmp_path / "user_progress.json"
    original_results = {
        "A": {"test_code": "A", "summary": {"tmin_a": 0.4}},
        "B": {"test_code": "B", "stages": {"1": {"accuracy_pct": 80}}},
        "C": {"test_code": "C", "cycles": [{"success": True}]},
        "D": {"test_code": "D", "stages": {"1": {"correct": 3}}},
        "E": {"test_code": "E", "tasks": [{"correct": True}]},
    }
    path.write_text(
        json.dumps({"person": {"results": original_results, "completed_tests": list("ABCDE")}}),
        encoding="utf-8",
    )

    aviatest_v2._migrate_progress(JsonStore(path))
    saved = json.loads(path.read_text(encoding="utf-8"))["person"]

    assert saved["results"] == original_results
    assert saved["completed_tests"] == list("ABCDE")
    assert saved["aviatest_v1_order_migrated"]


def test_new_records_are_stamped_as_v2(tmp_path):
    profile = aviatest_v2.base.UserProfile(name="Test User", age="30", gender="M")
    store = aviatest_v2.base.UserProgressStore(tmp_path)

    record = store.ensure_user(profile)

    assert record["aviatest_v1_order_migrated"]
