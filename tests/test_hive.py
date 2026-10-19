"""Offline tests for the lite hive and the provider router (mock provider, no network, no keys)."""
import json
import re
import pytest

from app.hive import run_hive
from app.hive.store import HiveStore
from app.hive.watchdog import is_looping
from app.hive.agents import final_gate, parse_json
from app.llm import LLMConfig, LLMRouter, ModelSpec, set_router
from app.llm.config import load_llm_config

SRC = [
    {"id": "a1", "title": "Attention is all you need", "url": "http://x/a1",
     "abstract": "The Transformer relies entirely on self-attention and dispenses with recurrence."},
    {"id": "a2", "title": "Cache study", "url": "http://x/a2",
     "abstract": "Semantic caching reduced redundant model calls by roughly forty percent in our trials."},
]


async def fake_search(q, n):
    return SRC


def routed_config() -> LLMConfig:
    m = lambda name: ModelSpec(provider="mock", model=name)
    return LLMConfig(default=m("m-default"),
                     layers={"knull": m("m-knull"), "workers": m("m-workers"), "verifier": m("m-verifier")},
                     agents={"writer": m("m-writer")})


def make_handler(bad_quote=False, bad_verdict=False, uncited=False):
    def h(spec, messages):
        sysmsg = messages[0]["content"]
        user = messages[-1]["content"]
        if "Knull" in sysmsg:
            return json.dumps({"subtasks": [{"title": "Attention", "query": "self attention"}]})
        if "research symbiote" in sysmsg:
            ids = re.findall(r"\[(E-[0-9a-f]{8})\]", user)
            claims = [
                {"claim": "Transformers use self-attention without recurrence.", "evidence_id": ids[0],
                 "quote": "relies entirely on self-attention"},
                {"claim": "Caching cut calls by 40%.", "evidence_id": ids[1],
                 "quote": "reduced redundant model calls by roughly forty percent"},
            ]
            if bad_quote:
                claims.append({"claim": "Made-up claim.", "evidence_id": ids[0], "quote": "this text is not in the source"})
            return json.dumps({"claims": claims})
        if "verifier" in sysmsg:
            if bad_verdict and "Caching" in user:
                return json.dumps({"verdict": "unsupported", "note": "overstated"})
            return json.dumps({"verdict": "supported", "note": "ok"})
        if "writer symbiote" in sysmsg:
            facts = re.findall(r"\[(F-[0-9a-f]{8})\] (.*)", user)
            body = "## Findings\n" + " ".join(f"{c} [{i}]" for i, c in facts)
            if uncited:
                body += " This sentence has no citation. This one cites a fake fact [F-deadbeef]."
            return body
        return "{}"
    return h


@pytest.fixture
def router():
    r = LLMRouter(routed_config(), mock_handler=make_handler())
    set_router(r)
    yield r
    set_router(None)


def test_config_resolution_order():
    c = routed_config()
    assert c.resolve("knull", "planner").model == "m-knull"
    assert c.resolve("workers", "writer").model == "m-writer"   # agent beats layer
    assert c.resolve("unknown").model == "m-default"


def test_load_yaml_config(tmp_path):
    p = tmp_path / "llm.yaml"
    p.write_text("default: {provider: openai, model: gpt-x}\nlayers:\n  knull: {provider: anthropic, model: c-x}\n"
                 "agents:\n  critic: {provider: gemini, model: g-x}\n")
    c = load_llm_config(str(p))
    assert (c.resolve("knull").provider, c.resolve("graph", "critic").provider, c.resolve("graph").provider) == \
           ("anthropic", "gemini", "openai")
    p.write_text("default: {provider: bogus, model: x}\n")
    with pytest.raises(ValueError):
        load_llm_config(str(p))


def test_default_config_is_ollama(tmp_path):
    assert load_llm_config(str(tmp_path / "missing.yaml")).default.provider == "ollama"


def test_lease_fence_blocks_stale_worker():
    s = HiveStore()
    rid = s.create_run("x", 1000)
    tid = s.add_task(rid, "k", "research", "t", {})
    assert s.add_task(rid, "k", "research", "t", {}) == tid  # unique topic key
    a = s.claim(rid, "w1", lease_s=10, now=100)
    assert a and a["attempt"] == 1 and a["fence"] == 1
    assert s.claim(rid, "w2", now=101) is None               # already claimed
    s.expire_leases(rid, now=200)                             # w1's lease expired, requeued
    b = s.claim(rid, "w1", lease_s=10, now=201)               # SAME worker name reclaims
    assert b["fence"] == 2
    # the old attempt returns late: rejected even though the worker name matches
    assert not s.publish(tid, "w1", a["attempt"], a["fence"], {"r": 1}, now=202)
    assert s.publish(tid, "w1", b["attempt"], b["fence"], {"r": 2}, now=202)
    assert s.get_task(tid)["status"] == "done"


