"""HIVE-003 diagnosis, not desired-behavior acceptance tests.

Historical probe: targets the pre-HIVE-003 report interface. Pending Task 5
adaptation; do not use this script as a current acceptance command.

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
from app.hive.agents import final_gate
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


async def main() -> None:
    paths = ["app/hive/agents.py", "app/hive/runner.py", "app/hive/store.py",
             "tests/test_hive.py", "web/src/components/ReportView.tsx"]
    result = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                               check=True, capture_output=True, text=True).stdout.strip(),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        "python": sys.version.split()[0],
        "scope": "mock providers; in-memory SQLite; no network or application data",
        "gate_probes": {},
    }
    inputs = {
        "reversed_number": "## Findings\nCaching increases calls by 900% [F-aaaaaaaa].",
        "unsupported_heading": "## Caching increases calls by 900%",
        "empty_body": "",
        "citation_only": "[F-aaaaaaaa]",
        "multiple_valid_ids": "Contradiction [F-aaaaaaaa] [F-bbbbbbbb].",
        "html_heading": '## <img src=x onerror="alert(1)">',
    }
    for name, value in inputs.items():
        body, gate = final_gate(value, {"F-aaaaaaaa", "F-bbbbbbbb"})
        result["gate_probes"][name] = {"input": value, "retained_body": body, "gate": gate}
    result["heading_only_run"] = await probe_run(inputs["unsupported_heading"])
    result["empty_body_run"] = await probe_run("")
    result["objective_html_run"] = await probe_run(
        "## Findings", '<img src=x onerror="alert(1)">')
    result["html_observation_boundary"] = (
        "Raw HTML retention observed in report strings. ReportView passes marked output to "
        "dangerouslySetInnerHTML without sanitization by source inspection; browser execution not tested.")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
