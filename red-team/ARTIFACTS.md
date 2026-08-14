# RED TEAM — Artifacts

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> Like Blue's, most of Red's artifacts are **machine-produced and cryptographically bound**. The
> engagement definition and the assessment report are the two humans author.

| Artifact | Produced by | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| **Engagement definition** | **Human** — Purple + Red | System Owner + White | 7 yr | INTERNAL | Exercise record |
| Scope fingerprint | `aegis_rt.scope` | — (derived) | 7 yr | INTERNAL | Plan output + ledger |
| **Authorization receipt** | **Approval authority** (signs) | White | 7 yr | INTERNAL | Exercise record |
| Execution plan | `aegis_rt plan` | Red Lead | 7 yr | INTERNAL | Exercise record |
| Finding (normalized, CWE, redacted) | `aegis_rt.report` | Purple → White (severity) | 7 yr after closure | INTERNAL / CONFIDENTIAL | Case management |
| **Audit ledger** (hash-chained JSONL) | `aegis_rt.audit` | Red Lead | 7 yr | INTERNAL | `.aegis/audit.jsonl` → White |
| **Ledger seal** (Ed25519) | Approval authority | White | 7 yr | INTERNAL | Evidence manifest |
| Assessment report | **Human** — Red | GRC (as L2 evidence) | 7 yr | CONFIDENTIAL | GRC platform |
| Check definition | Red (peer reviewed) | Red Lead | Life of check | INTERNAL | `src/aegis_rt/checks/` |

---

## Engagement definition

The shape is [`examples/engagement.json`](examples/engagement.json). **The limits block is a
safety control, not performance tuning** — it is the blast-radius ceiling.

```jsonc
{
  "engagement_id": "EX-2026-014",         // [M] tie to the exercise ID, not a codename
  "owner": "Security Engineering",         // [M] the accountable system owner
  "targets": [                             // [M] ALLOW-LIST. No wildcards.
    { "kind": "path", "value": "." }       //     kinds are declared per check
  ],
  "allowed_checks": ["source.static"],     // [M] explicit; the registry is fixed
  "limits": {                              // [M] every field required
    "max_requests": 10,                    //   total request budget
    "max_concurrency": 2,
    "requests_per_second": 2,              //   rate limit
    "timeout_seconds": 8,
    "max_files": 20000,
    "max_findings": 5000
  }
}
```

**Governance fields that live in the RoE, not this file [M]:** legal and privacy sign-off,
system-owner authorization, stop conditions, emergency contacts, data handling, rollback. The
engagement file is the *technical* scope; the [RoE](../00-shared/04_rules_of_engagement_template.md)
is the *authorization*. Aegis's own SECURITY.md makes this point — do not let the JSON file
become a substitute for the signatures.

**Any change to targets, checks, or limits changes the fingerprint and voids the existing
receipt.** That is the intended behaviour. Re-authorize.

---

## Scope fingerprint

```
aegis-rt plan engagement.json      -> 64-character fingerprint
aegis-rt fingerprint engagement.json
```

| Rule | Detail |
|---|---|
| Bound to | The exact targets, checks, and execution limits |
| Acknowledged | **By hand, at run time** (`--ack-scope`) — a second deliberate confirmation |
| **Never** | Copy a fingerprint forward from an earlier plan. The control exists precisely to catch the change you did not notice |
| Recorded in | Plan output, authorization receipt, and the audit ledger |

---

## Authorization receipt

**Red receives this. Red never issues it.** The private key stays with the approval authority.

```
aegis-rt keygen    --private-key authority.pem --public-key authority.pub.pem \
                   --password-env AEGIS_KEY_PASSWORD --purpose authorization-v1
aegis-rt authorize engagement.json --approved-by "<name, title>" --ticket "<approval ticket>" \
                   --expires-at "<ISO 8601 UTC>" --signing-key authority.pem \
                   --password-env AEGIS_KEY_PASSWORD --ack "I AM AUTHORIZED"
```

