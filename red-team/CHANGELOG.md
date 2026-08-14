# Changelog — Red Team (Aegis Red Team)

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

Covers **both** the team's governance documents and the Aegis implementation in this folder.

**Change rules for this file [M]**
- **Any change to the authorization model, scope enforcement, the STOP switch, the fixed check
  registry, or the excluded-capability list is MAJOR** and requires CISO + White re-approval.
  These are the controls that make an offensive capability safe to hold in-house.
- Changes to checks, limits, or reporting are **MINOR**.
- Clarifications and fixes are **PATCH**.
- Every entry names its driver.

---

## [1.7.1] — 2026-08-14 — scan identity corrected to stable fields

### Fixed
- The descriptor identity check introduced in 1.7.0 compared `(st_dev, st_ino)`, which
  **Linux inode reuse defeats** — ext4 recycles inode numbers, so a delete-and-recreate
  can reproduce the same inode. Found by CI on `ubuntu-latest`; it passed on Windows,
  where NTFS does not recycle a file index that quickly.
- The first correction added `st_ctime_ns` and was **also wrong, in the opposite
  direction**: measured 31/300 mismatches on Windows between a path `lstat` and a
  handle `fstat` of the same untouched file, because NTFS serves the two from different
  sources. That is a ~10% false-refusal rate — a scanner silently skipping 10% of files,
  a worse failure than the defect being fixed.
- That flakiness exposed the underlying error: **the test asserted a stronger property
  than the control owns.** A file recreated at the same path inside the authorized root
  is still inside the root, so reading it is authorized. It is not a scope violation.

  The property is *never read content from outside the authorized root*, carried by
  `O_NOFOLLOW` (final-component symlinks), identity comparison on stable fields
  (hardlinks to out-of-scope files, swapped parent directories), and a post-open
  re-`lstat` — the open pins the inode, so the path cannot be swapped underneath the
  read.

### Testing
- Tests restated to the real property: hardlink-to-outside must be refused, and in-scope
  replacement is **explicitly permitted** so the over-strict flaky rule is not
  reintroduced. Measured 0/400 false refusals. Falsification-verified.

## [1.7.0] — 2026-08-14 — descriptor-verified scanning (RESIDUAL-HIGH)

### Changed
- **[M-adjacent] Offline scanners no longer trust a path between check and use.**
  `source.static` and `repository.posture` resolved a path, validated containment in
  the authorized root, then made SEPARATE `stat()` and `read_text()` calls against
  that path. A hostile local writer could swap a component for a link out of scope in
  that window and have the scanner read a file it was never authorized to touch. For
  a red-team tool the authorized root IS the authorization boundary, so this is a
  scope violation rather than a robustness issue.

  New `checks/safe_scan.py`: traversal via `os.walk(followlinks=False)` with full
  realpath containment on every component, and reads bound to an inode - the file is
  opened once with `O_NOFOLLOW` where available and `fstat` on the DESCRIPTOR is
  compared against the `lstat` taken during traversal. A swapped path no longer
  matches and is refused. Traversal is bounded and raises `TraversalLimitExceeded`
  rather than truncating silently, since silent truncation would let an attacker hide
  files by padding the tree.

  `is_symlink()` alone was insufficient: on Windows a JUNCTION is a reparse point that
  `is_symlink()` reports as False and `os.walk(followlinks=False)` descends into. The
  existing junction-escape tests caught this during development. Containment is
  therefore decided by realpath, which covers symlinks, junctions and mounts alike.

  Reads normalise CRLF explicitly, preserving the universal-newline behaviour that
  `read_text` previously provided.

### Testing
- `tests/test_scan_race.py`: deterministic race injection performed inside the real
  scanner's own loop (via `assert_running`, called once per entry), so the attacker
  wins the race every time rather than occasionally. Falsification-verified — with the
  inode binding removed, both end-to-end scanner tests read the out-of-scope content
  and fail.

## [1.6.1] — 2026-08-14 — atomic authorization writes (AUD-08)

### Fixed
- `aegis-rt authorize` wrote the engagement authorization through a predictable
  sibling temp path (`<engagement>.tmp`) with default permissions and no fsync. A
  concurrent or hostile local process could collide with or pre-create that path,
  and a crash mid-write could leave a truncated authorization on disk. Replaced with
  `atomicio.atomic_write_text`: a securely created unique temp file, fsynced, mode
  `0600`, atomically replaced, and removed on failure.

## [1.6.0] — 2026-08-14 — canonical implementation and cross-platform containment

