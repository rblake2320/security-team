#!/usr/bin/env python3
"""Outside-in proof for the browser-contained public mission workflow."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


MISSION_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.getenv("AEGIS_SHOWCASE_TEST_ARTIFACTS", MISSION_ROOT / "runtime" / "showcase-test-artifacts"))
GUIDE_KEY = "aegis.guide.seen.2026.08.31.1.demo"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, process: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Showcase server exited early.\n{log_path.read_text(encoding='utf-8', errors='replace')[-4000:]}")
        try:
            with urllib.request.urlopen(f"{base_url}api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Showcase server did not become healthy.\n{log_path.read_text(encoding='utf-8', errors='replace')[-4000:]}")


def wait_for_app(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightTimeoutError:
        pass
    page.locator(".app-shell").wait_for()


def assert_no_horizontal_clip(page, label: str) -> None:
    metrics = page.evaluate(
        """() => ({
            viewport: window.innerWidth,
            html: document.documentElement.scrollWidth,
            body: document.body.scrollWidth
        })"""
    )
    assert max(metrics["html"], metrics["body"]) <= metrics["viewport"] + 2, f"{label} clips: {metrics}"


def run_journey(base_url: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        errors: list[str] = []
        writes: list[str] = []
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        page.add_init_script(f"localStorage.setItem('{GUIDE_KEY}', '1')")
        page.on("console", lambda message: errors.append(f"console:{message.text}") if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"page:{error}"))
        page.on("request", lambda request: writes.append(f"{request.method} {request.url}") if request.method not in {"GET", "HEAD", "OPTIONS"} else None)
        page.goto(f"{base_url}#/command", wait_until="domcontentloaded")
        wait_for_app(page)

        assert page.get_by_role("button", name="Start interactive mission").is_visible()
        assert "Do the work. Don’t just tour the screens." in page.locator(".demo-quickstart").inner_text()
        page.get_by_role("button", name="Start interactive mission").click()
        page.get_by_role("heading", name="Run a mission. See what AEGIS produces.", level=1).wait_for()
        assert page.evaluate("window.location.hash") == "#/engagements"
        assert "Zero real target traffic" in page.locator(".showcase-boundary").inner_text()

        page.get_by_role("button", name="Continue to safe intake").click()
        page.get_by_role("heading", name="Give the teams enough context to work.", level=2).wait_for()
        page.locator(".showcase-dropzone input").set_input_files(
            {"name": "launch-diagram.png", "mimeType": "image/png", "buffer": b"synthetic-browser-only-file"}
        )
        assert page.get_by_text("launch-diagram.png", exact=True).is_visible()
        assert page.get_by_text("METADATA ONLY", exact=True).is_visible()
        page.get_by_role("button", name="Add prepared sample inputs").click()
        assert "4 attached" in page.locator(".showcase-input-register").inner_text()

        page.get_by_role("button", name="Begin seven-team simulation").click()
        page.get_by_role("heading", name="Seven teams are processing the mission.", level=2).wait_for()
        page.get_by_role("heading", name="Mission results are ready to use.", level=2).wait_for(timeout=6_000)
        assert "64/100" in page.locator(".showcase-score").inner_text().replace("\n", "")
        assert page.locator(".showcase-findings article").count() == 3
        assert "3 findings" in page.locator(".showcase-result-seal").inner_text()

        with page.expect_download() as download_info:
            page.get_by_role("link", name="Export evidence JSON").click()
        download = download_info.value
        assert download.suggested_filename == "aegis-prelaunch-synthetic-evidence.json"
        payload = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        assert payload["classification"] == "PUBLIC_SYNTHETIC_DEMONSTRATION"
        assert payload["boundary"] == {
            "realTargetContacted": False,
            "fileContentUploaded": False,
            "serverMutationPerformed": False,
            "note": "This package demonstrates the workflow. It is not a real security assessment.",
        }
        assert len(payload["teams"]) == 7 and len(payload["findings"]) == 3

        page.get_by_role("button", name="Apply sample fixes + rerun").click()
        page.get_by_role("heading", name="Seven teams are processing the mission.", level=2).wait_for()
        page.get_by_role("heading", name="Mission results are ready to use.", level=2).wait_for(timeout=6_000)
        assert "91/100" in page.locator(".showcase-score").inner_text().replace("\n", "")
        assert page.locator(".showcase-comparison .is-resolved strong").inner_text() == "2"
        comparison_text = page.locator(".showcase-comparison").inner_text()
        assert "1" in comparison_text and "persistent" in comparison_text.lower()
        assert_no_horizontal_clip(page, "desktop public journey")
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=ARTIFACTS / "interactive-showcase-desktop.png", full_page=True)
        context.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        phone = mobile.new_page()
        phone.add_init_script(f"localStorage.setItem('{GUIDE_KEY}', '1')")
        phone.on("console", lambda message: errors.append(f"mobile-console:{message.text}") if message.type == "error" else None)
        phone.on("pageerror", lambda error: errors.append(f"mobile-page:{error}"))
        phone.goto(f"{base_url}#/engagements", wait_until="domcontentloaded")
        wait_for_app(phone)
        phone.get_by_role("heading", name="Run a mission. See what AEGIS produces.", level=1).wait_for()
        phone.get_by_role("button", name="Continue to safe intake").click()
        phone.get_by_role("button", name="Add prepared sample inputs").click()
        phone.get_by_role("button", name="Begin seven-team simulation").click()
        phone.get_by_role("heading", name="Mission results are ready to use.", level=2).wait_for(timeout=6_000)
        assert phone.get_by_role("link", name="Export report").is_visible()
        assert_no_horizontal_clip(phone, "mobile public journey")
        phone.screenshot(path=ARTIFACTS / "interactive-showcase-mobile.png", full_page=False)
        mobile.close()

        browser.close()
        assert not writes, "Public mission made network mutation requests: " + " | ".join(writes)
        assert not errors, "Browser errors: " + " | ".join(errors)


def main() -> int:
    profile = MISSION_ROOT / "web" / "dist" / "aegis-build-profile.txt"
    assert profile.is_file() and profile.read_text(encoding="utf-8").strip() == "showcase", (
        "Run `npm run build:showcase` before the public journey regression."
    )
    port = free_port()
    base_url = f"http://127.0.0.1:{port}/"
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(prefix="aegis-showcase-journey-", ignore_cleanup_errors=True) as temp_dir:
        log_path = Path(temp_dir) / "server.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            server = subprocess.Popen(
                [sys.executable, "server.py", "--port", str(port), "--mode", "demo"],
                cwd=MISSION_ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creation_flags,
            )
            try:
                wait_for_health(base_url, server, log_path)
                run_journey(base_url)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)

    for result in (
        "SHOWCASE_GUIDED_WORKFLOW=PASS",
        "SHOWCASE_BROWSER_ONLY_INTAKE=PASS",
        "SHOWCASE_SEVEN_TEAM_PROCESSING=PASS",
        "SHOWCASE_RERUN_COMPARISON=PASS",
        "SHOWCASE_EXPORT_DOWNLOAD=PASS",
        "SHOWCASE_ZERO_NETWORK_MUTATIONS=PASS",
        "SHOWCASE_RESPONSIVE_JOURNEY=PASS",
    ):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
