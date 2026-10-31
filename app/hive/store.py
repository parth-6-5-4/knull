"""
Hive store: one SQLite database holding tasks (claim table with lease + fence),
evidence, facts (the hive memory), decisions/events and a token ledger.

Claim/publish follow Book 1 ch. 12.3 / 15.2: a claim records an attempt number, an
increasing fence and an expiry. Publication re-checks owner, attempt, fence and expiry
inside one transaction, so a worker whose lease expired (or was reassigned, even to the
same worker name) cannot write.
"""
from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
import uuid
from typing import Optional

from app.hive.schema import SCHEMA, initialize_hive_schema
from app.hive.transactions import SQLiteTransactions, DatabaseIO
from app.hive.resource_types import SystemClock
from app.hive.reporting import (
    MAX_CANDIDATES, ReportInputError, ReportSelectionError, ReportSnapshot,
    ReportSnapshotChanged, WriterAssignment, render_report, snapshot_from_rows,
)

TERMINAL = ("done", "exhausted", "failed", "blocked")
TASK_KINDS = {"research", "verify", "write"}
_REPORT_ROWS = (
    "SELECT f.id,f.run_id,f.status,f.claim,f.evidence_id,f.quote,"
    "e.run_id AS evidence_run_id,e.source_id,e.title,e.url,e.text "
    "FROM facts f JOIN evidence e ON e.run_id=f.run_id AND e.id=f.evidence_id "
    "WHERE f.run_id=? AND f.status='verified'"
)


class TaskGraphError(ValueError):
    """Task graph cannot safely execute under the lite engine."""


class EvidenceIntegrityError(ValueError):
    """Publication or promotion would violate run-owned immutable provenance."""


class RunDeadlineExceeded(TimeoutError):
    """The whole run expired before its writer could publish."""


class ReportPublicationBusy(RuntimeError):
    """Transient report lock contention; retry under the task attempt/deadline policy."""


