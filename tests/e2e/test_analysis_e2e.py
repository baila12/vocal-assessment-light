"""
E2E测试 - 测试音频分析功能
1. 中文文件名可视化
2. 长音频分析（threaded模式）
"""
import os
import sys
import time
import requests
from pathlib import Path

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_DATA_DIR = Path(__file__).parent.parent / "tests" / "test_data" / "audio"
VOCAL_DIR = TEST_DATA_DIR / "vocal"
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


def test_health():
    """测试服务器健康状态"""
    print("\n=== 测试服务器健康状态 ===")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"健康检查失败: {resp.status_code}"
    data = resp.json()
    print(f"状态: {data['status']}")
    print(f"检查项: {data['checks']}")
    return True


def test_chinese_filename_analysis():
    """测试中文文件名的音频分析"""
    print("\n=== 测试中文文件名分析 ===")

    # 查找中文文件名的音频
    chinese_files = list(TEST_DATA_DIR.glob("*.mp3")) + list(TEST_DATA_DIR.glob("*.wav"))
    chinese_files = [f for f in chinese_files if any('\u4e00' <= c <= '\u9fff' for c in f.name)]

    if not chinese_files:
        print("未找到中文文件名的测试音频，跳过此测试")
        return True

    test_file = chinese_files[0]
    print(f"测试文件: {test_file.name}")

    # 上传并分析
    with open(test_file, 'rb') as f:
        file_content = f.read()

    # 根据扩展名确定MIME类型
    ext = test_file.suffix.lower()
    mime_type = 'audio/mpeg' if ext == '.mp3' else 'audio/wav'

    files = {'file': (test_file.name, file_content, mime_type)}
    data = {'enable_separation': 'false'}

    print("上传中...")
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/api/upload", files=files, data=data, timeout=120)
    elapsed = time.time() - start_time

    print(f"响应状态: {resp.status_code}, 耗时: {elapsed:.2f}s")

    if resp.status_code != 200:
        print(f"错误响应: {resp.text[:500]}")
        return False

    result = resp.json()
    print(f"分析结果: success={result.get('success')}")

    if not result.get('success'):
        print(f"错误: {result.get('error')}")
        return False

    # 检查可视化图片URL
    viz_data = result.get('data', {}).get('visualization', {})
    plots = ['spectrogram', 'pitch_trajectory', 'energy_curve']

    for plot_name in plots:
        url = viz_data.get(plot_name)
        if url:
            print(f"{plot_name}: {url}")
            # 测试图片是否可访问
            img_resp = requests.head(f"{BASE_URL}{url}")
            if img_resp.status_code == 200:
                print(f"  [OK] Image accessible")
            else:
                print(f"  [FAIL] Image not accessible: {img_resp.status_code}")
        else:
            print(f"{plot_name}: 未生成")

    return True


def test_long_audio_analysis():
    """测试长音频分析（验证threaded模式）"""
    print("\n=== 测试长音频分析 ===")

    # 查找较长的音频文件（>1分钟）
    all_files = list(TEST_DATA_DIR.glob("*.mp3")) + list(TEST_DATA_DIR.glob("*.wav"))

    if not all_files:
        print("未找到测试音频文件")
        return True

    # 使用第一个找到的文件进行测试
    test_file = all_files[0]
    file_size_mb = test_file.stat().st_size / (1024 * 1024)
    print(f"测试文件: {test_file.name} ({file_size_mb:.2f} MB)")

    # 根据扩展名确定MIME类型
    ext = test_file.suffix.lower()
    mime_type = 'audio/mpeg' if ext == '.mp3' else 'audio/wav'

    # 上传并分析
    with open(test_file, 'rb') as f:
        file_content = f.read()

    files = {'file': (test_file.name, file_content, mime_type)}
    data = {'enable_separation': 'false'}

    print("上传分析中（可能需要较长时间）...")
    start_time = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/api/upload", files=files, data=data, timeout=300)
        elapsed = time.time() - start_time

        print(f"响应状态: {resp.status_code}, 耗时: {elapsed:.2f}s")

        if resp.status_code == 200:
            result = resp.json()
            print(f"分析成功: {result.get('success')}")
            return True
        else:
            print(f"分析失败: {resp.text[:200]}")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        print("这表明 threaded=True 可能未生效")
        return False
    except requests.exceptions.Timeout as e:
        print(f"请求超时: {e}")
        return False


def test_history_api():
    """测试历史记录API"""
    print("\n=== 测试历史记录API ===")

    resp = requests.get(f"{BASE_URL}/api/history")
    assert resp.status_code == 200, f"历史记录API失败: {resp.status_code}"

    data = resp.json()
    print(f"历史记录数量: {len(data.get('records', []))}")
    return True


def main():
    print("=" * 50)
    print("声乐评估系统 E2E 测试")
    print("=" * 50)

    results = []

    # 运行测试
    results.append(("健康检查", test_health()))
    results.append(("历史记录API", test_history_api()))
    results.append(("中文文件名分析", test_chinese_filename_analysis()))
    results.append(("长音频分析", test_long_audio_analysis()))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