### Verified
- `red-team/` is the sole canonical `aegis-red-team` implementation in this program tree.
- `tools/verify_canonical_packages.py` makes duplicate or unregistered package identities a CI failure.
- The path-containment falsification test uses a directory junction on Windows and a symbolic
  link on POSIX, so lack of Windows symbolic-link privilege can no longer turn the boundary test
  into a skip.
- Engineering CI runs the same security suites on Windows and Linux and forbids Red test skips.

### Driver
Closure items 1 and 4 in `00-shared/config/assessment_readiness.json`.

---

## [1.5.0] — 2026-08-14 — assurance claim gate

### Added — claim-mechanism-evidence discipline with an automated checker
- Shared **assurance-claim registry** ([`00-shared/config/assurance_claims.json`](../00-shared/config/assurance_claims.json)):
  every normative claim must state property, scope, mechanism, assumptions, evidence,
  **negative/falsification tests**, owner, reviewer, regression triggers, and limitations.
- **Lifecycle:** `PROPOSED -> MECHANISM_IDENTIFIED -> TESTABLE -> EVIDENCED ->
  INDEPENDENTLY_REVIEWED -> OPERATIONAL`, with `DISPUTED` / `REGRESSED`. No state skipped.
- **CI tool** ([`00-shared/tools/claim_check.py`](../00-shared/tools/claim_check.py)) enforcing
  R1-R7: normative language without a claim id · no named mechanism · no negative tests ·
  documentation-only evidence · skipped/stale evidence · OPERATIONAL while a gate is false ·
  mechanism changed without a version increment.
- **Invariant:** `CLAIM != CONTROL != MECHANISM != EVIDENCE`.
- **The rule:** *no security property is credited because it appears plausible in prose.*

### Found — by running it on our own corpus
- **3 of 10 claims are EVIDENCED.** 1 DISPUTED, 1 REGRESSED, 3 MECHANISM_IDENTIFIED, 2 TESTABLE.
- **26 unsupported claim candidates** across 93 markdown files (R1 lint).
- `AEGIS-LEDGER-TAMPER-001` **half-evidenced**: Aegis and Sentinel Blue both claim their chains
  detect *"mutation and interior deletion."* Only **mutation** is tested. No test deletes an
  interior record. Narrow the claim or add the negative test.
- `AEGIS-SOD-AUTHZ-001` **has no evidence**: nobody has attempted to authorize as Red and been
  denied. The model's strongest control is asserted, not demonstrated.

### Driver
Program owner assurance-claim decision, 2026-08-14. See [`00-shared/23`](../00-shared/22_assurance_claims.md).

---

## [1.4.0] — 2026-08-14 — commitment hiding fix

### Added — key status: expiration is not compromise
- The "key status as at `created_at`" rule is refined into five dispositions
  ([§20.5a](../00-shared/19_aegis_trust_model.md)):

  | Condition | Disposition |
  |---|---|
  | Routine expiration / rotation after `created_at` | Do not invalidate |
  | Administrative revocation after `created_at` | Preserve validity unless policy says otherwise |
  | Known compromise beginning after `created_at` | Preserve if trusted timestamp establishes earlier signing |
  | Known or possibly **earlier** compromise | `SIGNATURE_VALID_BUT_ASSURANCE_DISPUTED` → manual review |
  | Unknown compromise onset | Neither accept nor reject automatically — escalate on evidence |

- **A self-declared `created_at` is not evidence when the signing key may be compromised.**
  Independent temporal anchors required: prior publication to White (already mandated), an
  append-only transparency record, or a trusted timestamp.
- `SIGNATURE_VALID_BUT_ASSURANCE_DISPUTED` is a **terminal state**, not a soft pass — the
  signature verifies and the assurance does not. Applies to all five keys, including
  authorization receipts and ledger seals.

### Note
Program state remains **`PREREQUISITES_PENDING` / `NOT_ASSESSMENT_READY`**. This change corrects a
cryptographic construction before first use; it does not advance readiness.

### Driver
Program owner cryptographic correction, 2026-08-14.

---

## [1.3.0] — 2026-08-14 — readiness gate

### Changed — SA-11(5) wording corrected; three controls separated
- The v1.2.0 phrasing "SA-11(5) is unqualified" was imprecise. Corrected:
  **SA-11(5) is unqualified with respect to assessor independence, but NOT unconditionally
  satisfied.** It requires the *developer* to perform or contractually provide the testing at an
  organization-defined rigor; the evidence must establish that relationship.
- Three controls that look interchangeable demand **three different relationships**:

  | Control | Required relationship |
  |---|---|
  | **CA-2(1)** | Independent **control assessor** |
  | **CA-8(1)** | Independent **penetration-testing agent or team** |
  | **SA-11(5)** | **Developer-performed or developer-provided** |