class HiveStore:
    def __init__(self, path: str = ":memory:", *, clock=None):
        self.path = path
        self.clock = clock if clock is not None else SystemClock()
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        try:
            initialize_hive_schema(self.db)
        except BaseException:
            self.db.close()
            raise

        self.transactions = SQLiteTransactions(self.db, self._lock, clock=self.clock)
        self.database_io = DatabaseIO(clock=self.clock)
        from app.hive.resource_store import ResourceStore
        self.resources = ResourceStore(self)

    async def aclose(self):
        """Drain owned SQL work before closing the shared connection."""
        try:
            await self.database_io.aclose()
        except Exception:
            self.db.close()  # Drain failed only after all worker operations finished.
            raise
        self.db.close()

    # --- helpers

    def event(self, run_id: str, kind: str, **data) -> None:
        with self._lock:
            self.db.execute("INSERT INTO events(run_id,ts,kind,data) VALUES(?,?,?,?)",
                            (run_id, time.time(), kind, json.dumps(data, default=str)))

    def events(self, run_id: str) -> list[dict]:
        rows = self.db.execute("SELECT ts,kind,data FROM events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [{"ts": r["ts"], "kind": r["kind"], **json.loads(r["data"])} for r in rows]

    # --- runs
    def create_run(self, objective: str, budget_tokens: int) -> str:
        rid = uuid.uuid4().hex[:12]
        with self._lock:
            self.db.execute("INSERT INTO runs(id,objective,status,budget_tokens,created) VALUES(?,?,?,?,?)",
                            (rid, objective, "running", budget_tokens, time.time()))
        return rid

    def get_run(self, run_id: str) -> Optional[dict]:
        r = self.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(r) if r else None

    def finish_run(self, run_id: str, status: str, report: str = "", gate: Optional[dict] = None) -> None:
        with self._lock:
            self.db.execute("UPDATE runs SET status=?, report=?, gate=? WHERE id=?",
                            (status, report, json.dumps(gate or {}), run_id))

    def set_status(self, run_id: str, status: str) -> None:
        with self._lock:
            self.db.execute("UPDATE runs SET status=? WHERE id=?", (status, run_id))

    # --- tasks
    def add_task(self, run_id: str, key: str, kind: str, title: str, payload: dict,
                 deps: Optional[list[str]] = None) -> str:
        """Idempotent on (run_id, key): a duplicate insert returns the existing task id."""
        tid = uuid.uuid4().hex[:10]
        with self._lock:
            self.db.execute(
                "INSERT OR IGNORE INTO tasks(id,run_id,topic_key,kind,title,payload,deps) VALUES(?,?,?,?,?,?,?)",
                (tid, run_id, key, kind, title, json.dumps(payload), json.dumps(deps or [])))
            r = self.db.execute("SELECT id FROM tasks WHERE run_id=? AND topic_key=?", (run_id, key)).fetchone()
        return r["id"]

    def get_task(self, task_id: str) -> dict:
        r = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._task(r)

    def tasks(self, run_id: str) -> list[dict]:
        return [self._task(r) for r in self.db.execute("SELECT * FROM tasks WHERE run_id=? ORDER BY rowid", (run_id,))]

    @staticmethod
    def _task(r) -> dict:
        d = dict(r)
        d["payload"] = json.loads(d["payload"] or "{}")
        d["deps"] = json.loads(d["deps"] or "[]")
        d["result"] = json.loads(d["result"]) if d.get("result") else None
        return d

    def claim(self, run_id: str, worker: str, kinds: Optional[list[str]] = None,
              lease_s: float = 600, now: Optional[float] = None,
              exclude: Optional[set[str]] = None) -> Optional[dict]:
        """Atomically claim one READY task (pending, all deps done)."""
        now = now if now is not None else time.time()
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self._block_unsatisfied(run_id)
                rows = self.db.execute(
                    "SELECT * FROM tasks WHERE run_id=? AND status='pending' ORDER BY rowid", (run_id,)).fetchall()
                done = {r["id"] for r in self.db.execute(
                    "SELECT id FROM tasks WHERE run_id=? AND status='done'", (run_id,))}
                for r in rows:
                    if exclude and r["id"] in exclude:
                        continue
                    if kinds and r["kind"] not in kinds:
                        continue
                    if not all(d in done for d in json.loads(r["deps"] or "[]")):
                        continue
                    self.db.execute(
                        "UPDATE tasks SET status='claimed', owner=?, attempt=attempt+1, fence=fence+1,"
                        " lease_expires=? WHERE id=? AND status='pending'", (worker, now + lease_s, r["id"]))
                    self.db.execute("COMMIT")
                    return self.get_task(r["id"])
                self.db.execute("COMMIT")
                return None
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def _holds(self, task_id: str, worker: str, attempt: int, fence: int, now: float) -> bool:
        r = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return bool(r and r["status"] == "claimed" and r["owner"] == worker and r["attempt"] == attempt
                    and r["fence"] == fence and r["lease_expires"] is not None and r["lease_expires"] > now)

    def owns(self, task_id, worker, attempt, fence, now=None) -> bool:
        with self._lock:
            return self._holds(task_id, worker, attempt, fence, time.time() if now is None else now)

    def heartbeat(self, task_id, worker, attempt, fence, lease_s=600, now=None) -> bool:
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                now = time.time() if now is None else now
                changed = self.db.execute(
                    "UPDATE tasks SET lease_expires=? WHERE id=? AND status='claimed' AND owner=? "
                    "AND attempt=? AND fence=? AND lease_expires>?",
                    (now + lease_s, task_id, worker, attempt, fence, now))
                self.db.execute("COMMIT")
                return changed.rowcount == 1
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def publish(self, task_id, worker, attempt, fence, result: dict, evidence: Optional[list[dict]] = None,
                facts: Optional[list[dict]] = None, now: Optional[float] = None) -> bool:
        """Write result + evidence + proposed facts in ONE transaction, only if the claim is still held."""
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                now = time.time() if now is None else now
                if not self._holds(task_id, worker, attempt, fence, now):
                    self.db.execute("ROLLBACK")
                    return False
                t = self.db.execute("SELECT run_id,kind FROM tasks WHERE id=?", (task_id,)).fetchone()
                if t["kind"] == "write":
                    raise TaskGraphError("Writer tasks require report publication")
                run_id = t["run_id"]
                for e in evidence or []:
                    eid = e.get("id")
                    if not isinstance(eid, str) or not eid.strip():
                        raise EvidenceIntegrityError(f"run {run_id}: invalid evidence identity")
                    values = tuple(e.get(k, "") for k in ("source_id", "title", "url", "text"))
                    existing = self.db.execute(
                        "SELECT source_id,title,url,text FROM evidence WHERE run_id=? AND id=?", (run_id, eid)).fetchone()
                    if existing is not None:
                        if tuple(existing) != values:
                            raise EvidenceIntegrityError(f"run {run_id}: conflicting evidence {eid}")
                    else:
                        self.db.execute("INSERT INTO evidence(id,run_id,source_id,title,url,text) VALUES(?,?,?,?,?,?)",
                                        (eid, run_id, *values))
                for f in facts or []:
                    eid = f.get("evidence_id")
                    if not eid or not self.db.execute(
                            "SELECT 1 FROM evidence WHERE run_id=? AND id=?", (run_id, eid)).fetchone():
                        raise EvidenceIntegrityError(f"run {run_id}: unresolved fact evidence {eid}")
                    self.db.execute("INSERT OR IGNORE INTO facts(id,run_id,task_id,claim,evidence_id,quote,status,note) VALUES(?,?,?,?,?,?,?,?)",
                                    (f["id"], run_id, task_id, f["claim"], f.get("evidence_id"), f.get("quote"),
                                     f.get("status", "proposed"), f.get("note", "")))
                self._complete_task(task_id, result)
                self.db.execute("COMMIT")
                return True
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def set_fact_status(self, task_id, worker, attempt, fence, updates: dict[str, tuple[str, str]],
                        result: dict, now: Optional[float] = None) -> bool:
        """Verifier publication: {fact_id: (status, note)} + task done, atomically, fence-checked."""
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                now = time.time() if now is None else now
                if not self._holds(task_id, worker, attempt, fence, now):
                    self.db.execute("ROLLBACK")
                    return False
                task = self.db.execute("SELECT run_id,kind FROM tasks WHERE id=?", (task_id,)).fetchone()
                if task["kind"] != "verify":
                    raise TaskGraphError("Fact-status publication requires a verifier task")
                run_id = task["run_id"]
                for fid, (status, note) in updates.items():
                    fact = self.db.execute("SELECT evidence_id FROM facts WHERE id=? AND run_id=?", (fid, run_id)).fetchone()
                    if fact is None or (status == "verified" and not self.db.execute(
                            "SELECT 1 FROM evidence WHERE run_id=? AND id=?", (run_id, fact[0])).fetchone()):
                        raise EvidenceIntegrityError(f"run {run_id}: unresolved provenance for fact {fid}")
                    self.db.execute("UPDATE facts SET status=?, note=? WHERE id=? AND run_id=?", (status, note, fid, run_id))
                self._complete_task(task_id, result)
                self.db.execute("COMMIT")
                return True
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def _complete_task(self, task_id: str, result: dict) -> None:
        """Complete inside the caller's fenced write transaction; never acquire the lock."""
        self.db.execute("UPDATE tasks SET status='done', result=? WHERE id=?", (json.dumps(result), task_id))

    def report_snapshot(self, run_id: str, objective: str, *,
                        assignment: WriterAssignment | None = None) -> ReportSnapshot:
        """Capture count and candidate sources in one short SQLite read snapshot."""
        with self._lock:
            self.db.execute("BEGIN")
            try:
                count = self.db.execute("SELECT COUNT(*) FROM (" + _REPORT_ROWS + ")", (run_id,)).fetchone()[0]
                rows = self.db.execute(_REPORT_ROWS + " ORDER BY f.id LIMIT ?", (run_id, MAX_CANDIDATES)).fetchall()
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        # Hashing/validation and subsequent model dispatch happen after releasing the read.
        return snapshot_from_rows(run_id, objective, [dict(row) for row in rows], count, assignment)

    def publish_report(self, task_id: str, worker: str, attempt: int, fence: int,
                       snapshot: ReportSnapshot, report: str, gate: dict, *,
                       now: float | None = None, task_deadline: float | None = None,
                       run_deadline: float | None = None) -> bool:
        """Fence, recheck selected provenance, and commit only deterministic report output."""

        def check_deadlines():
            current = time.monotonic()
            if run_deadline is not None and current >= run_deadline:
                raise RunDeadlineExceeded("logical run deadline exceeded")
            if task_deadline is not None and current >= task_deadline:
                raise TimeoutError("logical task deadline exceeded")

        deadline_bound = task_deadline is not None or run_deadline is not None
        with self._lock:
            try:
                # Rollback-journal readers can block COMMIT after BEGIN IMMEDIATE.
                # Acquire its exclusive lock first, then check deadlines before writes.
                # In WAL mode readers do not block commit; EXCLUSIVE equals IMMEDIATE.
                self.db.execute("BEGIN EXCLUSIVE" if deadline_bound else "BEGIN IMMEDIATE")
                now = time.time() if now is None else now
                if not self._holds(task_id, worker, attempt, fence, now):
                    self.db.execute("ROLLBACK")
                    return False
                for deadline in (task_deadline, run_deadline):
                    if (deadline is not None and (isinstance(deadline, bool)
                            or not isinstance(deadline, (int, float)) or not math.isfinite(deadline))):
                        raise ValueError("report deadline must be finite monotonic seconds")
                check_deadlines()
                task = self.db.execute("SELECT run_id,kind FROM tasks WHERE id=?", (task_id,)).fetchone()
                if task["kind"] != "write":
                    raise TaskGraphError("Report publication requires a writer task")
                if (not isinstance(snapshot, ReportSnapshot) or snapshot.run_id != task["run_id"]
                        or snapshot.assignment != WriterAssignment(task_id, worker, attempt, fence)):
                    raise ReportInputError("report_assignment_mismatch")
                if type(gate) is not dict or type(gate.get("selected_fact_ids")) is not list:
                    raise ReportInputError("report_gate_invalid")
                selected = tuple(gate["selected_fact_ids"])
                try:
                    expected_report, expected_gate = render_report(snapshot, selected)
                except ReportSelectionError:
                    raise ReportInputError("report_selection_invalid") from None
                candidates = {fact.id: fact for fact in snapshot.candidates}
                for fact_id in selected:
                    row = self.db.execute(_REPORT_ROWS + " AND f.id=?", (task["run_id"], fact_id)).fetchone()
                    if row is None:
                        raise ReportSnapshotChanged("report_selected_fact_missing")
                    try:
                        current = snapshot_from_rows(snapshot.run_id, snapshot.objective, [dict(row)], 1).candidates[0]
                    except ReportInputError:
                        raise ReportSnapshotChanged("report_selected_fact_changed") from None
                    # Equality also rejects caller-edited display fields with unchanged digest fields.
                    if current != candidates[fact_id]:
                        raise ReportSnapshotChanged("report_selected_fact_changed")
                try:
                    gate_matches = json.dumps(gate, sort_keys=True, allow_nan=False) == json.dumps(
                        expected_gate, sort_keys=True, allow_nan=False)
                except (TypeError, ValueError, RecursionError):
                    raise ReportInputError("report_gate_invalid") from None
                if type(report) is not str or report != expected_report or not gate_matches:
                    raise ReportInputError("report_artifact_mismatch")
                check_deadlines()
                self._complete_task(task_id, {"report": expected_report, "gate": expected_gate})
                self.db.execute("COMMIT")
                return True
            except BaseException as exc:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                if (deadline_bound and isinstance(exc, sqlite3.OperationalError)
                        and getattr(exc, "sqlite_errorcode", 0) & 0xff == sqlite3.SQLITE_BUSY):
                    check_deadlines()
                    raise ReportPublicationBusy("report publication lock busy") from exc
                raise

    def _transition_attempt(self, task_id, worker, attempt, fence, status, reason, code, now):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                now = time.time() if now is None else now
                changed = self.db.execute(
                    "UPDATE tasks SET status=?, owner=NULL, lease_expires=NULL, result=? "
                    "WHERE id=? AND owner=? AND attempt=? AND fence=? AND status='claimed' AND lease_expires>?",
                    (status, json.dumps({"error": reason, "code": code}), task_id, worker, attempt, fence, now))
                self.db.execute("COMMIT")
                return changed.rowcount == 1
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def release(self, task_id, worker, attempt, fence, error, *, now=None, code="execution_error") -> bool:
        """Retry only a still-current live assignment."""
        return self._transition_attempt(task_id, worker, attempt, fence, "pending", error, code, now)

    def mark_exhausted(self, task_id, reason, *, worker, attempt, fence, now=None, code="execution_error") -> bool:
        return self._transition_attempt(task_id, worker, attempt, fence, "exhausted", reason, code, now)

    def expire_leases(self, run_id: str, max_attempts: int = 3, now: Optional[float] = None) -> list[dict]:
        """Reclaim and propagation share one write transaction across SQLite handles."""
        now = time.time() if now is None else now
        out = []
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                rows = self.db.execute("SELECT id,attempt,fence,lease_expires FROM tasks "
                                       "WHERE run_id=? AND status='claimed' AND lease_expires<=?", (run_id, now)).fetchall()
                for r in rows:
                    exhausted = r["attempt"] >= max_attempts
                    self.db.execute(
                        "UPDATE tasks SET status=?,owner=NULL,lease_expires=NULL,result=? "
                        "WHERE id=? AND status='claimed' AND attempt=? AND fence=? AND lease_expires=?",
                        ("exhausted" if exhausted else "pending", json.dumps({"error": "lease expired", "code": "lease_expired"}),
                         r["id"], r["attempt"], r["fence"], r["lease_expires"]))
                    out.append({"task": r["id"], "action": "exhausted" if exhausted else "requeued"})
                self._block_unsatisfied(run_id)
                self.db.execute("COMMIT")
                return out
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def validate_graph(self, run_id: str) -> None:
        tasks = {t["id"]: t for t in self.tasks(run_id)}
        incoming = {}
        followers = {tid: [] for tid in tasks}
        for tid, task in tasks.items():
            deps = task["deps"]
            if task["kind"] not in TASK_KINDS or not isinstance(deps, list) or any(
                    not isinstance(d, str) or d not in tasks for d in deps) or len(set(deps)) != len(deps):
                raise TaskGraphError(f"Invalid task kind/dependency in {tid}")
            incoming[tid] = len(deps)
            for dep in deps: followers[dep].append(tid)
        ready = [tid for tid, count in incoming.items() if count == 0]
        visited = 0
        while ready:
            tid = ready.pop(); visited += 1
            for child in followers[tid]:
                incoming[child] -= 1
                if incoming[child] == 0: ready.append(child)
        if visited != len(tasks):
            raise TaskGraphError("Cyclic task dependencies")

    def _block_unsatisfied(self, run_id):
        changed = []
        while True:
            tasks = {r["id"]: r for r in self.db.execute("SELECT * FROM tasks WHERE run_id=?", (run_id,))}
            batch = []
            for tid, task in tasks.items():
                if task["status"] != "pending": continue
                deps = json.loads(task["deps"] or "[]")
                causes = [d for d in deps if d not in tasks or tasks[d]["status"] in TERMINAL[1:]]
                if causes: batch.append((tid, causes, "prerequisite_failed"))
            if not batch:
                pending = [t for t in tasks.values() if t["status"] == "pending"]
                active = any(t["status"] == "claimed" for t in tasks.values())
                runnable = any(all(d in tasks and tasks[d]["status"] == "done" for d in json.loads(t["deps"] or "[]")) for t in pending)
                if pending and not active and not runnable:
                    batch = [(t["id"], json.loads(t["deps"] or "[]"), "no_progress") for t in pending]
                else: break
            for tid, causes, code in batch:
                self.db.execute("UPDATE tasks SET status='blocked',result=? WHERE id=? AND status='pending'",
                                (json.dumps({"code": code, "prerequisites": causes}), tid))
                changed.append(tid)
        return changed

    def block_unsatisfied(self, run_id):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                result = self._block_unsatisfied(run_id)
                self.db.execute("COMMIT")
                return result
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def stop_run_tasks(self, run_id, code, reason):
        """Trusted local controller cleanup; preserve accepted results and fence active work."""
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute(
                    "UPDATE tasks SET status='failed',owner=NULL,lease_expires=NULL,fence=fence+1,result=? "
                    "WHERE run_id=? AND status='claimed'", (json.dumps({"code": code, "error": reason}), run_id))
                self.db.execute(
                    "UPDATE tasks SET status='blocked',result=? WHERE run_id=? AND status='pending'",
                    (json.dumps({"code": code, "error": reason}), run_id))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    # --- memory
    def facts(self, run_id: str, status: Optional[str] = None) -> list[dict]:
        q, a = "SELECT * FROM facts WHERE run_id=?", [run_id]
        if status:
            q += " AND status=?"; a.append(status)
        if status == "verified":
            q += " AND EXISTS (SELECT 1 FROM evidence e WHERE e.run_id=facts.run_id AND e.id=facts.evidence_id)"
        return [dict(r) for r in self.db.execute(q + " ORDER BY rowid", a)]

    def evidence(self, run_id: str, evidence_id: Optional[str] = None) -> list[dict]:
        q, a = "SELECT * FROM evidence WHERE run_id=?", [run_id]
        if evidence_id:
            q += " AND id=?"; a.append(evidence_id)
        return [dict(r) for r in self.db.execute(q, a)]

    # --- ledger
    def record_usage(self, run_id, layer, agent, provider, model, in_tok, out_tok) -> None:
        with self._lock:
            self.db.execute("INSERT INTO ledger(run_id,ts,layer,agent,provider,model,in_tok,out_tok) VALUES(?,?,?,?,?,?,?,?)",
                            (run_id, time.time(), layer, agent, provider, model, in_tok, out_tok))

    def spent(self, run_id: str) -> int:
        r = self.db.execute("SELECT COALESCE(SUM(in_tok+out_tok),0) s FROM ledger WHERE run_id=?", (run_id,)).fetchone()
        return int(r["s"])

    def usage_by_route(self, run_id: str) -> list[dict]:
        return [dict(r) for r in self.db.execute(
            "SELECT layer,agent,provider,model,COUNT(*) calls,SUM(in_tok) in_tok,SUM(out_tok) out_tok "
            "FROM ledger WHERE run_id=? GROUP BY layer,agent,provider,model", (run_id,))]

    def open_tasks(self, run_id: str) -> int:
        r = self.db.execute("SELECT COUNT(*) c FROM tasks WHERE run_id=? AND status IN ('pending','claimed')",
                            (run_id,)).fetchone()
        return int(r["c"])


