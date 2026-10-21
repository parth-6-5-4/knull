"""Real SQLite migration boundaries; no application data or providers."""
import json
import multiprocessing as mp
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from app.hive.store import HiveStore
from tests.hive_testkit import legacy_database, snapshot


def test_fresh_schema_has_run_scoped_evidence_key(tmp_path):
    store = HiveStore(str(tmp_path / 'fresh.db'))
    try:
        cols = store.db.execute('PRAGMA table_info(evidence)').fetchall()
        assert [(r['name'], r['pk'], r['notnull']) for r in cols if r['pk']] == [
            ('id', 2, 1), ('run_id', 1, 1)]
        assert store.db.execute('PRAGMA user_version').fetchone()[0] == 1
    finally:
        store.db.close()


def test_old_schema_requires_explicit_upgrade_without_writes(tmp_path):
    from app.hive.schema import HiveMigrationRequired
    path = legacy_database(tmp_path / 'old.db')
    before = snapshot(path)
    with pytest.raises(HiveMigrationRequired, match='app.hive.migrate'):
        HiveStore(str(path))
    assert snapshot(path) == before


def test_upgrade_preserves_original_evidence_and_other_tables(tmp_path):
    from app.hive.migrate import upgrade_hive_database
    path = legacy_database(tmp_path / 'old.db')
    before = snapshot(path)
    backup = tmp_path / 'backup.db'
    result = upgrade_hive_database(str(path), str(backup))
    assert result['schema_version'] == 1 and result['migrated'] is True
    assert snapshot(backup) == before
    assert backup.stat().st_mode & 0o777 == 0o600
    store = HiveStore(str(path))
    try:
        assert store.evidence('old')[0]['text'] == 'original text'
        assert store.evidence('old','E-foreign') == []
        assert store.get_run('old')['report'] == 'historical report'
        assert len(store.facts('old')) == 2
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        store.db.close()


def test_upgrade_reopen_and_reapply_are_idempotent(tmp_path):
    from app.hive.migrate import upgrade_hive_database
    path = legacy_database(tmp_path / 'old.db'); backup = tmp_path / 'backup.db'
    upgrade_hive_database(str(path), str(backup)); before = snapshot(path)
    original_backup = backup.read_bytes()
    assert upgrade_hive_database(str(path), str(backup))['migrated'] is False
    assert snapshot(path) == before and backup.read_bytes() == original_backup
    store = HiveStore(str(path)); store.db.close()


def test_check_is_read_only_and_reports_missing_references(tmp_path):
    path = legacy_database(tmp_path / 'old.db'); before = path.read_bytes()
    p = subprocess.run([sys.executable,'-m','app.hive.migrate','--db',str(path),'--check'],
                       capture_output=True,text=True,timeout=10)
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout)
    assert result['schema_version'] == 0
    assert result['unresolved_facts_by_run'] == {'old': 1}
    assert path.read_bytes() == before
    absent = tmp_path / 'absent.db'
    p = subprocess.run([sys.executable,'-m','app.hive.migrate','--db',str(absent),'--check'],
                       capture_output=True,text=True,timeout=10)
    assert p.returncode != 0 and not absent.exists()


@pytest.mark.parametrize('change',[
    'PRAGMA user_version=99',
    'PRAGMA user_version=1',
    'DROP TABLE ledger',
    "INSERT INTO evidence VALUES('null-run',NULL,'','','','')",
    "INSERT INTO evidence VALUES(NULL,'old','','','','')",
    'CREATE INDEX custom_evidence ON evidence(title)',
    'CREATE TRIGGER custom_evidence AFTER INSERT ON evidence BEGIN SELECT 1; END',
    'CREATE VIEW custom_evidence AS SELECT * FROM evidence',
])
def test_unknown_or_partial_schema_refused_before_writes(tmp_path, change):
    from app.hive.migrate import upgrade_hive_database
    from app.hive.schema import HiveSchemaError
    path = legacy_database(tmp_path / 'old.db')
    with sqlite3.connect(path) as db: db.execute(change)
    before = snapshot(path)
    with pytest.raises(HiveSchemaError):
        HiveStore(str(path))
    with pytest.raises(HiveSchemaError):
        upgrade_hive_database(str(path), str(tmp_path/'backup.db'))
    assert snapshot(path) == before and not (tmp_path/'backup.db').exists()


def test_backup_failure_leaves_original_unchanged(tmp_path):
    from app.hive.migrate import upgrade_hive_database
    path = legacy_database(tmp_path/'old.db'); before = snapshot(path)
    backup = tmp_path/'existing.db'; backup.write_text('do not overwrite')
    with pytest.raises(FileExistsError): upgrade_hive_database(str(path),str(backup))
    assert snapshot(path) == before and backup.read_text() == 'do not overwrite'
    with pytest.raises(ValueError): upgrade_hive_database(str(path),str(path))
    assert snapshot(path) == before


