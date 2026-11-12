"""Numbered test groups and assignment-based activation, separate from credentials."""
from pathlib import Path
import json
import sqlite3
import shutil

from accounts import AccountStore
from storage import CONFIGS, seed_configs, participant_directory
from surface_norms import read_norms,write_norms


def group_number(value):
    text = str(value).strip()
    if not text.isascii() or not text.isdigit() or not 1 <= int(text) <= 999999999:
        raise ValueError('Номер группы — целое число от 1 до 999999999.')
    return int(text)


class GroupStore:
    def __init__(self, root):
        self.root = Path(root)
        self.accounts = AccountStore(root)
        with self.accounts.connect() as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='study_groups'").fetchone()
        if not exists:
            backup = self.root / 'backups' / 'before_groups_v45.sqlite3'
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                with self.accounts.connect() as source, sqlite3.connect(backup) as destination:
                    source.backup(destination)
        seed_configs(self.directory(1), self.root)
        with self.accounts.connect() as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            migration_needed = not db.execute("SELECT 1 FROM sqlite_master WHERE name='study_groups'").fetchone()
            db.execute('''CREATE TABLE IF NOT EXISTS study_groups (
                number INTEGER PRIMARY KEY CHECK(number>0),
                test_count INTEGER NOT NULL CHECK(test_count IN (4,6)))''')
            db.execute('''CREATE TABLE IF NOT EXISTS group_memberships (
                participant_id TEXT PRIMARY KEY REFERENCES accounts(participant_id),
                group_number INTEGER NOT NULL REFERENCES study_groups(number))''')
            db.execute('INSERT OR IGNORE INTO study_groups VALUES (1,6)')
            if migration_needed:
                # Existing accounts remain usable; later registrations are pending.
                db.execute('INSERT OR IGNORE INTO group_memberships SELECT participant_id,1 FROM accounts')
            demo_table = db.execute("SELECT 1 FROM sqlite_master WHERE name='aviatest_demo_accounts'").fetchone()
            if demo_table:
                db.execute('''INSERT OR IGNORE INTO group_memberships
                    SELECT participant_id,1 FROM aviatest_demo_accounts''')

    def directory(self, number):
        return self.root / 'groups' / str(group_number(number))

    def list_groups(self):
        with self.accounts.connect() as db:
            return [dict(number=r[0], test_count=r[1], participants=r[2]) for r in db.execute('''
                SELECT g.number,g.test_count,COUNT(m.participant_id) FROM study_groups g
                LEFT JOIN group_memberships m ON m.group_number=g.number
                GROUP BY g.number ORDER BY g.number''')]

    def get(self, number):
        number = group_number(number)
        with self.accounts.connect() as db:
            row = db.execute('SELECT number,test_count FROM study_groups WHERE number=?', (number,)).fetchone()
        if row is None:
            raise ValueError('Группа не найдена.')
        return dict(number=row[0], test_count=row[1])

    def create(self, number, test_count, template=1):
        number = group_number(number)
        if test_count not in (4, 6):
            raise ValueError('Выберите четыре или шесть тестов.')
        self.get(template)
        target = self.directory(number)
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM study_groups WHERE number=?', (number,)).fetchone():
                raise ValueError('Группа с таким номером уже существует.')
            if target.exists():
                raise ValueError('Папка этой группы уже существует. Выберите другой номер.')
            seed_configs(target, self.directory(template))
            db.execute('INSERT INTO study_groups VALUES (?,?)', (number, test_count))
        return self.get(number)

    def set_variant(self, number, test_count):
        if test_count not in (4, 6):
            raise ValueError('Выберите четыре или шесть тестов.')
        self.get(number)
        with self.accounts.connect() as db:
            db.execute('UPDATE study_groups SET test_count=? WHERE number=?', (test_count, group_number(number)))

    def membership(self, identifier):
        with self.accounts.connect() as db:
            row = db.execute('''SELECT g.number,g.test_count FROM group_memberships m
                JOIN study_groups g ON g.number=m.group_number WHERE m.participant_id=?''', (identifier,)).fetchone()
        return dict(number=row[0], test_count=row[1]) if row else None

    def assign(self, identifier, number):
        self.assign_many([identifier], number)

    def assign_many(self, identifiers, number):
        number = self.get(number)['number']
        with self.accounts.connect() as db:
            db.execute('PRAGMA foreign_keys=ON')
            for identifier in identifiers:
                if not db.execute('SELECT 1 FROM accounts WHERE participant_id=?', (identifier,)).fetchone():
                    raise ValueError('Участник не найден.')
                db.execute('''INSERT INTO group_memberships VALUES (?,?)
                    ON CONFLICT(participant_id) DO UPDATE SET group_number=excluded.group_number''', (identifier, number))

    def participants(self):
        with self.accounts.connect() as db:
            rows = db.execute('''SELECT a.participant_id,a.login,a.profile,m.group_number
                FROM accounts a LEFT JOIN group_memberships m ON m.participant_id=a.participant_id
                ORDER BY (m.group_number IS NOT NULL),a.login''').fetchall()
        return [dict(participant_id=r[0], login=r[1], profile=json.loads(r[2]), group=r[3]) for r in rows]

    def codes(self, identifier):
        member = self.membership(identifier)
        if not member:return ()
        allowed=set('ABCDEF'[:member['test_count']])
        return tuple(code for code in ('A','C','D','E','F','B') if code in allowed)

    def prepare_participant(self, identifier):
        member = self.membership(identifier)
        if member is None:
            raise ValueError('Учётная запись ожидает назначения группы исследователем.')
        directory = participant_directory(self.root, identifier)
        seed_configs(directory, self.directory(member['number']), replace=True)
        try:
            norms=read_norms(self.directory(member['number']))
        except (ValueError,OSError):
            norms=[None]*3
        # A pre-4.6 group may have no norm file; never inherit the previous group's values.
        write_norms(directory,norms)
        return directory, member


def group_progress_store(base, directory, codes, member):
    class GroupProgressStore(base.UserProgressStore):
        def next_test_code(self, profile):
            completed = set(self.get_progress(profile).get('completed_tests', []))
            return next((code for code in codes if code not in completed), None)

        def save_test_result(self, profile, code, payload):
            if code not in codes:
                raise ValueError('Эта методика недоступна назначенной группе.')
            payload = dict(payload)
            payload['study_group'] = dict(member)
            # Preserve the exact group settings used for this saved attempt.
            snapshot = {}
            for name in (*CONFIGS, 'red_black_data/settings.json'):
                path = Path(directory) / name
                if path.suffix == '.json' and path.exists():
                    snapshot[name] = json.loads(path.read_text(encoding='utf-8-sig'))
            payload['group_settings'] = snapshot
            return super().save_test_result(profile, code, payload)
    return GroupProgressStore(directory)
