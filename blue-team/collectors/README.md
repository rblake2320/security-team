# Collectors

`windows_events.ps1` is a read-only starter collector for selected Windows
Security, System, and Defender events. It writes normalized JSONL to standard
output and never changes audit policy, services, firewall, Defender, or logs.

```powershell
.\collectors\windows_events.ps1 -SinceMinutes 15 > runtime\windows.jsonl
$env:PYTHONPATH = (Resolve-Path src).Path
python -m blue_team.cli ingest runtime\windows.jsonl --db runtime\blue.db
```

Some Security channels require an approved elevated session. Warnings are sent
to the warning stream; unavailable logs must be treated as blind spots.

Unsigned JSONL is suitable only for local evaluation. Production transport must
authenticate collectors, encrypt transit, prevent replay, and use the CLI's
source trust policy or a stronger asymmetric/mTLS boundary.
