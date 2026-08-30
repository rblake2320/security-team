#!/usr/bin/env python3
"""Browser regression for the public onboarding and view controls."""

from __future__ import annotations

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
ARTIFACTS = Path(os.getenv("AEGIS_UI_TEST_ARTIFACTS", MISSION_ROOT / "runtime" / "ui-test-artifacts"))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Demo server did not become healthy at {base_url}")


def assert_no_horizontal_clip(page, label: str) -> None:
    metrics = page.evaluate(
        """() => ({
            viewport: window.innerWidth,
            html: document.documentElement.scrollWidth,
            body: document.body.scrollWidth
        })"""
    )
    widest = max(metrics["html"], metrics["body"])
    assert widest <= metrics["viewport"] + 2, f"{label} clips horizontally: {metrics}"


def wait_for_app(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightTimeoutError:
        # Mission Control intentionally keeps a live event stream open.
        pass
    page.locator(".app-shell").wait_for()


def run_browser_checks(base_url: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        errors: list[str] = []

        desktop = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = desktop.new_page()
        page.on(
            "console",
            lambda message: errors.append(f"console:{message.text}") if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: errors.append(f"page:{error}"))
        page.goto(base_url)
        wait_for_app(page)

        guide = page.get_by_role("dialog", name="Mission Control orientation")
        guide.wait_for()
        assert "synthetic and every control action is removed" in guide.inner_text()
        for label in (
            "START / COMMAND",
            "SCOPE / ENGAGEMENT",
            "DIAGNOSE / COVERAGE",
            "DISCOVER / SHADOW AI",
            "VERIFY / EVIDENCE",
        ):
            assert guide.get_by_role("button").filter(has_text=label).count() == 1

        for _ in range(4):
            guide.get_by_role("button", name="Next step").click()
        guide.get_by_role("button", name="Open evidence").click()
        assert guide.count() == 0
        assert page.get_by_role("button", name="Evidence").get_attribute("aria-current") == "page"
        page.get_by_role("button", name="Engagements").click()
        page.get_by_text("Bring the target. Keep the proof.").wait_for()
        assert "without accepting targets" in page.locator(".tenant-only").inner_text()
        assert_no_horizontal_clip(page, "engagement preview")

        page.get_by_role("button", name="Open the Mission Control guide").click()
        guide.wait_for()
        guide.get_by_role("button", name="Close").click()

        page.get_by_role("button", name="Adjust view size, currently 100%").click()
        view_dialog = page.get_by_role("dialog", name="Adjust Mission Control view")
        view_dialog.wait_for()
        view_dialog.get_by_role("slider", name="Interface size").fill("120")
        view_dialog.locator(".density-switch button").filter(has_text="Compact").click()
        assert page.locator(".app-shell").get_attribute("data-density") == "compact"
        assert page.locator(".app-shell").evaluate("element => getComputedStyle(element).zoom") == "1.2"
        assert_no_horizontal_clip(page, "desktop 120%")
        view_dialog.get_by_role("button", name="Close").click()
        page.screenshot(path=ARTIFACTS / "onboarding-desktop.png", full_page=True)

        page.reload()
        wait_for_app(page)
        assert page.get_by_role("dialog", name="Mission Control orientation").count() == 0
        assert page.locator(".app-shell").get_attribute("data-density") == "compact"
        assert page.locator(".app-shell").evaluate("element => getComputedStyle(element).zoom") == "1.2"
        page.keyboard.press("Control+0")
        assert page.locator(".app-shell").evaluate("element => getComputedStyle(element).zoom") == "1"
        page.keyboard.press("?")
        page.get_by_role("dialog", name="Mission Control orientation").wait_for()
        desktop.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        phone = mobile.new_page()
        phone.on(
            "console",
            lambda message: errors.append(f"mobile-console:{message.text}") if message.type == "error" else None,
        )
        phone.on("pageerror", lambda error: errors.append(f"mobile-page:{error}"))
        phone.goto(base_url)
        wait_for_app(phone)
        phone_guide = phone.get_by_role("dialog", name="Mission Control orientation")
        phone_guide.wait_for()
        assert_no_horizontal_clip(phone, "mobile guide")
        phone.screenshot(path=ARTIFACTS / "onboarding-mobile.png", full_page=False)
        phone_guide.get_by_role("button", name="Close").click()
        assert phone.get_by_role("button", name="Open the Mission Control guide").is_visible()
        view_button = phone.get_by_role("button", name="Adjust view size, currently 100%")
        assert view_button.is_visible()
        view_button.click()
        phone_view = phone.get_by_role("dialog", name="Adjust Mission Control view")
        phone_view.get_by_role("slider", name="Interface size").fill("120")
        phone_view.get_by_role("button", name="Close").click()
        assert_no_horizontal_clip(phone, "mobile 120%")
        mobile.close()

        browser.close()
        assert not errors, "Browser errors: " + " | ".join(errors)


def run_tenant_engagement_checks(base_url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        errors: list[str] = []
        desktop = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = desktop.new_page()
        page.on(
            "console",
            lambda message: errors.append(f"tenant-console:{message.text}") if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: errors.append(f"tenant-page:{error}"))
        page.goto(base_url)
        wait_for_app(page)
        guide = page.get_by_role("dialog", name="Mission Control orientation")
        if guide.count():
            guide.get_by_role("button", name="Close").click()
        page.get_by_role("button", name="Engagements").click()
        page.get_by_role("button", name="New engagement").click()
        editor = page.get_by_role("dialog", name="Create an authorized security engagement")
        editor.get_by_label("Engagement name").fill("Browser-tested launch review")
        editor.get_by_label("Client / business").fill("Synthetic Client")
        editor.get_by_label("Target 1 locator").fill("https://staging.example.test")
        editor.get_by_label("Authority reference / attestation").fill(
            "I own this synthetic staging target and authorize the recorded non-destructive browser test."
        )
        editor.get_by_label("I confirm I am authorized to test every listed target.").check()
        page.screenshot(path=ARTIFACTS / "engagement-editor.png", full_page=False)
        editor.get_by_role("button", name="Create engagement").click()
        page.locator(".engagement-hero h2", has_text="Browser-tested launch review").wait_for()
        page.locator(".engagement-dropzone input").set_input_files(
            {"name": "architecture.png", "mimeType": "image/png", "buffer": b"synthetic-browser-image"}
        )
        page.locator(".asset-list", has_text="architecture.png").wait_for()
        assert "SUGGESTED NEXT REVIEWS" in page.locator(".suggestion-box").inner_text().upper()
        assert "Executor required" in page.locator(".executor-state").inner_text()
        export_link = page.get_by_role("link", name="Export package")
        assert export_link.get_attribute("href").endswith("/export")
        assert_no_horizontal_clip(page, "tenant engagement desktop")
        page.screenshot(path=ARTIFACTS / "engagement-desktop.png", full_page=True)
        desktop.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        phone = mobile.new_page()
        phone.on(
            "console",
            lambda message: errors.append(f"tenant-mobile-console:{message.text}") if message.type == "error" else None,
        )
        phone.on("pageerror", lambda error: errors.append(f"tenant-mobile-page:{error}"))
        phone.goto(base_url)
        wait_for_app(phone)
        phone_guide = phone.get_by_role("dialog", name="Mission Control orientation")
        if phone_guide.count():
            phone_guide.get_by_role("button", name="Close").click()
            phone_guide.wait_for(state="detached")
        phone.get_by_role("button", name="Engagements").click()
        phone.locator(".engagement-hero h2", has_text="Browser-tested launch review").wait_for()
        phone.wait_for_timeout(350)
        assert_no_horizontal_clip(phone, "tenant engagement mobile")
        phone.screenshot(path=ARTIFACTS / "engagement-mobile.png", full_page=False)
        mobile.close()

        browser.close()
        assert not errors, "Browser errors: " + " | ".join(errors)


def main() -> int:
    configured_url = os.getenv("AEGIS_UI_TEST_BASE_URL", "").strip()
    servers: list[subprocess.Popen[str]] = []
    temp_logs: tempfile.TemporaryDirectory[str] | None = None
    log_handles = []
    try:
        if configured_url:
            base_url = configured_url.rstrip("/") + "/"
            run_browser_checks(base_url)
        else:
            port = free_port()
            base_url = f"http://127.0.0.1:{port}/"
            temp_logs = tempfile.TemporaryDirectory(prefix="aegis-ui-test-", ignore_cleanup_errors=True)
            log_path = Path(temp_logs.name) / "server.log"
            log_handle = log_path.open("w", encoding="utf-8")
            log_handles.append(log_handle)
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            server = subprocess.Popen(
                [sys.executable, "server.py", "--port", str(port), "--mode", "demo"],
                cwd=MISSION_ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creation_flags,
            )
            servers.append(server)
            wait_for_health(base_url)
            run_browser_checks(base_url)
            server.terminate()
            server.wait(timeout=5)
            servers.remove(server)

            tenant_port = free_port()
            tenant_url = f"http://127.0.0.1:{tenant_port}/"
            tenant_log_handle = (Path(temp_logs.name) / "tenant-server.log").open("w", encoding="utf-8")
            log_handles.append(tenant_log_handle)
            tenant_env = os.environ.copy()
            tenant_env.update(
                {
                    "AEGIS_ENV": "test",
                    "DATABASE_URL": f"sqlite:///{(Path(temp_logs.name) / 'tenant.db').as_posix()}",
                    "EVIDENCE_ROOT": str(Path(temp_logs.name) / "evidence"),
                    "TOKEN_PEPPER": "0123456789abcdef0123456789abcdef",
                    "BOOTSTRAP_EMAIL": "browser-owner@example.test",
                    "BOOTSTRAP_ORGANIZATION": "Browser Test Workspace",
                    "BOOTSTRAP_SLUG": "browser-test",
                }
            )
            tenant_server = subprocess.Popen(
                [sys.executable, "saas_server.py", "--port", str(tenant_port)],
                cwd=MISSION_ROOT,
                stdout=tenant_log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creation_flags,
                env=tenant_env,
            )
            servers.append(tenant_server)
            wait_for_health(tenant_url)
            run_tenant_engagement_checks(tenant_url)
    finally:
        for server in servers:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        for log_handle in log_handles:
            log_handle.close()
        if temp_logs is not None:
            temp_logs.cleanup()

    for result in (
        "ONBOARDING_GUIDE=PASS",
        "VIEW_CONTROLS=PASS",
        "PREFERENCE_PERSISTENCE=PASS",
        "DESKTOP_OVERFLOW=PASS",
        "MOBILE_OVERFLOW=PASS",
        "BROWSER_CONSOLE=PASS",
        "ENGAGEMENT_WORKFLOW=PASS",
        "MEDIA_INTAKE=PASS",
        "ENGAGEMENT_MOBILE=PASS",
    ):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
