# Worked example — a stop decision

Shows what "good" looks like when the pressure is on. Adapted from
[§6.5](../../00-shared/05_communication_protocol.md) and the White [playbook](../PLAYBOOK.md).

## The call
```
STOP EXERCISE -- called by soc.analyst.k at 2026-09-17T11:14:33Z
Reason: auth failures from an IP not on the exercise allow-list
```

## What White did, in order
| Time (UTC) | Action |
|---|---|
| 11:14:33 | Stop called in #ex-2026-014-ops |
| 11:15:02 | All operators confirmed halted. **No cleanup yet** — state preserved for adjudication |
| 11:18 | System owner, SOC lead, and Ops on-call notified (inside the 15-minute requirement) |
| 11:22 | Answer key checked: the IP is **not** Red's. Not an exercise action |
| 11:40 | Blue investigated as a real incident. Source identified as a misconfigured internal scanner |
| 12:02:10 | White decided: **resume with conditions** |

## The decision record
```
DECISION EX-2026-014-D07 | 2026-09-17T12:02Z | white.exercise.director
DECIDED:   Resume with conditions after STOP-002
OPTIONS:   (a) terminate  (b) resume as-is  (c) resume with conditions
WHY:       Activity confirmed unrelated and benign; exercise objectives not yet met;
           added monitoring reduces recurrence risk
CONSULTED: SOC lead, Purple lead, System owner (ASSET-0442)
REVERSIBLE: yes -- stop again at any time
```

## Why this scores well
- The analyst **called the stop without certainty** — that is the behaviour you want, and it was
  recorded as healthy rather than as noise.
- White treated ambiguity as real until proven otherwise.
- **Nobody resumed on their own judgment.** The 47-minute gap is the control working, not the
  control failing.
- The stop appears in the AAR even though the concern turned out to be unfounded.

## What would have scored zero
Any operator continuing "just to finish this one step," or removing the halt themselves once
they became confident the concern was unfounded. Both are automatic-failure conditions on the
[White scorecard](../tests/assessment.md).
