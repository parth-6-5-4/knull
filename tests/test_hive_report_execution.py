"""Supported-report outcomes through the real scheduler, router and SQLite store."""
import asyncio
import json
import re
import sqlite3
import threading
import time
from dataclasses import replace

import pytest

from app.hive import agents, run_hive
from app.hive.reporting import ReportInputError
from app.hive.store import HiveStore
from app.llm import LLMRouter, set_router
from tests.test_hive import fake_search, make_handler, routed_config


@pytest.fixture
def store(tmp_path):
    value = HiveStore(str(tmp_path / "reports.db"))
    yield value
    set_router(None)
    value.db.close()


def writer_payload(user):
    # Support the old path too, so pre-integration RED is behavioral.
    try:
        return json.loads(user)
    except ValueError:
        return {"candidates": [{"id": fid, "claim": claim} for fid, claim in
                               re.findall(r"\[(F-[0-9a-f]{8})\] (.*)", user)]}


def install_writer(response, *, reject_all=False):
    """Keep planning/extraction/verification real; replace only provider responses."""
    base = make_handler(bad_verdict=True)
    inputs = []

    def handler(spec, messages):
        system, user = messages[0]["content"], messages[-1]["content"]
        if "writer symbiote" in system:
            payload = writer_payload(user)
            inputs.append(payload)
            return response(payload) if callable(response) else response
        if reject_all and "verifier" in system:
            return '{"verdict":"unsupported","note":"unsupported"}'
        return base(spec, messages)

    set_router(LLMRouter(routed_config(), mock_handler=handler))
    return inputs


def select_first(payload):
    return json.dumps({"fact_ids": [payload["candidates"][0]["id"]]})


async def execute(store, **kwargs):
    return await asyncio.wait_for(run_hive("Attention research", store, workers=1,
                                         max_subtasks=1, search=fake_search, tick_s=.005,
                                         **kwargs), 2)


def write_task(store, result):
    return next(task for task in store.tasks(result.run_id) if task["kind"] == "write")


def assert_facts_preserved(result):
    assert (result.facts_verified, result.facts_rejected) == (1, 1)


def assert_no_hive_tasks():
    assert not [task for task in asyncio.all_tasks()
                if task.get_name().startswith("hive:") and not task.done()]


def test_writer_succeeds_when_event_loop_clock_has_different_origin(store):
    """The asyncio timer must use loop time even when publication uses monotonic time."""
    install_writer(select_first)

    class OffsetLoop(asyncio.SelectorEventLoop):
        def time(self):
            return super().time() + 10_000

    with asyncio.Runner(loop_factory=OffsetLoop) as runner:
        result = runner.run(execute(store, task_timeout_s=1, run_timeout_s=1))
    assert result.status == "done"
    assert write_task(store, result)["status"] == "done"
    assert result.report


async def test_empty_selection_blocks_run(store):
    inputs = install_writer('{"fact_ids":[]}')
    result = await execute(store)
    assert result.status == "blocked" and result.report == ""
    assert result.gate["finding_count"] == 0
    assert result.gate["reason"] == "no_selected_findings"
    assert len(inputs) == 1
    assert write_task(store, result)["status"] == "done"
    assert_facts_preserved(result)


async def test_no_candidates_skips_writer(store):
    inputs = install_writer(select_first, reject_all=True)
    result = await execute(store)
    assert result.status == "blocked" and result.report == ""
    assert result.gate["reason"] == "no_verified_facts"
    assert result.gate["finding_count"] == 0
    assert len(inputs) == 0
    assert (result.facts_verified, result.facts_rejected) == (0, 2)
    assert write_task(store, result)["status"] == "done"


@pytest.mark.parametrize("response", [
    lambda p: "## Caching increases calls by 900%\n" + p["candidates"][0]["claim"] +
              " [" + p["candidates"][0]["id"] + "]",
    lambda p: "Other models use recurrence by 900%. [" + p["candidates"][0]["id"] + "]",
    lambda p: "[" + p["candidates"][0]["id"] + "]",
    lambda p: select_first(p) + " Unsupported trailing statement.",
], ids=["unsupported-heading", "entity-number-relation", "citation-only", "json-plus-prose"])
async def test_writer_prose_cannot_be_salvaged(store, response):
    inputs = install_writer(response)
    result = await execute(store)
    assert result.status == "blocked" and result.report == ""
    writer = write_task(store, result)
    assert writer["status"] == "exhausted"
    assert writer["result"]["code"] == "report_selection_invalid"
    assert writer["attempt"] == len(inputs) == 1
    assert "900%" not in json.dumps(result.events)
    assert "Unsupported trailing" not in json.dumps(result.events)
    assert_facts_preserved(result)


