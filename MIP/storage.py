"""Writable per-Windows-user storage, preserving the original data directory."""
import json
import os
from pathlib import Path
import shutil
import tempfile

CONFIGS = ('method_a_config.json', 'method_b_config.json', 'method_c_config.json',
           'method_d_config.json', 'orientation_config.json', 'surface_norms.json', 'config_schema_version.txt')


def writable(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=directory) as handle:
        handle.write(b'aviatest')
        handle.flush()
    return directory


def prepare_storage(app_dir, resources, local_root=None):
    root = Path(local_root or Path(os.environ['LOCALAPPDATA']) / 'Aviatest' / 'aviatest_v4_data')
    writable(root)
    legacy = Path(app_dir) / 'aviatest_v4_data'
    marker = root / 'legacy_import.json'
    if legacy.is_dir() and legacy.resolve() != root.resolve() and not marker.exists():
        # Stage before activating, never overwrite files or invent participant accounts.
        if any(root.iterdir()):
            raise RuntimeError(f'Найдены две папки данных: {root} и {legacy}. '
                               'Для их объединения требуется отдельный перенос; файлы не изменены.')
        stage = root.parent / 'legacy-import-staging'
        if stage.exists():
            raise RuntimeError(f'Осталась незавершённая копия {stage}. Сохраните её перед повторным переносом.')
        shutil.copytree(legacy, stage)
        relocate_result_paths(stage, legacy, root)
        for item in stage.iterdir():
            shutil.move(str(item), str(root / item.name))
        stage.rmdir()
        marker.write_text(json.dumps({'source': str(legacy.resolve())}, ensure_ascii=False), encoding='utf-8')
    seed_configs(root, resources)
    return root


def relocate_result_paths(staging, legacy, target):
    """Detailed reports can contain absolute paths inside the old data directory."""
    def relocate(value):
        if isinstance(value, dict):
            return {key: relocate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relocate(item) for item in value]
        if isinstance(value, str):
            try:
                path = Path(value)
                if path.is_absolute() and path.is_relative_to(legacy):
                    return str(target / path.relative_to(legacy))
            except (OSError, ValueError):
                pass
        return value
    for path in Path(staging).rglob('*.json'):
        try:
            original = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError):
            continue  # Preserve even an unreadable legacy file as-is.
        moved = relocate(original)
        if moved != original:
            path.write_text(json.dumps(moved, ensure_ascii=False, indent=2), encoding='utf-8')


def seed_configs(root, resources, replace=False):
    root, resources = Path(root), Path(resources)
    root.mkdir(parents=True, exist_ok=True)
    for name in (*CONFIGS, 'red_black_data/settings.json'):
        source, target = resources / name, root / name
        if source.is_file() and (replace or not target.exists()):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def participant_directory(root, participant_id):
    if len(participant_id) != 32 or any(c not in '0123456789abcdef' for c in participant_id):
        raise ValueError('Некорректный идентификатор участника.')
    return Path(root) / 'participants' / participant_id
