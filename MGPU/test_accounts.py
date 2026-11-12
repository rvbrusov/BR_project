import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import pytest
import aviatest_v4 as v
from accounts import AccountStore, account_profile, verify_admin
import installer
from storage import prepare_storage, participant_directory


def profile():
    return v.base.UserProfile(name='Одинаковые ФИО', age=30, gender='Мужской',
                              flight_hours='120,5', aircraft_type='Ту-204', position='Пилот', education='Высшее')


def test_account_restart_hash_and_identity(tmp_path):
    accounts = AccountStore(tmp_path)
    first = accounts.register(' Pilot ', 'test-only-1', 'test-only-1', profile())
    second = accounts.register('second', 'test-only-1', 'test-only-1', profile())
    assert first[0] != second[0]
    assert AccountStore(tmp_path).authenticate('PILOT', 'test-only-1') == first
    assert accounts.authenticate('pilot', 'bad') is None
    assert accounts.authenticate('missing', 'bad') is None
    with sqlite3.connect(accounts.path) as db:
        rows = db.execute('SELECT salt,digest,iterations,profile FROM accounts').fetchall()
    assert rows[0][0] != rows[1][0] and rows[0][1] != rows[1][1]
    assert all(row[2] >= 600000 and 'test-only-1' not in row[3] for row in rows)
    assert b'test-only-1' not in accounts.path.read_bytes()


@pytest.mark.parametrize('login,password,confirmation,message', [
    ('admin', 'a', 'a', 'зарезервирован'), ('ＡＤＭＩＮ', 'a', 'a', 'зарезервирован'),
    ('', 'a', 'a', 'логин'), ('a b', 'a', 'a', 'логин'),
    ('pilot', '', '', 'пароль'), ('pilot', 'a', 'b', 'совпадают')])
def test_invalid_credentials(tmp_path, login, password, confirmation, message):
    with pytest.raises(ValueError, match=message):
        AccountStore(tmp_path).register(login, password, confirmation, profile())


def test_duplicate_login(tmp_path):
    accounts = AccountStore(tmp_path)
    accounts.register('PILOT', 'a', 'a', profile())
    with pytest.raises(ValueError, match='занят'):
        accounts.register('pilot', 'b', 'b', profile())


def test_administrator():
    assert verify_admin('admin', 'nowayin!')
    assert not verify_admin('admin', 'wrong')
    assert not verify_admin('pilot', 'nowayin!')


def test_identical_names_are_independent_after_restart(tmp_path):
    ids = [AccountStore(tmp_path).register(login, 'a', 'a', profile())[0] for login in ('one', 'two')]
    profiles = [account_profile(v.base, identifier, asdict(profile())) for identifier in ids]
    stores = [v.base.UserProgressStore(participant_directory(tmp_path, identifier)) for identifier in ids]
    stores[0].mark_completed(profiles[0], 'A')
    stores[0].save_test_result(profiles[0], 'F', {'stages': [{'stage': 1, 'table_pace': 1.2}]})
    restarted = v.base.UserProgressStore(participant_directory(tmp_path, ids[0]))
    assert restarted.next_test_code(profiles[0]) == 'B'
    assert stores[1].next_test_code(profiles[1]) == 'A'
    assert stores[1].get_test_result(profiles[1], 'F') is None
    assert restarted.get_test_result(profiles[0], 'F')['stages'][0]['table_pace'] == 1.2


def test_legacy_migration_reinstall_keeps_bytes(tmp_path):
    app = tmp_path / 'Старая программа'
    legacy = app / 'aviatest_v4_data'
    (legacy / 'data').mkdir(parents=True)
    original = b'{"legacy-profile": {"results": {"F": {"stages": []}}}}'
    (legacy / 'data/user_progress.json').write_bytes(original)
    target = tmp_path / 'Local/data'
    prepare_storage(app, Path(__file__).parent, target)
    assert (target / 'data/user_progress.json').read_bytes() == original
    accounts = AccountStore(target)
    record = accounts.register('pilot', 'test-only', 'test-only', profile())
    prepare_storage(app, Path(__file__).parent, target)
    assert AccountStore(target).authenticate('pilot', 'test-only') == record
    assert (legacy / 'data/user_progress.json').read_bytes() == original


def test_two_data_directories_never_silently_overwrite(tmp_path):
    (tmp_path / 'app/aviatest_v4_data').mkdir(parents=True)
    target = tmp_path / 'Local/data'
    target.mkdir(parents=True)
    (target / 'keep.txt').write_text('keep')
    with pytest.raises(RuntimeError, match='две папки'):
        prepare_storage(tmp_path / 'app', Path(__file__).parent, target)
    assert (target / 'keep.txt').read_text() == 'keep'


def test_legacy_detailed_report_references_follow_copy(tmp_path):
    legacy = tmp_path / 'app/aviatest_v4_data'
    (legacy / 'data').mkdir(parents=True)
    report = legacy / 'data/report.json'
    report.write_text('[1,2,3]')
    original = {'result_path': str(report), 'name': 'Preserved'}
    (legacy / 'data/result.json').write_text(json.dumps(original))
    target = tmp_path / 'new-data'
    prepare_storage(legacy.parent, Path(__file__).parent, target)
    migrated = json.loads((target / 'data/result.json').read_text())
    assert Path(migrated['result_path']).read_text() == '[1,2,3]'
    assert Path(migrated['result_path']).is_relative_to(target)
    assert json.loads((legacy / 'data/result.json').read_text()) == original


def test_installer_exact_folder_existing_new_and_reinstall(tmp_path, monkeypatch):
    resources = tmp_path / 'resource'
    resources.mkdir()
    (resources / installer.EXE_NAME).write_bytes(b'packaged-exe-test')
    monkeypatch.setattr(installer, 'RESOURCE_DIR', resources)
    for name in ('Существующая папка', 'Новая папка/с пробелами'):
        destination = tmp_path / name
        if name.startswith('Существующая'):
            destination.mkdir()
        executable = installer.install(destination, create_shortcut=False)
        assert executable == destination / installer.EXE_NAME
        assert not (destination / 'Aviatest').exists()
        data = destination / 'aviatest_v4_data'
        data.mkdir()
        (data / 'keep.json').write_bytes(b'unchanged')
        installer.install(destination, create_shortcut=False)
        assert (data / 'keep.json').read_bytes() == b'unchanged'


def test_installer_write_error(tmp_path):
    destination = tmp_path / 'file'
    destination.write_text('file')
    with pytest.raises(OSError, match='записи'):
        installer.install(destination, create_shortcut=False)


@pytest.mark.parametrize('path', ['', 'relative/path'])
def test_installer_requires_explicit_absolute_path(path):
    with pytest.raises(ValueError):
        installer.install(path, create_shortcut=False)