async def test_valid_selection_finishes_with_exact_claim(store):
    inputs = install_writer(select_first)
    result = await execute(store)
    assert result.status == "done" and result.gate["passed"] is True
    assert result.gate["policy_version"] == "accepted-claims-v1"
    assert result.gate["finding_count"] == 1
    assert 'class="hive-claim"' in result.report
    assert ">Transformers use self-attention without recurrence.</span>" in result.report
    assert "Caching" not in result.report and len(inputs) == 1
    writer = write_task(store, result)
    assert result.report == writer["result"]["report"]
    assert result.gate == writer["result"]["gate"]
    assert result.gate["writer_assignment"]["task_id"] == writer["id"]
    assert_facts_preserved(result)


@pytest.mark.parametrize("mode,calls,code", [
    ("malformed", 1, "report_selection_invalid"),
    ("transport", 2, "execution_error"),
    ("deadline", 1, "task_timeout"),
    ("late-output", 1, "task_timeout"),
])
async def test_writer_error_classification_preserves_facts(store, monkeypatch, mode, calls, code):
    inputs = install_writer(select_first)
    original = agents.Caller.__call__
    writer_calls = 0
    cancelled = asyncio.Event()

    async def call(self, layer, agent, system, user, max_tokens=1500):
        nonlocal writer_calls
        if agent == "writer":
            writer_calls += 1
            if mode == "malformed":
                return "Private failing selection contents"
            if mode == "transport":
                raise OSError("provider unavailable")
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                if mode != "late-output":
                    raise
                # A cancellation-resistant provider must still lose publication authority.
                return select_first(writer_payload(user))
        return await original(self, layer, agent, system, user, max_tokens)

    monkeypatch.setattr(agents.Caller, "__call__", call)
    result = await execute(store, max_attempts=2, task_timeout_s=.04)
    assert result.status == "blocked" and result.report == ""
    writer = write_task(store, result)
    assert writer["status"] == "exhausted" and writer["result"]["code"] == code
    assert writer["attempt"] == writer_calls == calls
    assert_facts_preserved(result)
    assert "Private failing selection" not in json.dumps(result.events)
    if mode in {"deadline", "late-output"}:
        assert cancelled.is_set()
    assert_no_hive_tasks()


@pytest.mark.parametrize("lock_kind", ["mutex", "sqlite", "reader"])
@pytest.mark.parametrize("deadline_kind", ["task", "run"])
async def test_writer_cannot_publish_after_deadline_during_real_lock_wait(
        store, monkeypatch, lock_kind, deadline_kind):
    """A live lease does not permit writer completion after a logical deadline."""
    install_writer(select_first)
    original = store.publish_report
    waits = []
    lease_expiries = []

    def contended(*args, **kwargs):
        lease_expiries.append(store.get_task(args[0])["lease_expires"])
        acquired = threading.Event()
        release = threading.Event()
        errors = []

        def hold():
            other = None
            try:
                if lock_kind == "mutex":
                    with store._lock:
                        acquired.set()
                        release.wait(timeout=.3)
                else:
                    other = HiveStore(store.path)
                    if lock_kind == "reader":
                        assert other.db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
                        other.db.execute("BEGIN")
                        assert other.db.execute("SELECT * FROM tasks").fetchall()
                    else:
                        other.db.execute("BEGIN IMMEDIATE")
                    acquired.set()
                    release.wait(timeout=.3)
                    other.db.execute("ROLLBACK")
            except BaseException as exc:
                errors.append(exc)
            finally:
                if other is not None:
                    if other.db.in_transaction:
                        other.db.execute("ROLLBACK")
                    other.db.close()

        holder = threading.Thread(target=hold)
        holder.start()
        started = time.monotonic()
        try:
            assert acquired.wait(timeout=2), errors
            started = time.monotonic()
            return original(*args, **kwargs)
        finally:
            waits.append(time.monotonic() - started)
            release.set()
            holder.join(timeout=2)
            assert not holder.is_alive() and not errors

    monkeypatch.setattr(store, "publish_report", contended)
    result = await execute(store, max_attempts=1, lease_s=3,
                           task_timeout_s=.1 if deadline_kind == "task" else 3,
                           run_timeout_s=.1 if deadline_kind == "run" else 3)
    assert waits and waits[0] >= .2
    assert result.report == ""
    writer = write_task(store, result)
    assert lease_expiries[0] > time.time()
    assert writer["status"] != "done"
    assert not (writer["result"] or {}).get("report")
    if deadline_kind == "task":
        assert result.status == "blocked"
        assert writer["status"] == "exhausted"
        assert writer["result"]["code"] == "task_timeout"
        assert any(e["kind"] == "task_error" and e["code"] == "task_timeout" for e in result.events)
    else:
        assert result.status == "stopped"
        assert result.gate["code"] == "run_timeout"
        assert writer["result"]["code"] == "run_timeout"
    assert_facts_preserved(result)
    assert sorted(f["status"] for f in store.facts(result.run_id)) == ["rejected", "verified"]
    assert_no_hive_tasks()


