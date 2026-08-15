#!/usr/bin/env python3
"""Assurance-claim gate. CI enforcement for the claim-mechanism-evidence discipline.

    python 00-shared/tools/claim_check.py            # all checks
    python 00-shared/tools/claim_check.py --gates    # readiness gates only
    python 00-shared/tools/claim_check.py --lint     # normative-language lint only
    python 00-shared/tools/claim_check.py --json     # machine-readable

Exit 0 = pass. Exit 1 = blocking violation. Exit 2 = NOT_ASSESSMENT_READY (advisory
when only --gates is requested, blocking when an OPERATIONAL claim depends on it).

Rejection rules (spec: 00-shared/22_assurance_claims.md):
  R1 normative language without a claim reference
  R2 claim without a named mechanism
  R3 claim without BOTH positive and negative tests
  R4 claim whose only evidence is documentation
  R5 claim referencing skipped or missing tests
  R6 claim marked OPERATIONAL while a readiness gate is false
  R7 mechanism changed without a claim-version increment
"""

import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLAIMS = os.path.join(ROOT, "00-shared", "config", "assurance_claims.json")
GATES = os.path.join(ROOT, "00-shared", "config", "assessment_readiness.json")

# R1: normative assurance vocabulary. Deliberately over-inclusive; triage is the point.
NORMATIVE = re.compile(
    r"\b(is enforced|are enforced|cryptographically enforced|machine-enforced|tamper-proof|"
    r"tamper proof|guarantees?|is satisfied|are satisfied|fully satisfies|"
    r"cannot be bypassed|impossible to|ensures that|prevents\b)",
    re.IGNORECASE)
CLAIM_REF = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3}\b")   # e.g. AEGIS-COMMIT-HIDING-001

# Contexts where normative words are description, not assertion.
EXEMPT_LINE = re.compile(
    r"(^\s*[-*]?\s*\"|^\s*//|DEPRECATED|defect|MUST NOT|must not|never |NEVER |"
    r"does not|did not|cannot state|would have|overclaim|withdrawn|"
    r"^\s*\|?\s*R\d\b|rejection rule|banned|anti-pattern|failure indicator)", re.IGNORECASE)

NEGATIVE_HINT = re.compile(r"(WRONG|TAMPER|FAIL|REJECT|DENIED|NEGATIVE|ENUMERATION|BOUNDARY|UNKNOWN)", re.I)
DOC_ONLY = re.compile(r"\.(md|txt|rst)(::|$)|^docs?/", re.I)


def mechanism_digest(claim):
    """Canonical digest of the claim's mechanism. Changing the mechanism changes this;
    there is no field an author can omit to avoid it."""
    body = json.dumps(claim.get("mechanism", {}), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def md_files():
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".ruff_cache", "node_modules"}]
        for fn in files:
            if fn.endswith(".md"):
                out.append(os.path.join(base, fn))
    return sorted(out)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def check_gates(gates):
    ar = gates["assessment_readiness"]
    defs = gates["gate_definitions"]
    failed = [g for g in ar["required_gates"] if defs[g]["status"] != "VERIFIED"]
    return failed, ar


def check_claims(reg, gates_failed):
    v = []
    for c in reg["claims"]:
        cid, st = c["claim_id"], c["status"]

        # R2 - named mechanism
        if not c.get("mechanism", {}).get("construction"):
            v.append(("R2", cid, "no named mechanism"))

        ev = c.get("evidence") or []

        # R4 - documentation-only evidence
        if ev and all(DOC_ONLY.search(e) for e in ev):
            v.append(("R4", cid, "evidence is documentation only"))

        # R3 - positive AND negative tests required at EVIDENCED or beyond
        if st in ("EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"):
            if not ev:
                v.append(("R3", cid, f"status {st} with no evidence"))
            elif not any(NEGATIVE_HINT.search(e) for e in ev):
                v.append(("R3", cid, f"no negative/falsification test among {len(ev)} evidence items"))

        # R5 - stale, skipped, or missing evidence
        if c.get("evidence_gap") and st in ("EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"):
            v.append(("R5", cid, f"evidence_gap present at status {st}"))

        # R6 - OPERATIONAL while a gate is false
        if st == "OPERATIONAL" and gates_failed:
            v.append(("R6", cid, "OPERATIONAL while gates false: {}".format(",".join(gates_failed))))

        # R7 - mechanism change without version increment.
        # F2 (opus): this fired only on `mechanism_changed_at`, a field the CLAIM
        # AUTHOR writes. Rewriting `mechanism.construction` to a materially different
        # mechanism and simply OMITTING the field evaded the rule entirely - proven by
        # PoC. Self-attestation detects an honest author and is silent against any
        # other kind. Derive it: hash the mechanism, compare to the recorded digest.
        digest = mechanism_digest(c)
        recorded = c.get("mechanism_digest")
        if st in ("EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"):
            if not recorded:
                v.append(("R7", cid, "no mechanism_digest recorded; mechanism changes "
                                     "cannot be detected"))
            elif recorded != digest:
                v.append(("R7", cid,
                          f"mechanism changed (digest {digest[:12]} != recorded "
                          f"{recorded[:12]}) without re-recording it alongside a "
                          "version increment"))

        # lifecycle sanity
        if st in ("INDEPENDENTLY_REVIEWED", "OPERATIONAL") and not c.get("independent_reviewer"):
            v.append(("R3", cid, f"status {st} without an independent reviewer"))
    return v


