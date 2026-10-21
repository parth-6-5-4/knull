"""Report snapshots and publication against real, file-backed SQLite state."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import threading
import time

import pytest

from app.hive.reporting import (
    ReportInputError, ReportSnapshotChanged, WriterAssignment, render_report,
)
from app.hive.store import HiveStore, TaskGraphError


@pytest.fixture
def store(tmp_path):
    store = HiveStore(str(tmp_path / "reports.db"))
    yield store
    store.db.close()


def seed(store, run, ids=("F-one",), *, status="verified", evidence_id="E-one"):
    task_id = store.add_task(run, "seed-" + ids[0], "research", "Research", {})
    task = store.claim(run, "researcher", kinds=["research"], now=1)
    assert task["id"] == task_id
    assert store.publish(task_id, "researcher", task["attempt"], task["fence"], {},
                         evidence=[{"id": evidence_id, "source_id": "source-one", "title": "Source title",
                                    "url": "https://example.com/source", "text": "raw source secret"}],
                         facts=[{"id": fid, "claim": "Accepted " + fid, "evidence_id": evidence_id,
                                 "quote": "raw quote secret", "status": status} for fid in ids], now=2)


def writer(store, run, *, kind="write"):
    task_id = store.add_task(run, "writer", kind, "Write", {})
    task = store.claim(run, "writer", kinds=[kind], now=10, lease_s=100)
    assert task["id"] == task_id
    return WriterAssignment(task_id, "writer", task["attempt"], task["fence"])


def publish(store, assignment, snapshot, report, gate, *, now=11):
    return store.publish_report(assignment.task_id, assignment.worker, assignment.attempt,
                                assignment.fence, snapshot, report, gate, now=now)


def assert_unpublished(store, run, assignment):
    task = store.get_task(assignment.task_id)
    assert task["status"] == "claimed"
    assert task["result"] is None
    assert store.get_run(run)["report"] is None
    assert store.get_run(run)["gate"] is None
    assert not store.db.in_transaction


def prepared(store):
    run = store.create_run("Objective", 1000)
    seed(store, run, ("F-one", "F-two"))
    assignment = writer(store, run)
    snapshot = store.report_snapshot(run, "Objective", assignment=assignment)
    report, gate = render_report(snapshot, ("F-one",))
    return run, assignment, snapshot, report, gate


def test_snapshot_excludes_unaccepted_or_foreign_provenance(store):
    run = store.create_run("own", 1000)
    foreign = store.create_run("foreign", 1000)
    seed(store, run)
    seed(store, run, ("F-proposed",), status="proposed")
    seed(store, run, ("F-rejected",), status="rejected")
    seed(store, foreign, ("F-foreign",), evidence_id="E-foreign")
    for fid, eid in [("F-missing", "E-missing"), ("F-bound-foreign", "E-foreign")]:
        store.db.execute("INSERT INTO facts(id,run_id,claim,evidence_id,quote,status) VALUES(?,?,?,?,?,?)",
                         (fid, run, "orphan", eid, "quote", "verified"))
    snapshot = store.report_snapshot(run, "own")
    assert [fact.id for fact in snapshot.candidates] == ["F-one"]
    assert snapshot.eligible_count == 1
    assert snapshot.assignment is None
    assert snapshot.candidates[0].source_id == "source-one"


def test_candidate_window_is_stable(store):
    run = store.create_run("Objective", 1000)
    seed(store, run, tuple(f"F-{i:02}" for i in reversed(range(33))))
    snapshot = store.report_snapshot(run, "Objective")
    assert [fact.id for fact in snapshot.candidates] == [f"F-{i:02}" for i in range(32)]
    report, gate = render_report(snapshot, ("F-00",))
    assert report and gate["candidate_count"] == 32
    assert gate["eligible_count"] == 33 and gate["omitted_count"] == 1


def test_snapshot_read_is_coherent(store):
    """A committed insert between count and candidate reads must not split the view."""
    run = store.create_run("Objective", 1000)
    seed(store, run, ("F-01", "F-02"))
    # WAL is restricted to this disposable fixture, to allow commit while a reader is open.
    assert store.db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    other = HiveStore(store.path)
    barrier = threading.Barrier(2)
    intercepted = []

    def trace(sql):
        if "ORDER BY f.id" in sql and not intercepted:
            intercepted.append(True)
            barrier.wait(timeout=3)
            barrier.wait(timeout=3)

    def insert():
        barrier.wait(timeout=3)
        other.db.execute("INSERT INTO facts(id,run_id,claim,evidence_id,quote,status) VALUES(?,?,?,?,?,?)",
                         ("F-00", run, "Concurrent fact", "E-one", "quote", "verified"))
        barrier.wait(timeout=3)

    store.db.set_trace_callback(trace)
    try:
        with ThreadPoolExecutor(1) as pool:
            mutation = pool.submit(insert)
            snapshot = store.report_snapshot(run, "Objective")
            mutation.result(timeout=4)
        assert intercepted
        assert snapshot.eligible_count == 2
        assert [fact.id for fact in snapshot.candidates] == ["F-01", "F-02"]
        assert len(store.facts(run, "verified")) == 3
        assert not store.db.in_transaction
    finally:
        store.db.set_trace_callback(None)
        other.db.close()


async def test_snapshot_releases_transaction_before_model_await(store):
    run = store.create_run("Objective", 1000)
    seed(store, run)
    snapshot = store.report_snapshot(run, "Objective")

    async def model():
        assert not store.db.in_transaction
        await asyncio.sleep(0)
        assert not store.db.in_transaction
        return snapshot.candidates[0].id

    assert await model() == "F-one"


@pytest.mark.parametrize("mutation", [
    "claim", "quote", "evidence_binding", "source_id", "text", "title", "url",
    "revoked", "removed_fact", "removed_source", "fact_run", "source_run",
    "malformed_claim", "malformed_source",
])
def test_changed_snapshot_publication_is_atomic(store, mutation):
    run, assignment, snapshot, report, gate = prepared(store)
    other = HiveStore(store.path)
    try:
        if mutation in {"claim", "quote", "malformed_claim"}:
            field = "claim" if mutation == "malformed_claim" else mutation
            value = None if mutation == "malformed_claim" else "changed"
            other.db.execute(f"UPDATE facts SET {field}=? WHERE id='F-one'", (value,))
        elif mutation in {"source_id", "text", "title", "url", "malformed_source"}:
            field = "title" if mutation == "malformed_source" else mutation
            value = None if mutation == "malformed_source" else "changed"
            other.db.execute(f"UPDATE evidence SET {field}=? WHERE run_id=?", (value, run))
        elif mutation == "evidence_binding":
            other.db.execute("INSERT INTO evidence SELECT 'E-two',run_id,source_id,title,url,text FROM evidence WHERE run_id=?", (run,))
            other.db.execute("UPDATE facts SET evidence_id='E-two' WHERE id='F-one'")
        elif mutation == "revoked":
            other.db.execute("UPDATE facts SET status='rejected' WHERE id='F-one'")
        elif mutation == "removed_fact":
            other.db.execute("DELETE FROM facts WHERE id='F-one'")
        elif mutation == "removed_source":
            other.db.execute("DELETE FROM evidence WHERE run_id=?", (run,))
        else:
            foreign = other.create_run("foreign", 1000)
            table = "facts" if mutation == "fact_run" else "evidence"
            other.db.execute(f"UPDATE {table} SET run_id=? WHERE run_id=?", (foreign, run))
        with pytest.raises(ReportSnapshotChanged):
            publish(store, assignment, snapshot, report, gate)
        assert_unpublished(store, run, assignment)
    finally:
        other.db.close()


@pytest.mark.parametrize("mismatch", ["run", "assignment", "unbound"])
def test_publication_requires_matching_snapshot_binding(store, mismatch):
    run, assignment, snapshot, report, gate = prepared(store)
    if mismatch == "run":
        snapshot = replace(snapshot, run_id=store.create_run("foreign", 1000))
    elif mismatch == "assignment":
        snapshot = replace(snapshot, assignment=replace(assignment, fence=assignment.fence + 1))
    else:
        snapshot = replace(snapshot, assignment=None)
    with pytest.raises(ReportInputError):
        publish(store, assignment, snapshot, report, gate)
    assert_unpublished(store, run, assignment)


def test_unselected_fact_change_does_not_block_report(store):
    run, assignment, snapshot, report, gate = prepared(store)
    other = HiveStore(store.path)
    try:
        other.db.execute("UPDATE facts SET claim='Changed',status='rejected' WHERE id='F-two'")
        assert publish(store, assignment, snapshot, report, gate)
        result = store.get_task(assignment.task_id)["result"]
        assert result["gate"]["eligible_count"] == 2
        assert result["gate"]["selected_fact_ids"] == ["F-one"]
        assert store.get_task(assignment.task_id)["status"] == "done"
    finally:
        other.db.close()


def test_stale_report_attempt_cannot_publish(store):
    run, old, snapshot, report, gate = prepared(store)
    store.expire_leases(run, now=111)
    task = store.claim(run, "writer", now=112, lease_s=100)
    fresh = WriterAssignment(task["id"], "writer", task["attempt"], task["fence"])
    before = store.get_task(old.task_id)
    # Malformed caller content cannot bypass or precede the stale-assignment check.
    assert publish(store, old, None, None, None, now=113) is False
    assert publish(store, old, snapshot, report, gate, now=113) is False
    assert store.get_task(old.task_id) == before
    fresh_snapshot = store.report_snapshot(run, "Objective", assignment=fresh)
    fresh_report, fresh_gate = render_report(fresh_snapshot, ("F-one",))
    assert publish(store, fresh, fresh_snapshot, fresh_report, fresh_gate, now=113)
    committed = store.get_task(fresh.task_id)
    assert publish(store, fresh, None, "forged", None, now=114) is False
    assert publish(store, old, snapshot, report, gate, now=114) is False
    assert store.get_task(fresh.task_id) == committed
    assert store.get_run(run)["report"] is None


def after_database_contention(store, assignment, operation):
    """Invoke a real mutation while another handle holds its SQLite write lock."""
    other = HiveStore(store.path)
    started = threading.Event()
    lease_expires = time.time() + 0.25
    store.db.execute("UPDATE tasks SET lease_expires=? WHERE id=?", (lease_expires, assignment.task_id))

    def trace(sql):
        if sql == "BEGIN IMMEDIATE" or sql.startswith("UPDATE tasks"):
            started.set()

    store.db.set_trace_callback(trace)
    other.db.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(operation)
            try:
                assert started.wait(timeout=2)
                assert time.time() < lease_expires
                # The real SQLite write lock stays held until authority has expired.
                time.sleep(max(0, lease_expires - time.time()) + 0.05)
                assert not pending.done()
            finally:
                other.db.execute("ROLLBACK")
            return pending.result(timeout=2)
    finally:
        store.db.set_trace_callback(None)
        if other.db.in_transaction:
            other.db.execute("ROLLBACK")
        other.db.close()


def test_report_publication_rechecks_lease_after_database_contention(store):
    """Waiting for another writer cannot extend authority past the real lease expiry."""
    run, assignment, snapshot, report, gate = prepared(store)
    accepted = after_database_contention(store, assignment, lambda: store.publish_report(
        assignment.task_id, assignment.worker, assignment.attempt, assignment.fence, snapshot, report, gate))
    assert accepted is False
    assert_unpublished(store, run, assignment)


@pytest.mark.parametrize("action", ["publish", "set_fact_status", "heartbeat", "release", "exhaust"])
def test_existing_mutation_rechecks_lease_after_database_contention(store, action):
    run = store.create_run("Objective", 1000)
    seed(store, run, status="proposed")
    assignment = writer(store, run, kind="verify" if action == "set_fact_status" else "research")
    args = (assignment.task_id, assignment.worker, assignment.attempt, assignment.fence)
    before_facts = store.facts(run)
    before_evidence = store.evidence(run)

    def mutate():
        if action == "publish":
            return store.publish(*args, {"late": True}, evidence=[{
                "id": "E-late", "source_id": "late", "title": "late", "url": "https://late", "text": "late",
            }], facts=[{"id": "F-late", "claim": "Late", "evidence_id": "E-late"}])
        if action == "set_fact_status":
            return store.set_fact_status(*args, {"F-one": ("verified", "Late promotion")}, {"late": True})
        if action == "heartbeat":
            return store.heartbeat(*args, lease_s=100)
        if action == "release":
            return store.release(*args, "Late failure")
        return store.mark_exhausted(assignment.task_id, "Late failure", worker=assignment.worker,
                                    attempt=assignment.attempt, fence=assignment.fence)

    assert after_database_contention(store, assignment, mutate) is False
    assert_unpublished(store, run, assignment)
    assert store.facts(run) == before_facts
    assert store.evidence(run) == before_evidence
    assert store.get_task(assignment.task_id)["lease_expires"] < time.time()


def test_generic_publication_cannot_complete_writer(store):
    run = store.create_run("Objective", 1000)
    assignment = writer(store, run)
    args = (assignment.task_id, "writer", assignment.attempt, assignment.fence)
    assert store.publish(assignment.task_id, "writer", 999, 999, {}, now=11) is False
    with pytest.raises(TaskGraphError):
        store.publish(*args, {"report": "forged"}, now=11)
    assert_unpublished(store, run, assignment)


@pytest.mark.parametrize("kind", ["write", "research"])
def test_verifier_publication_cannot_complete_writer(store, kind):
    run = store.create_run("Objective", 1000)
    assignment = writer(store, run, kind=kind)
    assert not store.set_fact_status(assignment.task_id, "writer", 999, 999, {}, {}, now=11)
    with pytest.raises(TaskGraphError):
        store.set_fact_status(assignment.task_id, "writer", assignment.attempt, assignment.fence,
                              {}, {}, now=11)
    assert_unpublished(store, run, assignment)


@pytest.mark.parametrize("kind", ["verify", "research"])
def test_report_publication_rejects_nonwriter_task(store, kind):
    run = store.create_run("Objective", 1000)
    seed(store, run)
    assignment = writer(store, run, kind=kind)
    snapshot = store.report_snapshot(run, "Objective", assignment=assignment)
    report, gate = render_report(snapshot, ("F-one",))
    with pytest.raises(TaskGraphError):
        publish(store, assignment, snapshot, report, gate)
    assert_unpublished(store, run, assignment)


@pytest.mark.parametrize("forgery", ["body", "gate", "selection", "missing_selection"])
def test_forged_report_body_is_rejected(store, forgery):
    run, assignment, snapshot, report, gate = prepared(store)
    if forgery == "body":
        report = report.replace("Accepted F-one", "Reversed claim")
    elif forgery == "gate":
        gate["provenance"][0]["evidence_sha256"] = "0" * 64
    elif forgery == "selection":
        gate["selected_fact_ids"] = ["F-forged"]
    else:
        del gate["selected_fact_ids"]
    with pytest.raises(ReportInputError):
        publish(store, assignment, snapshot, report, gate)
    assert_unpublished(store, run, assignment)


def test_report_provenance_survives_reopen(store):
    run, assignment, snapshot, report, gate = prepared(store)
    schema_version = store.db.execute("PRAGMA user_version").fetchone()[0]
    assert publish(store, assignment, snapshot, report, gate)
    reopened = HiveStore(store.path)
    try:
        result = reopened.get_task(assignment.task_id)["result"]
        assert result == {"report": report, "gate": gate}
        assert result["gate"]["writer_assignment"] == {
            "task_id": assignment.task_id, "worker": "writer", "attempt": 1, "fence": 1,
        }
        provenance = result["gate"]["provenance"]
        assert len(provenance) == 1
        assert {key: provenance[0][key] for key in ("fact_id", "claim", "evidence_id", "source_id", "title", "url")} == {
            "fact_id": "F-one", "claim": "Accepted F-one", "evidence_id": "E-one",
            "source_id": "source-one", "title": "Source title", "url": "https://example.com/source",
        }
        fact = snapshot.candidates[0]
        for field in ("claim_sha256", "quote_sha256", "evidence_sha256", "binding_sha256"):
            assert provenance[0][field] == getattr(fact, field)
            assert len(provenance[0][field]) == 64
        serialized = json.dumps(result)
        assert "raw source secret" not in serialized and "raw quote secret" not in serialized
        assert reopened.db.execute("PRAGMA user_version").fetchone()[0] == schema_version == 1
        assert reopened.get_run(run)["report"] is None
    finally:
        reopened.db.close()


def test_no_findings_publication_keeps_explicit_failure_metadata(store):
    run, assignment, snapshot, _, _ = prepared(store)
    report, gate = render_report(snapshot, ())
    assert publish(store, assignment, snapshot, report, gate)
    task = store.get_task(assignment.task_id)
    assert task["result"]["report"] == ""
    assert task["result"]["gate"]["passed"] is False
    assert task["result"]["gate"]["reason"] == "no_selected_findings"
