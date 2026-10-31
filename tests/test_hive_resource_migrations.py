"""Explicit schema-v2 maintenance against frozen historical DDL."""
import sqlite3
import pytest
from app.hive.store import HiveStore
from app.hive.schema import HiveMigrationRequired, HiveSchemaError, inspect_hive_schema
from app.hive.migrate import upgrade_hive_database
from tests.hive_resource_testkit import v1_database, historical_digests
from tests.hive_testkit import legacy_database

def test_new_database_is_v2(tmp_path):
    store=HiveStore(str(tmp_path/'new.db'))
    try:
        assert inspect_hive_schema(store.db)['schema_version']==2
        assert store.db.execute('SELECT COUNT(*) FROM resource_runs').fetchone()[0]==0
    finally: store.db.close()

def test_v1_requires_explicit_maintenance(tmp_path):
    path=v1_database(tmp_path/'v1.db'); before=path.read_bytes()
    with pytest.raises(HiveMigrationRequired): HiveStore(str(path))
    assert path.read_bytes()==before

def test_v1_to_v2_preserves_historical_tables(tmp_path):
    path=v1_database(tmp_path/'v1.db'); before=historical_digests(path)
    backup=tmp_path/'backup.db'
    result=upgrade_hive_database(str(path),str(backup))
    assert result['schema_version']==2 and result['migrated']
    assert historical_digests(path)==before==historical_digests(backup)
    assert backup.stat().st_mode & 0o777==0o600
    store=HiveStore(str(path))
    try:
        assert store.get_run('r')['report']=='historical\nreport \u03bb'
        assert store.db.execute('SELECT COUNT(*) FROM resource_runs').fetchone()[0]==0
    finally: store.db.close()
    assert not upgrade_hive_database(str(path),str(backup))['migrated']

