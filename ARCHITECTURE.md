# Knull: from a lite hive to a modular agent system

This guide explains the proposed design for someone new to agent systems. It also gives a developer or coding agent a starting point for implementation. Read it alongside the [visual guide](docs/architecture/index.html) and [Knull control-room walkthrough](docs/architecture/knull.html).

**Foundation update, 20 October 2026:** HIVE-001 and HIVE-002 are implemented and verified in the SQLite lite engine. See [the delivered foundation](docs/architecture/implemented-foundation.md) and [acceptance evidence](docs/reports/hive-integrity/summary.md). Source-linked HTML diagrams retain their original committed snapshot; they are not regenerated as current implementation receipts.

**Status: architecture explanation, not approval of the remaining modular program.** The modular engine is proposed. The [spec index](docs/superpowers/README.md) records each feature's actual delivery state. This guide explains those contracts; it does not replace them or authorize runtime changes. Source was inspected on 20 October 2026 at revision `f4f541332b3f78a755bccc5f4890931b1b256d07`, plus the existing local MCP fixes. Diagram source links use that committed revision. Local MCP review evidence is linked separately.

## 1. The idea in one minute

Imagine a small research team. A user gives its manager an objective. The manager splits it into tasks, assigns specialists, checks their results, and combines accepted findings into a report.

**Knull is the root coordinator.** It can propose a plan and request new tasks. Optional **Lieutenants** coordinate individual branches. **Specialists** research, verify or write. A **worker** is the limited execution slot that temporarily runs one of those tasks. A role is therefore not a permanently running process.

The platform is the team's operating system. Deterministic code decides whether a proposed task is legal, whether resources are available, who may use a tool, and whether a result can be committed. Models generate plans and text. Jev supplies bounded semantic judgments among choices the platform has already permitted. Neither Knull nor Jev can create permissions, invent budget, bypass verification or overwrite authoritative state.

Start with one modular application and PostgreSQL. Separate interfaces and responsibilities first. Microservices, an operating-system process for every agent and a public skill marketplace are not first-release requirements.

## 2. What works today, and what changes

| Part | Current code | Proposed direction |
|---|---|---|
| Main hive | Fixed plan → research tasks → verify tasks → writer | Validated task graph with versioned role dispatch |
| Persistence | Versioned SQLite tasks, run-owned evidence and results | PostgreSQL state plus transactional events and restart recovery |
| Coordination | Fixed Knull planning step | Root coordination plus bounded optional branch coordinators |
| Workers | Supervised in-process workers, renewal, fences and deadlines | Bounded shared capacity, leases, fencing and fair admission |
| Resources | Partial local accounting | Reserve before calls; settle actual or unknown usage conservatively |
| Verification | Run-owned evidence, quote checks, verifier model, citation checks | Run-owned evidence and supported-final-finding acceptance gates |
| Routing | Agent/layer/default provider configuration | Evaluated profiles; optional qualified Jev decisions |
| Skills | Host-installed developer skills | Separate repository registry of versioned instruction bundles |
| Interfaces | v1 hive API, CLI, React console | Explicit modular engine selection; versioned commands/events API |
| MCP | Local adapter exposes health/start/get | Preserve truthful capabilities; extend only with implemented engine APIs |

There is also a **separate legacy LangGraph research path** behind `/v1/research`. It uses its own planning/retrieval/synthesis loop and NetworkX/Chroma helpers. It is not the hive scheduler. The [Graphify code graph](graphify-out/graph.html) maps source relationships for developers; it is not runtime memory or an agent permission system.

Current entry points: [hive runner](app/hive/runner.py), [store](app/hive/store.py), [agents](app/hive/agents.py), [v1 hive API](app/api/routes_hive.py), [CLI](app/hive/cli.py), [console](web/src/App.tsx), [legacy graph](app/agent/graph.py), and [MCP adapter](integrations/mcp/README.md).

## 3. Follow one proposed run

Suppose the objective is “Compare three public research approaches and explain their trade-offs.”

