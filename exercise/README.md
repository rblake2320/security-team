# First integrated engineering rehearsal

This is an offline, disposable simulation of one seeded authorization weakness. It uses only
synthetic identities and records, performs no network activity, starts no service, and writes
only a bounded evidence result beneath `exercise/evidence/`.

Orange predicts the complete abuse path in `orange/abuse_cases.json`. Red's one approved test,
Blue's detection, Purple's six-stage traceability, Yellow's application fix, and Green's
least-privilege requirement use the same stable identifiers. The runner refuses an altered,
expired, out-of-scope, non-synthetic, or egress-enabled authorization.

Run from the program root:

```text
python exercise/run_rehearsal.py
python -m unittest discover -s exercise/tests -v
```

Every result is `TRAINING_OR_ENGINEERING_USE_ONLY`; this rehearsal cannot issue assurance.
