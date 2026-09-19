"""Create a development faculty account from explicit CLI input; no credentials are embedded."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import init_db, connect
from werkzeug.security import generate_password_hash

parser=argparse.ArgumentParser(); parser.add_argument('--name',required=True); parser.add_argument('--email',required=True); parser.add_argument('--password',required=True)
args=parser.parse_args(); init_db()
with connect() as db:
    db.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',(args.name,args.email.lower(),generate_password_hash(args.password),'faculty'))
print('Faculty account created.')
