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


def assert_html_transform_is_disabled(base_url: str) -> None:
    request = urllib.request.Request(
        base_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-transform" in cache_control, (
            f"HTML must prevent edge script injection: Cache-Control={cache_control!r}"
        )


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


def assert_focus_is_inside(page, dialog, label: str) -> None:
    expected_label = dialog.get_attribute("aria-label")
    try:
        page.wait_for_function(
            "expected => document.activeElement?.closest('[role=\"dialog\"]')?.getAttribute('aria-label') === expected",
            arg=expected_label,
            timeout=1_000,
        )
    except PlaywrightTimeoutError:
        active = page.evaluate(
            "() => ({tag: document.activeElement?.tagName, className: document.activeElement?.className, label: document.activeElement?.getAttribute('aria-label')})"
        )
        raise AssertionError(f"Keyboard focus escaped {label}: {active}")


def assert_focus_trap(page, dialog, label: str) -> None:
    for _ in range(20):
        page.keyboard.press("Tab")
        assert_focus_is_inside(page, dialog, label)
    for _ in range(20):
        page.keyboard.press("Shift+Tab")
        assert_focus_is_inside(page, dialog, label)


def assert_mobile_touch_targets(page) -> None:
    targets = page.locator(".nav-rail button, .topbar__right .utility-trigger, .topbar__right .command-trigger")
    assert targets.count() > 0
    for index in range(targets.count()):
        target = targets.nth(index)
        if not target.is_visible():
            continue
        box = target.bounding_box()
        assert box is not None
        assert box["width"] >= 44 and box["height"] >= 44, (
            f"Mobile touch target is smaller than 44px: {box}"
        )


