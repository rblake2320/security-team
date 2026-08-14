# Worked example — a safe regression test vs. an exploit

Every discovered weakness class should become a test that runs forever. **Safe** means it proves
the weakness is absent **without performing an attack.**

| Weakness class | Safe regression test | NOT this |
|---|---|---|
| Cross-tenant data access | Authenticated as tenant A, request tenant B's object, assert **403** | A script that retrieves tenant B's data |
| Over-permissive workload identity | Policy-as-code check fails the build if role assignments exceed the allow-list | A privilege-escalation chain run in CI |
| Missing auth on an endpoint | Contract test: unauthenticated request asserts **401** | A scanner sweeping production |
| Secret in code | Secret scanning in CI with the specific pattern | Manual review |
| Vulnerable dependency reintroduced | SCA gate pinned to the fixed version | Periodic manual checking |
| Security logging removed by a refactor | Test asserting the event is emitted with its required fields | Hoping Green notices |

## The authoring standard
```
[ ] Runs in CI, on every PR
[ ] Deterministic         <- flaky security tests get disabled, and then deleted
[ ] Fast enough that nobody disables it
[ ] Fails loudly, with a message saying WHAT is wrong and HOW to fix it
[ ] Contains no exploitation, no credential material, no payloads
[ ] Fails SAFELY if the environment is unavailable -- never silently passes
```

That last line is the one people get wrong. **A test that silently passes when the environment is
unavailable is worse than no test**: it reports coverage you do not have, and it will do so
quietly for months.

## Why this is Orange's job and not Yellow's
Yellow knows how the system is supposed to work. Orange knows what the attacker tried. The
regression test has to encode the *attacker's* intent — which is why the two co-author it, and
why Orange is scored on `T` (conversion into safe tests) at the same weight as `E` (engineering
usefulness) in the [scorecard](../tests/assessment.md).