@pytest.mark.parametrize('boundary',['copy','drop','rename','version'])
def test_migration_error_rolls_back(tmp_path, monkeypatch, boundary):
    import app.hive.migrate as migration
    path = legacy_database(tmp_path/'old.db'); before = snapshot(path)
    original = migration._connect_existing
    def connect(path, **kwargs):
        db = original(path, **kwargs)
        if not kwargs.get('readonly'):
            def authorize(action,a,b,*rest):
                deny = ((boundary=='copy' and action==sqlite3.SQLITE_INSERT and a=='evidence_v1')
                        or (boundary=='drop' and action==sqlite3.SQLITE_DROP_TABLE and a=='evidence')
                        or (boundary=='rename' and action==sqlite3.SQLITE_ALTER_TABLE)
                        or (boundary=='version' and action==sqlite3.SQLITE_PRAGMA and a=='user_version' and b=='1'))
                return sqlite3.SQLITE_DENY if deny else sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
        return db
    monkeypatch.setattr(migration,'_connect_existing',connect)
    with pytest.raises(sqlite3.DatabaseError):
        migration.upgrade_hive_database(str(path),str(tmp_path/'backup.db'))
    assert snapshot(path) == before
    assert snapshot(tmp_path/'backup.db') == before


def _interrupt_migration(path, backup, boundary, pipe):
    import app.hive.migrate as migration
    original = migration._connect_existing
    prefixes={'copy':'INSERT INTO EVIDENCE_V1','drop':'DROP TABLE EVIDENCE',
              'rename':'ALTER TABLE EVIDENCE_V1','version':'PRAGMA USER_VERSION=1',
              'before_commit':'COMMIT','after_commit':'COMMIT'}
    class BarrierConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            hit=sql.strip().upper().startswith(prefixes[boundary])
            if hit and boundary=='before_commit': pipe.send('at boundary'); pipe.recv()
            result=super().execute(sql,*args,**kwargs)
            if hit and boundary!='before_commit': pipe.send('at boundary'); pipe.recv()
            return result
    def connect(path, **kwargs):
        if kwargs.get('readonly'): return original(path,**kwargs)
        db=sqlite3.connect(path,isolation_level=None,factory=BarrierConnection)
        db.row_factory=sqlite3.Row
        return db
    migration._connect_existing=connect
    try: migration.upgrade_hive_database(path,backup)
    except BaseException as exc: pipe.send(repr(exc))


@pytest.mark.parametrize('boundary',['copy','drop','rename','version','before_commit','after_commit'])
def test_process_death_during_migration_recovers_old_or_new_schema(tmp_path,boundary):
    from app.hive.schema import HiveMigrationRequired
    path=legacy_database(tmp_path/'old.db'); before=snapshot(path)
    ctx=mp.get_context('fork'); parent,child=ctx.Pipe()
    process=ctx.Process(target=_interrupt_migration,args=(str(path),str(tmp_path/'backup.db'),boundary,child))
    process.start(); child.close()
    try:
        assert parent.poll(10), 'migration did not reach explicit barrier'
        assert parent.recv() == 'at boundary'
    finally:
        process.terminate(); process.join(5)
        if process.is_alive(): process.kill(); process.join(5)
        parent.close()
    probe = subprocess.run([sys.executable, '-c',
        "import sqlite3,json,sys; d=sqlite3.connect(sys.argv[1]); print(json.dumps([d.execute('PRAGMA integrity_check').fetchone()[0],d.execute('PRAGMA user_version').fetchone()[0],d.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]])); d.close()", str(path)],
        capture_output=True, text=True, timeout=10)
    assert probe.returncode == 0, probe.stderr
    integrity, version, count = json.loads(probe.stdout)
    assert integrity == 'ok' and count == 2
    if boundary=='after_commit':
        assert version==1
        store=HiveStore(str(path)); store.db.close()
    else:
        assert version==0 and snapshot(path)==before
        with pytest.raises(HiveMigrationRequired): HiveStore(str(path))
    assert snapshot(tmp_path/'backup.db') == before


@pytest.mark.parametrize('custom',[
    "text TEXT CHECK(text != 'forbidden')",
    'text TEXT REFERENCES runs(id)',
    'text TEXT COLLATE NOCASE',
])
def test_custom_constraints_are_refused_without_discarding_semantics(tmp_path,custom):
    from tests.hive_testkit import LEGACY_SCHEMA
    from app.hive.schema import HiveSchemaError
    from app.hive.migrate import upgrade_hive_database
    path=tmp_path/'custom.db'
    with sqlite3.connect(path) as db:
        db.executescript(LEGACY_SCHEMA.replace('url TEXT, text TEXT);',f'url TEXT, {custom});'))
    before=snapshot(path)
    with pytest.raises(HiveSchemaError):HiveStore(str(path))
    with pytest.raises(HiveSchemaError):upgrade_hive_database(str(path),str(tmp_path/'backup.db'))
    assert snapshot(path)==before and not (tmp_path/'backup.db').exists()


def test_interrupted_backup_is_not_reported_as_valid(tmp_path,monkeypatch):
    import app.hive.migrate as migration
    path=legacy_database(tmp_path/'old.db');before=snapshot(path)
    original=migration._connect_existing
    class FailedBackup(sqlite3.Connection):
        def backup(self,*args,**kwargs):raise sqlite3.OperationalError('backup interrupted')
    def connect(path,**kwargs):
        if kwargs.get('readonly'):return original(path,**kwargs)
        db=sqlite3.connect(path,isolation_level=None,factory=FailedBackup)
        db.row_factory=sqlite3.Row
        return db
    monkeypatch.setattr(migration,'_connect_existing',connect)
    with pytest.raises(sqlite3.OperationalError,match='backup interrupted'):
        migration.upgrade_hive_database(str(path),str(tmp_path/'partial.db'))
    assert snapshot(path)==before and not (tmp_path/'partial.db').exists()
