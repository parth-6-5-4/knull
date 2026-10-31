# Architecture guide verification — original snapshot

Documentation task, 20 October 2026, before HIVE-001/002 implementation. Guide/source hashes below describe that original snapshot, not later application edits. The eight source-pinned diagram artifacts remain unchanged. Current implementation evidence lives in the [foundation report](../reports/hive-integrity/summary.md). [Machine-readable receipt](verification.json) records each candidate/artifact hash, source range, committed-source hash, finalization receipt and advisory. The [atlas](index.html) links all eight diagrams.

## Evidence boundary

Diagrams use committed repository revision `f4f541332b3f78a755bccc5f4890931b1b256d07` and credential-free origin `https://github.com/parth-6-5-4/knull.git`. Proposed components cite design documents at that revision. Those citations establish the proposal, not its implementation. Each referenced path and inclusive line range was checked against committed bytes.

The workspace already contained local MCP fixes and refreshed Graphify outputs before this documentation task. The beginner notes acknowledge those changes and link their existing review. No product source, test, dependency, schema or runtime configuration changed in this task. No spec approval or application issue was advanced because a diagram was generated.

## Checks performed

- Eight candidates passed Archify `finalize --quality showcase --repo-root ...`: validation, delivery, strict artifact check and automated Chrome browser gate. Each diagram passes all nine showcase checks with zero errors and warnings.
- Chrome gates cover the packaged viewer's specified light/dark desktop viewports and read/still states. These checks apply to the eight exact generated artifacts, not the custom atlas or walkthrough wrapper.
- Candidate and HTML SHA-256 digests match the latest passing receipts. Source ranges and committed-source digests were checked. Local documentation/HTML targets were checked for existence. All 102 source hashes in the pre-existing Graphify provenance snapshot still match, including the existing MCP fixes.
- The Knull page loaded in Chrome through Computer Use. Its accessible content showed the initial illustrative board, progress indicator, scenario selector and embedded Archify viewer. Native UI automation subsequently reported stale app/no-window errors; a complete browser click-through is not claimed.
- The walkthrough's actual inline JavaScript was exercised in a local Node DOM harness: all five scenario selections, forward/back boundaries, reset, progress, history and full-board replacement (108 assertions). This is a script-level check, not a browser interaction or responsive-layout qualification.
- Product acceptance tests are not applicable to this documentation-only change. Earlier MCP/application test results remain separately dated evidence.

## Layout advisories retained

The current-code overview has one resolved line crossover and several detours. A single placement trial failed validation; the original passing candidate was restored and fully re-finalized into `review-3`. The task lifecycle has two resolved crossovers. The roles/skills diagram has one detour advisory. The Knull view was updated to show the progress feedback loop and has no remaining route advisory. These are recorded in the machine receipt rather than hidden by claiming perceptual approval.

All eight diagrams have `browser_evidence: passed` and `visual_review: not_requested`. No screenshot-based visual approval is claimed. Correction rounds: one for the current overview placement trial and one for the delivery workflow's main-path constraint; one for the Knull feedback-loop revision; zero for the other candidates.

## Refreshing a diagram

The published candidate sources, original HTML and finalization summaries live in `diagrams/`. Copy the relevant candidate into a new local `.archify/` workspace before changing it; set its output path for that workspace. Preserve current/proposed status and source evidence. Run the installed Archify skill's complete finalization workflow for its diagram type, with a fresh review evidence directory. Update the published files, receipt and atlas only after the exact new artifact passes. A newer Git revision requires rechecking source ranges and facts rather than simply replacing the revision string.

## Publication packaging — 21 October 2026

Eight HTML artifacts and candidates were copied byte-for-byte from the original validated local outputs into `diagrams/`. Published finalization summaries preserve the original results with personal absolute host paths sanitized; original receipts remain in ignored local scratch. Every HTML/candidate SHA256 matched the existing receipt. Atlas, walkthrough iframe and Markdown links now use these shared copies. The ignored `.archify/` intermediates remain local. This packaging check does not regenerate diagrams or establish a new visual review.

The bundled Archify viewer retains its upstream [MIT license](../../LICENSES/Archify-MIT.txt); embedded font notices/licenses remain in each HTML. Project diagrams and explanations follow the repository license. Third-party runtime rights remain unchanged.

Fresh Chromium packaging smoke loaded all eight published diagrams plus the Knull iframe: zero page errors and zero external requests. [Receipt](publication-check.json). This checks loading and SVG presence, not screenshot quality or a new responsive-layout review.
