# Worked example — acceptance criteria that actually close a finding

Gate **G5** rejects a finding whose acceptance criteria are not testable. This is the difference
in practice, and it is the single most common place remediation goes wrong.

| Untestable (reject back to Purple) | Testable (accept and start) |
|---|---|
| "Improve input validation" | "Requests with a `tenant_id` not matching the authenticated principal return 403; integration test `t_cross_tenant_denied` passes in CI" |
| "Harden the service principal" | "The workload identity holds only roles X and Y; a policy-as-code check fails the build on any additional role assignment" |
| "Add logging" | "Every authentication decision emits an event to source S with fields {principal, result, source_ip, tenant}; Green confirms the event is queryable within 5 minutes of the action" |
| "Fix the dependency" | "Package P is at version >= N in all built artifacts; SCA reports zero known-critical findings for P; the SBOM reflects the new version" |
| "Make sure it can't happen again" | "Regression test `t_workload_cred_added` fails against the pre-fix state and passes against the fixed state, and runs on every PR" |

## The test for a good criterion
> Could a different engineer, who was not in the exercise, prove this is met — **without asking
> anyone** — and would two engineers reach the same verdict?

If no, it is not a criterion. It is a wish.

## Why this matters more than it looks
Metric **M-8** (retest success rate) falling below 70% is almost never a remediation-quality
problem. It is an acceptance-criteria problem upstream: fixes are being declared complete against
criteria that were never checkable. **Fix it at G5, not by retesting harder** — retesting bad
fixes just costs more.
