# Custom-skill preservation review

Scope: independent read-only comparison of all 17 staged original/candidate SKILL.md pairs. Review sought lost domain requirements, authority changes, safety/provenance/source-loading omissions, frontmatter problems, and delivery-preference changes. Generic engineering boilerplate was not required solely to preserve length. No active skills were modified by this reviewer.

## Initial findings and resolutions

1. **Agent containment:** candidate/stripe-agentic-delivery/SKILL.md initially omitted the original explicit prohibition on production data/resources and explicit filesystem/repository containment (original line 13). The hard-constraint blocking requirement (original line 14) also needed to remain explicit. Rechecked candidate line 8 now excludes production data/resources, enforces filesystem/repository boundaries, and requires deterministic blocking controls. Resolved.
2. **Compatibility and local authority:** candidate/stripe-engineering/SKILL.md initially omitted the original compatibility-by-default requirement with explicit acceptance of breaking change and migration (original line 24), and the precedence of local standards, product constraints and user instructions (original line 14). Rechecked candidate line 8 restores both. Resolved.
3. **Hiring data safeguards:** candidate/stripe-hiring-system/SKILL.md initially omitted explicit candidate-data minimization, lawful collection purpose and deletion (original line 18). Rechecked candidate line 12 restores these alongside correction, access, retention and vendor rules with HR/legal/privacy owners. Resolved.
4. **Follow-up bounds:** candidate/write-job-outreach-dms/SKILL.md and candidate/write-recruiter-emails/SKILL.md initially lost the original single requested follow-up defaults. Rechecked DM line 16 now specifies one final requested follow-up, and email line 14 one substantive requested follow-up. Timing, substantive content, rejection/opt-out stops and draft-only authority remain. Resolved.

## Recheck result

Re-read all five revised candidate files in full. No remaining material preservation regression identified in those revisions. Initial full review found no other material preservation regression across the 17 candidates. Stripe reference-loading routes remain present; core provenance, replay side-effect isolation, active-testing authorization and draft-only outreach boundaries are retained. Default strongest-draft delivery, project-advice DM framing, exact-limit counting and email word-range guidance remain.

All 17 current candidate YAML frontmatters parse with Ruby/Psych; each name matches its manifest entry and each description is a string. This is structural and semantic preservation evidence, not runtime behavior or model-effectiveness proof. Third-party package integrity and installation are outside this review; this reviewer did not modify or install them.

## Skills reviewed

- stripe-agentic-delivery
- stripe-api-review
- stripe-behavioral-replay
- stripe-codebase-migrations
- stripe-engineering
- stripe-hiring-system
- stripe-incident-response
- stripe-interview-prep
- stripe-invariant-recovery
- stripe-production-readiness
- stripe-safe-migrations
- stripe-security-review
- stripe-staff-engineering
- stripe-testing-rigor
- write-human-social-posts
- write-job-outreach-dms
- write-recruiter-emails
