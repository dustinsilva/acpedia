"""Report local restoration counts without exposing credentials or source prose."""
import json,pathlib,sqlite3
ROOT=pathlib.Path(__file__).resolve().parents[1];db=sqlite3.connect(ROOT/'.data/db/acpedia.sqlite',timeout=30)
counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in ['page','revision','image','categorylinks','pagelinks','templatelinks','searchindex']}
print(json.dumps(counts,indent=2));db.close()
