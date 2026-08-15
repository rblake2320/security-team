"""Adversarial proof that job_guard.run_guarded() actually caps a multiplicative spawn -
the exact failure shape of the 2026-08-15 incident, reproduced harmlessly and bounded.

Uses `-S` (skip site initialization) for every spawned interpreter, deliberately - the
production incident, and opus's first verification attempt the same day, were both
confounded by this environment's `sitecustomize.py` eagerly importing torch/CUDA on every
bare `python` invocation, which by itself can exhaust memory before the test's own logic
ever runs. `-S` removes that confound so this test measures job_guard, not sitecustomize.

Self-bounded regardless of whether job_guard works: BRANCH=3, MAX_DEPTH=6 gives an
unbounded worst case of (3**7-1)/2 = 1093 processes if the cap failed completely - still
finite, still recoverable, chosen deliberately smaller than the original incident's
100+-in-4-minutes so a failed assertion here costs seconds, not a hung machine.
"""
from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import job_guard  # noqa: E402

SPAWNER_SOURCE = textwrap.dedent("""
    import subprocess, sys, time
    BRANCH, MAX_DEPTH = 3, 6
    def main():
        depth = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        print(f"gen {depth}", flush=True)
        if depth >= MAX_DEPTH:
            return
        kids = []
        for _ in range(BRANCH):
            try:
                kids.append(subprocess.Popen([sys.executable, "-S", __file__, str(depth + 1)]))
            except OSError as exc:
                print(f"REFUSED at gen {depth}: {exc}", flush=True)
        time.sleep(0.05)
        for p in kids:
            p.wait()
    if __name__ == "__main__":
        main()
    """)


class JobGuardCapsMultiplicativeSpawn(unittest.TestCase):
    def setUp(self):
        fd, self.spawner_path = tempfile.mkstemp(suffix="_spawner.py")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(SPAWNER_SOURCE)

    def tearDown(self):
        with __import__("contextlib").suppress(OSError):
            os.remove(self.spawner_path)

    def test_uncapped_baseline_would_actually_multiply(self):
        """Sanity: prove the spawner itself is genuinely multiplicative (not a test that
        passes because the spawner is secretly harmless), by running ONE generation
        directly (no job_guard) and confirming multiple children print their own gen
        line - i.e. real fan-out is happening, this isn't a no-op script."""
        import subprocess
        proc = subprocess.run(
            [sys.executable, "-S", self.spawner_path, "5"],  # depth=5, only 1 gen from cap
            capture_output=True, text=True, timeout=15,
        )
        gen_lines = [line for line in proc.stdout.splitlines() if line.startswith("gen ")]
        self.assertGreaterEqual(
            len(gen_lines), 3,
            "spawner did not fan out even near the depth limit - test fixture itself is "
            "broken, would make the capped assertion below meaningless")

    def test_job_guard_caps_the_process_tree(self):
        result = job_guard.run_guarded(
            [sys.executable, "-S", self.spawner_path, "0"],
            timeout=30, max_processes=10, max_memory_mb=2048,
        )
        gen_lines = [line for line in result.stdout.splitlines() if line.startswith("gen ")]
        refused_lines = [line for line in (result.stdout + result.stderr).splitlines()
                         if "REFUSED" in line]

        # Uncapped, gen 0 alone would reach depth 6 -> up to 1093 processes.
        # A working cap must stop this far short of that, deterministically.
        self.assertLess(
            len(gen_lines), 30,
            f"job_guard did not cap the spawn: saw {len(gen_lines)} generation lines, "
            f"expected well under 30 with max_processes=10. stdout tail: "
            f"{result.stdout[-500:]!r}")
        self.assertTrue(
            result.timed_out or refused_lines or result.returncode != 0,
            "tree was capped in size but nothing recorded WHY - job_guard should "
            "surface the limit hit (timeout, a CreateProcess refusal, or a non-zero "
            "exit), not silently truncate")


class JobGuardEnvironmentHandoff(unittest.TestCase):
    """Regression test: run_ci.py's real usage passes a custom `env` dict (to set
    PYTHONPATH per gate) on every single call. The first attempt to wire job_guard into
    run_ci.py failed on every gate with `'str' object has no attribute 'values'` -
    pywin32's CreateProcess wants the raw environment mapping, not a pre-built
    null-separated block string. This wasn't caught by the process-cap test above
    because that test never passed a custom env (defaulted to None, which took a
    different, never-buggy branch)."""

    def test_custom_env_var_is_visible_to_the_child(self):
        marker = "JOB_GUARD_ENV_HANDOFF_PROBE"
        env = dict(os.environ)
        env[marker] = "present"
        result = job_guard.run_guarded(
            [sys.executable, "-c", f"import os; print(os.environ.get('{marker}', 'MISSING'))"],
            env=env, timeout=15,
        )
        self.assertEqual(result.returncode, 0, f"child failed: {result.stderr}")
        self.assertIn("present", result.stdout)


if __name__ == "__main__":
    unittest.main()