def test_expired_lease_cannot_publish_and_attempts_cap():
    s = HiveStore()
    rid = s.create_run("x", 1000)
    tid = s.add_task(rid, "k", "research", "t", {})
    a = s.claim(rid, "w1", lease_s=5, now=0)
    assert not s.publish(tid, "w1", a["attempt"], a["fence"], {}, now=50)   # lease expired
    for i in range(1, 3):
        s.expire_leases(rid, max_attempts=3, now=1000 * i)
        s.claim(rid, "w", lease_s=5, now=1000 * i + 1)
    out = s.expire_leases(rid, max_attempts=3, now=9999)
    assert out and out[0]["action"] == "exhausted"


def test_dependencies_gate_claims():
    s = HiveStore()
    rid = s.create_run("x", 1000)
    r = s.add_task(rid, "r", "research", "r", {})
    v = s.add_task(rid, "v", "verify", "v", {}, [r])
    assert s.claim(rid, "w", kinds=["verify"]) is None
    t = s.claim(rid, "w", kinds=["research"])
    s.publish(t["id"], "w", t["attempt"], t["fence"], {})
    assert s.claim(rid, "w", kinds=["verify"])["id"] == v


def test_looping_detector():
    assert is_looping(["same output here", "same output here", "same output here"])
    assert not is_looping(["alpha beta", "gamma delta", "epsilon zeta"])


def test_final_gate_removes_uncited_and_unverified():
    body, gate = final_gate("## Findings\nGood claim [F-aaaaaaaa]. Unsupported prose here. Fake [F-bbbbbbbb].", {"F-aaaaaaaa"})
    assert "Good claim" in body and "Unsupported" not in body and "Fake" not in body
    assert not gate["passed"] and len(gate["removed_uncited_or_unverified"]) == 2


def test_parse_json_tolerant():
    assert parse_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json("no json") is None


async def test_full_run_routes_each_layer_to_its_model(router):
    r = await run_hive("Attention and caching", workers=2, max_subtasks=1, search=fake_search, tick_s=0.01)
    assert r.status == "done" and r.facts_verified == 2 and r.gate["passed"]
    assert "[F-" in r.report and "## Sources" in r.report
    used = {(u["layer"], u["agent"]): u["model"] for u in r.usage_by_route}
    assert used[("knull", "planner")] == "m-knull"
    assert used[("workers", "researcher")] == "m-workers"
    assert used[("verifier", "verifier")] == "m-verifier"
    assert used[("workers", "writer")] == "m-writer"
    assert r.spent_tokens > 0


async def test_non_verbatim_quote_never_enters_hive():
    set_router(LLMRouter(routed_config(), mock_handler=make_handler(bad_quote=True)))
    r = await run_hive("x", workers=1, max_subtasks=1, search=fake_search, tick_s=0.01)
    set_router(None)
    assert all("Made-up" not in l for l in r.report.splitlines())
    assert r.facts_verified == 2


async def test_verifier_rejection_keeps_claim_out_of_report():
    set_router(LLMRouter(routed_config(), mock_handler=make_handler(bad_verdict=True)))
    r = await run_hive("x", workers=1, max_subtasks=1, search=fake_search, tick_s=0.01)
    set_router(None)
    assert r.facts_verified == 1 and r.facts_rejected == 1 and "Caching" not in r.report


async def test_writer_uncited_sentences_are_stripped():
    set_router(LLMRouter(routed_config(), mock_handler=make_handler(uncited=True)))
    r = await run_hive("x", workers=1, max_subtasks=1, search=fake_search, tick_s=0.01)
    set_router(None)
    assert r.status == "done_with_removals" and "no citation" not in r.report and "deadbeef" not in r.report


async def test_budget_cap_stops_run_instead_of_reporting_done():
    set_router(LLMRouter(routed_config(), mock_handler=make_handler()))
    r = await run_hive("x", workers=1, max_subtasks=1, budget_tokens=30, search=fake_search, tick_s=0.01)
    set_router(None)
    assert r.status in ("stopped", "blocked") and r.report == ""


async def test_worker_crash_is_requeued_and_run_completes(router):
    calls = {"n": 0}

    async def flaky(q, n):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("tool down")
        return SRC
    r = await run_hive("x", workers=1, max_subtasks=1, search=flaky, tick_s=0.01)
    assert r.status == "done" and any(e["kind"] == "task_error" for e in r.events)
