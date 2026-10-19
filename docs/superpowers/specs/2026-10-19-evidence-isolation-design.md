# Run-scoped evidence isolation design

**Spec ID:** HIVE-001
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** None
**Plan:** [Draft implementation candidate](../plans/2026-10-19-evidence-isolation.md); joint spec/plan review pending

## Intent

A researcher should be able to run two objectives using the same papers without the second run losing its evidence or rejecting supported claims. Each claim must resolve to the source content actually published for its own run.

The maintainer requested a modular hive review and adoption of spec-driven development. This spec proposes the first isolated repair from that review; its technical design has not yet been approved.

## Current behavior and evidence

`app/hive/agents.py::evidence_id` derives a short ID from a source URL, ID or title. `app/hive/store.py` gives `evidence.id` a global primary key. `publish()` inserts evidence with `INSERT OR IGNORE`, while `evidence(run_id, evidence_id)` filters by run. A second run publishing the same source therefore has facts referring to evidence that exists only under the first run.

The [F1 reproduction](../../reviews/hive-gap-evidence.json) recorded: first run done with two verified facts; second run blocked with zero verified facts, two rejected facts and zero evidence rows. [Audit context](../../reviews/hive-modularization-review.md). These are dated observations; reproduce against current source before implementation.

## Scope and non-goals

Repair evidence identity, lookup and publication for the existing SQLite hive. Preserve the external citation representation and current research/verifier workflow.

Postgres, content-addressed cross-run memory, Jev, hierarchy, report paraphrase verification and crash-resume belong to separate specs. Run-scoped identity does not establish that two sources with identical URLs contain identical text, or that a supported claim is universally true.

## Approaches and chosen design

1. **Run-scoped evidence identity — proposed.** Store and resolve evidence under `(run_id, evidence_id)`. This directly repairs the existing invariant while preserving local evidence IDs used in model prompts.
2. **Global immutable snapshots plus run links.** Better foundation for shared long-term memory, but requires a snapshot/authorization/versioning model beyond this repair.
3. **Read the first global evidence row regardless of run.** Rejected: silently substitutes another run's source content and hides the provenance defect.

Within one run, re-publishing identical evidence may be idempotent. Conflicting content for an existing run-scoped ID must fail atomically and visibly; it must not overwrite or silently ignore the conflict. A later run may retain different content under its own run-scoped key.

## Requirements and invariants

| ID | Required observable behavior | Acceptance oracle |
|---|---|---|
| EVI-01 | Two runs can store the same local evidence ID independently. | Publishing identical source fixtures to two runs leaves two resolvable run-scoped records and both runs can verify their claims. |
| EVI-02 | Every new fact resolves evidence only in its own run. | A fact referencing evidence present only in another run is refused; no task completion, facts or partial evidence commit. |
| EVI-03 | Existing run content remains stable. | Same-run identical evidence publication is harmless; same ID with changed source metadata/text fails without altering earlier evidence or completing the conflicting attempt. |
| EVI-04 | Different runs may observe changed source content at one URL. | Both texts remain independently retrievable and each verifier receives its own run's text. |
| EVI-05 | Fenced publication remains atomic. | Stale attempt publication writes no evidence/facts/result; valid publication commits them together. Existing lease/fence tests still pass. |
| EVI-06 | Existing citations and callers retain their representation. | `E-...` and `F-...` prompt/report forms and successful API/CLI behavior remain compatible; no unrelated public response change. |
| EVI-07 | Storage upgrade preserves known provenance and makes missing provenance explicit. | Reopening an old-schema fixture retains resolvable evidence under its original run; a missing run/evidence pair is never repaired by copying another run's content or treated as verified. |
| EVI-08 | Upgrade is restartable and failure-safe. | Reopening upgraded data does not repeat destructive work; an interrupted/failed schema transition leaves an original recoverable database or a complete new schema, with an explicit error rather than mixed writable state. |

## Interfaces and data flow

API/CLI → existing runner → researcher evidence and proposed facts → fenced store publication → run-scoped evidence lookup → verifier → existing fact assessment path.

The store owns uniqueness, evidence resolution, conflicting-insert errors, migration and transaction scope. Existing `publish(...) -> bool` retains its false result for a lost lease; an evidence conflict or unresolved reference is an explicit integrity error and rolls back publication. The implementation plan must name the error type and migration mechanism before execution.

`evidence(run_id, evidence_id=None)` remains the caller-facing lookup. Any schema or index change must preserve the meaning of this interface. Callers do not gain a global evidence fallback. Source metadata and text used for same-run conflict detection are the fields already persisted: source ID, title, URL and text.

## Failure and resource model

Cover repeated sources, separate runs, changed text at one URL, duplicate publication, stale leases, unresolved fact references and exceptions during publication/upgrade. Use file-backed SQLite fixtures for reopen/migration behavior. This spec makes no multi-process locking or Postgres guarantee.

Missing historical evidence cannot be reconstructed safely from a URL or another run's record. Existing facts with missing run-scoped evidence must fail assessment/report eligibility until their provenance is explicitly recovered by a separate repair; they must not remain usable solely because an old status says verified.

## Compatibility, rollout and recovery

Keep schema upgrade local to hive storage. Test against an old-schema fixture, fresh database and already upgraded database. Take a consistent recoverable copy before a destructive table rebuild; record schema version only after a successful transaction. Do not mutate the unrelated legacy `app.db` workflow.

Existing reports are historical artifacts; this change must not silently regenerate them. Fresh verification/report construction must reject unresolved provenance. Before rollout, inspect affected stored data and report missing references without inventing repairs. Rollback stops new writes and restores the pre-upgrade copy only if no accepted new writes would be lost; otherwise retain upgraded data and use a forward repair. Exact tooling belongs in the reviewed implementation plan.

## Verification strategy

| Requirements | Required evidence |
|---|---|
| EVI-01, EVI-04, EVI-06 | Offline end-to-end hive runs sharing one file-backed store, with repeated and changed source fixtures; existing successful API path |
| EVI-02, EVI-03, EVI-05 | Store-interface tests asserting resolved provenance, immutable prior records and atomic rollback |
| EVI-07, EVI-08 | Old/fresh/upgraded SQLite fixtures; reopen and injected upgrade failure; missing historical evidence remains ineligible |

Use deterministic mock model/search results so the oracle measures storage and provenance, not model variance. Run focused tests plus existing hive and affected API tests. The gap probe must be updated or retired when fixed: its original purpose is recording a defect, not defining desired behavior.

No implementation or acceptance tests have been run for this proposed design. Test names, task breakdown and exact commands will be supplied by the plan after spec approval.

## Open decisions

None blocking design review. The storage migration and error interfaces must be made concrete in the implementation plan. Cross-run immutable snapshots remain deferred to the durable-state design.

## Review record

Self-review on 2026-10-19: requirements cover observed collision, provenance ownership, immutable content, lost leases, atomic rollback, existing clients and old-data recovery. Technical design awaits user review. No approval recorded.

Step-1 investigation on 2026-10-19 reproduced F1 in a disposable file-backed database, plus ignored same-run conflicts, accepted unresolved-reference publication, and writer eligibility of missing-provenance facts. Existing hive tests passed 15/15. [Fresh baseline](../../reviews/2026-10-19-hive-001-baseline.json). These are diagnosis results, not implementation acceptance.

The linked planning candidate proposes an explicit stopped-writer migration with a verified backup; opening an unmigrated old store fails clearly with migration instructions. Historical statuses/reports remain inspectable, while verified-memory reads and new assessments require run-owned evidence. These concrete choices remain subject to the same pending spec/plan review. No runtime changes or storage upgrade executed.
