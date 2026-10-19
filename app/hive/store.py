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
import sqlite3
import threading
import time
import uuid
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY, objective TEXT, status TEXT, budget_tokens INTEGER,
  created REAL, report TEXT, gate TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, run_id TEXT, topic_key TEXT, kind TEXT, title TEXT,
  payload TEXT, deps TEXT, status TEXT DEFAULT 'pending', owner TEXT,
  attempt INTEGER DEFAULT 0, fence INTEGER DEFAULT 0, lease_expires REAL,
  result TEXT, UNIQUE(run_id, topic_key));
CREATE TABLE IF NOT EXISTS evidence(
  id TEXT PRIMARY KEY, run_id TEXT, source_id TEXT, title TEXT, url TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS facts(
  id TEXT PRIMARY KEY, run_id TEXT, task_id TEXT, claim TEXT, evidence_id TEXT,
  quote TEXT, status TEXT DEFAULT 'proposed', note TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS ledger(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, layer TEXT, agent TEXT,
  provider TEXT, model TEXT, in_tok INTEGER, out_tok INTEGER);
"""

TERMINAL = ("done", "exhausted", "failed")


class HiveStore:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

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
              lease_s: float = 600, now: Optional[float] = None) -> Optional[dict]:
        """Atomically claim one READY task (pending, all deps done)."""
        now = now if now is not None else time.time()
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                rows = self.db.execute(
                    "SELECT * FROM tasks WHERE run_id=? AND status='pending' ORDER BY rowid", (run_id,)).fetchall()
                done = {r["id"] for r in self.db.execute(
                    "SELECT id FROM tasks WHERE run_id=? AND status='done'", (run_id,))}
                for r in rows:
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

    def heartbeat(self, task_id, worker, attempt, fence, lease_s=600, now=None) -> bool:
        now = now if now is not None else time.time()
        with self._lock:
            if not self._holds(task_id, worker, attempt, fence, now):
                return False
            self.db.execute("UPDATE tasks SET lease_expires=? WHERE id=?", (now + lease_s, task_id))
            return True

    def publish(self, task_id, worker, attempt, fence, result: dict, evidence: Optional[list[dict]] = None,
                facts: Optional[list[dict]] = None, now: Optional[float] = None) -> bool:
        """Write result + evidence + proposed facts in ONE transaction, only if the claim is still held."""
        now = now if now is not None else time.time()
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if not self._holds(task_id, worker, attempt, fence, now):
                    self.db.execute("ROLLBACK")
                    return False
                t = self.db.execute("SELECT run_id FROM tasks WHERE id=?", (task_id,)).fetchone()
                run_id = t["run_id"]
                for e in evidence or []:
                    self.db.execute("INSERT OR IGNORE INTO evidence(id,run_id,source_id,title,url,text) VALUES(?,?,?,?,?,?)",
                                    (e["id"], run_id, e.get("source_id", ""), e.get("title", ""), e.get("url", ""), e.get("text", "")))
                for f in facts or []:
                    self.db.execute("INSERT OR IGNORE INTO facts(id,run_id,task_id,claim,evidence_id,quote,status,note) VALUES(?,?,?,?,?,?,?,?)",
                                    (f["id"], run_id, task_id, f["claim"], f.get("evidence_id"), f.get("quote"),
                                     f.get("status", "proposed"), f.get("note", "")))
                self.db.execute("UPDATE tasks SET status='done', result=? WHERE id=?", (json.dumps(result), task_id))
                self.db.execute("COMMIT")
                return True
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def set_fact_status(self, task_id, worker, attempt, fence, updates: dict[str, tuple[str, str]],
                        result: dict, now: Optional[float] = None) -> bool:
        """Verifier publication: {fact_id: (status, note)} + task done, atomically, fence-checked."""
        now = now if now is not None else time.time()
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if not self._holds(task_id, worker, attempt, fence, now):
                    self.db.execute("ROLLBACK")
                    return False
                for fid, (status, note) in updates.items():
                    self.db.execute("UPDATE facts SET status=?, note=? WHERE id=?", (status, note, fid))
                self.db.execute("UPDATE tasks SET status='done', result=? WHERE id=?", (json.dumps(result), task_id))
                self.db.execute("COMMIT")
                return True
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def release(self, task_id: str, worker: str, attempt: int, fence: int, error: str) -> None:
        """Worker reports failure: back to pending (watchdog caps attempts)."""
        with self._lock:
            self.db.execute("UPDATE tasks SET status='pending', owner=NULL, result=? "
                            "WHERE id=? AND owner=? AND attempt=? AND fence=? AND status='claimed'",
                            (json.dumps({"error": error}), task_id, worker, attempt, fence))

    def mark_exhausted(self, task_id: str, reason: str) -> None:
        with self._lock:
            self.db.execute("UPDATE tasks SET status='exhausted', result=? WHERE id=?",
                            (json.dumps({"error": reason}), task_id))

    def expire_leases(self, run_id: str, max_attempts: int = 3, now: Optional[float] = None) -> list[dict]:
        """Requeue claimed tasks whose lease expired; mark exhausted past max_attempts."""
        now = now if now is not None else time.time()
        out = []
        with self._lock:
            rows = self.db.execute("SELECT id,attempt FROM tasks WHERE run_id=? AND status='claimed' AND lease_expires<=?",
                                   (run_id, now)).fetchall()
            for r in rows:
                if r["attempt"] >= max_attempts:
                    self.db.execute("UPDATE tasks SET status='exhausted', result=? WHERE id=?",
                                    (json.dumps({"error": "lease expired, attempts exhausted"}), r["id"]))
                    out.append({"task": r["id"], "action": "exhausted"})
                else:
                    self.db.execute("UPDATE tasks SET status='pending', owner=NULL WHERE id=?", (r["id"],))
                    out.append({"task": r["id"], "action": "requeued"})
        return out

    # --- memory
    def facts(self, run_id: str, status: Optional[str] = None) -> list[dict]:
        q, a = "SELECT * FROM facts WHERE run_id=?", [run_id]
        if status:
            q += " AND status=?"; a.append(status)
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


