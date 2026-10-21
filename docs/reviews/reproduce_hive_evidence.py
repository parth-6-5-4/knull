"""Read-only HIVE-001 diagnosis using disposable SQLite databases and mock models.

Historical probe: targets the pre-HIVE-003 report interface. Pending Task 5
adaptation; do not use this script as a current acceptance command.

Run from project root: DEBUG=false python docs/reviews/reproduce_hive_evidence.py
Records observed behavior, not desired acceptance behavior. Never opens app_data.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.hive import run_hive
from app.hive.agents import run_writer
from app.hive.store import HiveStore, EvidenceIntegrityError
from app.llm import LLMRouter, set_router
from tests.test_hive import fake_search, make_handler, routed_config


def claimed(store, run_id, key):
    task_id = store.add_task(run_id, key, "research", key, {})
    task = store.claim(run_id, "probe", lease_s=60, now=100)
    assert task["id"] == task_id
    return task


def publish(store, task, evidence, facts=()):
    return store.publish(task["id"], "probe", task["attempt"], task["fence"],
                         {"probe": True}, list(evidence), list(facts), now=101)


async def main():
    result = {"date": "2026-10-20", "python": sys.version.split()[0],
              "sqlite": sqlite3.sqlite_version, "providers": "mock only",
              "database_scope": "disposable TemporaryDirectory; no application data"}
    set_router(LLMRouter(routed_config(), mock_handler=make_handler()))
    try:
        with tempfile.TemporaryDirectory(prefix="hive-evidence-review-") as folder:
            store = HiveStore(str(Path(folder) / "repeat.db"))
            try:
                runs = []
                for _ in range(2):
                    run = await asyncio.wait_for(run_hive(
                        "Attention and caching", store, workers=2, max_subtasks=1,
                        search=fake_search, tick_s=0.001), timeout=5)
                    runs.append({"status": run.status, "verified": run.facts_verified,
                                 "rejected": run.facts_rejected,
                                 "evidence_rows": len(store.evidence(run.run_id))})
                result["repeated_source_runs"] = runs
                result["current_evidence_primary_key"] = [r["name"] for r in
                    sorted(store.db.execute("PRAGMA table_info(evidence)"), key=lambda row: row["pk"]) if r["pk"]]
                result["current_schema_version"] = store.db.execute("PRAGMA user_version").fetchone()[0]
            finally:
                store.db.close()

            store = HiveStore(str(Path(folder) / "integrity.db"))
            try:
                first = store.create_run("source owner", 1000)
                ev = {"id": "E-aaaaaaaa", "source_id": "paper-a", "title": "Original",
                      "url": "http://fixture/paper-a", "text": "Original evidence text."}
                assert publish(store, claimed(store, first, "original"), [ev])
                conflict = claimed(store, first, "conflict")
                try:
                    accepted = publish(store, conflict, [{**ev, "text": "Changed evidence text."}])
                except EvidenceIntegrityError:
                    accepted = False
                result["same_run_conflict"] = {
                    "accepted": accepted, "task_status": store.get_task(conflict["id"])["status"],
                    "retained_text": store.evidence(first, ev["id"])[0]["text"]}

                second = store.create_run("missing provenance", 1000)
                task = claimed(store, second, "foreign-reference")
                fact = {"id": "F-aaaaaaaa", "claim": "Claim with foreign-only evidence.",
                        "evidence_id": ev["id"], "quote": "Original evidence text.", "status": "verified"}
                extra = {**ev, "id": "E-bbbbbbbb", "url": "http://fixture/extra"}
                try:
                    accepted = publish(store, task, [extra], [fact])
                except EvidenceIntegrityError:
                    accepted = False
                result["unresolved_reference_publication"] = {
                    "accepted": accepted, "task_status": store.get_task(task["id"])["status"],
                    "facts_committed": len(store.facts(second)),
                    "extra_evidence_committed": bool(store.evidence(second, extra["id"])),
                    "referenced_evidence_found": bool(store.evidence(second, ev["id"]))}

                async def writer_call(layer, agent, system, user, max_tokens):
                    return "## Findings\nClaim with foreign-only evidence. [F-aaaaaaaa]"

                # Historical corruption enters only through a frozen legacy fixture and explicit upgrade.
                from tests.hive_testkit import legacy_database
                from app.hive.migrate import upgrade_hive_database
                historical_path = Path(folder) / 'historical.db'
                legacy_database(historical_path)
                upgrade_hive_database(str(historical_path), str(Path(folder) / 'historical-backup.db'))
                historical = HiveStore(str(historical_path))
                historical.db.execute("DELETE FROM evidence WHERE run_id='old'")
                try:
                    report, gate = await run_writer(historical, 'old', 'Missing provenance', writer_call)
                    eligible = len(historical.facts('old', 'verified'))
                finally:
                    historical.db.close()
                result["missing_provenance_marked_verified"] = {
                    "eligible_verified_facts": eligible,
                    "writer_report_nonempty": bool(report), "writer_gate_passed": gate["passed"],
                    "source_reference_present": "http://fixture/paper-a" in report}
            finally:
                store.db.close()
    finally:
        set_router(None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
