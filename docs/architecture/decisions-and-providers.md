# Decisions and providers

[Main guide](../../ARCHITECTURE.md) · [Visual atlas](index.html)

**Proposed.** Governing [Jev decision spec](../superpowers/specs/2026-10-19-jev-decisions-design.md). The lite hive currently uses configured provider selection in [app/llm](../../app/llm/config.py); it does not implement the proposed Jev policy layer.

A generative model produces plans or text. A decision model evaluates a bounded semantic question. Deterministic code enforces rules that must have the same answer regardless of model opinion.

| Question | Decision owner |
|---|---|
| Is the lease still valid? Is the budget sufficient? | Code and authoritative state |
| Does this caller have the tool capability? | Code authorization |
| Which of these eligible role/provider profiles fits this task? | Optional qualified Jev profile |
| Is this evidence semantically relevant? | Evaluated semantic assessment policy |
| What research plan or paragraph should we produce? | Generative handler |

The proposed decision flow is: derive eligible choices in code → defer if none → select deterministically if only one → otherwise request a typed Jev judgment → validate the response → persist the decision → recheck current state/version → perform the permitted action. A decision can become stale while it is being computed.

Choice, Score and Noul have different contracts in the spec. A probability-like answer is not automatically a calibrated confidence score. Provider exceptions, malformed output and policy defer need distinct results. Do not convert an unavailable model into “unsupported claim” or a confident fallback.

Suggested seams are `app/decisions/contracts.py`, `policy.py` and `typesafe.py`. Keep the provider transport behind a narrow adapter. Persist enough metadata to audit candidates, profile/model version, input references, result, latency, usage and the code action actually taken. Store sensitive context according to its data policy rather than indiscriminately logging prompts.

Rollout proceeds through fixture contracts, real transport qualification, shadow decisions without authority, held-out evaluation and reversible promotion. Shadow calls still consume budget. Automatic routing stays off while promotion thresholds are unspecified.

For mixed providers, build a fixed evaluation set for each role/layer and provider-profile pair. Measure factual support, refusal/error behavior, latency and cost under the same inputs. Pin a qualified version/profile and evaluate fallback behavior. Static configuration and passing transport tests do not establish model quality. Legacy `eval/run_eval.py` is not a Hive/Jev qualification suite.
