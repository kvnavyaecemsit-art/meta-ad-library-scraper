"""Drives a headless browser against the Meta Ad Library search page.

Meta serves the first page of results embedded as JSON inside a
`<script type="application/json" data-sjs>` tag on initial page load, and
every subsequent page of results as a GraphQL XHR response fired while the
page is scrolled. Both are plain JSON, so rather than parsing the rendered
DOM (whose class names are obfuscated and change often) we intercept and
parse that JSON directly. See scraper/parser.py for the extraction logic.
"""
import asyncio
import json
import logging

from playwright.async_api import async_playwright, Response

from .parser import parse_json_blob

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

COOKIE_BANNER_SELECTORS = [
    'button:has-text("Allow all cookies")',
    'button:has-text("Decline optional cookies")',
    'button[data-cookiebanner="accept_only_essential_button"]',
]


async def _dismiss_cookie_banner(page) -> None:
    for selector in COOKIE_BANNER_SELECTORS:
        try:
            await page.locator(selector).first.click(timeout=2000)
            return
        except Exception:
            continue


async def _extract_embedded_json(page) -> list[dict]:
    """Pull JSON out of every data-sjs script tag on the current page."""
    texts = await page.eval_on_selector_all(
        'script[type="application/json"]', "els => els.map(e => e.textContent)"
    )
    blobs = []
    for text in texts:
        try:
            blobs.append(json.loads(text))
        except (json.JSONDecodeError, TypeError):
            continue
    return blobs


async def scrape_ads(
    url: str,
    *,
    max_ads: int = 200,
    headless: bool = True,
    max_idle_scrolls: int = 8,
    scroll_pause_ms: int = 1500,
    nav_timeout_ms: int = 60_000,
) -> list[dict]:
    """Scrape ad records from a Meta Ad Library search URL.

    Scrolls the results feed, intercepting GraphQL responses, until either
    `max_ads` unique ads have been collected or `max_idle_scrolls`
    consecutive scrolls produce no new ads (end of results / rate limited).
    """
    seen: dict[str, dict] = {}

    def _record(records: list[dict]) -> None:
        for rec in records:
            ad_id = rec.get("ad_archive_id")
            if ad_id and ad_id not in seen:
                seen[ad_id] = rec

    async def on_response(response: Response) -> None:
        if "/api/graphql/" not in response.url:
            return
        try:
            body = await response.json()
        except Exception:
            return
        _record(parse_json_blob(body))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))

        logger.info("Navigating to %s", url)
        await page.goto(url, wait_until="networkidle", timeout=nav_timeout_ms)
        await _dismiss_cookie_banner(page)
        await page.wait_for_timeout(2000)

        for blob in await _extract_embedded_json(page):
            _record(parse_json_blob(blob))
        logger.info("Initial load: %d ads", len(seen))

        idle_scrolls = 0
        while len(seen) < max_ads and idle_scrolls < max_idle_scrolls:
            before = len(seen)
            await page.mouse.wheel(0, 6000)
            await page.wait_for_timeout(scroll_pause_ms)
            gained = len(seen) - before
            idle_scrolls = 0 if gained else idle_scrolls + 1
            logger.info(
                "Scroll: +%d ads (total %d, idle_scrolls=%d)",
                gained, len(seen), idle_scrolls,
            )

        await browser.close()

    return list(seen.values())[:max_ads]
