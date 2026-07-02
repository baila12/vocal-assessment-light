"""
E2E conftest — Edge browser specific fixtures.
Overrides the default chromium launch to use Edge channel.

Usage:
    pytest tests/e2e/ -c tests/e2e/conftest_edge.py --browser-channel=msedge
"""
import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override to use a larger viewport for desktop testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "zh-CN",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Launch args for Edge/chromium."""
    return {
        "headless": False,  # We want to SEE the browser for real testing
        "channel": "msedge",
        "args": [
            "--disable-web-security",  # localhost testing
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    }
