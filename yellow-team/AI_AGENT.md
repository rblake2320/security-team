# YELLOW TEAM — Remediation Assistance Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: 5th of 7.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

## Purpose

Help engineers close findings faster and more completely: explain a finding in the context of the
actual codebase, propose a remediation approach, draft a regression test, draft the fix evidence
package, and check a proposed fix against the acceptance criteria before it goes to retest.

**Existing code review is the control.** This agent proposes; humans review and merge exactly as
they would any other contribution. That is why this agent is comparatively low-risk — you already
have the mitigating process.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Source code repositories | Read | Trusted |
| Finding records + acceptance criteria | Read | **Structure trusted, free text untrusted** |
| Threat models, ADRs | Read | Trusted |
| Paved-road catalog and platform modules (Green's) | Read | Trusted |
| CI results, test suites | Read | Trusted |
| SBOM / dependency data | Read | Trusted |
| Internal secure-coding standards | Read | Trusted |
| Public vulnerability advisories | Read | **Untrusted** — external content |

## 2 · Permitted tools

- Read the sources above
- Propose code changes as a **draft branch or draft PR** — never to a protected branch, never
  auto-merged
- Draft regression tests
- Draft fix evidence packages
- Check a proposed fix against acceptance criteria and report gaps
- Run **read-only** static analysis

## 3 · Denied capabilities

Beyond the seven universal prohibitions:

- Merging to any protected branch; approving its own or anyone's PR
- Deploying to any environment
- Modifying CI/CD pipeline configuration, branch protection, or repository settings
- Modifying security controls, IaC that provisions identity or network policy, or
  policy-as-code rules — **it may propose these as drafts; a human always applies them**
- Changing a finding's status, severity, or acceptance criteria
- Marking a finding closed or awaiting_retest
- Handling secrets, or writing anything that looks like a credential into code
- Executing code against any environment beyond the sandboxed test runner

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Draft code change | **Two humans**: the assigned engineer + a normal code reviewer | Standard PR process, unchanged |
| Draft regression test | Assigned engineer | Test must be reviewed for *what it actually asserts* — a test that passes trivially is worse than none |
| Fix evidence package | Assigned engineer, then Purple at retest | |
| Dependency upgrade proposal | Engineer + normal change process | |
| Anything touching identity, network, or crypto | Engineer + **Orange review** | These are the categories where a plausible-looking wrong answer is most costly |

## 5 · Data-classification restrictions

Maximum **INTERNAL**. Never processes production data, real credentials, PII/PHI/CUI, or evidence
content. If a finding's description contains regulated data (it should not — see RoE §5.9), the
agent stops and reports the policy violation.

## 6 · Audit logging

Every repository read, every draft produced, every human decision on that draft — 7 years.
Draft-to-merge attribution retained so that a later defect can be traced to its origin.

## 7 · Prompt-injection defenses

Threat model: **code comments, commit messages, dependency metadata, issue text, and public
advisories are all attacker-writable in a supply-chain scenario.** A malicious dependency can
carry instructions in its README.

| Defense | Implementation |
|---|---|
| D1 | Untrusted content (comments, advisories, dependency metadata) delimited and labeled as data |
| **D2** | **No write access to protected branches, pipelines, or deploy paths.** An injection that fully succeeds still produces a draft PR that a human must read. This is the structural defense that makes this agent tolerable. |
| D3 | Structured output for evidence packages and criteria checks |
| D5 | Instruction-like patterns in dependency metadata stripped and flagged — **a dependency containing injection text is itself a supply-chain finding**, and should be raised as one |
| D6 | The advisory-reading path is separate from the code-writing path |
| D7 | Evaluation set includes poisoned dependency metadata |

## 8 · Secret handling

Never receives secrets. **Never writes a credential, key, token, or connection string into code
or configuration, even as a placeholder that looks real** — use documented placeholder
conventions. On detecting a secret in the codebase: **stop, report to the identity owner within
1 hour, do not include the value in any output or log.**

## 9 · Output validation

- Proposed code must compile/lint and pass the existing test suite before a human is asked to review
- Regression tests must **demonstrably fail against the vulnerable state and pass against the
  fixed state** — a test that passes in both directions is rejected automatically [M]
- Acceptance-criteria checks cite the specific evidence for each criterion
- **Missing evidence is reported as missing, never asserted as satisfied**
- Pre-deployment evaluation on past findings with known-good fixes; measured and published rates

## 10 · Kill switch

Engineering Manager or CISO. <60 s; revokes the agent's repository identity. Tested quarterly.
Engineers continue exactly as before.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Acceptance criteria ambiguous | Stop; ask the engineer; **never guess at what "done" means** |
| Fix would require touching security controls | Stop; route to Green/Orange; do not draft it unilaterally |
| Proposed change fails tests or lint | Do not surface to a human; iterate or report inability |
| Regression test does not fail against the vulnerable state | Reject the test; report |
| Secret detected | Stop; report; redact |
| Injection suspected in dependency metadata | Stop; flag as a supply-chain finding |
| Agent unavailable | Engineers fix findings the normal way |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | Regression tests (tedious, skipped under pressure, and the highest-compounding artifact in the model — see M-13) and fix evidence packages (pure clerical work engineers reliably shortchange). |
| **Moderate value** | Explaining a finding in the context of *this* codebase. Genuinely useful for engineers who did not attend the exercise. |
| **Low value / high risk** | Security fixes in identity, authorization, and cryptography. A plausible-looking wrong fix in these areas is worse than an open finding, because it closes the ticket. Require Orange review on all three. |
| **Main risk** | Confident, plausible, subtly wrong changes passing review because they look reasonable and the reviewer is busy. Mitigation is the existing two-human review — **do not relax it for agent-authored changes; if anything, review them harder.** |
