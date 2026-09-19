import sqlite3
from config import DATABASE

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('faculty','student')),
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
 id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id), student_id TEXT UNIQUE NOT NULL,
 department TEXT, year TEXT, section TEXT, features_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS predictions (
 id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), predicted_score REAL NOT NULL,
 risk_level TEXT NOT NULL, snapshot_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS academic_snapshots (
 id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id),
 G1 REAL NOT NULL, G2 REAL NOT NULL, absences REAL NOT NULL,
 studytime REAL NOT NULL, failures REAL NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS interventions (
 id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), detected_factor TEXT,
 recommended_action TEXT NOT NULL, priority TEXT, notes TEXT, status TEXT NOT NULL DEFAULT 'Planned',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.executescript(SCHEMA)
        # SQLite does not add new columns through CREATE TABLE IF NOT EXISTS.
        # Keep legacy predictions intact and link only newly created ones.
        prediction_columns = {row['name'] for row in db.execute('PRAGMA table_info(predictions)')}
        if 'snapshot_id' not in prediction_columns:
            db.execute('ALTER TABLE predictions ADD COLUMN snapshot_id INTEGER')
        # A student login must always have a profile row. This only backfills
        # legacy logins that predate the student-profile creation flow.
        missing = db.execute(
            "SELECT id FROM users WHERE role='student' AND id NOT IN (SELECT user_id FROM students)"
        ).fetchall()
        for user in missing:
            db.execute(
                'INSERT INTO students(user_id,student_id,features_json) VALUES(?,?,?)',
                (user['id'], f"student-{user['id']}", '{}'),
            )
