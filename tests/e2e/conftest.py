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
TEST_MUSIC_FOLDER = PROJECT_ROOT / "test_music"
WEB_APP_SCRIPT = PROJECT_ROOT / "web_app.py"

UPLOAD_FOLDER.mkdir(exist_ok=True)
TEST_MUSIC_FOLDER.mkdir(exist_ok=True)

BACKEND_URL = "http://127.0.0.1:5000"


@pytest.fixture(scope="session", autouse=True)
def backend_server():
    """启动 Flask 后端服务器"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()

    if result == 0:
        print("\n[INFO] Flask 服务器已在运行")
        yield
        return

    print("\n[INFO] 启动 Flask 服务器...")
    process = subprocess.Popen(
        [sys.executable, str(WEB_APP_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, 'FLASK_ENV': 'testing'}
    )

    max_wait = 30
    for i in range(max_wait):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sock.connect_ex(('localhost', 5000)) == 0:
                sock.close()
                print(f"[INFO] Flask 服务器启动成功 (等待 {i+1} 秒)")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        stdout, stderr = process.communicate(timeout=1)
        print(f"[ERROR] stdout: {stdout.decode('utf-8', errors='ignore')}")
        print(f"[ERROR] stderr: {stderr.decode('utf-8', errors='ignore')}")
        process.kill()
        raise RuntimeError("Flask 服务器启动超时")

    yield

    print("\n[INFO] 关闭 Flask 服务器...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture
def create_test_audio() -> Path:
    """创建测试音频文件（简单的正弦波）"""
    import numpy as np
    import wave

    test_file = TEST_MUSIC_FOLDER / "test_e2e_audio.wav"

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
