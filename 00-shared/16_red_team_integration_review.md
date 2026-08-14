# §17 — Red Team Integration Review

← [Index](../README.md) · Related → [§15 Blue review](14_blue_team_integration_review.md) · [§5 RoE](04_rules_of_engagement_template.md) · [§11 Compliance](10_compliance_crosswalk.md)

**Review date:** 2026-08-14 · **Subject:** `red-team/` (Aegis Red Team v0.1.0) as a seventh team
**Verification performed:** test suite run in both the source and destination locations —
**14 tests, 13 passed, 1 skipped**, identical results. CLI verified responsive. Not README claims.

---

## 17.1 Answer first

Red was already referenced throughout the model as an execution arm with no folder — the same
gap Blue had. But Red closes something larger.

**Aegis mechanizes the Rules of Engagement in code.** Seven RoE sections that were previously
paper controls are now represented in executable checks, and one of them — the separation between *executing*
and *authorizing* — uses a cryptographic mechanism rather than a procedural assertion
(`AEGIS-SOD-AUTHZ-001`). Its production custody assumption remains unevidenced.

**And Red closes part of a hole the model could not close by itself.** Crosswalk conflict **F-1**
named an assessor-independence requirement that no team satisfied. Red satisfies **two of the four
kinds of independence** — from development, and from defense operations.

