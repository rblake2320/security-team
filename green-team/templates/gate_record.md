<!-- Defensibility gate. Green has BLOCKING authority. Spec: ../ARTIFACTS.md -->
# Gate Record — <service> — <release>

## Required log sources
[ ] Authentication / authorization decisions emitted and queryable
[ ] Administrative and configuration changes logged
[ ] Data access logged at the granularity its classification requires
[ ] Errors distinguishable from attacks
[ ] VERIFIED ARRIVING in the pipeline — not merely "configured"   <- query run at ____ UTC

## Required detections
[ ] At least one detection for the top attack path in the threat model  -> DET-____
[ ] Alert routes to a real queue with a real owner   -> queue ____ owner ____
[ ] Runbook exists  -> link ____

## Required resilience
[ ] Backup configured AND a restore tested for this data class  -> drill ref ____
[ ] Rollback documented and TIMED  -> ____ minutes, verified ____
[ ] Dependency failure behaviour known

## Required identity
[ ] Workload identity least-privileged; role assignments enumerated
[ ] Credential lifetime bounded; rotation path exists
[ ] No shared or static credentials

OUTCOME:  [ ] PASS   [ ] PASS WITH CONDITIONS (dated: ____)   [ ] BLOCK
Reviewer: ____________  Date: ______
If waived: risk accepted by System Owner ____ on ____, expiry ____

<!-- Publish the waiver rate monthly. A gate waived >20% of the time is not a gate. -->
