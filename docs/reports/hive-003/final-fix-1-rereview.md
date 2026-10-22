**I1 — Logical task/run deadlines can expire during publication lock acquisition, yet a successful writer artifact is committed — NOT ADDRESSED (Important).** `app/hive/store.py:276`, `:286`, `:319`–`:322`: the repair checks after `BEGIN IMMEDIATE` and before completion, but SQLite `COMMIT` still waits for an existing reader in the actual default `delete` journal mode. This wait occurs after the last deadline check. Both task and run variants reproduced against the repaired source with valid selection, unchanged facts and a live lease. This is the remaining original I1, not an unrelated new finding.

### Finding evidence

- `app/hive/runner.py:70`–`:71`, `:82`, `:116`–`:117`, `:128`, `:161`–`:162`, `:170`, `:210`: absolute system-monotonic store deadlines and the separate loop-clock timeout are propagated consistently; typed run timeout escapes the worker's task-error handler. These portions address the original mutex/competing-writer waits and the intermediate clock-origin defect.
- `app/hive/store.py:275`–`:286`: assignment rejection still precedes deadline/content validation; no caller callback or runner guard executes under the non-reentrant mutex. Optional deadline arguments preserve existing direct callers. Exceptions before commit roll back publication.
- `app/hive/store.py:319`–`:322`: a reader's shared lock permits `BEGIN IMMEDIATE` and the task UPDATE, then holds up COMMIT's exclusive lock acquisition. After the reader releases, COMMIT succeeds after the logical deadline and returns True. Checking after COMMIT would be too late to roll back. Move acquisition of the lock required for commit before the transactional deadline checks, or otherwise make the commit wait deadline-aware with rollback before success; add the separate-reader regression for both deadlines. `BEGIN EXCLUSIVE` is one small candidate to assess for this store's journal-mode behavior.
- `tests/test_hive_report_execution.py:193`–`:218`: the added SQLite branch holds another `BEGIN IMMEDIATE`, so it exercises a competing writer at BEGIN rather than a reader at COMMIT. Its four passing cases do not cover the residual path.

### New Breakage in the Fix Diff

- None independently identified. The blocking Important issue is unresolved I1 above. Clock separation, stale-assignment precedence, optional direct-store inputs, transactional rollback before commit, and timeout exception routing were inspected without finding additional fix-induced breakage.

### Checks

- Read the scoped four-file snapshot diff, original I1, fix brief/report, machine-readable command receipts, relevant current source and governing REP-08/12 contract. No git/index/branch operations or production-code edits.
- Inspected retained logs, without rerunning suites: mutex/competing-writer regressions 4 RED → 4 GREEN; clock-origin regression 1 RED → 1 GREEN; changed runner/store coverage 112 passed; focused acceptance 360 passed; MCP log shows 54 successful test indicators with exit 0 in the receipt; full suite 387 passed and 11 failed. Full-log failure names agree with ten embedding-stack `HfFolder` imports and the Anthropic SDK case. These existing passes do not answer the separate-reader doubt.
- Ran only the focused two-variant reproduction below, from `/Users/parthsdambhare/hive-lite-v5`, with `PYTHONDONTWRITEBYTECODE=1 DEBUG=false /opt/anaconda3/bin/python -`; exit 0 means the diagnostic ran successfully, not that acceptance passed. It used disposable `/tmp` SQLite databases, mocked providers, the real scheduler/router/publisher, and a real separate-connection read transaction. Threads/connections were closed and temporary databases removed. No provider or application data was used.

```python
import asyncio, json, sqlite3, tempfile, threading, time
from pathlib import Path
from app.hive import run_hive
from app.hive.store import HiveStore
from app.llm import set_router
from tests.test_hive_report_execution import install_writer, select_first
from tests.test_hive import fake_search

async def probe(kind):
    with tempfile.TemporaryDirectory(prefix='hive003-reader-', dir='/tmp') as folder:
        store = HiveStore(str(Path(folder) / 'probe.db'))
        install_writer(select_first)
        original = store.publish_report
        observed = {'deadline_kind': kind, 'journal_mode': store.db.execute('PRAGMA journal_mode').fetchone()[0]}
        def contended(*args, **kwargs):
            ready, release = threading.Event(), threading.Event()
            errors = []
            def reader():
                db = None
                try:
                    db = sqlite3.connect(store.path, isolation_level=None)
                    db.execute('BEGIN')
                    db.execute('SELECT * FROM tasks').fetchall()
                    ready.set()
                    release.wait(.3)
                    db.execute('ROLLBACK')
                except BaseException as exc:
                    errors.append(repr(exc))
                    ready.set()
                finally:
                    if db is not None: db.close()
            thread = threading.Thread(target=reader)
            thread.start()
            try:
                assert ready.wait(2) and not errors, errors
                observed['lease_live_before'] = store.get_task(args[0])['lease_expires'] > time.time() + .3
                started = time.monotonic()
                observed['deadline_remaining_before'] = kwargs[kind + '_deadline'] - started
                result = original(*args, **kwargs)
                observed['publication_elapsed'] = time.monotonic() - started
                observed['publication_returned'] = result
                observed['deadline_overrun_after'] = time.monotonic() - kwargs[kind + '_deadline']
                return result
            finally:
                release.set()
                thread.join(2)
                assert not thread.is_alive() and not errors, errors
        store.publish_report = contended
        try:
            result = await run_hive('Attention research', store, workers=1, max_subtasks=1,
                                    search=fake_search, tick_s=.005, lease_s=3,
                                    task_timeout_s=.1 if kind == 'task' else 3,
                                    run_timeout_s=.1 if kind == 'run' else 3)
            writer = next(t for t in store.tasks(result.run_id) if t['kind'] == 'write')
            observed.update(status=result.status, run_report_present=bool(result.report),
                            writer_status=writer['status'], writer_report_present=bool((writer['result'] or {}).get('report')),
                            gate_code=result.gate.get('code'), facts=[result.facts_verified, result.facts_rejected],
                            surviving_hive_tasks=[t.get_name() for t in asyncio.all_tasks() if t.get_name().startswith('hive:') and not t.done()])
            print(json.dumps(observed, sort_keys=True))
        finally:
            set_router(None)
            store.db.close()
async def main():
    await probe('task')
    await probe('run')
asyncio.run(main())
```

Observed output:

```json
{"deadline_kind": "task", "deadline_overrun_after": 0.2716741249896586, "deadline_remaining_before": 0.0964573749806732, "facts": [1, 1], "gate_code": null, "journal_mode": "delete", "lease_live_before": true, "publication_elapsed": 0.3681293339468539, "publication_returned": true, "run_report_present": true, "status": "done", "surviving_hive_tasks": [], "writer_report_present": true, "writer_status": "done"}
{"deadline_kind": "run", "deadline_overrun_after": 0.27407804201357067, "deadline_remaining_before": 0.0917866249801591, "facts": [1, 1], "gate_code": "run_timeout", "journal_mode": "delete", "lease_live_before": true, "publication_elapsed": 0.3658632499864325, "publication_returned": true, "run_report_present": false, "status": "stopped", "surviving_hive_tasks": [], "writer_report_present": true, "writer_status": "done"}
```

### Out-of-Scope Observations

- None. Delivery/status/register reconciliation remains controller-owned; no additional scope requested.

### Verdict

**Fix round: Findings remain open — I1 (Important), reader-blocked COMMIT still publishes a report after either logical deadline.**