> ⚠ **Corrected 2026-08-14.** An earlier version of this document said "Red closes F-1," which
> was too broad. Red does **not** provide independent exercise scoring for an exercise it
> participated in, and does **not** meet external organizational-assessor requirements. See
> [RC-3](#174-boundary-reconciliations) and [§11.14](10_compliance_crosswalk.md).

---

## 17.2 What Red is

| Property | Detail |
|---|---|
| Name | Aegis Red Team v0.1.0 |
| Nature | **Runnable Python** — authorization-first assessment orchestration |
| Size | ~1,560 lines across `src/`, `tests/` |
| Tests | **14: 13 passed, 1 skipped** (verified 2026-08-14) |
| Modules | `scope` · `authorization` · `audit` · `engine` · `models` · `report` · `cli` · `checks` |
| CLI | `list-checks · keygen · fingerprint · authorize · validate · plan · run · verify-ledger · seal-ledger` |
| Checks shipped | `source.static` (offline source review), `http.headers` (minimally invasive) |
| Dependency | `cryptography>=44`, Python ≥3.11 |
| Deliberate exclusions | Credential theft, persistence, evasion, malware, destructive payloads, uncontrolled scanning, arbitrary shell, plugin loading |

**What was copied and what was not.** The original at `PKA testing\Red Team (1)` was reported
open, so it was **left untouched**. Copied: `src/aegis_rt/`, `tests/`, `examples/`, `README.md`,
`SECURITY.md`, `pyproject.toml`, `.gitignore`. Not copied: `build/`, `dist/`, `.egg-info/`,
`__pycache__/` — regenerable artifacts that would have inflated the folder without adding work.

---

## 17.3 Aegis as RoE enforcement — the significant finding

| RoE section | Paper control | Aegis enforcement |
|---|---|---|
| §5.1 Written authorization | A signature on a document | **Ed25519-signed receipt** with named approver, real ticket, and expiry — verified against a separately pinned trust key |
| §5.3 In-scope assets | An allow-list table | Targets allow-list; **public addresses denied unless the receipt opts in**; DNS resolution validated and the address pinned |
| §5.5/5.6 Permitted / prohibited actions | A list of ticked boxes | **Fixed check registry.** No shell, no plugins, no code from engagement files |
| §5.7 Approved tools | An inventory table | The bounded built-in registry *is* the inventory |
| §5.8 Blast radius | "Permitted impact ceiling" prose | Request budget, rate limit, concurrency cap, timeout — all mandatory fields |
| §5.10 Test schedule | A stated window | `expires_at` on the receipt; expiry stops the run |
| §5.13 Stop conditions | A phone call | `.aegis/STOP` file, checked at every safety boundary |
| §5.16 Evidence handling | Hashing by hand | Hash-chained ledger + **Ed25519 seal by the approval authority** + redaction to one-way digests |

**The strongest control is the one that is easy to miss: the operator cannot authorize their own
work, and cannot forge a complete ledger, because they do not hold the private key.** Compare
SoD-2 in [§3](02_org_structure_and_raci.md) — "the person who authorizes may not execute" — which
the model listed as having *no compensating control*, because it is the definition of
authorization. Aegis enforces it in cryptography.

**What Aegis does NOT cover — and its own SECURITY.md says so:** legal and privacy sign-off,
the system-owner signature, the emergency contact roster, SOC deconfliction, rollback plans, and
insurance/regulatory notification. The receipt is *"a technical guardrail, not a substitute for
legal authorization, change control, stakeholder notification, or an emergency plan."*
**Do not let the JSON file become a substitute for the signatures.**

---

## 17.4 Boundary reconciliations

| # | Conflict | Resolution |
|---|---|---|
| **RC-1** | **Red vs Orange — who does offensive work?** | **Red executes; Orange reviews designs.** Red is independent of the builders and works in lab/pre-prod/prod under an RoE. Orange is *deliberately* embedded and **never** operates in production. Both are offensive; only one is independent. |
| **RC-2** | **Red vs Purple — who runs the exercise?** | **Purple coordinates and measures; Red executes.** Purple does not manage Red (it must be able to critique Red's coverage), and Red does not choose targets. Purple scores the six-stage outcome; Red reports what happened, including failures to execute. |
| **RC-3** | **Independent-assessment evidence (crosswalk F-1)** | **CORRECTED 2026-08-14 — the original wording here was too broad.** "Independent" is four requirements, and Red satisfies two: independence *from development* and *from defense operations*. Red does **not** satisfy **independent exercise scoring** where Red participated ([Exercise Assurance](18_exercise_assurance.md) does), nor **external organizational assessment** (3PAO / C3PAO / QSA). Orange remains embedded and must not issue an independent assurance opinion. Full taxonomy: [§11.14](10_compliance_crosswalk.md). |
| **RC-4** | **Two authorization systems** — Aegis receipts vs. the RoE | **Layered, not competing.** The RoE authorizes the *engagement* (people, legal, safety, comms). Aegis authorizes the *execution* (targets, checks, limits) and enforces it at runtime. **An Aegis receipt without a signed RoE is not authorization**; an RoE without an Aegis receipt means the run simply will not start. |
| **RC-5** | **Two audit chains** — Aegis ledger vs. Blue's Sentinel chain vs. White's manifest | **Three layers, one anchor.** Blue's chain covers operational records and is anchored procedurally (SoD-11 head-hash export). Aegis's ledger covers engagement actions and is anchored **cryptographically** by the approval authority's seal. Both terminate in White's WORM evidence manifest. **Aegis's anchor is the stronger design — consider it the target state for Blue.** |
| **RC-6** | **`.aegis/STOP` vs. the RoE stop procedure** | Both, and they are not redundant. The file halts *tooling* at a safety boundary; the RoE procedure halts *people*, notifies, preserves state, and routes the resume decision to White. **Removing the STOP file yourself is the same violation as ignoring a stop call.** |
| **RC-7** | **Aegis findings vs. the Finding artifact (A5)** | Aegis output **feeds** A5. Red does not maintain a parallel findings list — parallel trackers are where findings die ([§7.4](06_artifact_index_and_standards.md)). Severity stays Purple's proposal and White's adjudication. |

---

## 17.5 Where Red sits

```
   ORANGE  -->  PURPLE  <-->  RED  -->  GREEN  -->  YELLOW
   reviews      coordinates   EXECUTES  makes it    builds the
   designs      & measures    (indep.)  defensible  fix
   (embedded)                    |
      ^            ^             |         ^            |
      |            |             |         |            |
      +--- operator rotation ----+         |            |
      |            |                       |            |
      +------------+-----------+-----------+------------+
                               |
                            BLUE  <-- operates the defense every day
                               |
                        +------+------+
                        |    WHITE    |  authorization · safety · scoring ·
                        | (independent)|  evidence integrity · stop authority
                        +-------------+
                               ^
                    holds the Aegis SIGNING KEY
                    -- Red can execute, but cannot authorize --
```

That last line is the structural point. **The approval authority's key is what makes Red safe to
hold in-house.**

---

## 17.6 Changes applied

| File | Change |
|---|---|
| `red-team/` | Created: source copied + `CHARTER`, `PLAYBOOK`, `ARTIFACTS`, `AI_AGENT`, `.init`, `CHANGELOG` |
| [`01_executive_operating_model.md`](01_executive_operating_model.md) | Red added to the value chain and the dedicated-vs-virtual table |
| [`02_org_structure_and_raci.md`](02_org_structure_and_raci.md) | Red named in the org chart; **SoD-2 note added** — Aegis enforces it cryptographically |
| [`10_compliance_crosswalk.md`](10_compliance_crosswalk.md) | **Conflict F-1 now has an owner** |
| [`README.md`](../README.md) | Seven teams |

---

## 17.7 Residual items — flagged, not fixed

| # | Item | Owner |
|---|---|---|
| **R-6** | `test_source_link_cannot_escape_authorized_root` **skips on this machine** (Windows symlink privilege, WinError 1314). It guards a **path-escape containment boundary**, so that boundary is **unproven here**. Run under Developer Mode, elevation, or Linux CI. *This is a verification gap, not a known defect.* | Red Lead |
| **R-7** | Only two checks ship. Appropriate for v0.1.0 with a fixed registry, but Red's ATT&CK coverage contribution is presently **narrow** — most emulation will be manual and Purple-authored rather than Aegis-executed. Do not let the tool's existence imply coverage it does not have. | Purple + Red |
| **R-8** | The original at `PKA testing\Red Team (1)` still exists and now diverges from this copy. Decide which is canonical before either is edited again. | Owner |
| **R-9** | `license = "LicenseRef-Proprietary"` with no distribution decision recorded. | Owner / LEGAL |
| **R-10** | Key-custody procedure is described but not operationally established: **who** holds `authority.pem`, in which secret manager, with what rotation and break-glass path. Until that is named, the model's strongest control is theoretical. | White + CISO |

**R-10 is the one to close first.** Every other control in this section depends on that key being
somewhere Red cannot reach.
