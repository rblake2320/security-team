"""Make this team's package importable without environment variables.

CI runs on both ubuntu-latest and windows-latest. Setting PYTHONPATH in a `run:`
step means writing it twice with different shell syntax; putting it here means the
same command works identically on both, and `python -m pytest <team>/tests` needs
no wrapper.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