def lint(reg):
    known = {c["claim_id"] for c in reg["claims"]}
    hits, scanned = [], 0
    for path in md_files():
        scanned += 1
        infence = False
        with open(path, encoding="utf-8") as handle:
            for n, line in enumerate(handle, 1):
                if line.lstrip().startswith("```"):
                    infence = not infence
                    continue
                if infence or EXEMPT_LINE.search(line):
                    continue
                if NORMATIVE.search(line):
                    # F3 (opus): `known` was computed and never used, so ANY
                    # claim-shaped token licensed a normative sentence -
                    # `TOTALLY-FAKE-CLAIM-999` passed clean. The escape hatch was
                    # citing something that LOOKS like a claim ID, not a real one.
                    refs = CLAIM_REF.findall(line)
                    if not refs:
                        hits.append((rel(path), n, line.strip()[:96]))
                    elif not any(r in known for r in refs):
                        hits.append((rel(path), n,
                                     f"cites UNREGISTERED claim id {refs[0]}: "
                                     + line.strip()[:70]))
        # F4 (opus): an ODD number of fences left infence=True to EOF, silently
        # suppressing R1 for the rest of the file - an ordinary markdown typo
        # disabled the scanner. Fail closed: unlintable is not clean.
        if infence:
            hits.append((rel(path), 0,
                         "UNBALANCED CODE FENCE - file is unlintable, R1 cannot be "
                         "trusted for it; close the fence"))
    return hits, scanned, known