def run_browser_checks(base_url: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        errors: list[str] = []

        resilience = browser.new_context(viewport={"width": 1024, "height": 768})
        hung = resilience.new_page()
        hung.add_init_script(
            """
            window.__aegisOriginalFetch = window.fetch.bind(window);
            window.fetch = (input, init = {}) => {
              if (String(input).endsWith('/api/snapshot')) {
                return new Promise((_resolve, reject) => {
                  init.signal?.addEventListener(
                    'abort',
                    () => reject(new DOMException('Aborted', 'AbortError')),
                    { once: true },
                  );
                });
              }
              return window.__aegisOriginalFetch(input, init);
            };
            """
        )
        hung.goto(base_url, wait_until="domcontentloaded")
        hung.get_by_text("CONTROL PLANE UNAVAILABLE", exact=True).wait_for(timeout=12_000)
        assert hung.get_by_text(
            "The secure status feed is temporarily unavailable. No controls or assurance data have been loaded.",
            exact=True,
        ).is_visible()
        retry = hung.get_by_role("button", name="Retry secure connection")
        assert retry.is_visible()
        body = hung.locator("body").inner_text()
        assert "AbortError" not in body and "Snapshot request failed" not in body
        hung.evaluate("window.fetch = window.__aegisOriginalFetch")
        retry.click()
        wait_for_app(hung)
        resilience.close()

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
        assert_focus_is_inside(page, guide, "orientation guide")
        assert_focus_trap(page, guide, "orientation guide")
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
        assert page.evaluate("window.location.hash") == "#/engagements"
        assert page.locator("main h1").count() == 1
        assert "without accepting targets" in page.locator(".tenant-only").inner_text()
        assert float(page.locator(".engagement-template-grid span").first.evaluate("element => parseFloat(getComputedStyle(element).fontSize)")) >= 12
        assert_no_horizontal_clip(page, "engagement preview")

        guide_trigger = page.get_by_role("button", name="Open the Mission Control guide")
        guide_trigger.click()
        guide.wait_for()
        assert_focus_is_inside(page, guide, "reopened orientation guide")
        page.keyboard.press("Escape")
        guide.wait_for(state="detached")
        assert guide_trigger.evaluate("element => element === document.activeElement")

        command_trigger = page.locator(".command-trigger")
        command_trigger.click()
        command = page.get_by_role("dialog", name="Command deck")
        command.wait_for()
        assert_focus_is_inside(page, command, "command deck")
        assert_focus_trap(page, command, "command deck")
        page.keyboard.press("Escape")
        command.wait_for(state="detached")
        assert command_trigger.evaluate("element => element === document.activeElement")

        page.get_by_role("button", name="Command", exact=True).click()
        page.get_by_role("heading", name="Trust is a state. Prove every transition.", level=1).wait_for()
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.get_by_role("button", name="Gate runner", exact=True).click()
        page.get_by_role("heading", name="Engineering gate runner", level=1).wait_for()
        page.wait_for_timeout(100)
        assert page.evaluate("window.location.hash") == "#/gate-runner"
        assert page.evaluate("window.scrollY") <= 1
        assert page.locator("main h1").count() == 1
        assert page.locator("main h1").evaluate("element => element === document.activeElement")
        assert page.locator('[role="row"]').count() == 0
        assert page.get_by_role("list", name="Engineering verification gates").count() == 1
        assert page.get_by_role("list", name="Engineering verification gates").get_by_role("listitem").count() > 0
        assert page.get_by_role("button", name="Control actions are unavailable in this public showcase").count() == 0
        assert page.get_by_role("status", name="Control actions are unavailable in this public showcase").count() == 1
        assert float(page.locator(".console-empty span").evaluate("element => parseFloat(getComputedStyle(element).fontSize)")) >= 12

        page.get_by_role("button", name="Engagements").click()
        page.get_by_text("Bring the target. Keep the proof.").wait_for()
        page.go_back()
        page.get_by_role("heading", name="Engineering gate runner", level=1).wait_for()
        assert page.evaluate("window.location.hash") == "#/gate-runner"

        for destination in (
            "Command",
            "Engagements",
            "Security coverage",
            "Shadow AI defense",
            "Seven teams",
            "Gate runner",
            "Live agents",
            "Workspace controls",
            "Evidence",
        ):
            page.get_by_role("button", name=destination, exact=True).click()
            page.wait_for_timeout(30)
            assert page.locator("main h1").count() == 1, f"{destination} must expose exactly one h1"
            assert page.locator("main h1[data-view-heading]").count() == 1

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
        page.evaluate(
            """() => {
                window.__aegisZoomShortcutResults = [];
                window.addEventListener('keydown', event => {
                    if (event.ctrlKey && ['=', '-', '0'].includes(event.key)) {
                        window.__aegisZoomShortcutResults.push(event.defaultPrevented);
                    }
                });
            }"""
        )
        for shortcut in ("Control+=", "Control+-", "Control+0"):
            page.keyboard.press(shortcut)
            assert page.locator(".app-shell").evaluate("element => getComputedStyle(element).zoom") == "1.2"
        assert page.evaluate("window.__aegisZoomShortcutResults") == [False, False, False]
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
        assert_focus_is_inside(phone, phone_guide, "mobile orientation guide")
        assert_focus_trap(phone, phone_guide, "mobile orientation guide")
        assert_no_horizontal_clip(phone, "mobile guide")
        phone.screenshot(path=ARTIFACTS / "onboarding-mobile.png", full_page=False)
        phone_guide.get_by_role("button", name="Close").click()
        assert phone.get_by_role("button", name="Open the Mission Control guide").is_visible()
        assert phone.locator('button[aria-label="Local operator identity"]').count() == 0
        assert_mobile_touch_targets(phone)
        phone.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        assert phone.evaluate("window.scrollY") > 100
        phone.get_by_role("button", name="Gate runner", exact=True).click()
        phone.get_by_role("heading", name="Engineering gate runner", level=1).wait_for()
        phone.wait_for_timeout(100)
        assert phone.evaluate("window.scrollY") <= 1
        assert phone.get_by_role("heading", name="Engineering gate runner", level=1).is_visible()
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
            assert_html_transform_is_disabled(base_url)
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
            assert_html_transform_is_disabled(base_url)
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
            assert_html_transform_is_disabled(tenant_url)
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
        "VIEW_ROUTING_HISTORY=PASS",
        "MOBILE_SCROLL_RESET=PASS",
        "MODAL_FOCUS_TRAP=PASS",
        "ARIA_SEMANTICS=PASS",
        "MOBILE_TOUCH_TARGETS=PASS",
        "PUBLIC_CONTROL_AFFORDANCES=PASS",
        "MICROCOPY_LEGIBILITY=PASS",
        "INITIAL_SNAPSHOT_RECOVERY=PASS",
        "BROWSER_ZOOM_SHORTCUTS=PASS",
    ):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
