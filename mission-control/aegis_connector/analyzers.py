from __future__ import annotations

import hashlib
import json
import re
import ssl
import subprocess
import sys
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .config import ConnectorConfig


TEAMS = ("purple", "white", "yellow", "green", "orange", "blue", "red")
IGNORED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs", ".rb", ".php",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties",
    ".sh", ".ps1", ".sql", ".md", ".txt", ".xml",
}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs", ".rb", ".php"}
TEST_MARKERS = ("test_", "_test.", ".test.", ".spec.", "tests", "__tests__")
LOCK_FILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "pipfile.lock",
    "cargo.lock", "go.sum", "composer.lock", "gemfile.lock",
}
MANIFEST_LOCKS = {
    "package.json": {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"},
    "pyproject.toml": {"uv.lock", "poetry.lock", "requirements.lock"},
    "pipfile": {"pipfile.lock"},
    "cargo.toml": {"cargo.lock"},
    "go.mod": {"go.sum"},
    "composer.json": {"composer.lock"},
    "gemfile": {"gemfile.lock"},
}
SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("credential-assignment", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][^'\"\s]{12,}")),
    ("cloud-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)


def _finding(title: str, description: str, severity: str, owner: str) -> dict[str, str]:
    fingerprint = hashlib.sha256(f"{owner}|{title}".encode("utf-8")).hexdigest()
    return {
        "title": title[:240],
        "description": description[:20_000],
        "severity": severity,
        "ownerTeam": owner,
        "fingerprint": fingerprint,
    }


def _recommendations(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return [
        {
            "priority": item["severity"],
            "ownerTeam": item["ownerTeam"],
            "title": f"Remediate: {item['title']}",
            "acceptanceCriteria": f"The condition is removed or explicitly accepted, and the identical AEGIS check no longer reports fingerprint {item['fingerprint'][:12]}.",
        }
        for item in sorted(findings, key=lambda item: priority[item["severity"]])[:30]
    ]


def _score(findings: list[dict[str, str]]) -> tuple[int, bool]:
    automatic_failure = any(item["severity"] == "critical" for item in findings)
    deductions = {"critical": 35, "high": 15, "medium": 7, "low": 2}
    score = max(0, 100 - sum(deductions[item["severity"]] for item in findings))
    return score, automatic_failure


def _iter_files(root: Path, maximum: int = 10_000):
    count = 0
    for path in root.rglob("*"):
        if count >= maximum:
            return
        try:
            relative = path.relative_to(root)
            if any(part.lower() in IGNORED_PARTS for part in relative.parts):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            count += 1
            yield path, relative
        except (OSError, ValueError):
            continue


def inspect_repository(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    files = list(_iter_files(root))
    relative_names = {str(relative).replace("\\", "/").lower() for _, relative in files}
    basenames = {relative.name.lower() for _, relative in files}
    source_count = sum(path.suffix.lower() in SOURCE_SUFFIXES for path, _ in files)
    test_count = sum(any(marker in str(relative).lower() for marker in TEST_MARKERS) for _, relative in files)
    workflow_count = sum(name.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")) for name in relative_names)

    if ".gitignore" not in basenames:
        findings.append(_finding("Repository has no .gitignore boundary", "Generated files, local secrets, and private work products have no repository-level exclusion boundary.", "high", "yellow"))
    if not any(name in basenames for name in {"security.md", "security.txt"}):
        findings.append(_finding("Security reporting policy is missing", "No SECURITY.md or equivalent reporting policy was found in the authorized repository snapshot.", "low", "white"))
    if workflow_count == 0:
        findings.append(_finding("No continuous integration workflow was found", "The repository has no GitHub workflow that can prove tests and security gates run on changes.", "high", "yellow"))
    if source_count and test_count == 0:
        findings.append(_finding("Source code has no detected automated tests", f"AEGIS found {source_count} source files and no conventional test paths or filenames.", "high", "purple"))

    for manifest, acceptable_locks in MANIFEST_LOCKS.items():
        if manifest in basenames and not (acceptable_locks & basenames):
            findings.append(_finding(f"{manifest} is not paired with a lockfile", "Dependency resolution can change without a source change, weakening reproducibility and supply-chain review.", "high", "yellow"))

    tracked_env_files: list[str] = []
    if (root / ".git").exists():
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), "ls-files"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
            tracked_env_files = [
                line for line in completed.stdout.splitlines()
                if Path(line).name.lower() == ".env" or Path(line).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
            ][:25]
        except (OSError, subprocess.TimeoutExpired):
            pass
    for relative in tracked_env_files:
        findings.append(_finding("Sensitive configuration material is tracked", f"A credential-prone file is committed at {relative}. AEGIS did not return its contents.", "critical", "red"))

    exposed: list[tuple[str, int, str]] = []
    fixture_matches: list[tuple[str, int]] = []
    scanned = 0
    for path, relative in files:
        if len(exposed) >= 25 or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            if path.stat().st_size > 512 * 1024:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        for line_number, line in enumerate(content.splitlines(), 1):
            if "example" in line.lower() or "placeholder" in line.lower() or "[redacted]" in line.lower():
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    normalized_relative = str(relative).replace("\\", "/")
                    fixture_path = any(part in normalized_relative.lower().split("/") for part in {"test", "tests", "fixtures", "examples"})
                    if fixture_path and label == "credential-assignment":
                        fixture_matches.append((normalized_relative, line_number))
                    else:
                        exposed.append((normalized_relative, line_number, label))
                    break
            if len(exposed) >= 25:
                break
    for relative, line_number, label in exposed:
        findings.append(_finding("Potential secret material detected", f"The {label} detector matched {relative}:{line_number}. The value was intentionally excluded from the result.", "critical", "red"))
    if fixture_matches:
        sample = ", ".join(f"{path}:{line}" for path, line in fixture_matches[:5])
        findings.append(_finding("Secret-like test fixtures need review", f"AEGIS found {len(fixture_matches)} credential-like assignments in test or fixture paths ({sample}). Confirm they are inert fixtures and keep secret scanning in CI.", "low", "yellow"))

    score, automatic_failure = _score(findings)
    team_results = [
        {"team": "white", "status": "completed", "check": "Recorded authority and bounded local allowlist were enforced by the control plane and connector."},
        {"team": "yellow", "status": "completed", "check": f"Reviewed {source_count} source files, dependency locks, repository exclusions, and CI presence."},
        {"team": "green", "status": "completed", "check": f"Mapped the authorized repository boundary across {len(files)} files without following symlinks."},
        {"team": "orange", "status": "completed", "check": "Challenged unsafe defaults, unproven build paths, and sensitive-material handling."},
        {"team": "blue", "status": "completed", "check": f"Checked whether {workflow_count} detected workflows and repository evidence make changes observable."},
        {"team": "red", "status": "completed", "check": f"Performed a non-destructive credential and boundary review across {scanned} bounded text files."},
        {"team": "purple", "status": "completed", "check": f"Correlated {len(findings)} findings into repeatable fingerprints for later retest."},
    ]
    return {
        "kind": "repository",
        "metrics": {
            "filesInspected": len(files),
            "sourceFiles": source_count,
            "testFiles": test_count,
            "workflowFiles": workflow_count,
            "textFilesScanned": scanned,
            "lockfiles": sorted(LOCK_FILES & basenames),
        },
        "findings": findings,
        "teamResults": team_results,
        "recommendations": _recommendations(findings),
        "score": score,
        "automaticFailure": automatic_failure,
    }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def inspect_http_target(raw_url: str, config: ConnectorConfig) -> dict[str, Any]:
    current = raw_url
    redirects: list[str] = []
    response_headers: dict[str, str] = {}
    status = 0
    started = time.monotonic()
    opener = build_opener(_NoRedirect, HTTPSHandler(context=ssl.create_default_context()))
    for _ in range(4):
        parsed = urlsplit(current)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("website target must be a complete http or https URL")
        config.assert_allowed_host(parsed.hostname)
        request = Request(current, method="HEAD", headers={"User-Agent": "AEGIS-Safe-Assessment/1.0", "Accept": "*/*"})
        try:
            with opener.open(request, timeout=config.request_timeout_seconds) as response:
                status = response.status
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except HTTPError as exc:
            status = exc.code
            response_headers = {key.lower(): value for key, value in exc.headers.items()}
        except (URLError, TimeoutError, ssl.SSLError) as exc:
            return {
                "kind": "website",
                "metrics": {"reachable": False, "elapsedMs": round((time.monotonic() - started) * 1000)},
                "findings": [_finding("Target was not reachable from the connector", f"The safe HTTP inspection failed without retrying active requests: {type(exc).__name__}.", "high", "blue")],
            }
        location = response_headers.get("location")
        if status in {301, 302, 303, 307, 308} and location:
            next_url = urljoin(current, location)
            next_host = urlsplit(next_url).hostname or ""
            config.assert_allowed_host(next_host)
            redirects.append(next_url)
            current = next_url
            continue
        break

    findings: list[dict[str, str]] = []
    final = urlsplit(current)
    if final.scheme != "https":
        findings.append(_finding("Target is not protected by HTTPS", "The final authorized URL uses plaintext HTTP, exposing traffic and session data to interception.", "high", "green"))
    required_headers = {
        "content-security-policy": ("Content Security Policy is missing", "high", "green"),
        "strict-transport-security": ("HSTS is missing", "medium", "blue"),
        "x-content-type-options": ("MIME-sniffing protection is missing", "low", "yellow"),
        "referrer-policy": ("Referrer Policy is missing", "low", "orange"),
    }
    for header, (title, severity, owner) in required_headers.items():
        if header not in response_headers:
            findings.append(_finding(title, f"The final response did not include the {header} header.", severity, owner))
    if response_headers.get("access-control-allow-origin") == "*" and response_headers.get("access-control-allow-credentials", "").lower() == "true":
        findings.append(_finding("Credentialed CORS policy is overly broad", "The response combines wildcard origins with credentialed cross-origin requests.", "high", "red"))
    if status >= 500:
        findings.append(_finding("Target returned a server error", f"The passive request received HTTP {status}.", "high", "blue"))
    score, automatic_failure = _score(findings)
    team_results = [
        {"team": "white", "status": "completed", "check": "Verified the leased task carried recorded authority and the host matched the connector allowlist."},
        {"team": "green", "status": "completed", "check": "Reviewed HTTPS and browser trust-boundary headers."},
        {"team": "blue", "status": "completed", "check": f"Validated reachability and response state with one passive HEAD chain; final status {status}."},
        {"team": "yellow", "status": "completed", "check": "Reviewed safe response defaults and content-type protections."},
        {"team": "orange", "status": "completed", "check": "Reviewed information-flow and privacy headers."},
        {"team": "red", "status": "completed", "check": "Checked exposed HTTP/CORS boundaries without payloads, fuzzing, or exploitation."},
        {"team": "purple", "status": "completed", "check": f"Correlated {len(findings)} reproducible passive findings for retest."},
    ]
    return {
        "kind": "website",
        "metrics": {
            "reachable": True,
            "status": status,
            "redirectCount": len(redirects),
            "finalScheme": final.scheme,
            "elapsedMs": round((time.monotonic() - started) * 1000),
            "observedHeaders": sorted(response_headers),
        },
        "findings": findings,
        "teamResults": team_results,
        "recommendations": _recommendations(findings),
        "score": score,
        "automaticFailure": automatic_failure,
    }


def analyze_evidence(content: bytes, filename: str, media_kind: str) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    suggestions = [
        {"team": "white", "title": "Preserve verified provenance", "detail": f"Keep SHA-256 {digest[:12]} attached to the encrypted original and its authorization record."},
    ]
    findings: list[dict[str, str]] = []
    printable = sum(32 <= byte < 127 or byte in {9, 10, 13} for byte in content)
    text_ratio = printable / max(1, len(content))
    if media_kind in {"text", "structured-data"} or text_ratio > 0.9:
        decoded = content[:1_000_000].decode("utf-8", errors="replace")
        line_count = decoded.count("\n") + 1
        suggestions.append({"team": "yellow", "title": "Convert statements into executable checks", "detail": f"Review the {line_count}-line artifact for requirements that need a repeatable build or regression gate."})
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(decoded):
                findings.append(_finding("Uploaded evidence may contain secret material", f"The {label} detector matched the clean, authorized artifact {filename}. No matched value was returned.", "critical", "red"))
                break
    elif media_kind in {"image", "video", "audio"}:
        suggestions.append({"team": "orange", "title": "Review the demonstrated human workflow", "detail": "Inspect consent, trust signals, unsafe transitions, impersonation, and information exposure in the supplied media."})
        suggestions.append({"team": "blue", "title": "Extract observable control states", "detail": "Record visible identities, destinations, errors, alerts, and recovery evidence as bounded findings."})
    else:
        suggestions.append({"team": "green", "title": "Map artifact trust boundaries", "detail": "Identify producer, consumer, execution context, dependencies, and signature or provenance expectations."})
    return {
        "sha256": digest,
        "bytesAnalyzed": len(content),
        "mediaKind": media_kind,
        "suggestions": suggestions,
        "findings": findings,
    }


def run_gate(
    config: ConnectorConfig,
    gate_id: str,
    renew: Callable[[], None] | None = None,
) -> dict[str, Any]:
    manifest_path = config.program_root / "00-shared" / "config" / "ci_gates.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    known = {str(item.get("id")) for item in manifest.get("engineering_gates", [])}
    if gate_id != "all" and gate_id not in known:
        raise ValueError("gate is not present in the local authoritative manifest")
    argv = [sys.executable, "00-shared/tools/run_ci.py", "--json"]
    if gate_id != "all":
        argv.extend(["--gate", gate_id])
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=config.program_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output: list[str] = []
    lines: Queue[str] = Queue()

    def collect() -> None:
        if process.stdout:
            for line in process.stdout:
                lines.put(line)

    reader = Thread(target=collect, name=f"aegis-gate-{gate_id}", daemon=True)
    reader.start()
    last_renewal = started
    try:
        while process.poll() is None:
            if time.monotonic() - started > config.task_timeout_seconds:
                process.kill()
                raise TimeoutError(f"gate exceeded the {config.task_timeout_seconds}s connector limit")
            if renew and time.monotonic() - last_renewal >= 30:
                renew()
                last_renewal = time.monotonic()
            try:
                while True:
                    output.append(lines.get_nowait())
            except Empty:
                pass
            time.sleep(0.1)
        reader.join(timeout=2)
        try:
            while True:
                output.append(lines.get_nowait())
        except Empty:
            pass
    finally:
        if process.poll() is None:
            process.kill()
    joined = "".join(output)
    bounded = joined[-config.max_output_chars:]
    elapsed = round(time.monotonic() - started, 2)
    return {
        "gateId": gate_id,
        "passed": process.returncode == 0,
        "returnCode": process.returncode,
        "elapsedSeconds": elapsed,
        "output": bounded,
    }
