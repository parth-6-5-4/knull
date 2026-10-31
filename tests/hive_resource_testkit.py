"""Frozen pre-resource v1 DDL and disposable historical reconciliation helpers."""
import hashlib
import json
import sqlite3

V1_SCHEMA = "\nCREATE TABLE IF NOT EXISTS runs(\n  id TEXT PRIMARY KEY, objective TEXT, status TEXT, budget_tokens INTEGER,\n  created REAL, report TEXT, gate TEXT);\nCREATE TABLE IF NOT EXISTS tasks(\n  id TEXT PRIMARY KEY, run_id TEXT, topic_key TEXT, kind TEXT, title TEXT,\n  payload TEXT, deps TEXT, status TEXT DEFAULT 'pending', owner TEXT,\n  attempt INTEGER DEFAULT 0, fence INTEGER DEFAULT 0, lease_expires REAL,\n  result TEXT, UNIQUE(run_id, topic_key));\nCREATE TABLE IF NOT EXISTS evidence(\n  id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id, id));\nCREATE TABLE IF NOT EXISTS facts(\n  id TEXT PRIMARY KEY, run_id TEXT, task_id TEXT, claim TEXT, evidence_id TEXT,\n  quote TEXT, status TEXT DEFAULT 'proposed', note TEXT);\nCREATE TABLE IF NOT EXISTS events(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, kind TEXT, data TEXT);\nCREATE TABLE IF NOT EXISTS ledger(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, layer TEXT, agent TEXT,\n  provider TEXT, model TEXT, in_tok INTEGER, out_tok INTEGER);\n"
OLD_TABLES = ('runs','tasks','evidence','facts','events','ledger')

def v1_database(path):
    with sqlite3.connect(path) as db:
        db.executescript(V1_SCHEMA)
        db.execute('PRAGMA user_version=1')
        db.execute("INSERT INTO runs VALUES('r','objective','running',200000,1.0,?,?)", ('historical\nreport \u03bb', '{"ok":true}'))
        db.execute("INSERT INTO tasks(id,run_id,topic_key,kind,title,payload,deps,status) VALUES('t','r','key','write','title','{}','[]','claimed')")
        db.execute("INSERT INTO evidence VALUES('e','r','s','title','url','text')")
        db.execute("INSERT INTO facts VALUES('f','r','t','claim','e','text','verified','note')")
        db.execute("INSERT INTO events VALUES(1,'r',1.0,'event','{}')")
        db.execute("INSERT INTO ledger VALUES(1,'r',1.0,'layer','agent','provider','model',7,11)")
    return path

def historical_digests(path):
    with sqlite3.connect(path) as db:
        return {t: hashlib.sha256(json.dumps(db.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall(),ensure_ascii=False).encode()).hexdigest() for t in OLD_TABLES}

