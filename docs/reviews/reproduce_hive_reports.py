"""Current HIVE-003 observations, separate from desired-behavior acceptance tests.

Run from project root: DEBUG=false python docs/reviews/reproduce_hive_reports.py
Uses mock providers and in-memory SQLite only; never opens application data.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ["DEBUG"] = "false"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.hive import run_hive
from app.hive.agents import run_writer
from app.hive.reporting import ReportInputError, ReportSelectionError
from app.hive.store import HiveStore
from app.llm import LLMRouter, set_router
from tests.test_hive import fake_search, make_handler, routed_config


async def probe_run(writer_text: str, objective: str = "Report integrity probe") -> dict:
    base = make_handler()

    def handler(spec, messages):
        if "writer symbiote" in messages[0]["content"]:
            return writer_text
        return base(spec, messages)

    store = HiveStore()
    set_router(LLMRouter(routed_config(), mock_handler=handler))
    try:
        run = await asyncio.wait_for(run_hive(
            objective, store, workers=1, max_subtasks=1,
            search=fake_search, tick_s=0.005), timeout=10)
        return {"status": run.status, "verified_facts": run.facts_verified,
                "gate": run.gate, "report": run.report}
    finally:
        set_router(None)
        store.db.close()


async def probe_writer(writer_text: str | None, objective: str = "Report integrity probe") -> dict:
    """Observe rejection or supported rendering with known accepted wording."""
    store = HiveStore()
    run_id = store.create_run(objective, 10000)
    task_id = store.add_task(run_id, "seed", "research", "Seed accepted claims", {})
    task = store.claim(run_id, "probe")
    evidence = {"id": "E-aaaaaaaa", "source_id": "cache-study", "title": "Cache study",
                "url": "https://fixture.example/cache", "text": "Caching reduced calls by 40%."}
    facts = [{"id": "F-aaaaaaaa", "claim": "Caching reduces calls by 40%.",
              "evidence_id": evidence["id"], "quote": evidence["text"], "status": "verified"},
             {"id": "F-bbbbbbbb", "claim": "The study measured model calls.",
              "evidence_id": evidence["id"], "quote": evidence["text"], "status": "verified"}]
    assert store.publish(task_id, "probe", task["attempt"], task["fence"], {}, [evidence], facts)
    before = store.facts(run_id)

    async def call(layer, agent, system, user, max_tokens):
        if writer_text is None:
            return json.dumps({"fact_ids": [row["id"] for row in json.loads(user)["candidates"]]})
        return writer_text

    try:
        try:
            report, gate = await run_writer(store, run_id, objective, call)
            observation = {"outcome": "rendered" if report else "no_findings", "report": report, "gate": gate}
        except (ReportInputError, ReportSelectionError) as exc:
            observation = {"outcome": "rejected", "error_code": exc.code, "reason": str(exc), "report": ""}
        observation["facts_unchanged"] = store.facts(run_id) == before
        return observation
    finally:
        store.db.close()


async def main() -> None:
    paths = ["app/hive/agents.py", "app/hive/reporting.py", "app/hive/runner.py", "app/hive/store.py",
             "tests/test_hive.py", "web/src/components/ReportView.tsx"]
    result = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                               check=True, capture_output=True, text=True).stdout.strip(),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        "python": sys.version.split()[0],
        "scope": "mock providers; in-memory SQLite; no network or application data",
        "writer_probes": {},
    }
    inputs = {
        "reversed_number": "## Findings\nCaching increases calls by 900% [F-aaaaaaaa].",
        "unsupported_heading": "## Caching increases calls by 900%",
        "empty_body": "",
        "citation_only": "[F-aaaaaaaa]",
        "multiple_valid_ids": "Contradiction [F-aaaaaaaa] [F-bbbbbbbb].",
        "html_heading": '## <img src=x onerror="alert(1)">',
        "valid_selection": '{"fact_ids":["F-aaaaaaaa"]}',
        "empty_selection": '{"fact_ids":[]}',
        "forged_selection": '{"fact_ids":["F-aaaaaaaa","F-forged"]}',
    }
    for name, value in inputs.items():
        result["writer_probes"][name] = {"input": value, **await probe_writer(value)}
    result["heading_only_run"] = await probe_run(inputs["unsupported_heading"])
    result["empty_body_run"] = await probe_run("")
    result["objective_html_writer"] = await probe_writer(None, '<img src=x onerror="alert(1)">')
    result["html_observation_boundary"] = (
        "New reports encode untrusted objective/claim/source data as literal text inside code-owned HTML. "
        "This offline observation does not test arbitrary historical-report sanitization or browser execution.")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
