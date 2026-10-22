"""Finite local SQLite writes and one explicitly owned database worker.

Callbacks are internal, synchronous SQL-only operations: no provider/network work,
await, transaction control, or connection escape. The existing SQLite busy timeout
is preserved. A local deadline is rechecked after its bounded acquisition wait.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import sqlite3
import threading

from app.hive.resource_types import ResourceBusy, SystemClock, finite_number


def _deadline(value):
    if value is not None: finite_number(value, 'deadline_monotonic')


def _sync_result(result):
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result): result.close()
        raise TypeError('Database callbacks must be synchronous SQL-only operations')
    return result


class SQLiteTransactions:
    def __init__(self, db: sqlite3.Connection, lock=None, *, clock=None):
        self.db = db
        self.lock = lock if lock is not None else threading.Lock()
        self.clock = clock if clock is not None else SystemClock()
        self._mutex_timeout_s = max(.001, db.execute("PRAGMA busy_timeout").fetchone()[0] / 1000)

    def _check(self, deadline):
        if deadline is not None and self.clock.monotonic() >= deadline:
            raise ResourceBusy('resource_deadline_exceeded')

    def write(self, fn, *, deadline_monotonic=None, exclusive=False):
        _deadline(deadline_monotonic)
        if inspect.iscoroutinefunction(fn): raise TypeError('Database callback must be synchronous')
        self._check(deadline_monotonic)
        if deadline_monotonic is None:
            # Finite mutex wait even without a caller deadline; uses this connection's
            # configured local I/O envelope, without modifying SQLite's timeout.
            timeout = self._mutex_timeout_s
        else:
            timeout = max(0, deadline_monotonic - self.clock.monotonic())
        if not self.lock.acquire(timeout=min(timeout, threading.TIMEOUT_MAX)): raise ResourceBusy('resource_busy')
        started = False
        try:
            self._check(deadline_monotonic)
            if self.db.in_transaction: raise RuntimeError('Nested/shared transaction is not supported')
            self.db.execute('BEGIN EXCLUSIVE' if exclusive or deadline_monotonic is not None else 'BEGIN IMMEDIATE')
            started = True
            self._check(deadline_monotonic)
            result = _sync_result(fn(self.db))
            self._check(deadline_monotonic)
            self.db.execute('COMMIT')
            return result
        except BaseException as exc:
            if started and self.db.in_transaction: self.db.execute('ROLLBACK')
            if isinstance(exc, sqlite3.Error) and getattr(exc,'sqlite_errorcode',None) is not None and exc.sqlite_errorcode & 0xff == sqlite3.SQLITE_BUSY:
                raise ResourceBusy('resource_busy') from exc
            raise
        finally:
            self.lock.release()


class DatabaseIO:
    """Own one worker and retain detached outcomes until the owner drains them.

Cancelling a waiter never cancels an already submitted operation. aclose drains
all work, exposes detached successful values and raises detached failures; a
cancelled aclose may be awaited again to finish the same drain.
"""
    def __init__(self, *, clock=None):
        self.clock = clock if clock is not None else SystemClock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='hive-database')
        self._pending = set()
        self._detached = set()
        self._detached_results = []
        self._closed = False
        self._close_task = None

    @property
    def detached_results(self): return tuple(self._detached_results)

    async def call(self, fn, *, deadline_monotonic=None):
        _deadline(deadline_monotonic)
        if self._closed: raise RuntimeError('DatabaseIO is closed')
        if inspect.iscoroutinefunction(fn): raise TypeError('Database callback must be synchronous')
        def invoke():
            if deadline_monotonic is not None and self.clock.monotonic() >= deadline_monotonic:
                raise ResourceBusy('resource_deadline_exceeded')
            return _sync_result(fn())
        if deadline_monotonic is not None and self.clock.monotonic() >= deadline_monotonic:
            raise ResourceBusy('resource_deadline_exceeded')
        future = asyncio.wrap_future(self._executor.submit(invoke))
        self._pending.add(future)
        timeout_scope = None
        try:
            if deadline_monotonic is None: return await asyncio.shield(future)
            # Convert remaining system/injected monotonic duration to loop time;
            # no absolute timestamp crosses clock domains.
            remaining = max(0, deadline_monotonic - self.clock.monotonic())
            timeout_scope = asyncio.timeout(remaining)
            async with timeout_scope: return await asyncio.shield(future)
        except asyncio.CancelledError:
            self._detached.add(future)
            raise
        except TimeoutError as exc:
            if timeout_scope is None or not timeout_scope.expired():
                raise  # Preserve the callback's own error classification.
            self._detached.add(future)
            raise ResourceBusy('resource_deadline_exceeded') from exc
        finally:
            if future not in self._detached: self._pending.discard(future)

    async def _drain(self):
        # gather retrieves all results/exceptions, including work whose waiter left.
        pending = tuple(self._pending)
        if pending: await asyncio.gather(*pending, return_exceptions=True)
        failure = None
        for future in tuple(self._detached):
            try: result = future.result()
            except BaseException as exc:
                result = exc
                # Preserve every failure, preferring a substantive callback error
                # when queued deadline expiry also occurred during the same drain.
                if failure is None or (isinstance(failure,ResourceBusy) and not isinstance(exc,ResourceBusy)):
                    failure = exc
            self._detached_results.append(result)
        self._pending.clear();self._detached.clear()
        self._executor.shutdown(wait=True)
        if failure is not None: raise failure

    async def aclose(self):
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._drain())
        await asyncio.shield(self._close_task)
