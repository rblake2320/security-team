#!/usr/bin/env python3
"""Static analysis + compile gate. Mirrors the CI step so local runs match.

Added 2026-08-14: ruff and compileall ran in CI but were absent from the gate
manifest, so run_ci.py never executed them and a lint error reached CI. The
manifest must be a SUPERSET of the workflow.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ["purple-team/src", "purple-team/tests", "red-team/src", "red-team/tests",
           "blue-team/src", "blue-team/tests", "00-shared/tools", "tools", "exercise",
           "mission-control/aegis_platform", "mission-control/aegis_connector",
           "mission-control/tests", "mission-control/tools", "mission-control/saas_server.py",
           "mission-control/server.py"]
# Targets with their own pyproject.toml (blue-team's carries real, specific settings -
# line-length, target-version, a custom rule `select` - that must keep applying) vs.
# targets with no local config anywhere in their ancestry up to the repo root, which
# has none either.
CONFIGURED_TARGETS = ["purple-team/src", "purple-team/tests", "red-team/src",
                       "red-team/tests", "blue-team/src", "blue-team/tests"]
UNCONFIGURED_TARGETS = ["00-shared/tools", "tools", "exercise",
                        "mission-control/aegis_platform", "mission-control/aegis_connector",
                        "mission-control/tests", "mission-control/tools",
                        "mission-control/saas_server.py", "mission-control/server.py"]

def main() -> int:
    # Found live while investigating OPUS-CI-RED: ruff picked up and failed to parse
    # an unrelated, broken pyproject.toml sitting in the system temp directory when
    # run over UNCONFIGURED_TARGETS - those have no pyproject.toml of their own or at
    # the repo root (there isn't one), so ruff's config search kept looking. Same
    # class of environment-dependent failure already fixed once for claim_check.py's
    # own pytest invocations via an explicit config, never ported to this gate.
    # `--isolated` is the correct fix ONLY for the unconfigured targets - applying it
    # to CONFIGURED_TARGETS would silently drop blue-team's real, specific settings.
    ruff_cmds = [
        [sys.executable, "-m", "ruff", "check", *CONFIGURED_TARGETS],
        [sys.executable, "-m", "ruff", "check", "--isolated", *UNCONFIGURED_TARGETS],
    ]
    for cmd in (*ruff_cmds, [sys.executable, "-m", "compileall", "-q", *TARGETS]):
        p = subprocess.run(cmd, cwd=str(ROOT))
        if p.returncode != 0:
            return p.returncode
    print("static analysis + compile: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
