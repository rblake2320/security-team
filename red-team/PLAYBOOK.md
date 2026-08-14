# RED TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> Tool usage lives in [README.md](README.md); the threat model and control table live in
> [SECURITY.md](SECURITY.md). **This playbook covers how Red works with the other six teams.**

---

## 1. Workflow stages Red owns

| Stage | Red's role | Gate Red enforces |
|---|---|---|
| 6 · Test-case development | R (Purple accountable) | Every case dry-run in lab before it is scheduled |
| 8 · Execution | **R** (Purple accountable) | **No run without a signed, unexpired, fingerprint-bound receipt** |
| 9 · Detection validation | R | Full disclosure of what was done, when, from where, as which identity |
| 12 · Retesting | R | Re-execute the **original** procedure verbatim |

Red executes; **Purple owns the outcome measurement.** That split is what stops the operator
from grading their own run.

---

## 2. The engagement sequence

Aegis enforces most of this in code. Do not work around any step — each one exists because the
step before it can be forged.

```powershell
cd security-team/red-team
$env:PYTHONPATH = (Resolve-Path src).Path

# 0. BASELINE -- know the tool works before you point it at anything
python -m unittest discover -s tests            # 14 tests (1 skips without symlink privilege)

# 1. DEFINE the engagement: targets, allowed checks, limits
#    -> examples/engagement.json is the shape. Limits are a SAFETY control, not a perf knob.
python -m aegis_rt list-checks
python -m aegis_rt validate  engagement.json
python -m aegis_rt plan      engagement.json    # prints the SCOPE FINGERPRINT

# 2. AUTHORIZE -- done by the APPROVAL AUTHORITY, on their machine, with their key.
#    Red does not run this step and does not hold the private key.
#    aegis-rt authorize engagement.json --approved-by ... --ticket SEC-#### \
#      --expires-at <ISO8601> --signing-key authority.pem --password-env AEGIS_KEY_PASSWORD \
#      --ack "I AM AUTHORIZED"

# 3. RUN -- acknowledge the fingerprint from step 1, deliberately, by hand
python -m aegis_rt run engagement.json --trust-key authority.pub.pem --ack-scope <fingerprint>

# 4. CLOSE
python -m aegis_rt verify-ledger .aegis/audit.jsonl
#    seal-ledger is signed by the APPROVAL AUTHORITY, not by Red
#    -> hand ledger + seal + trust key to WHITE for the evidence manifest
```

**Never paste `--ack-scope` from a previous plan.** The second acknowledgement exists so that a
scope change cannot slip through on a stale fingerprint. Copying it forward defeats the control
entirely and will not be caught by the tool.

---

## 3. Runbook — scope discipline

```
BEFORE EVERY ACTION, in order:
  1. Is this target in the engagement definition?           no -> STOP
  2. Does the resolved ADDRESS still match what was pinned? no -> STOP (rebinding)
  3. Is the authorization unexpired?                        no -> STOP
  4. Does the fingerprint match what I acknowledged?        no -> STOP
  5. Am I inside the request budget and rate limit?         no -> STOP

AMBIGUITY RESOLVES TO "OUT OF SCOPE". Always. Every time.
A wrong "in scope" is an unauthorized access; a wrong "out of scope" costs an email.

REDIRECTS are recorded and never followed. A redirect is not permission.
PUBLIC ADDRESSES are denied unless the receipt explicitly opted in.
```

**If you find yourself arguing that something is "obviously in scope," it is not.** Get the
scope amended and re-signed. A new fingerprint is cheap.

---

## 4. Runbook — the STOP switch

```
CREATE  .aegis/STOP          -> checks halt at their next safety boundary
WHO     anyone. No justification required at the time.
RESUME  ONLY after the engagement owner approves, and White authorizes.
        Removing the file yourself because you decided the concern was unfounded
        is the same violation as ignoring a stop call.
RECORD  every stop, including ones later found unnecessary, in the ledger and the AAR.
```

The file-based switch works when a person is panicking and cannot remember a CLI flag. That is
the design intent — do not replace it with something cleverer.

