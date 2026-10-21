"""Frozen pre-HIVE-001 data and test-only lifecycle helpers."""
import sqlite3

LEGACY_SCHEMA = "\nCREATE TABLE IF NOT EXISTS runs(\n  id TEXT PRIMARY KEY, objective TEXT, status TEXT, budget_tokens INTEGER,\n  created REAL, report TEXT, gate TEXT);\nCREATE TABLE IF NOT EXISTS tasks(\n  id TEXT PRIMARY KEY, run_id TEXT, topic_key TEXT, kind TEXT, title TEXT,\n  payload TEXT, deps TEXT, status TEXT DEFAULT 'pending', owner TEXT,\n  attempt INTEGER DEFAULT 0, fence INTEGER DEFAULT 0, lease_expires REAL,\n  result TEXT, UNIQUE(run_id, topic_key));\nCREATE TABLE IF NOT EXISTS evidence(\n  id TEXT PRIMARY KEY, run_id TEXT, source_id TEXT, title TEXT, url TEXT, text TEXT);\nCREATE TABLE IF NOT EXISTS facts(\n  id TEXT PRIMARY KEY, run_id TEXT, task_id TEXT, claim TEXT, evidence_id TEXT,\n  quote TEXT, status TEXT DEFAULT 'proposed', note TEXT);\nCREATE TABLE IF NOT EXISTS events(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, kind TEXT, data TEXT);\nCREATE TABLE IF NOT EXISTS ledger(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, layer TEXT, agent TEXT,\n  provider TEXT, model TEXT, in_tok INTEGER, out_tok INTEGER);\n"

def legacy_database(path):
    db = sqlite3.connect(path)
    db.executescript(LEGACY_SCHEMA)
    db.execute("INSERT INTO runs VALUES('old','history','done',1000,1,'historical report','{}')")
    db.execute("INSERT INTO runs VALUES('other','history','done',1000,1,'other report','{}')")
    db.execute("INSERT INTO evidence VALUES('E-old','old','s','Original','https://source','original text')")
    db.execute("INSERT INTO evidence VALUES('E-foreign','other','s2','Foreign','https://foreign','foreign text')")
    db.execute("INSERT INTO facts VALUES('F-good','old','r','valid','E-old','original','verified','unchanged')")
    db.execute("INSERT INTO facts VALUES('F-bad','old','r','orphan','E-foreign','foreign','verified','unchanged')")
    db.commit()
    db.close()
    return path

def snapshot(path):
    with sqlite3.connect(path) as db:
        return '\n'.join(db.iterdump())
