# Hive research orchestration

Language for the existing research hive and its proposed modular expansion. These definitions do not imply that every capability is implemented.

## Language

**Run**:
One accepted research objective and the work performed toward its completion.

**Task**:
A bounded piece of work with a defined result and completion criteria. A task can depend on other tasks without being their parent.

**Role**:
A specialist capability required by a task, such as research, verification, or writing.
_Avoid_: Worker when describing a capability.

**Worker**:
An execution resource that performs tasks using an allowed role.
_Avoid_: Agent when the distinction between role and executor matters.

**Skill package**:
A versioned bundle of task instructions and supporting resources, rooted at a `SKILL.md` file. A skill guides a role; it does not itself register executable tools or grant permissions.

**Skill registry**:
The proposed explicit allowlist mapping skill identities, versions, bundle digests and eligible roles to repository packages. Distinct from the executable role registry and the development host's installed skills.

**Skill snapshot**:
Immutable instruction/resource bytes and hashes pinned to a run or invocation so later edits cannot silently change its meaning.

**Attempt**:
One execution of a task. Retrying a task creates another attempt, not another task.

**Knull**:
The run-level coordinator responsible for decomposing the research objective.

**Lieutenant**:
A proposed coordinator for a bounded branch of a run. Its authority and resources come from its parent.

**Evidence snapshot**:
The particular source content used to assess a claim, distinguished from the source's identity or URL.

**Proposed fact**:
A claim submitted with supporting evidence for assessment.

**Verified fact**:
A claim accepted as supported by its evidence under a particular verification policy. Verification does not establish universal truth.

**Decision candidate**:
One permitted option supplied for a model to assess or select.

**Jev decision**:
A typed probabilistic judgment returned by TypeSafe AI's Jev model for a focused question about supplied state.

**Resource allocation**:
A bounded share of a run's spending authority. A child allocation divides its parent's authority rather than creating more.

**Call reservation**:
Allowance held for one external call attempt before dispatch. A hold is distinct from measured usage.

**Unknown usage**:
An external call outcome whose actual resource consumption is unresolved. Its reserved allowance remains charged until an authoritative receipt resolves it.

**Run admission**:
Acceptance of a run into a bounded waiting or active execution slot. Acceptance is distinct from the run having started work.

**Call permit**:
Capacity assigned to one provider attempt under the hive's shared limits. It is distinct from the token allowance reserved for that attempt.
