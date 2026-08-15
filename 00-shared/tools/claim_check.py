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
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLAIMS = os.path.join(ROOT, "00-shared", "config", "assurance_claims.json")
GATES = os.path.join(ROOT, "00-shared", "config", "assessment_readiness.json")

# Set in the environment of every subprocess collect_node_ids() spawns. Any test that
# itself invokes this script MUST check for this variable and skip rather than spawn
# another instance - see the incident note on collect_node_ids() and on
# test_gate_manifest.ClaimGateDoesNotMutateTreeTests. Without this, evidence collection
# for the 00-shared/tools package recursively re-invoked this script, which recursively
# re-collected evidence, unbounded - measured at 100+ live processes and tens of GB of
# RAM in under 4 minutes before being caught and killed by hand.
RECURSION_GUARD_ENV = "CLAIM_CHECK_RECURSION_GUARD"

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
CODE_EVIDENCE = re.compile(r"\.(py|js|ts|go|rs|java|rb|sh|ps1)$", re.I)
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
    """Readiness derived from EVERY defined gate, not from an author-editable list.

    OPUS-F6, reproduced: this iterated `assessment_readiness.required_gates`. Deleting
    the two PENDING entries from that list - WITHOUT touching their status, which still
    read PENDING in `gate_definitions` - flipped the program from NOT_ASSESSMENT_READY
    (exit 2) to ASSESSMENT_READY (exit 0) with `allow_assurance_statement` true, and
    made R6 unreachable. That is the exact negation of PROGRAM-READINESS-GATE-001.

    Third instance of one pattern: R5 trusted `evidence_gap`, R7 trusted
    `mechanism_changed_at`, readiness trusted `required_gates`. Each consulted a field
    the author writes while the ground truth sat unread beside it. Ground truth here is
    `gate_definitions`; `required_gates` is now an ASSERTION about it, validated rather
    than obeyed.
    """
    ar = gates["assessment_readiness"]
    defs = gates["gate_definitions"]
    failed = [name for name, d in defs.items() if d.get("status") != "VERIFIED"]

    # `required_gates` may not silently narrow the gate set. Omitting a defined gate is
    # itself a readiness failure, so shrinking the list can never buy readiness.
    declared = set(ar.get("required_gates") or [])
    omitted = sorted(set(defs) - declared)
    for name in omitted:
        if name not in failed:
            failed.append(name)
    if omitted:
        ar = dict(ar)
        ar["required_gates_omissions"] = omitted
    return sorted(failed), ar


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
    gates = load(os.path.join(ROOT, "00-shared", "config", "ci_gates.json"))

    # CRITICAL, self-found live during this review: multiple gate entries in
    # ci_gates.json share path "00-shared/tools" (repo-hygiene, ci-separation,
    # gate-drift, commitment). Iterating gate entries reran that SAME directory
    # once per entry. Combined with the recursion below, that gave a branching
    # factor of ~4 per recursion level - true exponential blowup, not a fixed
    # linear cost. Iterate unique test paths, not gate entries.
    unique_paths = []
    seen_paths = set()
    for gate in gates["engineering_gates"]:
        if gate.get("kind") != "unittest":
            continue
        key = (gate.get("path", ""), gate.get("pythonpath", ""))
        if key not in seen_paths:
            seen_paths.add(key)
            unique_paths.append(gate)

    # R2-F9 (opus, reproduced): running the suites made this gate MUTATE AND RE-SIGN
    # the very artifacts it verifies - exercise/white/authorization.json,
    # environment_attestation.json, and an evidence receipt - because the exercise
    # tests call make_fixture_trust.ensure(). A verification gate that mints fresh
    # signatures for signed authorization means signing authority is present in the
    # verification environment, and a clean tree can never be a CI precondition.
    # My own F1 fix introduced this, and moving to -v widened it from 2 files to 3.
    #
    # Execute against a throwaway copy. The tree under review is never written to.
    sandbox = tempfile.mkdtemp(prefix="claimcheck-")
    ignore = shutil.ignore_patterns(".git", "__pycache__", ".ruff_cache", ".pytest_cache")
    work = os.path.join(sandbox, "repo")
    try:
        shutil.copytree(ROOT, work, ignore=ignore, symlinks=True)
    except OSError as exc:
        shutil.rmtree(sandbox, ignore_errors=True)
        return set(), [f"sandbox copy failed: {exc}"], set()

    # MEDIUM (static sweep, 2026-08-15): cleanup previously ran only via the OSError
    # branch above and via unconditional fall-through at the end of the loop. Any
    # OTHER exception raised mid-loop - a bug in a future edit here, an unexpected
    # subprocess/OS error not already caught below, a KeyboardInterrupt - skipped
    # cleanup entirely and leaked the sandbox copy. This is the exact shape of the
    # already-disclosed 325-directory/668MB leak, just not fully closed by that fix.
    # try/finally makes cleanup unconditional on how the loop exits, not on which
    # exception types were anticipated when it was written.
    try:
        return _walk_packages(unique_paths, work)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def _walk_packages(unique_paths, work):
    """The per-package pytest-invocation loop, split out of `collect_node_ids` so its
    caller can guarantee sandbox cleanup with try/finally regardless of how this exits."""
    found, unresolvable, skipped = set(), [], set()
    for gate in unique_paths:
        test_path = gate.get("path", "")
        # Compare path COMPONENTS, not a raw string. sonnet's finding (crash-debate
        # cross-exam, 2026-08-15): a naive `test_path.split("/")[0] == "00-shared"`
        # silently fails to match an absolute path, a "./00-shared/..." prefix, a
        # backslash-separated path, or a case difference on a case-insensitive mount -
        # any of which would make this layer's check evaluate False and skip straight
        # past it without firing. Verified NOT reachable today (ci_gates.json's four
        # 00-shared/tools entries are all the literal string "00-shared/tools"), but a
        # future config edit or a Windows/Linux path-separator difference could
        # reintroduce it silently. PurePosixPath(...).parts normalizes both slash
        # directions and strips a leading "./", so this holds regardless of how the
        # path string is spelled.
        package = pathlib.PurePosixPath(test_path.replace("\\", "/")).parts[0] if test_path else ""
        # ONE computed boolean, reused everywhere `package` needs to mean "the
        # 00-shared/tools meta-package". Previously this was checked twice with two
        # DIFFERENT comparisons (`package == "00-shared"` here, case-sensitive; a
        # separate `.lower()` comparison at the recursion guard below) - found while
        # hardening the guard: if `package` ever derived to a different case, the two
        # checks would DISAGREE, silently routing 00-shared/tools tests to the
        # .git-less sandbox instead of the real tree they need (see the comment two
        # lines below), rather than failing safely. One boolean removes the
        # possibility of the two checks drifting apart.
        is_meta_tools = package.lower() == "00-shared"
        # DEFENSE IN DEPTH, layer 2. Layer 1 is the guard-env check inside the test
        # itself. This layer does not trust that every future test which spawns
        # claim_check.py will remember to check it: if THIS process is already
        # running inside a guarded (recursive) context, it refuses to walk into
        # 00-shared/tools again at all, rather than relying solely on the child
        # process behaving correctly.
        if is_meta_tools and os.environ.get(RECURSION_GUARD_ENV):
            unresolvable.append(
                f"{test_path}: skipped - already inside a guarded recursive "
                "evidence-collection context")
            continue
        # Tests under 00-shared/tools assert properties OF THE REPOSITORY - hygiene,
        # CI reachability, gate-manifest drift - and are meaningless in a detached copy
        # with no .git (207MB, far too large to clone per run). They are read-only with
        # respect to the tree; that is not assumed, it is asserted by
        # test_gate_manifest.ClaimGateDoesNotMutateTreeTests, which fails if a full gate
        # run leaves ANY file modified.
        base = ROOT if is_meta_tools else work
        cwd = os.path.join(base, package) if package else base
        target = test_path[len(package) + 1:] if package else test_path
        env = dict(os.environ)
        # CRITICAL, self-found live: this walked "00-shared/tools" using the REAL
        # tree (base=ROOT, not the sandbox), and that directory's own
        # test_gate_manifest.py contains a test that subprocess-spawns THIS SAME
        # claim_check.py to check for tree mutation. That inner invocation called
        # collect_node_ids() again, which ran "00-shared/tools" again, which spawned
        # claim_check.py again - unbounded recursive process spawning, amplified by
        # the ~4x path duplication above. Measured: 100+ live python.exe processes,
        # tens of GB of RAM, in under 4 minutes, before it was caught and killed by
        # hand. This is reachable through completely ordinary `run_ci.py` execution,
        # not just an ad hoc test run.
        #
        # RECURSION_GUARD is set in every subprocess this function spawns. Any test
        # that itself invokes claim_check.py MUST check for this and skip rather than
        # spawn another instance - see test_gate_manifest.ClaimGateDoesNotMutateTreeTests.
        env[RECURSION_GUARD_ENV] = "1"
        if gate.get("pythonpath"):
            env["PYTHONPATH"] = os.path.join(base, gate["pythonpath"])
        # Pin the config explicitly. pytest walks UPWARD from cwd for a rootdir config;
        # once execution moved into the sandbox it escaped the repo and found a broken
        # pyproject.toml sitting in the system temp directory, failing every package
        # with exit 4. Environment-dependent silent failure of exactly the kind that
        # already bit this function once (blue-team addopts).
        config = os.path.join(cwd, "pyproject.toml")
        if not os.path.isfile(config):
            config = os.path.join(work, "pytest-sandbox.ini")
            if not os.path.isfile(config):
                with open(config, "w", encoding="utf-8") as handle:
                    handle.write("[pytest]\n")
        try:
            proc = subprocess.run(
                # `-o addopts=` neutralises per-package addopts. blue-team's
                # pyproject sets addopts="-q"; combined with our own -q that becomes
                # DOUBLE quiet, and pytest prints per-file COUNTS instead of node ids.
                # The collector then silently saw zero blue-team tests and would have
                # reported every blue claim as unresolved evidence - a false positive
                # in the very gate meant to stop false confidence.
                # -v (not --collect-only) so we learn the OUTCOME, not just existence.
                # Collection alone includes SKIPPED tests, so proving a node id exists
                # never proved it ran - the residual of opus F1 that I disclosed.
                [sys.executable, "-m", "pytest", target, "-v", "--no-header",
                 "--tb=no", "-p", "no:cacheprovider", "-o", "addopts=",
                 "-c", config, "--rootdir", cwd],
                cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as exc:
            unresolvable.append(f"{test_path}: {type(exc).__name__}")
            continue
        if proc.returncode not in (0, 5):        # 5 = no tests ran
            unresolvable.append(f"{test_path}: pytest exit {proc.returncode}")
            continue
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "::" not in line or line.startswith(("=", "<", "ERROR", "FAILED")):
                continue
            node = line.split()[0]
            if "::" not in node:
                continue
            full = f"{package}/{node}".replace("\\", "/") if package else node
            found.add(full)
            if " SKIPPED" in line or line.endswith("SKIPPED"):
                skipped.add(full)
    return found, unresolvable, skipped


def check_evidence(reg, node_ids, unresolvable, skipped=frozenset()):
    """R5, honestly: does the cited evidence resolve to a test that exists?

    The spec promises detection of 'skipped or stale' tests. The implementation read
    `evidence_gap` - a field the CLAIM AUTHOR writes - so an author who simply omits
    it was compliant by construction (F2). Derive it instead.
    """
    violations = []
    if unresolvable:
        # Cannot prove evidence for those packages -> fail closed on them. But do NOT
        # stop here. R2-F8 (opus): this early-returned, so ONE broken package
        # suppressed evidence checking for EVERY claim - it invalidated opus's own
        # first R2-F7 run, which they caught with a control before reporting.
        violations.append(("R5", "-", "evidence collection failed for: "
                           + "; ".join(unresolvable[:3])))
    for c in reg["claims"]:
        if c["status"] not in ("EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"):
            continue
        for item in (c.get("evidence") or []):
            ref = item.split(" (")[0].strip()
            if "::" not in ref:
                # R2-F7 (opus): this `continue` reopened F1. A fictional code path with
                # NO `::` was skipped by the resolver AND missed by R4, because R4 only
                # fires when ALL evidence is doc-only. So one invented .py string was
                # unverifiable evidence that no rule examined.
                if CODE_EVIDENCE.search(ref):
                    violations.append(
                        ("R5", c["claim_id"],
                         f"evidence names a code file but no test node id, so it cannot "
                         f"be resolved: {ref[:60]}"))
                continue                          # prose/doc evidence handled by R4
            normalised = ref.replace("\\", "/")
            if normalised not in node_ids:
                violations.append(
                    ("R5", c["claim_id"],
                     f"evidence does not resolve to any collected test: {ref[:70]}"))
            elif normalised in skipped:
                # SELF-DISCLOSED residual of opus F1, now closed. Collection includes
                # SKIPPED tests, so proving a node ID exists did not prove it ever ran.
                # A claim resting on a test that never executes on this platform is
                # resting on nothing - and AEGIS-RT-SCAN-SCOPE-001 was doing exactly
                # that on Windows.
                violations.append(
                    ("R5", c["claim_id"],
                     f"evidence test is SKIPPED on this platform, so it evidences "
                     f"nothing here: {ref[:60]}"))
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
        node_ids, unresolvable, skipped = collect_node_ids()
        viol += check_evidence(reg, node_ids, unresolvable, skipped)
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
