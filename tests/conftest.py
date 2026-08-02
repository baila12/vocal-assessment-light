"""
声乐评估系统测试根配置 — v7.3

环境隔离: VAS_SKIP_GPU=1 防止 pytest 进程中 PyTorch C 扩展冲突
Playwright fixtures 仅 E2E 测试时加载
"""

import os
import pytest


def pytest_configure(config):
    """pytest 启动最早时机 — 在任何测试模块 import 前设置环境变量"""
    os.environ.setdefault("VAS_SKIP_GPU", "1")
    os.environ.setdefault("VAS_DISABLE_RATE_LIMIT", "1")
    # v7.7: 防止 numpy MKL + librosa + torch 线程冲突导致 Fatal Python error
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")


# ---- Playwright E2E fixtures (lazy import 避免单元测试加载 playwright) ----

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """浏览器启动参数"""
    return {
        "headless": True,
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
    """浏览器实例 - session 级别 (lazy import playwright)"""
    from playwright.sync_api import sync_playwright
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