- **CA-8(1) added to the crosswalk** — it was previously absent, and it is not the same
  requirement as CA-2(1).
- CA-2(1) qualified further: NIST requires assessors free from actual **or perceived** conflicts
  concerning development, operation, management, or determining control effectiveness — so
  qualification depends on assessment context and the authorizing authority. **Confirm with the
  AO.**
- **Red can support all three technically. Organizational position, contractual role, and
  independence determine which control its evidence actually satisfies.** Determine per system;
  do not carry the determination across systems.

### Added — automated assessment readiness gate (`PROGRAM-READINESS-GATE-001`)
- Program state is now **`PREREQUISITES_PENDING` / `NOT_ASSESSMENT_READY`**, enforced by
  [`00-shared/config/assessment_readiness.json`](../00-shared/config/assessment_readiness.json),
  not by a paragraph of prose.
- While not ready: exercises **may** run, diagnostic scores **may** be computed, **no assurance
  statement may be issued**, and every artifact carries `TRAINING_OR_ENGINEERING_USE_ONLY`.
- **Removing that marking requires a state transition, not an editorial decision.**
- Seven-state model added, with the rule: **no state may be skipped merely because test suites
  are green.** A passing suite is evidence about code; a transition is a claim about the program.
- Regression triggers defined — the program returns to `PREREQUISITES_PENDING` automatically if a
  gate ceases to hold, a signing key leaves custody, canonical ambiguity returns, or the Exercise
  Assurance performer becomes unavailable or conflicted.

### Driver
Program owner final review, 2026-08-14. See [`00-shared/22`](../00-shared/21_readiness_gate.md).

---

## [1.2.0] — 2026-08-14 — governance review

### Changed — independence claim CORRECTED (breaking)
- **The v1.1.0 claim that "Red closes F-1" was too broad and is withdrawn.** "Independent" is
  four distinct requirements. Red satisfies **two**:

  | Independence | Red? |
  |---|---|
  | From development | **Yes** — does not report through Yellow or Orange |
  | From defense operations | **Yes** — does not operate or own Blue's controls |
  | **Independent exercise scoring** | **No** — not for an exercise Red participated in |
  | **Independent organizational assessment** | **No** — 3PAO / C3PAO / QSA required |

- Statement of record now in [CHARTER.md](CHARTER.md) and [§11.14](../00-shared/10_compliance_crosswalk.md).
- CA-2(1) qualified: Red satisfies it **only where internal assessment is permitted** under your
  ATO/agency terms. Confirm; do not assume. SA-11(5) is unqualified.

### Added — five-key trust model (target state)
- `.init` now carries the key model and its six enforcement invariants. See [§20](../00-shared/19_aegis_trust_model.md).
- **Red will hold an execution key** of its own — able to attest *what it attempted*, never able
  to manufacture the authorization that made it permissible. Authorization and execution receipts
  are **separate objects**.

### Verified — and it is a real gap
- **Aegis v0.1.0 has ONE signature domain.** `authorize --signing-key` and
  `seal-ledger --signing-key` take the same key; the README uses `authority.pem` for both.
  Confirmed by reading `cli.py` on 2026-08-14.
- Consequence: **the approval authority could in principle re-seal a modified ledger.** The
  current model defends well against a rogue *operator* — the primary threat, and solved — but
  not against a compromised or mistaken *authority*.
- Fix is migration step 1 and is small: one CLI argument, one verification path. **Do it before
  the next engagement that produces compliance evidence.**

### Changed — assessment weights ratified as `baseline-v1`
- Program weight for this team is now exact: see [`config/scorecard.json`](config/scorecard.json).
  Purple 18.75 · White 18.75 · Blue 15.00 · Yellow 15.00 · Green 11.25 · Orange 11.25 · Red 10.00
  (= 100.00%).
- Labelled **governance defaults, not empirically validated.** Revise only through a versioned
  governance change after several exercises produce a score distribution — never per exercise,
  and never after seeing results.

### Added — auto-fail applied BEFORE aggregation
```
if any(team.auto_fail): program_status = "FAILED"   # weighted score kept for diagnostics only
elif evidence_completeness < threshold: program_status = "INSUFFICIENT_EVIDENCE"
else: program_status = score_to_readiness(weighted_score)
```
A weighted mean is not a safety property. Without this ordering, a catastrophic Red or White
failure is averaged away by strong performance elsewhere.

### Added — 95-100% triggers a mandatory challenge review
Four hypotheses must be examined: genuine maturity · insufficient test difficulty · scenario
leakage via telemetry or process · permissive scoring. **It never means "no more testing needed."**

