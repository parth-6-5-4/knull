"""Strict report boundary contracts; all snapshots come from joined source rows."""
import importlib
import importlib.util
import json
from dataclasses import FrozenInstanceError

import pytest


def reporting():
    # A missing reporting contract is an assertion failure, not a collection error.
    assert importlib.util.find_spec("app.hive.reporting") is not None, "strict report contract is missing"
    return importlib.import_module("app.hive.reporting")


def row(fact_id="F-good", **changes):
    result = dict(id=fact_id, run_id="run-1", status="verified", claim="Accepted claim.",
                  evidence_id="E-source", quote="Accepted", evidence_run_id="run-1",
                  source_id="source-1", title="Source title", url="https://example.org/source",
                  text="Accepted claim from source.")
    result.update(changes)
    return result


def snapshot(rows=None, **kwargs):
    r = reporting()
    rows = [row()] if rows is None else rows
    return r.snapshot_from_rows("run-1", kwargs.pop("objective", "Research objective"), rows,
                                kwargs.pop("eligible_count", len(rows)), **kwargs)


@pytest.mark.parametrize("raw", [
    '```json\n{"fact_ids":[]}\n```', '{"fact_ids":[]} extra',
    '{"fact_ids":[],"fact_ids":[]}', '[]', '"text"', '1', 'true', 'null',
    '{"fact_ids":"F-good"}', '{"fact_ids":[true]}', '{"fact_ids":[1]}',
    '{"fact_ids":[null]}', '{"fact_ids":[{}]}', '{"fact_ids":[],"other":1}',
    '{}', '{"fact_ids":NaN}', '{"fact_ids":Infinity}', '{"fact_ids":-Infinity}',
])
def test_selection_rejects_noncontract_json(raw):
    r = reporting()
    with pytest.raises(r.ReportSelectionError) as error:
        r.parse_selection(raw, snapshot())
    assert error.value.code == "report_selection_invalid"
    assert len(str(error.value)) < 100


@pytest.mark.parametrize("ids", [
    ["F-good", "F-forged"], ["F-good", "F-good"], [f"F-{n}" for n in range(17)],
])
def test_selection_rejects_duplicate_unknown_or_excess_ids(ids):
    r = reporting()
    s = snapshot([row("F-good"), *[row(f"F-{n}") for n in range(17)]])
    with pytest.raises(r.ReportSelectionError):
        r.parse_selection(json.dumps({"fact_ids": ids}), s)


def test_selection_empty_and_sixteen_preserve_order():
    r = reporting()
    ids = [f"F-{n}" for n in reversed(range(16))]
    s = snapshot([row(i) for i in ids])
    assert r.parse_selection('{"fact_ids":[]}', s) == ()
    assert r.parse_selection(json.dumps({"fact_ids": ids}), s) == tuple(ids)
    assert r.parse_selection('{"fact_ids":["F-good"]}', snapshot()) == ("F-good",)


@pytest.mark.parametrize("field,limit", [("claim", 4096), ("title", 2048), ("url", 4096),
                                         ("objective", 4096)])