@pytest.mark.parametrize('boundary',['table','index','version','commit'])
def test_interrupted_v2_upgrade_rolls_back(tmp_path,monkeypatch,boundary):
    import app.hive.migrate as migration
    path=v1_database(tmp_path/'v1.db'); before=historical_digests(path)
    original=migration._connect_existing
    class Interrupted(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            upper=sql.upper().strip()
            hit=(boundary=='table' and 'CREATE TABLE' in upper and 'RESOURCE_CALLS' in upper or boundary=='index' and 'CREATE INDEX' in upper or boundary=='version' and upper=='PRAGMA USER_VERSION=2' or boundary=='commit' and upper=='COMMIT')
            if hit: raise KeyboardInterrupt('injected interruption')
            return super().execute(sql,*args,**kwargs)
    def connect(path,**kwargs):
        if kwargs.get('readonly'): return original(path,**kwargs)
        db=sqlite3.connect(path,isolation_level=None,factory=Interrupted);db.row_factory=sqlite3.Row;return db
    monkeypatch.setattr(migration,'_connect_existing',connect)
    with pytest.raises(KeyboardInterrupt): upgrade_hive_database(str(path),str(tmp_path/'backup.db'))
    with sqlite3.connect(path) as db:
        assert inspect_hive_schema(db)['schema_version']==1
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert historical_digests(path)==before==historical_digests(tmp_path/'backup.db')

@pytest.mark.parametrize('target',[1,2])
def test_v0_to_requested_target_is_explicit(tmp_path,target):
    path=legacy_database(tmp_path/'v0.db')
    result=upgrade_hive_database(str(path),str(tmp_path/'backup.db'),target_version=target)
    assert result['schema_version']==target
    with sqlite3.connect(path) as db: assert inspect_hive_schema(db)['schema_version']==target

def test_unknown_shape_and_old_writer_refuse_v2(tmp_path):
    from tests.hive_resource_testkit import V1_SCHEMA
    path=tmp_path/'new.db';store=HiveStore(str(path));store.db.close()
    # Run the frozen actual v1 validator, so the compatibility assertion cannot drift.
    from tests.hive_resource_testkit import FROZEN_V1_VALIDATOR
    old={}
    exec(FROZEN_V1_VALIDATOR,old)
    with sqlite3.connect(path) as db:
        with pytest.raises(old['HiveSchemaError']): old['inspect_hive_schema'](db)
        db.execute('DROP INDEX resource_calls_queue')
        with pytest.raises(HiveSchemaError): inspect_hive_schema(db)

def test_v1_existing_backup_is_never_overwritten(tmp_path):
    path=v1_database(tmp_path/'v1.db');before=path.read_bytes();backup=tmp_path/'backup.db';backup.write_bytes(b'keep')
    with pytest.raises(FileExistsError):upgrade_hive_database(str(path),str(backup))
    assert path.read_bytes()==before and backup.read_bytes()==b'keep'


def test_backup_source_change_is_detected_before_mutation(tmp_path,monkeypatch):
    import app.hive.migrate as migration
    path=v1_database(tmp_path/'v1.db');original=migration._connect_existing
    class ChangedAfterBackup(sqlite3.Connection):
        def backup(self,*args,**kwargs):
            result=super().backup(*args,**kwargs)
            self.execute("UPDATE runs SET report='concurrent writer'")
            return result
    def connect(path,**kwargs):
        if kwargs.get('readonly'):return original(path,**kwargs)
        db=sqlite3.connect(path,isolation_level=None,factory=ChangedAfterBackup);db.row_factory=sqlite3.Row;return db
    monkeypatch.setattr(migration,'_connect_existing',connect)
    with pytest.raises(HiveSchemaError,match='changed'):upgrade_hive_database(str(path),str(tmp_path/'backup.db'))
    with sqlite3.connect(path) as db:
        assert inspect_hive_schema(db)['schema_version']==1
        assert db.execute('SELECT report FROM runs').fetchone()[0]=='concurrent writer'


def test_exact_shape_rejects_unexpected_similar_sqlite_name(tmp_path):
    path=tmp_path/'new.db';store=HiveStore(str(path))
    try:
        store.db.execute('CREATE TABLE sqliteXunexpected(value TEXT)')
        with pytest.raises(HiveSchemaError):inspect_hive_schema(store.db)
    finally:store.db.close()


def _v2_upgrade_barrier(path,backup,boundary,pipe):
    import app.hive.migrate as migration
    original=migration._connect_existing
    class Barrier(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            upper=sql.strip().upper()
            hit=(boundary=='ddl' and 'CREATE TABLE RESOURCE_CALLS' in upper or boundary=='marker' and upper=='PRAGMA USER_VERSION=2' or boundary in ('before_commit','after_commit') and upper=='COMMIT')
            if hit and boundary=='before_commit':pipe.send('barrier');pipe.recv()
            result=super().execute(sql,*args,**kwargs)
            if hit and boundary!='before_commit':pipe.send('barrier');pipe.recv()
            return result
    def connect(path,**kwargs):
        if kwargs.get('readonly'):return original(path,**kwargs)
        db=sqlite3.connect(path,isolation_level=None,factory=Barrier);db.row_factory=sqlite3.Row;return db
    migration._connect_existing=connect
    try:migration.upgrade_hive_database(path,backup)
    except BaseException as exc:pipe.send(repr(exc))


@pytest.mark.parametrize('boundary',['ddl','marker','before_commit','after_commit'])
def test_process_death_v2_upgrade_is_atomic(tmp_path,boundary):
    import multiprocessing as mp
    path=v1_database(tmp_path/'v1.db');backup=tmp_path/'backup.db';before=historical_digests(path)
    ctx=mp.get_context('fork');parent,child=ctx.Pipe();process=ctx.Process(target=_v2_upgrade_barrier,args=(str(path),str(backup),boundary,child))
    process.start();child.close()
    try:
        assert parent.poll(10),'upgrade did not reach barrier'
        assert parent.recv()=='barrier'
    finally:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
        parent.close()
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        version=inspect_hive_schema(db)['schema_version']
        assert version==(2 if boundary=='after_commit' else 1)
    assert historical_digests(path)==before==historical_digests(backup)
    print({'boundary':boundary,'version':version,'before':before,'after':historical_digests(path),'backup':historical_digests(backup)})


@pytest.mark.parametrize('change',[
    'DROP TABLE resource_usage_projection',
    'DROP INDEX resource_calls_run_queue',
    'CREATE INDEX custom_route ON resource_calls(model)',
    'CREATE INDEX custom_expression ON resource_calls(lower(model))',
    "CREATE INDEX custom_partial ON resource_calls(model) WHERE state='queued'",
    'CREATE TRIGGER extra AFTER INSERT ON resource_profiles BEGIN SELECT 1; END',
    'CREATE TABLE "strange""name"(value TEXT)',
])
def test_v2_all_objects_are_part_of_exact_shape(tmp_path,change):
    store=HiveStore(str(tmp_path/'v2.db'))
    try:
        store.db.execute(change)
        with pytest.raises(HiveSchemaError):inspect_hive_schema(store.db)
    finally:store.db.close()


def test_resource_schema_enforces_identity_checks_and_foreign_keys(tmp_path):
    store=HiveStore(str(tmp_path/'v2.db'));db=store.db
    try:
        db.execute("INSERT INTO resource_policy VALUES(1,'policy','{}')")
        db.execute("INSERT INTO resource_profiles VALUES('profile','{}')")
        db.execute("INSERT INTO runs(id) VALUES('r')")
        db.execute("INSERT INTO resource_allocations VALUES('a','r','a',NULL,200,0,0)")
        for sql in ("INSERT INTO resource_policy VALUES(2,'other','{}')",
                    "INSERT INTO resource_profiles VALUES('bad','not json')",
                    "INSERT INTO resource_allocations VALUES('bad','r','a','missing',10,0,0)",
                    "INSERT INTO resource_allocations VALUES('bad','r','bad',NULL,-1,0,0)",
                    "INSERT INTO resource_allocations VALUES('bad','r','bad',NULL,1.5,0,0)",
                    "INSERT INTO resource_allocations VALUES('bad','r','bad',NULL,5,2,0)",
                    "INSERT INTO resource_allocations VALUES('bad','missing-run','bad',NULL,5,0,0)",
                    "INSERT INTO resource_usage_projection VALUES('missing',123)"):
            with pytest.raises(sqlite3.IntegrityError):db.execute(sql)
    finally:db.close()


def test_cli_target_v1_is_explicit_and_downgrade_refused(tmp_path):
    import json,subprocess,sys
    path=legacy_database(tmp_path/'v0.db');backup=tmp_path/'backup.db'
    result=subprocess.run([sys.executable,'-m','app.hive.migrate','--db',str(path),'--apply','--backup',str(backup),'--target-version','1'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['schema_version']==1
    with pytest.raises(HiveMigrationRequired):HiveStore(str(path))
    upgrade_hive_database(str(path),str(tmp_path/'v1-backup.db'))
    before=path.read_bytes()
    with pytest.raises(HiveSchemaError,match='Downgrade'):
        upgrade_hive_database(str(path),str(tmp_path/'downgrade.db'),target_version=1)
    assert path.read_bytes()==before and not (tmp_path/'downgrade.db').exists()


@pytest.mark.parametrize('replacement',["'HARD','estimated'","'hard ','estimated'"])
def test_exact_shape_preserves_check_literal_case_and_spaces(tmp_path,replacement):
    from app.hive.schema import SCHEMA
    with sqlite3.connect(tmp_path/'modified.db') as db:
        db.executescript(SCHEMA.replace("'hard','estimated'",replacement))
        db.execute('PRAGMA user_version=2')
        with pytest.raises(HiveSchemaError):inspect_hive_schema(db)


def test_exact_shape_accepts_quoted_identifiers_but_rejects_escaped_literals(tmp_path):
    from app.hive.schema import SCHEMA
    with sqlite3.connect(tmp_path/'quoted.db') as db:
        db.executescript(SCHEMA.replace('resource_policy','"resource_policy"'))
        db.execute('PRAGMA user_version=2')
        assert inspect_hive_schema(db)['schema_version']==2
    with sqlite3.connect(tmp_path/'escaped.db') as db:
        db.executescript(SCHEMA.replace("'hard','estimated'","'ha''rd','estimated'"))
        db.execute('PRAGMA user_version=2')
        with pytest.raises(HiveSchemaError):inspect_hive_schema(db)


def test_v2_orphaned_resource_rows_are_refused_on_reopen(tmp_path):
    path=tmp_path/'orphan.db';store=HiveStore(str(path));store.db.close()
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO resource_usage_projection VALUES('absent-call',999)")
    with pytest.raises(HiveSchemaError):HiveStore(str(path))