FROZEN_V1_VALIDATOR = '"""Versioned SQLite shape validation. Legacy data requires explicit offline maintenance."""\nfrom __future__ import annotations\n\nimport sqlite3\nimport re\n\nHIVE_SCHEMA_VERSION = 1\nSCHEMA = """\nCREATE TABLE IF NOT EXISTS runs(\n  id TEXT PRIMARY KEY, objective TEXT, status TEXT, budget_tokens INTEGER,\n  created REAL, report TEXT, gate TEXT);\nCREATE TABLE IF NOT EXISTS tasks(\n  id TEXT PRIMARY KEY, run_id TEXT, topic_key TEXT, kind TEXT, title TEXT,\n  payload TEXT, deps TEXT, status TEXT DEFAULT \'pending\', owner TEXT,\n  attempt INTEGER DEFAULT 0, fence INTEGER DEFAULT 0, lease_expires REAL,\n  result TEXT, UNIQUE(run_id, topic_key));\nCREATE TABLE IF NOT EXISTS evidence(\n  id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id, id));\nCREATE TABLE IF NOT EXISTS facts(\n  id TEXT PRIMARY KEY, run_id TEXT, task_id TEXT, claim TEXT, evidence_id TEXT,\n  quote TEXT, status TEXT DEFAULT \'proposed\', note TEXT);\nCREATE TABLE IF NOT EXISTS events(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, kind TEXT, data TEXT);\nCREATE TABLE IF NOT EXISTS ledger(\n  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, layer TEXT, agent TEXT,\n  provider TEXT, model TEXT, in_tok INTEGER, out_tok INTEGER);\n"""\n\n\nclass HiveSchemaError(RuntimeError):\n    """An unrecognized/unsupported database must not be opened writable."""\n\n\nclass HiveMigrationRequired(HiveSchemaError):\n    """A recognized legacy database needs the stopped-writer migration."""\n\n\ndef _shape(db):\n    objects = list(db.execute("SELECT type,name,tbl_name FROM sqlite_master WHERE name NOT LIKE \'sqlite_%\' ORDER BY type,name"))\n    tables = [tuple(r) for r in objects]\n    columns = {r[1]: [tuple(c) for c in db.execute(f\'PRAGMA table_info("{r[1]}")\')]\n               for r in objects if r[0] == \'table\' and r[1] in {\'runs\',\'tasks\',\'evidence\',\'facts\',\'events\',\'ledger\'}}\n    indexes = {}\n    for name in columns:\n        indexes[name] = sorted((r[2],r[3],r[4],tuple(c[2] for c in db.execute(f\'PRAGMA index_info("{r[1]}")\')))\n                               for r in db.execute(f\'PRAGMA index_list("{name}")\'))\n    # Column/index pragmas omit CHECK, FK, collation and generated definitions.\n    # Accept only the known DDL, allowing SQLite\'s rename quoting/spacing.\n    definitions = {}\n    for row in db.execute("SELECT name,sql FROM sqlite_master WHERE type=\'table\' AND name NOT LIKE \'sqlite_%\'"):\n        ddl = re.sub(r\'\\bIF\\s+NOT\\s+EXISTS\\b\', \'\', row[1], flags=re.I)\n        definitions[row[0]] = re.sub(r\'[\\s"`\\[\\]]+\', \'\', ddl).lower()\n    return tables, columns, indexes, definitions\n\n\ndef _expected(version):\n    ddl = SCHEMA\n    if version == 0:\n        ddl = ddl.replace(\'id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id, id)\',\n                          \'id TEXT PRIMARY KEY, run_id TEXT, source_id TEXT, title TEXT, url TEXT, text TEXT\')\n    db = sqlite3.connect(\':memory:\')\n    try:\n        db.executescript(ddl)\n        return _shape(db)\n    finally:\n        db.close()\n\n\n_EXPECTED = {version: _expected(version) for version in (0, 1)}\n\n\ndef inspect_hive_schema(db: sqlite3.Connection) -> dict:\n    version = db.execute(\'PRAGMA user_version\').fetchone()[0]\n    if version not in _EXPECTED or _shape(db) != _EXPECTED[version]:\n        raise HiveSchemaError(\'Unsupported or incomplete hive schema; stop writers and inspect a recoverable copy.\')\n    if db.execute(\'SELECT 1 FROM evidence WHERE run_id IS NULL OR id IS NULL LIMIT 1\').fetchone():\n        raise HiveSchemaError(\'Legacy evidence has NULL identity; explicit provenance repair required.\')\n    missing = db.execute("SELECT f.run_id,COUNT(*) FROM facts f WHERE NOT EXISTS "\n                         "(SELECT 1 FROM evidence e WHERE e.run_id=f.run_id AND e.id=f.evidence_id) GROUP BY f.run_id").fetchall()\n    return {\'schema_version\': version, \'migration_required\': version == 0,\n            \'evidence_count\': db.execute(\'SELECT COUNT(*) FROM evidence\').fetchone()[0],\n            \'unresolved_facts_by_run\': {str(r[0]): r[1] for r in missing}}\n\n\ndef initialize_hive_schema(db: sqlite3.Connection) -> None:\n    db.execute(\'BEGIN IMMEDIATE\')\n    try:\n        empty = not db.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE \'sqlite_%\' LIMIT 1").fetchone()\n        if empty and db.execute(\'PRAGMA user_version\').fetchone()[0] == 0:\n            for statement in SCHEMA.split(\';\'):\n                if statement.strip(): db.execute(statement)\n            db.execute(\'PRAGMA user_version=1\')\n        info = inspect_hive_schema(db)\n        if info[\'migration_required\']:\n            raise HiveMigrationRequired(\'Stop writers; run python -m app.hive.migrate --db PATH --check, then --apply --backup BACKUP.\')\n        db.execute(\'COMMIT\')\n    except BaseException:\n        db.execute(\'ROLLBACK\')\n        raise\n'


def prepared_call(run_id, allocation_id='root', call_id='call', **changes):
    import time
    from app.hive.resource_types import PreparedCall, CallAuthority, RunAuthority
    values = dict(call_id=call_id, authority=CallAuthority(RunAuthority(run_id,'owner',1), allocation_id,'planner',None,None,None,None,1), provider='fake',model='model',endpoint_id='local',profile_digest='profile',sdk_version='test',request_fingerprint='fingerprint',messages=({'role':'user','content':'hello'},),temperature=0,max_output_tokens=10,bound_tokens=50,budget_mode='hard',expires_at_utc=time.time()+600)
    values.update(changes)
    return PreparedCall(**values)


def usage_receipt(total=30, **changes):
    from app.hive.resource_types import UsageReceipt
    values = dict(receipt_id='receipt',receipt_digest='digest',provider='fake',requested_model='model',resolved_model='model',request_id='remote',input_tokens=20,output_tokens=10,total_tokens=total,categories={'disjoint':{'input':20,'output':10}},usage_complete=True,execution_terminal=True)
    values.update(changes)
    return UsageReceipt(**values)


def attach_resource_run(hive, run_id, allocation_id='root', **changes):
    """Persist admission-owned metadata for resource-store tests, without a provider."""
    import time
    from app.hive.resource_types import ResourcePolicy
    policy=ResourcePolicy()
    def attach(db):
        db.execute('INSERT OR IGNORE INTO resource_policy VALUES(1,?,?)',(policy.digest,policy.canonical_json))
        db.execute("INSERT OR IGNORE INTO resource_profiles VALUES('profile','{}')")
        values=dict(run_id=run_id,allocation_id=allocation_id,request_json='{}',policy_digest=policy.digest,profile_digest='profile',budget_mode='hard',accepted_at_utc=time.time(),expires_at_utc=time.time()+600,state='active',sequence=1,origin_id='test',replayable=1,owner_id='owner',fence=1,lease_expires_at_utc=time.time()+600)
        values.update(changes)
        columns=','.join(values)
        db.execute(f'INSERT INTO resource_runs({columns}) VALUES({",".join("?" for _ in values)})',tuple(values.values()))
    hive.transactions.write(attach)
