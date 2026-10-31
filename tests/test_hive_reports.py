"""Selected-claim rendering and the actual marked/Chromium boundary."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from app.hive import reporting as r


def row(fact_id="F-one", **changes):
    result = dict(id=fact_id, run_id="run-1", status="verified",
                  claim="Caching cut calls by 40%.", evidence_id="E-one", quote="private quote",
                  evidence_run_id="run-1", source_id="S-one", title="Caching study",
                  url="https://example.org/caching", text="private evidence")
    result.update(changes)
    return result


def snapshot(rows=None, **kwargs):
    rows = [row()] if rows is None else rows
    return r.snapshot_from_rows("run-1", kwargs.pop("objective", "Evaluate caching"), rows,
                                kwargs.pop("eligible_count", len(rows)), **kwargs)


def render(s, ids):
    assert callable(getattr(r, "render_report", None)), "literal report renderer is missing"
    return r.render_report(s, ids)


def test_render_uses_only_selected_claims():
    s = snapshot([row(), row("F-two", claim="Unused claim.", title="Unused source",
                             url="https://unused.example/")], eligible_count=35,
                 assignment=r.WriterAssignment("T-1", "W-1", 2, 3))
    report, gate = render(s, ("F-one",))
    assert "Caching cut calls by 40%." in report
    assert all(text not in report for text in ("04%", "Unused claim", "Unused source", "unused.example"))
    assert [line for line in report.splitlines() if line.startswith("#")] == [
        "# Research report", "## Findings", "## Sources"]
    assert gate["finding_count"] == gate["sentences"] == 1
    assert gate["selected_fact_ids"] == ["F-one"]
    assert gate["removed_uncited_or_unverified"] == []
    assert gate["passed"] is True and "reason" not in gate
    assert gate["policy_version"] == "accepted-claims-v1"
    assert (gate["candidate_count"], gate["eligible_count"], gate["omitted_count"]) == (2, 35, 33)
    assert gate["writer_assignment"] == dict(task_id="T-1", worker="W-1", attempt=2, fence=3)
    assert gate["warnings"] == []
    provenance = gate["provenance"]
    assert len(provenance) == 1
    assert provenance[0] == dict(fact_id="F-one", claim="Caching cut calls by 40%.",
        evidence_id="E-one", source_id="S-one", title="Caching study", url="https://example.org/caching",
        **{key: getattr(s.candidates[0], key) for key in (
            "claim_sha256", "quote_sha256", "evidence_sha256", "binding_sha256")})
    assert "private quote" not in json.dumps(gate) and "private evidence" not in json.dumps(gate)
    assert s.candidates[0].claim == "Caching cut calls by 40%."


def test_sources_match_selected_findings():
    report, gate = render(snapshot([row(), row("F-two", claim="Second finding.",
        source_id="S-two", title="Second source", url="https://second.example/")]), ("F-two", "F-one"))
    assert report.index("Second finding.") < report.index("Caching cut calls by 40%.")
    assert report.index("Second source") < report.index("Caching study")
    assert report.count('href="#hive-source-1"') == report.count('id="hive-source-1"') == 1
    assert report.count('href="#hive-source-2"') == report.count('id="hive-source-2"') == 1
    assert [entry["fact_id"] for entry in gate["provenance"]] == ["F-two", "F-one"]


def test_citation_labels_preserve_fact_ids_with_ordinal_anchors():
    report, _ = render(snapshot([row("F-good")]), ("F-good",))
    assert report.count("[F-good]") == 2
    assert 'href="#hive-source-1"' in report and 'id="hive-source-1"' in report


def test_shared_evidence_and_legacy_ids_keep_distinct_ordinal_references():
    hostile_id = 'legacy\" onclick=\"alert(1)'
    report, gate = render(snapshot([row(hostile_id), row("F-two", claim="Distinct claim.")]),
                          (hostile_id, "F-two"))
    assert hostile_id not in report
    assert report.count('href="https://example.org/caching"') == 2
    assert report.count('id="hive-source-') == 2
    assert [p["evidence_id"] for p in gate["provenance"]] == ["E-one", "E-one"]


@pytest.mark.parametrize("ids", [("unknown",), ("F-one", "F-one"), tuple("F-one" for _ in range(17)),
                                 ["F-one"], (True,), ({},)])
def test_direct_renderer_revalidates_selection(ids):
    with pytest.raises(r.ReportSelectionError):
        render(snapshot(), ids)


@pytest.mark.parametrize("rows,reason", [([], "no_verified_facts"), ([row()], "no_selected_findings")])
def test_empty_report_has_no_supporting_artifact(rows, reason):
    report, gate = render(snapshot(rows), ())
    assert report == ""
    assert gate["passed"] is False and gate["reason"] == reason
    assert gate["finding_count"] == gate["sentences"] == 0
    assert gate["selected_fact_ids"] == gate["provenance"] == gate["warnings"] == []
    assert gate["writer_assignment"] is None


UNSAFE_URLS = ["javascript:alert(1)", "data:text/html,hi", "file:///etc/passwd", "//example.org/x",
    "https://user:password@example.org/", "https://user@example.org/", "https://example.org/a b",
    "https://example.org/\nattack", "https://example.org/\rattack", "https://example.org/\tattack",
    "https://example.org/%0aattack", "https://example.org/%1Fattack", "https://example.org/%7f",
    "https://example.org/%C2%85", "https://example.org/%85", 'https://example.org/" onclick="alert(1)',
    "https://example.org/'", "https://example.org:bad/", "https://example.org:65536/",
    "https://example.org:/", "https:///missing", "https://-bad.example/", "https://bad_.example/",
    "https://[broken/", "https://999.999.1.1/", "https://example.org\\evil/", "https://%65xample.org/"]


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_unsafe_url_is_inert(url):
    report, gate = render(snapshot([row(url=url)]), ("F-one",))
    assert report.count("<a ") == 1  # The sole active link is the finding's citation.
    assert gate["warnings"] == [{"code": "unsafe_source_url", "fact_id": "F-one"}]
    assert gate["provenance"][0]["url"] == url


@pytest.mark.parametrize("url", ["http://example.org/", "https://example.org:8443/a?b=1&c=2#part",
    "HTTPS://EXAMPLE.ORG/a", "https://127.0.0.1/a", "https://[::1]:443/a", "https://例え.テスト/a"])
def test_valid_http_urls_are_links(url):
    report, gate = render(snapshot([row(url=url)]), ("F-one",))
    assert report.count("<a ") == 2 and gate["warnings"] == []
    assert "target=" not in report


@pytest.mark.parametrize("url", ["https://[::1]ignored/", "https://[::1].evil/", "https://[::1]@/"])
def test_malformed_bracketed_authority_is_inert(url):
    report, gate = render(snapshot([row(url=url)]), ("F-one",))
    assert report.count("<a ") == 1
    assert gate["warnings"] == [{"code": "unsafe_source_url", "fact_id": "F-one"}]


def test_warning_count_is_bounded_by_selected_findings():
    rows = [row(f"F-{i}", url="javascript:alert(1)") for i in range(16)]
    _, gate = render(snapshot(rows), tuple(entry["id"] for entry in rows))
    assert len(gate["warnings"]) == 16


def test_escaping_expansion_cannot_bypass_output_cap():
    rows = [row(f"F-{i}", claim="&" * 4096, title="&" * 2048, url="&" * 4096) for i in range(16)]
    with pytest.raises(r.ReportInputError, match="report_output_oversized"):
        render(snapshot(rows), tuple(entry["id"] for entry in rows))


def test_output_cap_exact_boundary_and_one_over():
    # Keep all raw fields valid; grow only a literal ASCII claim to hit the final byte boundary.
    rows = [row(f"F-{i}", claim="&" * 530, title="&" * 500, url="&" * 500) for i in range(16)]
    ids = tuple(entry["id"] for entry in rows)
    base, _ = render(snapshot(rows), ids)
    remaining = 131072 - len(base.encode("utf-8"))
    assert 0 < remaining < 3000
    rows[0]["claim"] += "x" * remaining
    exact, _ = render(snapshot(rows), ids)
    assert len(exact.encode("utf-8")) == 131072
    rows[0]["claim"] += "x"
    with pytest.raises(r.ReportInputError, match="report_output_oversized"):
        render(snapshot(rows), ids)


def test_marked_rendering_round_trip():
    attacks = [
        '  repeated   spaces\tand trailing  \r\n\r\n# Fake heading\rFinal line  ',
        '</span></li></ul><img src="https://attacker.invalid/pixel" onerror="alert(1)"><script>alert(1)</script>',
        '[fake citation](javascript:alert(1)) [99](#fake-source) **bold**\n\n## Extra heading',
        '&amp; &#10; &lt; <style>body{display:none}</style>',
        '中文 日本語 한국어 العربية עברית 😀🚀',
        'LongToken' * 400,
    ]
    fixtures = []
    for i, claim in enumerate(attacks):
        url = UNSAFE_URLS[i] if i % 2 else 'https://example.org/a?x=1&y=2'
        title = attacks[(i + 1) % len(attacks)][:500]
        objective = attacks[(i + 2) % len(attacks)]
        s = snapshot([row(claim=claim, title=title, url=url)], objective=objective)
        markdown, _ = render(s, ("F-one",))
        fixtures.append(dict(markdown=markdown, claims=[claim], fact_ids=["F-one"], objective=objective,
                             titles=[title], urls=[url], active_urls=[url] if i % 2 == 0 else []))
    # Cover every hostile URL in the browser too, including quoted attribute data.
    for start in range(0, len(UNSAFE_URLS), 16):
        urls = UNSAFE_URLS[start:start + 16]
        rows = [row(f'legacy-{i}\" onclick=\"attack', claim=f"Accepted URL finding {i}.",
                    title=f"Pinned source {i}.", url=url) for i, url in enumerate(urls)]
        markdown, _ = render(snapshot(rows), tuple(entry["id"] for entry in reversed(rows)))
        fixtures.append(dict(markdown=markdown, claims=[entry["claim"] for entry in reversed(rows)],
            fact_ids=[entry["id"] for entry in reversed(rows)],
            objective="Evaluate caching", titles=[entry["title"] for entry in reversed(rows)],
            urls=list(reversed(urls)), active_urls=[]))
    long_id = "F-" + "A" * 2000
    markdown, _ = render(snapshot([row(long_id)]), (long_id,))
    fixtures.append(dict(markdown=markdown, claims=["Caching cut calls by 40%."], fact_ids=[long_id],
        objective="Evaluate caching", titles=["Caching study"], urls=["https://example.org/caching"],
        active_urls=["https://example.org/caching"]))
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["node", "web/scripts/check-hive-report.mjs"], input=json.dumps(fixtures),
                            text=True, cwd=root, capture_output=True, timeout=120, env=os.environ.copy())
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["fixtures"] == 9 and evidence["viewport_checks"] == 18
    assert evidence["network_requests"] == evidence["page_errors"] == []