---

## 5. Runbook — finding write-up

Aegis normalizes findings and redacts matched values to one-way digests. **Your job is the part
the tool cannot do: make it reproducible and make it matter.**

| Do | Don't |
|---|---|
| Describe the **weakness** | Describe your cleverness |
| Give exact reproduction steps an engineer can follow alone | "Ran the scanner, see attachment" |
| State business impact in the system owner's terms | Cite a CVSS number and stop |
| Provide one redacted screenshot proving access exists | Dump the database to prove it harder |
| Say what you did **not** test, and why | Imply full coverage you did not achieve |
| Report failures to execute a test case | Quietly drop it from the report |

**Proof of access ≠ extraction of data** ([RoE §5.9](../00-shared/04_rules_of_engagement_template.md)).
The minimum needed to prove the finding is the maximum you may take.

---

## 6. Runbook — working with each team

| Team | The interaction | The trap to avoid |
|---|---|---|
| **Purple** | Tasks Red, defines test cases, scores outcomes. Red executes and reports honestly, including "the technique failed to execute" | Red drifting into choosing what to test because it is more interesting |
| **White** | Issues the authorization. Holds the signing key. Receives the sealed ledger | Asking White to "just approve it quickly" — an emergency compresses the calendar, never the signatures |
| **Blue** | Blue is monitoring, live, and does **not** know the plan. Red discloses fully at the validation session | Softening the account to protect anyone's number, in either direction |
| **Orange** | Red rotates operators in 1–2 weeks/quarter. Keeps Orange's tradecraft current and Red's context organizational | Orange borrowing Red's tooling for production use. **Orange never operates in production** |
| **Green** | Green needs to know exactly what the action looked like on the wire and on the host | Handing over a narrative instead of timestamps, source, and identity |
| **Yellow** | Receives reproduction detail | Reporting to Yellow before White has adjudicated severity |

---

## 7. Escalation and hard stops

| Situation | Action |
|---|---|
| Authorization expired mid-run | **Stop.** Re-authorize. Do not "finish this one check." |
| Target resolves somewhere unexpected | **Stop.** Possible rebinding or a scope error. |
| Actively exploitable **production** issue found | **CSIRT immediately.** Do not exploit further to prove it (SoD-7 applies to Red as it does to Orange). |
| Real credential, PII, PHI, CUI, or cardholder data encountered | Stop that case. Report to the identity/data owner within 1 hour. Never store the value. |
| Classified material encountered unexpectedly | **Stop everything.** Do not investigate. Spillage procedure. |
| Signing key found outside the approval authority's control | **Halt the program.** Rotate keys. White investigates. |
| Ledger fails `verify-ledger` | Integrity incident → Red Lead + White. Do not re-run to "fix" it. |
| Asked to test something not in the receipt | Refuse. Get it signed. |

---

## 8. Metrics Red owns

Runs under valid authorization (**target 100%**) · out-of-scope actions (**target 0**) ·
unredacted secrets in output (**target 0**) · ledger verify + seal success (100%) ·
techniques **validated** (feeds M-1, M-2, M-3) · findings reproducible without Red's help (≥90%) ·
independent-assessment findings that are new rather than known repeats.

**Not a metric, ever:** systems compromised, "domain admin obtained," time-to-DA, or any
framing in which Red can win. Red has no score to defend — that is what makes collaborative
validation possible.

---

## 9. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Reusing a fingerprint from an earlier plan | Re-plan, re-acknowledge. The control only works if it is fresh |
| Treating limits as performance tuning | They are blast-radius controls |
| "It's obviously in scope" | Then it is cheap to get it signed |
| Following a redirect to see where it goes | Recorded, never followed |
| Proving impact by taking more data | One redacted screenshot beats a dump, always |
| Reports optimized for impressiveness | The audience is an engineer who has to fix it |
| Adding a check outside the fixed registry | The registry is the reason engagement files cannot become code |
| Holding the signing key "for convenience" | That single convenience destroys the independence the whole function exists for |
