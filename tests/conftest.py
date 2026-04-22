"""
声乐评估系统 E2E 测试 - Playwright 配置
提供 pytest fixtures 用于浏览器测试
"""
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """浏览器启动参数"""
    return {
        "headless": True,  # 无头模式，避免浏览器连接问题
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """浏览器上下文参数"""
    return {
        "viewport": {"width": 1280, "height": 720},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }


@pytest.fixture(scope="session")
def browser(browser_type_launch_args):
    """浏览器实例 - session 级别"""
    with sync_playwright() as p:
        browser = p.chromium.launch(**browser_type_launch_args)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser, browser_context_args):
    """为每个测试创建新页面"""
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
