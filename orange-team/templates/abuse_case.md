<!-- Written alongside functional requirements, same backlog. Spec: ../ARTIFACTS.md -->
# Abuse Case AC-<system>-NNN

Title:
System:
Related threat model element:

## Narrative
As an attacker with <starting position>,
I can <action>,
because <weakness>,
resulting in <impact>.

Starting position:  unauthenticated | authenticated user | another tenant
                    | compromised workload identity | insider | supply chain
                    <- BE SPECIFIC. This is the assumption most often left vague.

## Preconditions
## Why this is plausible      <- real-world basis or architectural reasoning. Do not invent actors.

## Becomes a requirement (Yellow's backlog)
"The system MUST <behaviour> such that <abuse case> is not possible."
Acceptance criterion: "<specific test> returns <specific result>"

## Becomes a test
Regression test ID:        <safe check, NOT an exploit>
Purple test case ID:       <if emulated>

## Instrumentation  -> to Green
"If this were attempted, we would see ____ in ____."
<- if the answer is "nothing", that is a telemetry gap. Raise it.
