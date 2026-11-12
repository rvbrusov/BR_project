from pathlib import Path

import aviatest_v4 as v
from accounts import AccountStore, account_profile
from demo_accounts import ensure_demo_accounts
from storage import participant_directory, seed_configs


def test_five_demo_logins_distinct_complete_surfaces(tmp_path):
    seed_configs(tmp_path, Path(__file__).parent)
    assert len(ensure_demo_accounts(v, tmp_path)) == 6
    accounts = AccountStore(tmp_path)
    profiles = []
    surfaces = []
    for index in range(1, 6):
        record = accounts.authenticate(f'user{index}', f'password{index}')
        assert record is not None
        identifier, fields = record
        profile = account_profile(v.base, identifier, fields)
        assert 'ДЕМО' in profile.name
        profiles.append(profile)
        store = v.base.UserProgressStore(participant_directory(tmp_path, identifier))
        assert store.next_test_code(profile) is None
        payloads = {code: store.get_test_result(profile, code) for code in 'ABCDEF'}
        assert all(p['demonstration'] and p['data_source'] == 'synthetic_demo' for p in payloads.values())
        values = v.extract_values(payloads)
        assert all(value is not None for row in values.values() for value in row)
        assert all(.9<=value<=1.13 for code,row in values.items() if code!='B' for value in row)
        assert payloads['B']['demo_orientation_norm_pct']==[80,80,80]
        assert all(f'password{index}' not in path.read_text(encoding='utf-8')
                   for path in participant_directory(tmp_path, identifier).rglob('*.json'))
        surfaces.append(tuple(tuple(values[c]) for c in v.ORDER))
    assert len({p.key for p in profiles}) == 5 and len(set(surfaces)) == 5


def test_demo_provisioning_never_overwrites_existing_login_or_later_results(tmp_path):
    accounts = AccountStore(tmp_path)
    profile = v.base.UserProfile(name='Existing participant', age=35, gender='Мужской')
    existing = accounts.register('user1', 'existing-only', 'existing-only', profile)
    assert len(ensure_demo_accounts(v, tmp_path)) == 5
    assert accounts.authenticate('user1', 'existing-only') == existing
    assert accounts.authenticate('user1', 'password1') is None
    identifier, fields = accounts.authenticate('user2', 'password2')
    profile = account_profile(v.base, identifier, fields)
    store = v.base.UserProgressStore(participant_directory(tmp_path, identifier))
    payload = store.get_test_result(profile, 'F')
    payload['stages'][0]['table_pace'] = 9.75
    store.save_test_result(profile, 'F', payload)
    before = store.progress_file.read_bytes()
    ensure_demo_accounts(v, tmp_path)
    assert store.progress_file.read_bytes() == before
    assert accounts.authenticate('user2', 'password2')[0] == identifier


def test_demo_revision_updates_only_synthetic_results(tmp_path):
    ensure_demo_accounts(v, tmp_path)
    accounts = AccountStore(tmp_path)
    identifier, fields = accounts.authenticate('user3', 'password3')
    profile = account_profile(v.base, identifier, fields)
    store = v.base.UserProgressStore(participant_directory(tmp_path, identifier))
    real = {'summary': {'tmin_a': .7, 'tmedio_a': .8, 'tmax_a': .9}, 'data_source': 'real_test'}
    store.save_test_result(profile, 'A', real)
    old_demo = store.get_test_result(profile, 'F')
    old_demo['stages'][0]['table_pace'] = 9.75
    store.save_test_result(profile, 'F', old_demo)
    with accounts.connect() as db:
        db.execute('UPDATE aviatest_demo_accounts SET data_revision=1 WHERE participant_id=?', (identifier,))
    ensure_demo_accounts(v, tmp_path)
    assert store.get_test_result(profile, 'A')['summary'] == real['summary']
    assert store.get_test_result(profile, 'F')['stages'][0]['table_pace'] == 1.08
