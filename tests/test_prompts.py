"""Prompt contract tests: every LLM-call prompt is well-formed and load-bearing rules hold."""
import json
import re

import pytest

from app.agent import prompts as graph_prompts
from app.hive import agents as hive
from app.llm.parsing import parse_json


def _json_skeletons(template: str) -> list[dict]:
    """Every doubled-brace JSON example inside a .format() template must be valid JSON."""
    found = []
    for m in re.finditer(r"\{\{.*?\}\}", template, re.S):
        skel = m.group(0).replace("{{", "{").replace("}}", "}")
        found.append(json.loads(skel))
    return found


def test_graph_prompts_format_cleanly():
    graph_prompts.PLANNER_PROMPT.format(objective="o", constraints="c", depth="normal")
    graph_prompts.SYNTHESIZER_PROMPT.format(objective="o", constraints="c",
                                            sources_text="s", chunks_text="ch")
    graph_prompts.CRITIC_PROMPT.format(objective="o", draft="d", sources_text="s")


def test_graph_prompts_have_valid_json_skeletons():
    p = _json_skeletons(graph_prompts.PLANNER_PROMPT)[0]
    assert isinstance(p["sub_queries"], list) and isinstance(p["estimated_sources_needed"], int)
    c = _json_skeletons(graph_prompts.CRITIC_PROMPT)[0]
    assert isinstance(c["confidence"], float) and isinstance(c["should_iterate"], bool)


def test_dead_prompts_removed():
    # intake/supervisor/finalizer never call the LLM (rule-based / mechanical), so
    # their prompts were deleted rather than iterated.
    for name in ("INTAKE_PROMPT", "SUPERVISOR_PROMPT", "FINALIZER_PROMPT"):
        assert not hasattr(graph_prompts, name), name


def test_synthesizer_grounds_claims():
    s = graph_prompts.SYNTHESIZER_PROMPT
    assert "untrusted" in s.lower()               # prompt-injection guardrail
    assert "Never invent" in s                    # no hallucinated citations
    assert "## Gaps & Open Questions" in s and "## References" in s  # finalizer expects these


async def test_hive_prompts_keep_output_contracts():
    for tmpl, key in ((hive.PLAN_SYSTEM, "subtasks"), (hive.RESEARCH_SYSTEM, "claims"),
                      (hive.VERIFY_SYSTEM, "verdict")):
        assert f'"{key}"' in tmpl
        assert "JSON only" in tmpl
    assert "untrusted data" in hive.RESEARCH_SYSTEM
    assert "untrusted data" in hive.VERIFY_SYSTEM
    assert "verbatim" in hive.RESEARCH_SYSTEM     # the quote rule the hive enforces mechanically
    # Exercise the current writer prompt boundary: candidate data goes in and
    # structured selection preserves accepted wording in the resulting report.
    from app.hive.store import HiveStore
    from tests.test_hive_report_store import seed
    store = HiveStore()
    run_id = store.create_run("Writer contract objective", 1000)
    seed(store, run_id)

    async def writer_call(layer, agent, system, user, max_tokens):
        data = json.loads(user)
        assert data == {"objective": "Writer contract objective",
                        "candidates": [{"id": "F-one", "claim": "Accepted F-one"}]}
        return '{"fact_ids":["F-one"]}'

    try:
        report, gate = await hive.run_writer(store, run_id, "Writer contract objective", writer_call)
        assert "Accepted F-one" in report and "[F-one]" in report
        assert gate["policy_version"] == "accepted-claims-v1"
        assert gate["passed"] is True and gate["selected_fact_ids"] == ["F-one"]
    finally:
        store.db.close()


def test_parse_json_tolerates_wrappers():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('Sure! Here is the JSON:\n```json\n{"a": 2}\n```') == {"a": 2}
    assert parse_json('prefix {"a": 3} suffix') == {"a": 3}
    assert parse_json("not json") is None
    assert parse_json('[1, 2]') is None           # arrays are not objects