def test_report_utf8_boundaries(field, limit):
    r = reporting()
    exact = "é" * (limit // 2)
    kwargs = {"objective": exact} if field == "objective" else {}
    rows = [row(**{field: exact})] if field != "objective" else [row()]
    r.writer_messages(snapshot(rows, **kwargs))
    over = exact + "x"
    kwargs = {"objective": over} if field == "objective" else {}
    rows = [row(**{field: over})] if field != "objective" else [row()]
    with pytest.raises(r.ReportInputError):
        r.writer_messages(snapshot(rows, **kwargs))


def test_report_utf8_boundaries_response():
    r = reporting()
    fact_id = "é" * 1000
    s = snapshot([row(fact_id)])
    raw = json.dumps({"fact_ids": [fact_id]}, ensure_ascii=False, separators=(",", ":"))
    exact = raw + " " * (4096 - len(raw.encode("utf-8")))
    assert r.parse_selection(exact, s) == (fact_id,)
    with pytest.raises(r.ReportSelectionError):
        r.parse_selection(exact + " ", s)


def test_report_utf8_boundaries_candidates_and_eligible_count():
    r = reporting()
    assert len(snapshot([row(f"F-{n}") for n in range(32)]).candidates) == 32
    assert snapshot([], eligible_count=0).candidates == ()
    with pytest.raises(r.ReportInputError):
        snapshot([row(f"F-{n}") for n in range(33)])
    for count in (-1, 0, True, "1", 1.0):
        with pytest.raises(r.ReportInputError):
            snapshot(eligible_count=count)


def test_report_utf8_boundaries_complete_message_array():
    r = reporting()
    rows = [row(f"F-{n}", claim="é" * 2048) for n in range(15)]
    system, user = r.writer_messages(snapshot(rows, objective=""))
    message_bytes = len(json.dumps([{"role": "system", "content": system},
                                    {"role": "user", "content": user}],
                                   ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    remaining = 65536 - message_bytes
    assert 0 < remaining <= 4096
    exact_objective = "é" * (remaining // 2) + "x" * (remaining % 2)
    r.writer_messages(snapshot(rows, objective=exact_objective))
    with pytest.raises(r.ReportInputError):
        r.writer_messages(snapshot(rows, objective=exact_objective + "x"))
    with pytest.raises(r.ReportInputError):
        r.writer_messages(snapshot([row(f"F-{n}", claim="é" * 2048) for n in range(32)]))


@pytest.mark.parametrize("claim", ["", " \r\n\t", "\u2003"])
def test_report_rejects_empty_claim(claim):
    r = reporting()
    with pytest.raises(r.ReportInputError):
        snapshot([row(claim=claim)])


@pytest.mark.parametrize("field", ["id", "run_id", "status", "claim", "evidence_id", "quote",
                                   "evidence_run_id", "source_id", "title", "url", "text"])
@pytest.mark.parametrize("bad", [None, True, 42, "bad\x00value", "bad\ud800value"])
def test_report_rejects_nonstring_or_unrepresentable_fields(field, bad):
    r = reporting()
    with pytest.raises(r.ReportInputError) as error:
        snapshot([row(**{field: bad})])
    assert error.value.code == "report_input_invalid"
    assert len(str(error.value)) < 100


@pytest.mark.parametrize("bad", [None, True, "bad\x00objective", "bad\ud800objective"])
def test_report_rejects_unrepresentable_objective(bad):
    r = reporting()
    with pytest.raises(r.ReportInputError):
        snapshot(objective=bad)


@pytest.mark.parametrize("change", [{"run_id": "other"}, {"evidence_run_id": "other"},
                                     {"status": "proposed"}, {"status": "rejected"}])
def test_report_rejects_foreign_or_unverified_rows(change):
    r = reporting()
    with pytest.raises(r.ReportInputError):
        snapshot([row(**change)])


def test_report_rejects_duplicate_or_missing_candidate_identity():
    r = reporting()
    with pytest.raises(r.ReportInputError):
        snapshot([row(), row()])
    missing = row()
    del missing["id"]
    with pytest.raises(r.ReportInputError):
        snapshot([missing])


def test_writer_messages_send_only_objective_and_candidate_claims():
    r = reporting()
    assignment = r.WriterAssignment("task-1", "worker-1", 2, 3)
    s = snapshot([row(claim="Raw\r\nclaim\rcontinued", text="private source")], assignment=assignment)
    system, user = r.writer_messages(s)
    assert system
    assert json.loads(user) == {"objective": "Research objective", "candidates": [
        {"id": "F-good", "claim": "Raw\nclaim\ncontinued"}]}
    assert "private source" not in user
    assert not hasattr(s.candidates[0], "text")
    assert not hasattr(s.candidates[0], "quote")
    assert s.assignment == assignment
    with pytest.raises(FrozenInstanceError):
        s.objective = "changed"
    with pytest.raises(FrozenInstanceError):
        s.candidates[0].claim = "changed"


@pytest.mark.parametrize("field", ["claim", "quote", "evidence_id", "source_id", "title", "url", "text", "id"])
def test_raw_source_changes_invalidate_binding(field):
    first = snapshot([row()]).candidates[0]
    original = row()[field]
    changed = snapshot([row(**{field: original + "\r\n"})]).candidates[0]
    assert first.binding_sha256 != changed.binding_sha256
    for digest in (first.claim_sha256, first.quote_sha256, first.evidence_sha256, first.binding_sha256):
        assert len(digest) == 64
    if field == "claim":
        normalized = snapshot([row(claim=original + "\n")]).candidates[0]
        assert changed.claim_sha256 != normalized.claim_sha256
    if field == "quote":
        assert first.quote_sha256 != changed.quote_sha256
    if field == "text":
        assert first.evidence_sha256 != changed.evidence_sha256


@pytest.mark.parametrize("raw", [None, True, "\ud800", '{"fact_ids":["F-good"]}\x00'])
def test_selection_rejects_nonstring_or_invalid_unicode(raw):
    r = reporting()
    with pytest.raises(r.ReportSelectionError):
        r.parse_selection(raw, snapshot())