| Field | Requirement |
|---|---|
| `approved_by` | **[M]** A named human with authority over the target, not a team |
| `ticket` | **[M]** A real approval ticket that a reviewer can open — not a placeholder |
| `expires_at` | **[M]** The engagement window, not "a year from now." Expiry is a control |
| Signature | **[M]** Ed25519, verified against a **separately pinned** trust key |
| Scope binding | **[M]** Bound to the exact fingerprint |

**Key handling [M]:** encrypted private key held by the approval authority; only the public
trust key is distributed to operators; the signing password comes from a secret manager, never a
committed file; clear the environment variable after signing. **A signing key found on an
operator's machine halts the program** — it collapses the separation of duty the tool enforces.

---

## Audit ledger and seal

```
aegis-rt verify-ledger .aegis/audit.jsonl --seal .aegis/audit.seal.json \
                       --evidence-trust-key evidence.pub.pem
aegis-rt seal-ledger   .aegis/audit.jsonl --seal .aegis/audit.seal.json \
                       --evidence-signing-key evidence.pem --password-env AEGIS_KEY_PASSWORD
```

| Property | Detail |
|---|---|
| Structure | Append-only JSONL, SHA-256 hash chain, exclusive file locking |
| Detects | Modification and interior deletion |
| **Final seal** | Domain-separated Ed25519 over the completed ledger, signed with the distinct evidence key — not by Red or the authorization key |
| Archive [M] | Ledger + seal + trust key to an access-controlled immutable store |
| Handoff [M] | To **White**, into the evidence manifest, at engagement close |

**Verification failure is an integrity incident**, escalated to Red Lead and White. Do not re-run
the engagement to produce a clean ledger.

> **Note the design symmetry with Blue.** Blue's chain is externally anchored by exporting its
> head hash to White (SoD-11). Aegis solves the same problem differently — the *approval
> authority's* key seals the ledger, so the operator cannot forge a complete history. Both
> reach independence; Aegis's is stronger because the anchor is cryptographic rather than
> procedural.

---

## Finding

Aegis normalizes findings, attaches CWE references, and **replaces matched values with short
one-way digests**. The human additions are the parts that make a finding actionable:

```markdown
# Finding (Red-authored section)

Reproduction:      [M] exact steps an engineer can follow WITHOUT Red present
Business impact:   [M] in the system owner's terms, not CVSS alone
Environment:       [M] lab | pre-prod | prod (+ authorization reference)
What was NOT tested: [M] and why -- silence here implies coverage you did not achieve
Failed executions: [M] test cases that did not run, and the reason
Evidence:          [M] minimum sufficient. Redacted at capture, never after.
```

Severity is **proposed by Purple and adjudicated by White** — not set by the operator who found
it. Aegis output feeds the standard Finding artifact
([purple-team/ARTIFACTS.md](../purple-team/ARTIFACTS.md) A5); Red does not maintain a parallel
findings list.

---

## Check definition

New checks implement the protocol in [`src/aegis_rt/checks/base.py`](src/aegis_rt/checks/base.py)
and are registered in the **fixed built-in registry**.

```markdown
Check ID:              [M] namespace.name  (e.g. source.static, http.headers)
Supported target kinds:[M] declared explicitly
Makes active requests: [M] true | false    <- drives rate limiting and authorization requirements
Safety class:          [M] passive | minimally invasive   (nothing beyond this ships)
Redaction:             [M] how matched values are digested
Peer reviewed by:      [M] a second engineer
Tests:                 [M] positive, negative, boundary, and a containment test
```

**Hard rules [M]** — these are the tool's central safety property:
- No arbitrary shell commands, no plugin loading, no code from engagement files
- **Data must never become executable control flow**
- No credential theft, persistence, evasion, malware, destructive payloads, or uncontrolled scanning
- A check that cannot state its blast radius does not ship

> **R-6 resolved:** `test_source_link_escape_is_rejected` uses an NTFS junction on Windows and
> a symbolic link on POSIX. It passes locally on Windows, and two-platform CI forbids skips.
