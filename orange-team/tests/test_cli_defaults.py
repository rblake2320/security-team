"""The CLI's default scorecard path must resolve to a real file.

Regression guard: DEFAULT_SCORECARD originally used parents[3], which resolves to
the repository root rather than the team directory, so every `score` invocation
without an explicit --scorecard crashed with FileNotFoundError. The unit tests all
passed a path explicitly, so nothing caught it until the CLI was actually used.
"""
from __future__ import annotations

import json

from aegis_orange.cli import DEFAULT_SCORECARD


def test_default_scorecard_path_exists():
    assert DEFAULT_SCORECARD.is_file(), f"default scorecard does not exist: {DEFAULT_SCORECARD}"


def test_default_scorecard_is_this_teams_scorecard():
    data = json.loads(DEFAULT_SCORECARD.read_text(encoding="utf-8"))
    assert data["team"] == "orange"