### Driver
Program owner governance review, 2026-08-14. Full record: [`00-shared/21`](../00-shared/20_closure_plan.md), [`00-shared/19`](../00-shared/18_exercise_assurance.md), [`00-shared/20`](../00-shared/19_aegis_trust_model.md).

---

## [1.1.0] — 2026-08-14

### Added
- Team integrated into the operating model as the **seventh** team. Written:
  `CHARTER.md`, `PLAYBOOK.md`, `ARTIFACTS.md`, `AI_AGENT.md`, `.init`, `CHANGELOG.md`.
- **The three-way boundary Red / Purple / Orange stated explicitly** — the distinction that is
  blurred in most programs. Red executes and is independent; Purple coordinates and measures;
  Orange reviews designs and is deliberately *not* independent.
- **Red named as the only function that can produce independent-assessment evidence** for
  NIST 800-53 CA-2(1) and SA-11(5), FedRAMP, and PCI DSS 11.4. This closes crosswalk conflict
  **F-1**, which previously had no owner: Orange cannot satisfy those requirements, and the
  model had no team that could.
- Aegis→RoE control mapping recorded in `.init` — seven RoE sections Aegis mechanizes, and six
  it explicitly does **not** cover.
- Why Engine: `why.recall` before finding write-up. Soul: `SOUL-PAIN:` on scope ambiguity and
  on authorization expiring mid-run.

### Copied
- Source copied from `PKA testing\Red Team (1)` on 2026-08-14. **The original was left in
  place, untouched** — it was reported open/locked.
- Copied: `src/aegis_rt/`, `tests/`, `examples/`, `README.md`, `SECURITY.md`, `pyproject.toml`,
  `.gitignore`.
- **Not copied:** `build/`, `dist/`, `src/aegis_red_team.egg-info/`, `__pycache__/` — build
  artifacts, regenerable, and they would have made the folder look larger than the actual work.

### Verified
- Test suite run in the new location on 2026-08-14: **14 tests, 13 passed, 1 skipped** —
  identical to the source location. Not a claim taken from the README.
- CLI verified responsive: `list-checks`, `keygen`, `fingerprint`, `authorize`, `validate`,
  `plan`, `run`, `verify-ledger`, `seal-ledger`.

### Known / not fixed
- **R-6 (new):** `test_source_link_cannot_escape_authorized_root` **skips on this machine** —
  Windows symlink creation needs a privilege this account does not hold (WinError 1314). It
  guards a **path-escape containment boundary**, so that boundary is currently **unproven
  here**. Run under Developer Mode, elevation, or Linux CI before relying on it. This is a
  verification gap, not a known defect.
- Only two checks ship (`source.static`, `http.headers`). That is appropriate for a v0.1.0 with
  a fixed registry, but it means Red's ATT&CK coverage contribution is presently narrow —
  most emulation will be manual and Purple-authored rather than Aegis-executed.
- `license = "LicenseRef-Proprietary"` — no distribution decision recorded.

### Driver
User request, 2026-08-14: *"add in this red team … copy over what's needed so there will be a
complete team."*

---

## [1.0.0] — 2026-08-13

### Added
- **Aegis Red Team v0.1.0** — authorization-first assessment orchestration, ~1,560 lines.
- **Ed25519-signed scope receipts** bound to the exact targets, checks, and execution limits.
- **Cryptographic separation of duty:** the encrypted private key stays with the approval
  authority; operators receive only the public trust key. *Red can execute but cannot
  authorize.*
- Second scope-fingerprint acknowledgement required at execution time.
- Public network targets **denied unless** an unexpired authorization explicitly opts in.
- DNS resolution validation and address-pinned HTTP connections (rebinding defence).
- TLS verification; **redirects recorded and never followed**; request budgets; rate limits;
  concurrency caps; timeouts.
- `.aegis/STOP` kill switch, checked at safety boundaries.
- Append-only **SHA-256 hash-chained JSONL ledger** with exclusive file locking, an integrity
  verifier, and a final **Ed25519 seal applied by the approval authority** — making the evidence
  independent of the operator who produced it.
- Normalized findings with CWE references and **secret evidence redacted to one-way digests**;
  JSON output plus a human-readable Markdown report.
- Built-in offline source review and minimally invasive HTTP security-header review.
- **Bounded check registry** — no arbitrary shell commands, no plugin loading, no code from
  engagement files. *Data must never become executable control flow.*
- Deliberate exclusions, stated as scope rather than backlog: credential theft, persistence,
  evasion, malware, destructive payloads, uncontrolled scanning.
- `SECURITY.md` threat model with a control per risk, and the correct framing that the
  authorization receipt is **not** a substitute for legal authorization, change control,
  stakeholder notification, or an emergency plan.
