"""Explicitly requested sample accounts. All measurements are synthetic and labelled."""
from dataclasses import asdict
import json
import secrets
import uuid

from accounts import AccountStore, ITERATIONS, account_profile, password_hash
from storage import participant_directory, seed_configs

DEMO_REVISION = 3
# Distinct, moderate synthetic results near r=1.0. These are not clinical norms.
# Order A,C,D,E,F,B; stages MIN/MED/MAX. B is raw accuracy, compared with 80% only in DEMO.
DEMO_VALUES = (
    ((1.08,1.03,.97),(1.10,1.01,.95),(.99,1.05,1.02),(1.07,1.00,.94),(1.04,.98,1.01),(.84,.80,.76)),
    ((.96,1.00,1.06),(1.02,1.08,1.04),(.94,.99,1.05),(.98,1.06,1.11),(.95,1.03,1.08),(.77,.82,.86)),
    ((1.03,.95,1.02),(.98,1.06,.99),(1.07,1.01,.96),(1.00,.94,1.04),(1.08,1.02,.97),(.82,.78,.83)),
    ((1.10,1.07,1.01),(1.04,1.00,.96),(1.12,1.05,1.00),(1.06,1.09,1.02),(1.03,1.07,.99),(.86,.84,.80)),
    ((.94,.99,1.03),(1.00,.95,1.02),(.97,1.04,.98),(.92,1.00,1.06),(.99,.94,1.04),(.75,.80,.84)),
)


# Boris's 11 November "Испытуемый 7": red annotations replace 13 values.
# Unannotated A-med, C-med, F-min, F-med and B-min retain the reference values.
# B is stored as raw accuracy; with the explicit 80% demo norm it displays
# the requested relative values (1.05, .8, .7).
USER7_VALUES = ((1.4,1.03,.5),(1.2,1.01,.4),(1.2,.8,.3),(.8,.7,.5),(1.04,.98,.8),(.84,.64,.56))
DEMO_INDICES = (1,2,3,4,5,7)


def _needs_demo_repair(v,root,identifier,fields):
    """Revision markers alone do not prove that all demo files still exist."""
    profile=account_profile(v.base,identifier,json.loads(fields))
    store=v.base.UserProgressStore(participant_directory(root,identifier))
    payloads={code:store.get_test_result(profile,code) for code in v.ORDER}
    values=v.extract_values(payloads)
    for code,payload in payloads.items():
        if not payload:return True
        if payload.get('data_source')=='synthetic_demo':
            triple=values[code]
            if any(value is None for value in triple) or all(value==0 for value in triple):return True
    return False


def demo_payloads(index, profile):
    values = USER7_VALUES if index == 7 else DEMO_VALUES[index - 1]
    revision=4 if index==7 else DEMO_REVISION
    common = {'session_id': f'demo-user{index}-synthetic-v{revision}',
              'demonstration': True, 'data_source': 'synthetic_demo', 'demo_revision': revision,
              'participant': {k: value for k, value in asdict(profile).items()},
              'notice': 'Демонстрационные данные; не результаты обследования.'}
    payloads = {}
    for offset, (code, suffix) in enumerate((('A', 'a'), ('C', 'b'), ('D', 'c'), ('E', 'd'))):
        triple = values[offset]
        payloads[code] = {**common, 'test_code': code, 'summary': {
            f'tmin_{suffix}': triple[0],
            f'tmedio_{suffix}': triple[1],
            f'tmax_{suffix}': triple[2]}}
    payloads['B'] = {**common, 'test_code': 'B', 'demo_orientation_norm_pct': [80,80,80], 'stages': {
        str(stage): {'tasks': 100, 'accuracy_pct': round(values[5][stage - 1] * 100)}
        for stage in range(1, 4)}}
    payloads['F'] = {**common, 'test_code': 'F', 'stages': [
        {'stage': stage, 'table_pace': pace,
         'errors': max(0, 6 - index - stage), 'duration': 100 + stage * 15}
        for stage, pace in enumerate(values[4], 1)]}
    return payloads


def ensure_demo_accounts(v, root):
    """Create once, resume interrupted provisioning; never claim an existing login."""
    accounts = AccountStore(root)
    with accounts.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS aviatest_demo_accounts (
            login TEXT PRIMARY KEY, participant_id TEXT UNIQUE NOT NULL,
            initialized INTEGER NOT NULL DEFAULT 0, data_revision INTEGER NOT NULL DEFAULT 0)''')
        if 'data_revision' not in {row[1] for row in db.execute('PRAGMA table_info(aviatest_demo_accounts)')}:
            db.execute('ALTER TABLE aviatest_demo_accounts ADD COLUMN data_revision INTEGER NOT NULL DEFAULT 0')
        for index in DEMO_INDICES:
            login = f'user{index}'
            if db.execute('SELECT 1 FROM accounts WHERE login=?', (login,)).fetchone():
                continue
            profile = v.base.UserProfile(name=('ДЕМО — Испытуемый 7 (user7)' if index == 7 else f'ДЕМО — тестовый пользователь {login}'), age=25 + index * 4,
                gender='Женский' if index % 2 == 0 else 'Мужской', flight_hours=str(index * 500),
                aircraft_type='Демонстрационное ВС', position='Тестовый участник', education='Высшее')
            identifier, salt = uuid.uuid4().hex, secrets.token_bytes(32)
            password = f'password{index}'
            db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?)', (
                login, identifier, salt, password_hash(password, salt), ITERATIONS,
                json.dumps(asdict(profile), ensure_ascii=False)))
            db.execute('INSERT INTO aviatest_demo_accounts (login,participant_id) VALUES (?,?)', (login, identifier))
        candidates = db.execute('''SELECT d.login,d.participant_id,a.profile,d.initialized,d.data_revision FROM aviatest_demo_accounts d
            JOIN accounts a ON a.participant_id=d.participant_id
            ''').fetchall()
    pending=[(login,identifier,fields) for login,identifier,fields,initialized,revision in candidates
             if not initialized or revision<(4 if login=='user7' else DEMO_REVISION)
             or _needs_demo_repair(v,root,identifier,fields)]
    for login, identifier, fields in pending:
        profile = account_profile(v.base, identifier, json.loads(fields))
        directory = participant_directory(root, identifier)
        seed_configs(directory, root)
        store = v.base.UserProgressStore(directory)
        if store.progress_file.exists():
            from datetime import datetime
            backup=directory/'backups'/f'before-demo-repair-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():backup.write_bytes(store.progress_file.read_bytes())
            revision_backup=backup.parent/f'before-demo-revision-{DEMO_REVISION}.json'
            if not revision_backup.exists():revision_backup.write_bytes(store.progress_file.read_bytes())
        store.ensure_user(profile)
        for code, payload in demo_payloads(int(login[-1]), profile).items():
            existing = store.get_test_result(profile, code)
            if existing and existing.get('data_source') != 'synthetic_demo':
                continue
            store.save_test_result(profile, code, payload)
            store.mark_completed(profile, code)
        records = store._load()
        records[profile.key]['demonstration'] = True
        store._save(records)
        with accounts.connect() as db:
            db.execute('UPDATE aviatest_demo_accounts SET initialized=1,data_revision=? WHERE participant_id=?',
                       (4 if login=='user7' else DEMO_REVISION, identifier))
    return {login for login, _ in _demo_logins(accounts)}


def _demo_logins(accounts):
    with accounts.connect() as db:
        return db.execute('SELECT login,participant_id FROM aviatest_demo_accounts').fetchall()
