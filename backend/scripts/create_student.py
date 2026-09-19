"""Create a student login account from explicit CLI input; no credentials are embedded."""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import connect, init_db
from werkzeug.security import generate_password_hash

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--email', required=True)
parser.add_argument('--password', required=True)
args = parser.parse_args()

init_db()
try:
    with connect() as db:
        cursor = db.execute(
            'INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',
            (args.name, args.email.lower(), generate_password_hash(args.password), 'student'),
        )
        db.execute(
            'INSERT INTO students(user_id,student_id,features_json) VALUES(?,?,?)',
            (cursor.lastrowid, f'student-{cursor.lastrowid}', '{}'),
        )
except sqlite3.IntegrityError:
    parser.error('A user with that email already exists.')

print('Student account created.')
