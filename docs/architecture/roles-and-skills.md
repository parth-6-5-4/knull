# Roles, hierarchy and skills

[Main guide](../../ARCHITECTURE.md) · [Knull walkthrough](knull.html)

**Proposed.** Governing specs: [role hierarchy](../superpowers/specs/2026-10-19-role-hierarchy-design.md) and [skill registry](../superpowers/specs/2026-10-19-skill-registry-design.md).

Three concepts stay separate. A **role** defines the handler, schemas and context for a capability. A **skill** supplies instructions to that handler. A **worker** supplies temporary execution capacity. Installing a developer skill in Codex or Claude does not install a runtime Hive skill.

Knull owns the run's plan. An optional Lieutenant owns a branch's result. Specialists do bounded research, verification or writing. The initial hierarchy permits a root, a branch coordinator and specialists, with explicit child/depth/task ceilings. It does not allow Lieutenants to recursively create more Lieutenants. Retry reuses the logical task ID rather than inflating the graph.

Every task proposal goes through code validation. Parent ownership answers “who must aggregate this?” Dependencies answer “what must finish first?” A task may belong to one parent while depending on another branch's accepted output. Neither relationship grants extra tools.

| Registry | Proposed interface | Returns |
|---|---|---|
| Role registry | `resolve(task_kind, capability, profile_version)` | Handler, schemas, context builder, generator policy and limits |
| Skill registry | `discover`, `validate`, `resolve`, `eligible`, `load_resource` | Validated metadata and pinned instruction/resource bytes |

Unknown task kinds must fail explicitly. A default branch that silently treats every unknown task as “write” is unsafe dispatch.

A repository contributor would add `skills/<name>/SKILL.md` and an explicit entry in proposed `hive.skills.yaml`. The entry identifies version/digest, enabled status, eligible roles and required capabilities. This layout is a draft contract, not an existing install command. The loader validates bundles and snapshots accepted bytes for the run. Later edits cannot silently alter a running task's instructions.

Metadata can be inspected before activation. Only eligible selected instructions enter the task's narrow context. Skills cannot run their packaged scripts, fetch dependencies, expand grants or auto-install another package. Path/symlink/hardlink escapes and resource-size limits are validation concerns. Current draft ceilings include three skills per invocation and a bounded combined text budget; read the spec for all limits.

Effective permissions come from the intersection of principal, parent, role and runtime policy. A skill requesting a browser does not grant browser access. Jev can rank eligible bindings only after deterministic checks, and only after its own qualification gates.

Acceptance scenarios: unknown role; forbidden skill/role pair; edited bundle during a run; path escape; oversized bundle; disabled versus revoked version; verifier context leakage; delegation cycles; children exceeding allocation; a waiting coordinator releasing its worker slot.
