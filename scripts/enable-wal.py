import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=ROOT/'.data/db/acpedia.sqlite'
import sqlite3
with sqlite3.connect(p,timeout=30) as db:print('SQLite journal:',db.execute('PRAGMA journal_mode=WAL').fetchone()[0])
