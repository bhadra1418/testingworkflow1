from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://dev-dsaapp.basichomeloan.com"
ARTIFACTS_DIR = Path("artifacts")


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
    assert body.count() == 1, "Expected a document body element to exist."
    page.wait_for_timeout(3000)  # Allow client-side styles/scripts to finish.

    # Inspect external stylesheets and their load state.
    stylesheets = page.locator('link[rel~="stylesheet"]').evaluate_all(
        """links => links.map(link => ({
            href: link.href,
            loaded: Boolean(link.sheet)
        }))"""
    )

    # Also inspect inline styles and computed style so apps using bundled
    # or injected styles are not incorrectly treated as unstyled.
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

    # Save useful diagnostics even when assertions fail.
    page.screenshot(path=str(ARTIFACTS_DIR / "dsa-homepage.png"), full_page=True)

    # Fail only when there is no CSS at all. A page may use inline or
    # dynamically injected styles rather than <link> stylesheet elements.
    assert css_info["stylesheetCount"] > 0, (
        "No stylesheets detected. Check the browser Network/Console logs."
    )

    unloaded_links = [item for item in stylesheets if not item["loaded"]]
    assert not unloaded_links, (
        f"One or more linked CSS stylesheets did not load: {unloaded_links}"
    )
