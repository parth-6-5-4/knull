"""Real SQLite locking and owned executor cancellation boundaries."""
import asyncio
import sqlite3
import threading
import time
import pytest


def connection(path=':memory:',**kwargs):
    db=sqlite3.connect(path,isolation_level=None,check_same_thread=False,**kwargs)
    db.execute('CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY)')
    return db


def test_transaction_rolls_back_errors_and_rejects_async_callbacks():
    from app.hive.transactions import SQLiteTransactions
    db=connection();tx=SQLiteTransactions(db,threading.Lock())
    try:
        def fail(db):db.execute('INSERT INTO items VALUES(1)');raise ValueError('broken')
        with pytest.raises(ValueError,match='broken'):tx.write(fail)
        assert not db.in_transaction and db.execute('SELECT COUNT(*) FROM items').fetchone()[0]==0
        async def invalid(db):return 1
        with pytest.raises(TypeError):tx.write(invalid)
        assert tx.write(lambda db:db.execute('INSERT INTO items VALUES(2)').rowcount)==1
    finally:db.close()


def test_real_busy_preserves_timeout_and_other_sqlite_errors(tmp_path):
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy
    path=tmp_path/'busy.db';db=connection(path,timeout=.017);other=connection(path)
    tx=SQLiteTransactions(db,threading.Lock());timeout=db.execute('PRAGMA busy_timeout').fetchone()[0]
    try:
        other.execute('BEGIN IMMEDIATE')
        started=time.monotonic()
        with pytest.raises(ResourceBusy):tx.write(lambda db:db.execute('INSERT INTO items VALUES(1)'))
        assert time.monotonic()-started < 1 and not db.in_transaction
        assert db.execute('PRAGMA busy_timeout').fetchone()[0]==timeout==17
        other.execute('ROLLBACK')
        with pytest.raises(sqlite3.OperationalError):tx.write(lambda db:db.execute('SELECT missing FROM items'))
        assert not db.in_transaction
    finally:other.close();db.close()


def test_mutex_deadline_is_finite_and_never_enters_callback():
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy,ResourceInputError
    db=connection();lock=threading.Lock();tx=SQLiteTransactions(db,lock);lock.acquire()
    try:
        for deadline in (float('nan'),float('inf'),True):
            with pytest.raises(ResourceInputError):tx.write(lambda db:None,deadline_monotonic=deadline)
        with pytest.raises(ResourceBusy):tx.write(lambda db:pytest.fail('late callback'),deadline_monotonic=time.monotonic()+.02)
        assert not db.in_transaction
    finally:lock.release();db.close()


def test_expiry_after_sqlite_acquisition_skips_callback(tmp_path):
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy
    path=tmp_path/'acquire.db';db=connection(path,timeout=.2);other=connection(path)
    other.execute('BEGIN IMMEDIATE')
    thread=threading.Thread(target=lambda:(time.sleep(.06),other.execute('ROLLBACK')));thread.start()
    try:
        with pytest.raises(ResourceBusy):SQLiteTransactions(db,threading.Lock()).write(lambda db:pytest.fail('expired callback'),deadline_monotonic=time.monotonic()+.02)
        assert not db.in_transaction and db.execute('SELECT COUNT(*) FROM items').fetchone()[0]==0
    finally:thread.join();other.close();db.close()


def test_precommit_deadline_rolls_back_and_exclusive_reader_conflict(tmp_path):
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy
    path=tmp_path/'reader.db';db=connection(path,timeout=.017);reader=connection(path)
    tx=SQLiteTransactions(db,threading.Lock())
    try:
        def expire(db):db.execute('INSERT INTO items VALUES(1)');time.sleep(.03)
        with pytest.raises(ResourceBusy):tx.write(expire,deadline_monotonic=time.monotonic()+.01)
        assert not db.in_transaction and db.execute('SELECT COUNT(*) FROM items').fetchone()[0]==0
        reader.execute('BEGIN');reader.execute('SELECT * FROM items').fetchall()
        with pytest.raises(ResourceBusy):tx.write(lambda db:pytest.fail('reader-conflicted decision'),deadline_monotonic=time.monotonic()+.1,exclusive=True)
        assert not db.in_transaction
        reader.execute('ROLLBACK')
        tx.write(lambda db:db.execute('INSERT INTO items VALUES(2)'),exclusive=True)
    finally:reader.close();db.close()


async def test_executor_cancellation_drains_started_work_and_preserves_outcome():
    from app.hive.transactions import DatabaseIO
    io=DatabaseIO();entered=threading.Event();release=threading.Event();threads=[]
    def work():threads.append(threading.get_ident());entered.set();release.wait(2);return 'durable result'
    task=asyncio.create_task(io.call(work))
    while not entered.is_set():await asyncio.sleep(.001)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    close=asyncio.create_task(io.aclose());await asyncio.sleep(.01)
    assert not close.done()
    release.set();await close
    assert io.detached_results==('durable result',)
    with pytest.raises(RuntimeError):await io.call(lambda:None)


