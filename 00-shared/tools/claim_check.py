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

        # R7 - mechanism change without version increment
        if c.get("mechanism_changed_at") and c.get("version_bumped_at") != c.get("mechanism_changed_at"):
            v.append(("R7", cid, "mechanism changed without claim-version increment"))

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
                if NORMATIVE.search(line) and not CLAIM_REF.search(line):
                    hits.append((rel(path), n, line.strip()[:96]))
    return hits, scanned, known


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
