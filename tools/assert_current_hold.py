from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    path = Path("00-shared/config/assessment_readiness.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    required = document["assessment_readiness"]["required_gates"]
    definitions = document["gate_definitions"]
    pending = [gate for gate in required if definitions[gate]["status"] != "VERIFIED"]
    if not pending:
        print("Assessment prerequisites are verified; issuance still requires the dedicated gate.")
        return 0
    failure = document["assessment_readiness"]["on_failure"]
    if failure.get("status") != "NOT_ASSESSMENT_READY" or failure.get("allow_assurance_statement") is not False:
        raise SystemExit("readiness failure no longer fails closed")
    if failure.get("result_marking") != "TRAINING_OR_ENGINEERING_USE_ONLY":
        raise SystemExit("readiness hold marking was weakened")
    print(f"Honest hold enforced for {len(pending)} prerequisite gate(s): {', '.join(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

