"""Explicit offline hive maintenance. Stop all old and new writers before --apply."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from app.hive.schema import HiveSchemaError, inspect_hive_schema
from app.hive.resource_schema import RESOURCE_SCHEMA


def _connect_existing(path: str, *, readonly: bool = False) -> sqlite3.Connection:
    if path == ':memory:':
        raise ValueError('Migration requires an existing file database')
    target = Path(path).resolve(strict=True)
    if not target.is_file():
        raise ValueError('Database must be a regular file')
    db = sqlite3.connect(target.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                         uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def upgrade_hive_database(db_path: str, backup_path: str, *, target_version: int = 2) -> dict:
    if type(target_version) is not int or target_version not in (1, 2):
        raise ValueError('target_version must be 1 or 2')
    db = _connect_existing(db_path)
    try:
        info = inspect_hive_schema(db)
        if info['schema_version'] > target_version:
            raise HiveSchemaError('Downgrade is not supported; preserve accounting history')
        if info['schema_version'] == target_version:
            return {**info, 'migrated': False}
        if Path(backup_path).resolve() == Path(db_path).resolve():
            raise ValueError('Backup must differ from source database')
        initial_rows = _historical_rows(db)
        backup_rows = None
        fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        valid_backup = False
        try:
            backup = sqlite3.connect(backup_path)
            try:
                db.backup(backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise HiveSchemaError('Backup integrity check failed')
                if inspect_hive_schema(backup)['schema_version'] != info['schema_version']:
                    raise HiveSchemaError('Schema changed during backup')
                backup_rows = _historical_rows(backup)
                if backup_rows != initial_rows:
                    raise HiveSchemaError('Historical content changed during backup')
                valid_backup = True
            finally:
                backup.close()
        finally:
            if not valid_backup:
                os.unlink(backup_path)
        db.execute('BEGIN EXCLUSIVE')
        try:
            if inspect_hive_schema(db)['schema_version'] != info['schema_version']:
                raise HiveSchemaError('Schema changed during offline maintenance')
            historical = _historical_rows(db)
            if historical != backup_rows:
                raise HiveSchemaError('Historical content changed after backup; stop all writers')
            if info['schema_version'] == 0:
                db.execute('CREATE TABLE evidence_v1(id TEXT NOT NULL, run_id TEXT NOT NULL, source_id TEXT, '
                           'title TEXT, url TEXT, text TEXT, PRIMARY KEY(run_id,id))')
                db.execute('INSERT INTO evidence_v1 SELECT id,run_id,source_id,title,url,text FROM evidence')
                if db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0] != db.execute('SELECT COUNT(*) FROM evidence_v1').fetchone()[0]:
                    raise HiveSchemaError('Evidence row-count reconciliation failed')
                if db.execute('SELECT * FROM evidence EXCEPT SELECT * FROM evidence_v1').fetchone() or db.execute('SELECT * FROM evidence_v1 EXCEPT SELECT * FROM evidence').fetchone():
                    raise HiveSchemaError('Evidence content reconciliation failed')
                db.execute('DROP TABLE evidence')
                db.execute('ALTER TABLE evidence_v1 RENAME TO evidence')
                db.execute('PRAGMA user_version=1')
                if inspect_hive_schema(db)['schema_version'] != 1:
                    raise HiveSchemaError('Intermediate v1 validation failed')
                if _historical_rows(db) != historical:
                    raise HiveSchemaError('Intermediate v1 content reconciliation failed')
            if target_version == 2:
                for statement in RESOURCE_SCHEMA.split(';'):
                    if statement.strip(): db.execute(statement)
                db.execute('PRAGMA user_version=2')
            inspect_hive_schema(db)
            if _historical_rows(db) != historical or db.execute('PRAGMA foreign_key_check').fetchone():
                raise HiveSchemaError('Historical content or foreign key reconciliation failed')
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction: db.execute('ROLLBACK')
            raise
    finally:
        db.close()
    reopened = _connect_existing(db_path, readonly=True)
    try:
        return {**inspect_hive_schema(reopened), 'migrated': True, 'backup': backup_path}
    finally:
        reopened.close()


def _historical_rows(db):
    return {table: [tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in ('runs', 'tasks', 'evidence', 'facts', 'events', 'ledger')}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    parser.add_argument('--target-version', type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error('--apply requires --backup and all writers stopped')
    try:
        if args.check:
            db = _connect_existing(args.db, readonly=True)
            try: result = inspect_hive_schema(db)
            finally: db.close()
        else:
            result = upgrade_hive_database(args.db, args.backup, target_version=args.target_version)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, sqlite3.Error, HiveSchemaError) as exc:
        print(f'Hive maintenance failed: {exc}', file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
