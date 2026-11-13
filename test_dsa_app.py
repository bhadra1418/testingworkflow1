from pathlib import Path

from playwright.sync_api import Page

BASE_URL = "https://dev-dsaapp.basichomeloan.com"
ARTIFACTS_DIR = Path("artifacts")


def _save_failure_diagnostics(page: Page, error: Exception, diagnostics: dict) -> None:
    """Save browser state when a page assertion fails, then retain it as an artifact."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    diagnostics["failure"] = repr(error)

    try:
        diagnostics["url"] = page.url
        diagnostics["title"] = page.title()
        diagnostics["inputs"] = page.locator("input").evaluate_all(
            "inputs => inputs.map(input => ({"
            "type: input.type, placeholder: input.placeholder, "
            "ariaLabel: input.getAttribute('aria-label'), visible: "
            "Boolean(input.getClientRects().length)"
            "}))"
        )
        diagnostics["bodyText"] = page.locator("body").inner_text(timeout=3000)[:5000]
        (ARTIFACTS_DIR / "dsa-homepage-failure.html").write_text(
            page.content(), encoding="utf-8"
        )
        page.screenshot(
            path=str(ARTIFACTS_DIR / "dsa-homepage-failure.png"),
            full_page=True,
            timeout=10_000,
        )
    except Exception as diagnostic_error:
        diagnostics["diagnostic_capture_error"] = repr(diagnostic_error)

    (ARTIFACTS_DIR / "dsa-homepage-failure.txt").write_text(
        "\n".join(f"{key}: {value}" for key, value in diagnostics.items()),
        encoding="utf-8",
    )


def test_dsa_app_loads_and_css_is_available(page: Page):
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    failed_requests = []
    http_errors = []

    page.on(
        "requestfailed",
        lambda request: failed_requests.append(
            f"{request.method} {request.url} - {request.failure}"
        ),
    )
    page.on(
        "response",
        lambda response: http_errors.append(
            f"HTTP {response.status}: {response.url}"
        ) if response.status >= 400 else None,
    )

    response = page.goto(
        BASE_URL,
        wait_until="domcontentloaded",
        timeout=60_000,
    )

    assert response is not None, "Navigation did not return a response."
    assert response.status < 400, (
        f"Application returned HTTP {response.status}: {BASE_URL}"
    )

    # Some real-world pages intentionally keep the body hidden until hydration
    # completes. This test checks CSS availability, not a specific visibility state.
    body = page.locator("body")
    assert body.count() == 1, "Expected a document body element."
    page.wait_for_timeout(3000)

    stylesheets = page.locator('link[rel~="stylesheet"]').evaluate_all(
        """links => links.map(link => ({
            href: link.href,
            loaded: Boolean(link.sheet)
        }))"""
    )

    css_info = page.evaluate(
        """() => {
            const body = document.body;
            return {
                bodyExists: Boolean(body),
                bodyVisibility: body ? getComputedStyle(body).visibility : null,
                bodyDisplay: body ? getComputedStyle(body).display : null,
                stylesheetCount: document.styleSheets.length,
                bodyFontFamily: body ? getComputedStyle(body).fontFamily : '',
                bodyBackground: body ? getComputedStyle(body).backgroundColor : '',
                bodyColor: body ? getComputedStyle(body).color : ''
            };
        }"""
    )

    print("\nPage title:", page.title())
    print("Stylesheet links:", stylesheets)
    print("Computed CSS:", css_info)
    print("HTTP errors:", http_errors)
    print("Failed requests:", failed_requests)

    page.screenshot(path=str(ARTIFACTS_DIR / "dsa-homepage.png"), full_page=True)

    assert css_info["stylesheetCount"] > 0, (
        "No stylesheets detected. Check the browser Network/Console logs."
    )

    unloaded_links = [item for item in stylesheets if not item["loaded"]]
    assert not unloaded_links, (
        f"One or more linked CSS stylesheets did not load: {unloaded_links}"
    )


def test_dsa_app_homepage_screenshot(page: Page):
    """Wait for the login UI and capture diagnostics if it does not render."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    failed_requests = []
    http_errors = []
    console_errors = []
    page_errors = []
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(
            f"{request.method} {request.url} - {request.failure}"
        ),
    )
    page.on(
        "response",
        lambda response: http_errors.append(
            f"HTTP {response.status}: {response.url}"
        ) if response.status >= 400 else None,
    )
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    response = page.goto(
        BASE_URL,
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    assert response is not None, "Navigation did not return a response."
    assert response.status < 400, (
        f"Application returned HTTP {response.status}: {BASE_URL}"
    )

    mobile_input = page.get_by_placeholder("Enter your mobile number", exact=False)
    try:
        mobile_input.wait_for(state="visible", timeout=60_000)
    except Exception as error:
        _save_failure_diagnostics(
            page,
            error,
            {
                "expected_placeholder": "Enter your mobile number",
                "http_errors": http_errors,
                "failed_requests": failed_requests,
                "console_errors": console_errors,
                "page_errors": page_errors,
            },
        )
        raise

    # Allow fonts and client-side visual updates to settle before capture.
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(1000)

    screenshot_path = ARTIFACTS_DIR / "dsa-homepage-screenshot.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    assert screenshot_path.is_file(), "The homepage screenshot was not created."
    assert screenshot_path.stat().st_size > 0, "The homepage screenshot is empty."
