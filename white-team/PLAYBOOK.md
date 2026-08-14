# WHITE TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

---

## 1. Workflow stages White owns

| Stage | White's role | Gate White enforces |
|---|---|---|
| 3 · System-owner authorization | R (owner accountable) | **G1 — no signature, no scope** |
| 4 · RoE approval | **A** | **G2 — conditional approval is denial** |
| 7 · Safety validation | **A** | **G3 — no-go means no-go** |
| 8 · Execution | Control and observation | No action outside the approved set |
| 10 · Finding classification | **A** (adjudicates disputes) | Severity disputes resolved and recorded |
| 13 · Risk acceptance | Routes and records (owner signs) | Every acceptance has an expiry |
| 14 · After-action report | **A** | Participants correct facts, never conclusions |
| 15 · Evidence preservation | R (GRC accountable) | Hashes verified; destruction certified |

---

## 2. The Exercise Review Board

Monthly, 60 minutes. Chaired by the Exercise Director.

```
AGENDA
1. Prior exercise closure status (open findings, evidence, destruction certs)
2. New proposals -- 10 min each:
     - Does it trace to a risk register entry?
     - Is the system owner identified and pre-notified?
     - Are the scoring criteria pre-declared and specific?
     - Is the environment justified? (production requires explicit reasoning)
     - Is there a rollback for every state-changing case?
     - Is the window clear of freezes, audits, close periods, other exercises?
3. Decision: APPROVE / APPROVE WITH CONDITIONS / DEFER / DENY  (with recorded reason)
4. Calendar deconfliction
5. Standing item: independence check -- has anything changed in reporting lines?
```

**Denial is a healthy output.** An Exercise Review Board that approves everything unmodified is
not reviewing. Track and publish the approve/modify/deny distribution.

---

## 3. Runbook — RoE approval

```
1. Receive the proposal. Confirm every [M] field is populated -- "TBD" is blank.
2. Verify system-owner authorization for EVERY in-scope system. Missing one?
   That system is out of scope. Proceed with the rest, or return the proposal.
3. Route to Legal and Privacy. Target 1 business day (the TEMPLATE is pre-approved,
   so per-exercise review is scoped to the deltas only).
4. Review the safety assessment. Question every rollback that has not been TIMED.
   "We can restore" is not a rollback plan.
5. Check the calendar: change freezes, close periods, audits, other exercises,
   peak business events, holidays.
6. Confirm insurance/regulatory notification obligations (O-14).
7. Verify third-party authorization where applicable (RoE 5.15). A vendor's
   acceptable-use page is NOT authorization.
8. Set conditions if needed. UNMET CONDITIONS = NOT APPROVED.
9. Collect signatures. Confirm each operator signed individually -- a team lead
   signature does not cover the team.
10. Test the emergency contact roster BY LIVE CALL within 5 business days of start.
11. Seal the answer key. Brief the SOC lead on deconfliction only -- not on the plan.
```

---

## 4. Runbook — the stop decision

This is the role's defining function. Practice it before you need it.

```
STOP CALLED
  |
  v
1. HALT everything. Confirm in the channel that all activity has ceased.
   Do NOT let anyone "finish this one step." Do NOT let anyone clean up yet.
  |
  v
2. PRESERVE state. Evidence may matter for either an incident or an adjudication.
  |
  v
3. NOTIFY within 15 minutes: System Owner, SOC lead, Ops on-call.
  |
  v
4. ASSESS -- three questions, in this order:
     a. Is anyone or anything at risk RIGHT NOW?         -> if yes, act on that first
     b. Is this a real incident?                          -> if yes, CSIRT takes primacy
     c. Did exercise activity cause it?                   -> if yes, rollback
  |
  v
5. DECIDE -- yours alone: TERMINATE / RESUME / RESUME WITH CONDITIONS
   Do not poll the room for consensus. Consult, then decide.
  |
  v
6. RECORD the decision, the options considered, and the rationale.
  |
  v
7. COMMUNICATE explicitly. No one resumes on their own judgment, ever --
   including if they have become confident the concern was unfounded.
  |
  v
8. REPORT in the AAR. INCLUDING stops later found unnecessary.
```

**The first unnecessary stop is the most important moment in the program's culture.** Praise it
publicly and specifically. If the first person to call a wrong stop is embarrassed, nobody will
call the right one.

---

## 5. Runbook — real vs. simulated adjudication

```
Query arrives: "is this us?"
  |
  +-- Check the answer key. Answer ONLY the specific query.
  |     "That IP, at that time: yes, exercise."   <- do not volunteer the plan
  |
  +-- Response format is fixed: EXERCISE / NOT EXERCISE / UNKNOWN-INVESTIGATING
  |
  +-- SLA: 5 minutes. If you cannot answer in 5 minutes, answer UNKNOWN --
  |   and the SOC treats it as real. That is the correct outcome.
  |
  +-- Log every query as an exercise event. A query means someone noticed:
      that is a partial detection success and it should be scored as one.
```

**Never answer "no" loosely.** If the activity is not yours *and* you are not certain, the answer
is UNKNOWN, not NOT EXERCISE. A confident wrong "no" sends the SOC into a real incident response
against your own traffic; a confident wrong "yes" tells them to stand down during a real breach.
The second is catastrophic — bias toward UNKNOWN.

---

## 6. Runbook — scoring and the AAR

```
BEFORE EXECUTION   Publish the rubric. It is now frozen.
DURING             Scribe records; Scoring Analyst observes but does not participate.
AFTER
  1. Score against the frozen rubric. Do not adjust for how it went.
  2. Draft the AAR. Structure:
       - Objective and hypothesis (was it falsified?)
       - What actually happened -- timeline
       - Six-stage outcome table
       - Score, per criterion, with evidence
       - WHAT WORKED  <- first, and specific. A report of only failures
                          teaches people to avoid exercises.
       - What did not
       - Stop events, including unnecessary ones
       - Deviations from the RoE
       - Findings summary by severity
       - Recommendations with named owners and dates
  3. Circulate for FACTUAL review only. 3 business days.
       Participants may correct facts. Participants may NOT change conclusions
       or scores. Record any disputed conclusion as a dissent, verbatim, in an annex.
  4. Publish within 10 business days. Version it. Never edit in place after publication.
```

---

## 7. Independence maintenance

| Practice | Frequency | Why |
|---|---|---|
| Confirm no reporting-line change has occurred | Every Exercise Review Board | Reorganizations quietly destroy independence |
| Do not attend participant team social or offsite events during an active exercise | Continuous | Social embedding is how capture starts |
| Rotate the Scoring Analyst | Annually | Reduces familiarity bias |
| Publish approve/modify/deny and stop statistics | Quarterly | Makes rubber-stamping visible |
| Internal Audit independence review | Annual | External check on the checker |
| Decline to draft the technical content of proposals | Continuous | Drafting what you approve is approving your own work |

**Warning signs that independence is eroding:** you find yourself defending the program's results
to executives · participants ask you informally whether something "would be approved" and you
answer definitively · you have not modified a proposal in six months · you are invited to the
Purple team's planning sessions as a participant rather than an observer.

---

## 8. Metrics White owns

Authorization completeness (100%) · scope violations (0) · RoE turnaround (≤5 business days) ·
deconfliction SLA compliance · AAR timeliness (≤10 business days) · destruction/revocation
completion (100% within 5 business days) · **M-15 safety stop rate (healthy band 5–20%)**.

**M-15 is a U-curve, not "lower is better."** 0% over a year is a finding about your culture, not
a clean record.