1. **Accept the run.** The API validates the request and records its owner, engine, deadline, limits and pinned configuration. A repeated operation key must not start duplicate work.
2. **Ask Knull for a plan.** Knull proposes tasks with dependencies, expected outputs and acceptance criteria. A parent says who is accountable; a dependency says what must finish first. These are separate relationships.
3. **Validate and persist.** Code rejects cycles, unavailable capabilities, excessive depth, unauthorized tools and allocations that exceed the parent. The accepted plan becomes durable state.
4. **Schedule a ready task.** Dependencies must be satisfied. Admission requires a worker permit and the relevant resource reservation. The store grants a short lease with an attempt ID and fencing token.
5. **Build a narrow context.** Resolve a pinned role, handler, provider policy and eligible skills. The researcher receives source-finding context. The verifier receives claim and evidence, without the researcher's conversation.
6. **Execute and account.** The handler calls permitted tools or a provider outside database locks. Call receipts settle reservations. An unknown outcome stays charged until reconciled; it is not free retry capacity.
7. **Accept a candidate result.** The worker submits output. Code checks schema, acceptance rules, current lease, attempt and fence before atomically publishing result, task transition and event.
8. **Join branches.** A Lieutenant waiting on children releases its worker lease. When required children finish, code makes aggregation eligible again. Children finishing does not itself prove that the branch's goal was met.
9. **Verify and report.** Evidence is scoped to this run. Independent verification assesses meaning, and final findings must be supported. Unresolved claims remain visible as unresolved. Budget exhaustion must not masquerade as successful completion.
10. **Recover if interrupted.** Another worker can reclaim an expired lease under retry policy. The old worker's stale result cannot commit. State and events explain what happened without replaying completed paid calls.

This story is the target contract. It is not the current lite execution path.

## 4. Learn the modules

| Module / part | Beginner question | Read next | Proposed ownership seam |
|---|---|---|---|
| Runtime and durable state | Who runs the next task, and what survives a crash? | [Runtime and state](docs/architecture/runtime-and-state.md) | `app/orchestration/` and guarded store operations |
| Evidence and reporting | Why should we believe a finding? | [Evidence and reports](docs/architecture/evidence-and-reports.md) | Run-owned evidence, assessments and report acceptance |
| Roles and skills | What can an agent do, and what instructions does it receive? | [Roles and skills](docs/architecture/roles-and-skills.md) | Versioned role profiles and `hive.skills.yaml` registry |
| Decisions and providers | When should a model decide, and which model? | [Decisions and providers](docs/architecture/decisions-and-providers.md) | `app/decisions/` and evaluated provider profiles |
| Interfaces and platform | How do people and external clients control the system? | [Interfaces and platform](docs/architecture/interfaces-and-platform.md) | API, CLI, console and MCP adapter |

Paths in the last column describe intended seams. They are not a promise that those modules already exist. Keep business rules behind small interfaces; avoid making every noun into a new service or framework.

## 5. Vocabulary that prevents mistakes

| Term | Plain meaning |
|---|---|
| Run | One user's objective, its tasks, limits, evidence and outcome |
| Task | A durable unit of work with an input/output contract |
| Role | A versioned capability profile, handler and context policy |
| Skill | A versioned instruction bundle; it grants no tools or permissions |
| Worker | Temporary execution capacity; one worker can run different roles over time |
| Lease | A time-limited right to attempt a task |
| Fence | A generation token that makes an old worker's writes invalid |
| Reservation | Budget/capacity held before an external call |
| Event | A committed record explaining a state change |
| Candidate result | Untrusted worker output awaiting platform acceptance |
| Jev decision | A typed semantic judgment constrained by deterministic policy |

## 6. Where implementation should start

Use the [delivery phases and handoff checklist](docs/architecture/delivery-phases.md). Evidence isolation and execution integrity are now delivered in the lite engine. Next comes the reviewed durable resource-governed runtime. Role extensibility, skills and Jev build on those contracts. Hierarchy must not multiply tasks faster than the platform can account for or recover them.

Before implementing a slice, read its spec and linked plan, check their approval state, and follow [DEVELOPMENT.md](docs/DEVELOPMENT.md). Existing architectural drafts still require their documented review stages. The evidence-isolation and execution-integrity plans now link observed acceptance; other architectural drafts retain their individual review states.

Known defects and actual fixes remain in the [problems/fixes register](docs/reports/problems-and-fixes.md). A diagram or spec scopes a fix; it does not fix the running application.

## 7. Decisions still needed

Automatic Jev routing needs explicit evaluation thresholds and promotion approval. High-impact claims need a specified verification policy; two agreeing models alone do not establish correctness. Shared deployment needs caller authorization and idempotency. Provider profiles need measured qualification. Capacity needs fault/load evidence at the intended deployment size. [HIVE-003 report contract revision 1 is approved](docs/superpowers/specs/2026-10-20-supported-reports-design.md): the model selects accepted fact IDs and code renders the findings. Its [implementation plan](docs/superpowers/plans/2026-10-20-supported-reports.md) is completed with [verified lite acceptance](docs/reports/hive-003/summary.md). Separate runtime contention and historical-report consumer limits remain documented. HIVE-005 and other backlog items still need detailed contracts before implementation.

The first release remains a bounded public-source research system. Arbitrary shell agents, automatic downloaded plugins, production write tools and multi-tenant hosting need separate designs and authority controls.
