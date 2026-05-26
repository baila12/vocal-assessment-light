"""
声乐评估系统 - E2E 测试共享 Fixtures

提供测试所需的共享 fixtures 和常量定义。
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from playwright.sync_api import Page

PROJECT_ROOT = Path(__file__).parent.parent.parent
UPLOAD_FOLDER = PROJECT_ROOT / "uploads"
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data" / "audio"
VOCAL_DIR = TEST_DATA_DIR / "vocal"
NON_VOCAL_DIR = TEST_DATA_DIR / "non_vocal"
# Backward compatibility alias
TEST_MUSIC_FOLDER = TEST_DATA_DIR
WEB_APP_SCRIPT = PROJECT_ROOT / "web_app.py"

UPLOAD_FOLDER.mkdir(exist_ok=True)
VOCAL_DIR.mkdir(parents=True, exist_ok=True)
NON_VOCAL_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_URL = "http://127.0.0.1:5000"

# 全局服务器进程引用
_server_process = None


def _is_server_running():
    """检查服务器是否在运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        return result == 0
    except Exception:
        return False


def _start_server():
    """启动 Flask 服务器"""
    global _server_process

    if _is_server_running():
        print("\n[INFO] Flask 服务器已在运行")
        return True

    print("\n[INFO] 启动 Flask 服务器...")
    _server_process = subprocess.Popen(
        [sys.executable, str(WEB_APP_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, 'FLASK_ENV': 'testing'}
    )

    max_wait = 90
    for i in range(max_wait):
        if _is_server_running():
            print(f"[INFO] Flask 服务器启动成功 (等待 {i+1} 秒)")
            return True
        time.sleep(1)

    # 超时处理
    if _server_process:
        stdout, stderr = _server_process.communicate(timeout=1)
        print(f"[ERROR] stdout: {stdout.decode('utf-8', errors='ignore')}")
        print(f"[ERROR] stderr: {stderr.decode('utf-8', errors='ignore')}")
        _server_process.kill()
        _server_process = None

    raise RuntimeError("Flask 服务器启动超时")


def _stop_server():
    """停止 Flask 服务器"""
    global _server_process
    if _server_process:
        print("\n[INFO] 关闭 Flask 服务器...")
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None


@pytest.fixture(scope="session", autouse=True)
def backend_server():
    """启动 Flask 后端服务器（session 作用域，整个测试会话只启动一次）"""
    _start_server()
    yield
    # 会话结束后不关闭服务器，让后续测试可以继续使用


@pytest.fixture(autouse=True)
def ensure_server_running():
    """每个测试前确保服务器在运行"""
    if not _is_server_running():
        _start_server()
    yield


@pytest.fixture
def create_test_audio() -> Path:
    """创建测试音频文件（简单的正弦波）"""
    import numpy as np
    import wave

    test_file = NON_VOCAL_DIR / "test_e2e_audio.wav"

    if test_file.exists():
        return test_file

    # 生成2秒的440Hz正弦波（模拟人声基频）
    sample_rate = 22050
    duration = 2.0
    frequency = 440

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.5).astype(np.int16)

    with wave.open(str(test_file), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    return test_file