async def test_transient_reader_contention_retries_within_deadline(store, monkeypatch):
    """A busy publication rolls back, then the ordinary bounded retry can succeed."""
    install_writer(select_first)
    original = store.publish_report
    original_timeout = 17
    store.db.execute(f"PRAGMA busy_timeout={original_timeout}")
    calls = []

    def contended(*args, **kwargs):
        if calls:
            calls.append(time.monotonic())
            return original(*args, **kwargs)
        calls.append(time.monotonic())
        reader = sqlite3.connect(store.path, isolation_level=None)
        try:
            assert reader.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
            reader.execute("BEGIN")
            assert reader.execute("SELECT * FROM tasks").fetchall()
            return original(*args, **kwargs)
        finally:
            reader.execute("ROLLBACK")
            reader.close()
            assert store.db.execute("PRAGMA busy_timeout").fetchone()[0] == original_timeout
            assert not store.db.in_transaction

    monkeypatch.setattr(store, "publish_report", contended)
    result = await execute(store, max_attempts=2, lease_s=3, task_timeout_s=1, run_timeout_s=1)
    assert result.status == "done" and result.report
    writer = write_task(store, result)
    assert writer["status"] == "done" and writer["attempt"] == len(calls) == 2
    errors = [e for e in result.events if e["kind"] == "task_error" and e["task"] == writer["id"]]
    assert len(errors) == 1 and errors[0]["retryable"] is True
    assert calls[1] - calls[0] >= .01  # The existing attempt backoff remains active.
    assert store.db.execute("PRAGMA busy_timeout").fetchone()[0] == original_timeout
    assert_facts_preserved(result)
    assert_no_hive_tasks()


async def test_snapshot_change_retries_with_fresh_inputs(store):
    def response(payload):
        if payload["candidates"][0]["claim"] != "Updated accepted claim.":
            store.db.execute("UPDATE facts SET claim='Updated accepted claim.' WHERE id=?",
                             (payload["candidates"][0]["id"],))
        return select_first(payload)

    inputs = install_writer(response)
    result = await execute(store, max_attempts=2)
    assert result.status == "done" and ">Updated accepted claim.</span>" in result.report
    assert "Transformers use" not in result.report
    assert [p["candidates"][0]["claim"] for p in inputs] == [
        "Transformers use self-attention without recurrence.", "Updated accepted claim."]
    assert write_task(store, result)["attempt"] == 2
    assert any(e["kind"] == "task_error" and e["code"] == "report_snapshot_changed"
               and e["retryable"] is True for e in result.events)
    assert_facts_preserved(result)


@pytest.mark.parametrize("damage", ["policy", "passed", "count", "boolean-count", "report", "empty-body",
                                     "empty-reason", "empty-passed"])
async def test_invalid_committed_artifact_fails_closed(store, monkeypatch, damage):
    install_writer('{"fact_ids":[]}' if damage.startswith("empty-") else select_first)
    original = store.tasks

    def tasks(run_id):
        rows = original(run_id)
        for task in rows:
            if task["kind"] == "write" and task["status"] == "done":
                artifact = task["result"]
                if damage == "policy": artifact["gate"]["policy_version"] = "other-policy"
                elif damage == "passed": artifact["gate"]["passed"] = False
                elif damage == "count": artifact["gate"]["finding_count"] = 0
                elif damage == "boolean-count": artifact["gate"]["finding_count"] = True
                elif damage == "report": artifact["report"] = ""
                elif damage == "empty-body": artifact["report"] = "Injected body"
                elif damage == "empty-reason": artifact["gate"]["reason"] = "other-reason"
                else: artifact["gate"]["passed"] = True
        return rows

    monkeypatch.setattr(store, "tasks", tasks)
    result = await execute(store)
    assert result.status == "blocked" and result.report == ""
    assert result.gate["reason"] == "report_artifact_invalid"
    assert_facts_preserved(result)


async def test_writer_cancellation_cleans_assignments_and_children(store, monkeypatch):
    install_writer(select_first)
    started = asyncio.Event()
    original = agents.Caller.__call__

    async def call(self, layer, agent, system, user, max_tokens=1500):
        if agent == "writer":
            started.set()
            await asyncio.Event().wait()
        return await original(self, layer, agent, system, user, max_tokens)

    monkeypatch.setattr(agents.Caller, "__call__", call)
    task = asyncio.create_task(execute(store))
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    run_id = store.db.execute("SELECT id FROM runs").fetchone()[0]
    assert store.get_run(run_id)["status"] == "stopped"
    assert store.open_tasks(run_id) == 0
    assert store.get_run(run_id)["report"] == ""
    assert (len(store.facts(run_id, "verified")), len(store.facts(run_id, "rejected"))) == (1, 1)
    assert_no_hive_tasks()


@pytest.mark.parametrize("field,value", [("run_id", "other-run"), ("objective", "other-objective")])
async def test_direct_writer_rejects_mismatched_snapshot_before_dispatch(store, field, value):
    rid = store.create_run("objective", 1000)
    snapshot = replace(store.report_snapshot(rid, "objective"), **{field: value})

    async def call(*args):
        pytest.fail("invalid snapshot dispatched to writer")

    with pytest.raises(ReportInputError):
        await agents.run_writer(store, rid, "objective", call, snapshot=snapshot)
