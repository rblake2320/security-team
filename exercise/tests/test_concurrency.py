"""AUD-02 / AUD-08 regression: real concurrent processes, not simulated ones.

The original defect was invisible to sequential tests. Calling consume() twice in a
row always refused correctly; the failure only appeared when several processes
entered the read-modify-write at the same instant. A barrier releases the workers
together so they genuinely overlap.

Before the fix this failed 12/12 rounds at 6 workers, with THREE processes each
consuming the same nonce successfully. Replay protection did not hold at all.

These use real subprocesses and a real on-disk ledger. Nothing here is mocked: a
mocked lock would prove only that the mock works.
"""

from __future__ import annotations

import multiprocessing as mp
import sys
import unittest
from pathlib import Path

EXERCISE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXERCISE))


WORKERS = 6
ROUNDS = 3


def _worker(nonce: str, ledger: str, barrier, queue) -> None:
    """Run in a fresh process; import inside so each worker has its own module state."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import clearance as clr

    clr.NONCE_LEDGER = Path(ledger)
    barrier.wait()  # release every worker at the same moment
    try:
        clr.consume(nonce, "EX-CONCURRENCY")
        queue.put("SUCCESS")
    except clr.ClearanceError as exc:
        queue.put("REPLAY" if "CLEARANCE-REPLAY" in str(exc) else f"OTHER:{exc}"[:80])
    except Exception as exc:  # untyped leakage is itself the defect
        queue.put(f"RAW:{type(exc).__name__}:{exc}"[:80])


class NonceRaceTests(unittest.TestCase):
    def test_concurrent_consume_admits_exactly_one_winner(self) -> None:
        """Exactly one process may consume a nonce; the rest get typed replay refusals.

        Two invariants, both of which failed before the fix:
          1. exactly one SUCCESS (replay protection actually holds under concurrency)
          2. every loser gets CLEARANCE-REPLAY, never a raw OSError/PermissionError
        """
        import tempfile

        for round_index in range(ROUNDS):
            with tempfile.TemporaryDirectory() as tmp:
                ledger = Path(tmp) / "nonces.json"
                ledger.write_text("{}", encoding="utf-8")
                barrier = mp.Barrier(WORKERS)
                queue: mp.Queue = mp.Queue()
                nonce = f"race-{round_index}"
                procs = [
                    mp.Process(target=_worker, args=(nonce, str(ledger), barrier, queue))
                    for _ in range(WORKERS)
                ]
                for proc in procs:
                    proc.start()
                for proc in procs:
                    proc.join(timeout=60)
                outcomes = [queue.get() for _ in procs]

                self.assertEqual(
                    outcomes.count("SUCCESS"), 1,
                    f"round {round_index}: nonce consumed {outcomes.count('SUCCESS')} times "
                    f"(expected exactly 1) - replay protection failed: {sorted(outcomes)}",
                )
                self.assertEqual(
                    [o for o in outcomes if o not in ("SUCCESS", "REPLAY")], [],
                    f"round {round_index}: losers must get typed CLEARANCE-REPLAY refusals, "
                    f"got: {sorted(outcomes)}",
                )


class AtomicWriteTests(unittest.TestCase):
    """AUD-08: writes must not use predictable sibling temp paths."""

    def test_temp_file_is_unique_per_writer(self) -> None:
        import tempfile

        from filelock import atomic_write

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "evidence.json"
            observed = set()
            real_mkstemp = __import__("tempfile").mkstemp

            def record(*args, **kwargs):
                fd, name = real_mkstemp(*args, **kwargs)
                observed.add(name)
                return fd, name

            import tempfile as _tf
            _tf.mkstemp = record
            try:
                for index in range(5):
                    atomic_write(target, f'{{"n":{index}}}')
            finally:
                _tf.mkstemp = real_mkstemp

            self.assertEqual(len(observed), 5, "each write must use its own temp path")
            self.assertEqual(target.read_text(encoding="utf-8"), '{"n":4}')
            self.assertEqual(
                list(Path(tmp).iterdir()), [target],
                "no temp files may survive a successful write",
            )

    def test_no_predictable_sibling_path_is_used(self) -> None:
        """The pre-fix implementation wrote to `<name>.tmp`; nothing may do that now."""
        import tempfile

        from filelock import atomic_write

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "evidence.json"
            predictable = target.with_suffix(".tmp")
            # Occupy the old predictable path. A correct implementation never touches it.
            predictable.write_text("SENTINEL", encoding="utf-8")
            atomic_write(target, '{"ok":true}')
            self.assertEqual(
                predictable.read_text(encoding="utf-8"), "SENTINEL",
                "write must not use the predictable sibling temp path",
            )


if __name__ == "__main__":
    unittest.main()
