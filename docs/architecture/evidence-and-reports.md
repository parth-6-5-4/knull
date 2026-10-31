# Evidence and reports

[Main guide](../../ARCHITECTURE.md) · [Visual atlas](index.html)

**Current status:** run-scoped evidence isolation and guarded historical eligibility are verified under [HIVE-001](../superpowers/specs/2026-10-19-evidence-isolation-design.md). See [the delivered foundation](implemented-foundation.md). HIVE-003 final-finding support is backlog in the [spec index](../superpowers/README.md).

A source says something. A researcher extracts a claim. A verifier asks whether the supplied source actually supports that claim. A writer turns accepted findings into prose. Each step can introduce a different mistake.

| Part | What it owns | What it must not imply |
|---|---|---|
| Retrieval | Source identity and captured material | A retrieved page is true or relevant |
| Evidence publication | Immutable, run-owned evidence records | A URL hash proves this run owns the record |
| Quote check | Whether quoted text occurs in captured material | The researcher interpreted that quote correctly |
| Independent verifier | Claim-to-evidence assessment with isolated context | Provider failure means the claim is false |
| Final-finding gate | Support for each material report finding | A valid citation identifier proves the whole sentence |
| Writer | Readable report from accepted material | Permission to strengthen or invent conclusions |

HIVE-001 now fixes run isolation and publication consistency. Reusing a public source in a second run must not leave that run with zero evidence because a globally keyed record already exists. A failed or stale attempt must not publish accepted evidence. See the completed [evidence-isolation plan](../superpowers/plans/2026-10-19-evidence-isolation.md) and F1/F1A–C in the problem register.

The verifier should receive a precise claim and the relevant evidence snapshot, without the researcher's persuasive conversation. Its output needs typed support/uncertainty/failure states. For high-impact claims, define an entailment or independent-verifier policy and evaluate it. Agreement is useful evidence, not a substitute for a calibrated acceptance policy.

The final report needs a further check because correct facts can be assembled into an unsupported sentence. HIVE-003 must specify which findings require support, how contradictions and partial support appear, and when the run ends partial or blocked. Do not implement an invented threshold from this explanation.

Useful acceptance scenarios: same source in two runs; duplicate publication; stale worker; real quote with reversed meaning; supported citations under an unsupported heading; contradictory sources; malformed verifier output; verifier outage; report budget exhaustion. Keep provenance and unsupported material inspectable.
