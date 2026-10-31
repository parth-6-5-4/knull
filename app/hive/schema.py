"""Versioned SQLite shape validation. Legacy data requires explicit offline maintenance."""
from __future__ import annotations

import sqlite3
import re

from app.hive.resource_schema import RESOURCE_SCHEMA

HIVE_SCHEMA_VERSION = 2
V1_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY, objective TEXT, status TEXT, budget_tokens INTEGER,
  created REAL, report TEXT, gate TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, run_id TEXT, topic_key TEXT, kind TEXT, title TEXT,
  payload TEXT, deps TEXT, status TEXT DEFAULT 'pending', owner TEXT,
  attempt INTEGER DEFAULT 0, fence INTEGER DEFAULT 0, lease_expires REAL,
  result TEXT, UNIQUE(run_id, topic_key));
CREATE TABLE IF NOT EXISTS evidence(
  id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id, id));
CREATE TABLE IF NOT EXISTS facts(
  id TEXT PRIMARY KEY, run_id TEXT, task_id TEXT, claim TEXT, evidence_id TEXT,
  quote TEXT, status TEXT DEFAULT 'proposed', note TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS ledger(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, layer TEXT, agent TEXT,
  provider TEXT, model TEXT, in_tok INTEGER, out_tok INTEGER);
"""

SCHEMA = V1_SCHEMA + RESOURCE_SCHEMA


class HiveSchemaError(RuntimeError):
    """An unrecognized/unsupported database must not be opened writable."""


class HiveMigrationRequired(HiveSchemaError):
    """A recognized legacy database needs the stopped-writer migration."""


def _ddl_tokens(sql):
    """Normalize SQLite identifier quoting/spacing without changing SQL literals."""
    tokens = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|\[[^\]]*\]|\w+|[^\s]", sql)
    normalized = []
    for token in tokens:
        if token.startswith("'"):
            normalized.append(token)  # Case, spaces and escaped quotes are semantic.
        elif token[0] in ('"', '`', '['):
            normalized.append(token[1:-1].replace('""', '"').replace('``', '`').lower())
        else:
            normalized.append(token.lower())
    # SQLite omits IF NOT EXISTS on renamed tables. Only this DDL clause is optional.
    if normalized[:2] in (['create', 'table'], ['create', 'index']):
        if normalized[2:5] == ['if', 'not', 'exists']:
            del normalized[2:5]
    return tuple(normalized)


def _shape(db):
    objects = list(db.execute("SELECT type,name,tbl_name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name"))
    tables = [tuple(r) for r in objects]
    columns = {r[1]: [tuple(c) for c in db.execute('PRAGMA table_info("' + r[1].replace('"', '""') + '")')]
               for r in objects if r[0] == 'table'}
    indexes = {}
    for name in columns:
        entries = [(r[2], r[3], r[4], tuple(c[2] for c in db.execute(
            'PRAGMA index_info("' + r[1].replace('"', '""') + '")')))
            for r in db.execute('PRAGMA index_list("' + name.replace('"', '""') + '")')]
        # Expression indexes expose NULL column names. Unknown shapes must fail
        # validation rather than fail Python's mixed None/string ordering.
        indexes[name] = sorted(entries, key=repr)
    # Column/index pragmas omit CHECK, FK, collation and generated definitions.
    # Accept only the known DDL, allowing SQLite's rename quoting/spacing.
    definitions = {}
    for row in db.execute("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') AND sql IS NOT NULL AND name NOT GLOB 'sqlite_*'"):
        definitions[row[0]] = _ddl_tokens(row[1])
    return tables, columns, indexes, definitions


def _expected(version):
    ddl = SCHEMA if version == 2 else V1_SCHEMA
    if version == 0:
        ddl = ddl.replace('id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id, id)',
                          'id TEXT PRIMARY KEY, run_id TEXT, source_id TEXT, title TEXT, url TEXT, text TEXT')
    db = sqlite3.connect(':memory:')
    try:
        db.executescript(ddl)
        return _shape(db)
    finally:
        db.close()


_EXPECTED = {version: _expected(version) for version in (0, 1, 2)}


def inspect_hive_schema(db: sqlite3.Connection) -> dict:
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in _EXPECTED or _shape(db) != _EXPECTED[version]:
        raise HiveSchemaError('Unsupported or incomplete hive schema; stop writers and inspect a recoverable copy.')
    if version == 2 and db.execute('PRAGMA foreign_key_check').fetchone():
        raise HiveSchemaError('Resource foreign-key integrity violation; inspect a recoverable copy.')
    if db.execute('SELECT 1 FROM evidence WHERE run_id IS NULL OR id IS NULL LIMIT 1').fetchone():
        raise HiveSchemaError('Legacy evidence has NULL identity; explicit provenance repair required.')
    missing = db.execute("SELECT f.run_id,COUNT(*) FROM facts f WHERE NOT EXISTS "
                         "(SELECT 1 FROM evidence e WHERE e.run_id=f.run_id AND e.id=f.evidence_id) GROUP BY f.run_id").fetchall()
    return {'schema_version': version, 'migration_required': version < HIVE_SCHEMA_VERSION,
            'evidence_count': db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0],
            'unresolved_facts_by_run': {str(r[0]): r[1] for r in missing}}


def initialize_hive_schema(db: sqlite3.Connection) -> None:
    db.execute('BEGIN IMMEDIATE')
    try:
        empty = not db.execute("SELECT 1 FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' LIMIT 1").fetchone()
        if empty and db.execute('PRAGMA user_version').fetchone()[0] == 0:
            for statement in SCHEMA.split(';'):
                if statement.strip(): db.execute(statement)
            db.execute('PRAGMA user_version=2')
        info = inspect_hive_schema(db)
        if info['migration_required']:
            raise HiveMigrationRequired('Stop writers; run python -m app.hive.migrate --db PATH --check, then --apply --backup BACKUP.')
        db.execute('COMMIT')
    except BaseException:
        if db.in_transaction: db.execute('ROLLBACK')
        raise
