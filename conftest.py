import asyncio
import os
import sys
from pathlib import Path

import pytest

try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError:  # Playwright is optional for non-browser suites
    sync_playwright = None
    PlaywrightError = Exception

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault("SECRET_KEY", "pytest-secret")
os.environ.setdefault("DEBUG", "0")

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture(autouse=True)
def _configure_channel_layers(settings):
    """
    Use in-memory channel layers for websocket tests so Redis is not required.
    """
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }


@pytest.fixture
def fake_redis(monkeypatch):
    """
    Patch the module-level Redis client used by websocket helpers with a fakeredis
    instance so tests can assert persistence semantics without external services.
    """
    import app.websockets.base_consumer as base_consumer
    import fakeredis

    client = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(base_consumer, "redis_client", client)
    return client


@pytest.fixture
def channel_layer():
    """
    Provide a fresh in-memory channel layer for tests that interact with groups
    directly, ensuring isolation across test cases.
    """
    from channels.layers import InMemoryChannelLayer

    layer = InMemoryChannelLayer()
    yield layer


@pytest.fixture(scope="module")
def _playwright():
    """
    Provide a Playwright driver bound to the Edge channel for browser-based
    websocket tests. If Playwright or the Edge binary is unavailable, the
    reliant tests are skipped gracefully.
    """
    if sync_playwright is None:
        pytest.skip("Playwright is not installed. Run `python3 -m pip install playwright`.")

    previous_policy = None
    if sys.platform.startswith("win"):
        previous_policy = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        context_manager = sync_playwright()
        playwright = context_manager.__enter__()
    except (NotImplementedError, RuntimeError) as exc:
        pytest.skip(f"Playwright could not start the Edge driver: {exc}")
    try:
        yield playwright
    finally:
        context_manager.__exit__(None, None, None)
        if previous_policy is not None:
            asyncio.set_event_loop_policy(previous_policy)


@pytest.fixture(scope="module")
def playwright_browser(_playwright):
    try:
        browser = _playwright.chromium.launch(channel="msedge", headless=True)
    except PlaywrightError as exc:
        message = str(exc)
        if "Old Headless mode has been removed" in message or "Target page, context or browser has been closed" in message:
            try:
                browser = _playwright.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--headless=new"],
                )
            except PlaywrightError as second_exc:
                pytest.skip(f"Playwright Edge channel unavailable: {second_exc}")
        else:
            pytest.skip(f"Playwright Edge channel unavailable: {exc}")
    try:
        yield browser
    finally:
        browser.close()


@pytest.fixture
def edge_page(playwright_browser):
    page = playwright_browser.new_page()
    try:
        yield page
    finally:
        page.close()