def collect_node_ids():
    """Every test node ID that actually EXISTS, repo-relative.

    F1/F2 (opus): evidence was a STRING, never a resolved reference. A claim could
    cite `tests/does_not_exist.py::test_fictional_BOUNDARY` and pass clean - proven
    by PoC, 4/4 forged evidence sets accepted. `NEGATIVE_HINT` matched the string,
    so an invented token also satisfied R3, and one invented non-doc entry defeated
    R4's documentation-only check.

    Collected once per package (~8 pytest invocations) rather than once per evidence
    entry, so this stays fast enough to run on every gate execution.
    """
    import subprocess

    gates = load(os.path.join(ROOT, "00-shared", "config", "ci_gates.json"))
    found, unresolvable = set(), []
    for gate in gates["engineering_gates"]:
        if gate.get("kind") != "unittest":
            continue
        test_path = gate.get("path", "")
        package = test_path.split("/")[0] if "/" in test_path else ""
        cwd = os.path.join(ROOT, package) if package else ROOT
        target = test_path[len(package) + 1:] if package else test_path
        env = dict(os.environ)
        if gate.get("pythonpath"):
            env["PYTHONPATH"] = os.path.join(ROOT, gate["pythonpath"])
        try:
            proc = subprocess.run(
                # `-o addopts=` neutralises per-package addopts. blue-team's
                # pyproject sets addopts="-q"; combined with our own -q that becomes
                # DOUBLE quiet, and pytest prints per-file COUNTS instead of node ids.
                # The collector then silently saw zero blue-team tests and would have
                # reported every blue claim as unresolved evidence - a false positive
                # in the very gate meant to stop false confidence.
                [sys.executable, "-m", "pytest", target, "--collect-only", "-q",
                 "--no-header", "-p", "no:cacheprovider", "-o", "addopts="],
                cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as exc:
            unresolvable.append(f"{test_path}: {type(exc).__name__}")
            continue
        if proc.returncode not in (0, 5):        # 5 = no tests collected
            unresolvable.append(f"{test_path}: pytest exit {proc.returncode}")
            continue
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "::" not in line or line.startswith(("=", "<", "ERROR", "FAILED")):
                continue
            found.add(f"{package}/{line}".replace("\\", "/") if package else line)
    return found, unresolvable


def check_evidence(reg, node_ids, unresolvable):
    """R5, honestly: does the cited evidence resolve to a test that exists?

    The spec promises detection of 'skipped or stale' tests. The implementation read
    `evidence_gap` - a field the CLAIM AUTHOR writes - so an author who simply omits
    it was compliant by construction (F2). Derive it instead.
    """
    violations = []
    if unresolvable:
        # Cannot prove evidence exists -> cannot certify. Fail closed rather than
        # silently treating an uncollectable package as having no bad evidence.
        violations.append(("R5", "-", "evidence collection failed for: "
                           + "; ".join(unresolvable[:3])))
        return violations
    for c in reg["claims"]:
        if c["status"] not in ("EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"):
            continue
        for item in (c.get("evidence") or []):
            ref = item.split(" (")[0].strip()
            if "::" not in ref:
                continue                          # prose/doc evidence handled by R4
            if ref.replace("\\", "/") not in node_ids:
                violations.append(
                    ("R5", c["claim_id"],
                     f"evidence does not resolve to any collected test: {ref[:70]}"))
    return violations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--allow-not-ready",
        action="store_true",
        help="return success when claims/lint pass and readiness is honestly pending (engineering CI only)",
    )
    a = ap.parse_args()
    allc = not (a.gates or a.lint)

    reg, gates = load(CLAIMS), load(GATES)
    failed, ar = check_gates(gates)
    result = {"readiness": {"failed_gates": failed,
                            "status": ar["on_failure"]["status"] if failed else "ASSESSMENT_READY",
                            "marking": ar["on_failure"]["result_marking"] if failed else None,
                            "allow_assurance_statement": not failed}}

    if a.gates or allc:
        print("READINESS")
        print("  status  : {}".format(result["readiness"]["status"]))
        if failed:
            print("  marking : {}".format(result["readiness"]["marking"]))
            for g in failed:
                print("  PENDING : {} (closure item {})".format(g, gates["gate_definitions"][g]["closure_item"]))
        print()

    viol = []
    if allc:
        viol = check_claims(reg, failed)
        # F1/F2 (opus): resolve cited evidence instead of trusting the string.
        node_ids, unresolvable = collect_node_ids()
        viol += check_evidence(reg, node_ids, unresolvable)
        by = {}
        for r, cid, msg in viol:
            by.setdefault(cid, []).append((r, msg))
        print(f"CLAIMS ({len(reg['claims'])} registered)")
        counts = {}
        for c in reg["claims"]:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
            flag = "  <-- {}".format(", ".join("{} {}".format(*x) for x in by[c["claim_id"]])) if c["claim_id"] in by else ""
            print(f"  {c['claim_id']:<32} {c['status']:<22}{flag}")
        print("  " + " | ".join(f"{key}={value}" for key, value in sorted(counts.items())))
        print()
        result["claims"] = {"total": len(reg["claims"]), "by_status": counts,
                            "violations": [{"rule": r, "claim": c, "detail": m} for r, c, m in viol]}

    if a.lint or allc:
        hits, scanned, known = lint(reg)
        print("NORMATIVE-LANGUAGE LINT (R1)")
        print(f"  scanned : {scanned} markdown files")
        print(f"  claims  : {len(known)} registered ids")
        print(f"  UNSUPPORTED CLAIM CANDIDATES: {len(hits)}")
        perfile = {}
        for f, _, _ in hits:
            perfile[f] = perfile.get(f, 0) + 1
        for f, n in sorted(perfile.items(), key=lambda x: -x[1])[:12]:
            print(f"    {f:<58} {n}")
        if hits:
            print("  sample:")
            for f, n, t in hits[:5]:
                print(f"    {f}:{n}  {t}")
        print("  NOTE: intentionally over-inclusive. Each hit is a candidate requiring triage,")
        print("        not a confirmed defect. Triage = register a claim, or reword.")
        print()
        result["lint"] = {"scanned": scanned, "candidates": len(hits)}

    if a.json:
        print(json.dumps(result, indent=2))

    if viol:
        print(f"RESULT: FAIL - {len(viol)} blocking claim violation(s)")
        return 1
    if failed and not a.allow_not_ready:
        print("RESULT: NOT_ASSESSMENT_READY - exercises permitted, assurance statements prohibited.")
        print("        All results carry: {}".format(ar["on_failure"]["result_marking"]))
        return 2
    if failed:
        print("RESULT: PASS WITH HONEST READINESS HOLD - engineering CI may continue; assurance remains prohibited.")
        return 0
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
