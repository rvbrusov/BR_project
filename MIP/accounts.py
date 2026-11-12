"""Local credentials and immutable participant identities (no legacy auto-linking)."""
import hashlib
import hmac
import json
import math
import secrets
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

ITERATIONS = 600_000
ADMIN_LOGIN = 'admin'
ADMIN_SALT = bytes.fromhex('fd433a040a7fc04bfad0c082564a6584cc9101bffd6f6e622c74b0dc080d8ccf')
ADMIN_DIGEST = bytes.fromhex('75fd261ea345554ebfb574dc7f4b4e3a46815dd25d660e299e7079b8592c1a44')


def normalized_login(value):
    return unicodedata.normalize('NFKC', value).strip().casefold()


def password_hash(password, salt, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)


def verify_admin(login, password):
    return normalized_login(login) == ADMIN_LOGIN and hmac.compare_digest(
        password_hash(password, ADMIN_SALT), ADMIN_DIGEST)


class AccountStore:
    def __init__(self, root):
        self.path = Path(root) / 'accounts.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS accounts (
                login TEXT PRIMARY KEY, participant_id TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL, digest BLOB NOT NULL, iterations INTEGER NOT NULL,
                profile TEXT NOT NULL)''')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def register(self, login, password, confirmation, profile):
        login = normalized_login(login)
        if not login or len(login) > 80 or any(c.isspace() or unicodedata.category(c)[0] == 'C' for c in login):
            raise ValueError('Введите логин до 80 символов без пробелов.')
        if login == ADMIN_LOGIN:
            raise ValueError('Логин admin зарезервирован.')
        if not password:
            raise ValueError('Введите пароль.')
        if password != confirmation:
            raise ValueError('Пароли не совпадают.')
        if len(password) > 1024:
            raise ValueError('Пароль слишком длинный (не более 1024 символов).')
        participant_id = uuid.uuid4().hex
        salt = secrets.token_bytes(32)
        fields = asdict(profile)
        fields.pop('participant_id', None)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?)', (
                    login, participant_id, salt, password_hash(password, salt), ITERATIONS,
                    json.dumps(fields, ensure_ascii=False)))
        except sqlite3.IntegrityError:
            raise ValueError('Этот логин уже занят.') from None
        return participant_id, fields

    def authenticate(self, login, password):
        with self.connect() as db:
            row = db.execute('SELECT participant_id,salt,digest,iterations,profile FROM accounts WHERE login=?',
                             (normalized_login(login),)).fetchone()
        if row is None:
            password_hash(password, bytes(32))
            return None
        if not hmac.compare_digest(password_hash(password, row[1], row[3]), row[2]):
            return None
        return row[0], json.loads(row[4])

    def profiles(self):
        with self.connect() as db:
            return [(row[0], json.loads(row[1])) for row in
                    db.execute('SELECT participant_id,profile FROM accounts ORDER BY login')]


def account_profile(base, participant_id, fields):
    # Subclass rather than replace the legacy type; previous profiles retain their keys.
    @dataclass(frozen=True)
    class IdentifiedProfile(base.UserProfile):
        participant_id: str = ''

        @property
        def key(self):
            return 'account:' + self.participant_id

    allowed = {k: fields[k] for k in ('name', 'age', 'gender', 'flight_hours',
                                    'aircraft_type', 'position', 'education') if k in fields}
    return IdentifiedProfile(**allowed, participant_id=participant_id)


def finite_flight_hours(text):
    try:
        return math.isfinite(float(text.replace(',', '.')))
    except ValueError:
        return False


def registration_profile(base, values):
    """The shortened new-registration questionnaire; legacy profile fields stay intact."""
    name=values.get('name','').strip()
    age_text=values.get('age','').strip()
    education=values.get('education','').strip()
    gender=values.get('gender','').strip()
    if not name:
        raise ValueError('Введите ФИО.')
    if not age_text:
        raise ValueError('Введите возраст.')
    if not age_text.isdecimal():
        raise ValueError('Возраст должен быть целым числом лет.')
    try:
        age=int(age_text)
    except ValueError:
        raise ValueError('Возраст должен быть целым числом лет.') from None
    if not 1<=age<=120:
        raise ValueError('Возраст должен быть в диапазоне от 1 до 120 лет.')
    if not education:
        raise ValueError('Введите образование.')
    if gender not in ('Мужской','Женский'):
        raise ValueError('Выберите пол.')
    return base.UserProfile(name=name,age=age,gender=gender,education=education)