async def test_executor_queued_deadline_and_detached_failure_are_observable():
    from app.hive.transactions import DatabaseIO
    from app.hive.resource_types import ResourceBusy
    io=DatabaseIO();entered=threading.Event();release=threading.Event()
    def work():entered.set();release.wait(2);raise ValueError('durable failure')
    task=asyncio.create_task(io.call(work))
    while not entered.is_set():await asyncio.sleep(.001)
    with pytest.raises(ResourceBusy):await io.call(lambda:pytest.fail('expired queued work'),deadline_monotonic=time.monotonic()+.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    release.set()
    with pytest.raises(ValueError,match='durable failure'):await io.aclose()
    assert any(isinstance(x,ValueError) for x in io.detached_results)


async def test_executor_uses_one_worker_and_close_survives_cancellation():
    from app.hive.transactions import DatabaseIO
    io=DatabaseIO();entered=threading.Event();release=threading.Event()
    def hold():entered.set();release.wait(2);return threading.get_ident()
    first=asyncio.create_task(io.call(hold))
    while not entered.is_set():await asyncio.sleep(.001)
    second=asyncio.create_task(io.call(threading.get_ident));await asyncio.sleep(.01)
    closing=asyncio.create_task(io.aclose());await asyncio.sleep(.01);closing.cancel()
    with pytest.raises(asyncio.CancelledError):await closing
    release.set();assert await first==await second
    await io.aclose()


async def test_store_owns_shared_transaction_and_drains_before_close(tmp_path):
    from app.hive.store import HiveStore
    from app.hive.resource_types import SystemClock
    clock=SystemClock();store=HiveStore(str(tmp_path/'owned.db'),clock=clock)
    assert store.transactions.db is store.db and store.transactions.lock is store._lock
    assert store.transactions.clock is clock and store.database_io.clock is clock
    assert store.db.execute('PRAGMA foreign_keys').fetchone()[0]==1
    run_id=await store.database_io.call(lambda:store.transactions.write(lambda db:db.execute("INSERT INTO runs(id,status) VALUES('owned','running')").rowcount))
    assert run_id==1
    await store.aclose()
    with pytest.raises(sqlite3.ProgrammingError):store.db.execute('SELECT 1')


def test_only_genuine_busy_family_is_translated():
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy
    db=connection();tx=SQLiteTransactions(db,threading.Lock())
    try:
        def locked(db):
            exc=sqlite3.OperationalError('database table is locked');exc.sqlite_errorcode=sqlite3.SQLITE_LOCKED;raise exc
        with pytest.raises(sqlite3.OperationalError):tx.write(locked)
        def extended_busy(db):
            exc=sqlite3.OperationalError('snapshot busy');exc.sqlite_errorcode=sqlite3.SQLITE_BUSY_SNAPSHOT;raise exc
        with pytest.raises(ResourceBusy):tx.write(extended_busy)
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(RuntimeError,match='Nested'):tx.write(lambda db:None)
        assert db.in_transaction  # Do not roll back another owner's transaction.
        db.execute('ROLLBACK')
    finally:db.close()


def test_deadline_default_acquires_reader_conflicting_lock_before_decision(tmp_path):
    from app.hive.transactions import SQLiteTransactions
    from app.hive.resource_types import ResourceBusy
    path=tmp_path/'default-reader.db';db=connection(path,timeout=.017);reader=connection(path)
    reader.execute('BEGIN');reader.execute('SELECT * FROM items').fetchall()
    try:
        with pytest.raises(ResourceBusy):
            SQLiteTransactions(db,threading.Lock()).write(lambda db:pytest.fail('guarded decision ran under held reader'),deadline_monotonic=time.monotonic()+.2)
        assert not db.in_transaction and db.execute('SELECT COUNT(*) FROM items').fetchone()[0]==0
    finally:reader.execute('ROLLBACK');reader.close();db.close()


@pytest.mark.parametrize('with_deadline',[False,True])
async def test_executor_preserves_callback_timeout_errors(with_deadline):
    from app.hive.transactions import DatabaseIO
    io=DatabaseIO()
    def fail():raise TimeoutError('callback failure, not queue timeout')
    try:
        kwargs={'deadline_monotonic':time.monotonic()+1} if with_deadline else {}
        with pytest.raises(TimeoutError,match='callback failure'):
            await io.call(fail,**kwargs)
    finally:await io.aclose()


async def test_detached_sqlite_busy_is_not_silently_treated_as_success():
    from app.hive.transactions import DatabaseIO
    from app.hive.resource_types import ResourceBusy
    io=DatabaseIO();entered=threading.Event();release=threading.Event()
    def busy():entered.set();release.wait(2);raise ResourceBusy('resource_busy')
    task=asyncio.create_task(io.call(busy))
    while not entered.is_set():await asyncio.sleep(.001)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    release.set()
    with pytest.raises(ResourceBusy,match='resource_busy'):await io.aclose()
    assert isinstance(io.detached_results[0],ResourceBusy)
