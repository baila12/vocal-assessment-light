"""
声乐评估系统 - 测试验证脚本
测试内容:
1. 音频加载异步是否正常
2. 评估流程是否完整
3. 五维评分计算是否正确
4. 情绪模型是否能正确加载
5. UI组件是否能正常显示
"""

import unittest
import sys
import os
import numpy as np
import tempfile
import wave
import struct
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestAudioAsyncLoading(unittest.TestCase):
    """测试音频异步加载功能"""

    @classmethod
    def setUpClass(cls):
        """创建测试用的音频文件"""
        cls.test_audio_path = tempfile.mktemp(suffix='.wav')
        cls._create_test_audio(cls.test_audio_path, duration=2.0)

    @classmethod
    def tearDownClass(cls):
        """清理测试文件"""
        if os.path.exists(cls.test_audio_path):
            os.remove(cls.test_audio_path)

    @staticmethod
    def _create_test_audio(filepath: str, duration: float = 2.0, sample_rate: int = 22050):
        """创建测试音频文件"""
        num_samples = int(duration * sample_rate)
        frequency = 440.0  # A4 note

        # 生成正弦波
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            sample = np.sin(2 * np.pi * frequency * t) * 0.5
            samples.append(sample)

        samples = np.array(samples)

        # 写入WAV文件
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            # 转换为16位整数
            samples_int = (samples * 32767).astype(np.int16)
            wav_file.writeframes(samples_int.tobytes())

    def test_01_audio_analyzer_basic(self):
        """测试音频分析器基本功能"""
        from core.audio_analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        result = analyzer.analyze(self.test_audio_path)

        self.assertTrue(result['valid'], "音频分析应该成功")
        self.assertIsNotNone(result['basic_info'], "应该返回基本信息")
        self.assertIsNotNone(result['technical_params'], "应该返回技术参数")
        self.assertIsNotNone(result['volume_info'], "应该返回音量信息")
        self.assertIsNotNone(result['pitch_stats'], "应该返回音高统计")

        # 验证基本信息
        basic = result['basic_info']
        self.assertEqual(basic['format'], 'WAV', "格式应该是WAV")
        self.assertTrue(basic['size_mb'] > 0, "文件大小应该大于0")

        print("[PASS] 音频分析器基本功能测试通过")

    def test_02_audio_analyzer_display_info(self):
        """测试音频分析器显示信息格式化"""
        from core.audio_analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        display_info = analyzer.get_display_info(self.test_audio_path)

        self.assertNotIn('error', display_info, "不应该返回错误")
        self.assertIn('filename', display_info, "应该包含文件名")
        self.assertIn('duration', display_info, "应该包含时长")
        self.assertIn('sample_rate', display_info, "应该包含采样率")

        print("[PASS] 音频分析器显示信息测试通过")

    def test_03_audio_loader_signals(self):
        """测试音频加载任务的信号机制"""
        from core.workers import AudioLoadTask, WorkerSignals

        task = AudioLoadTask(self.test_audio_path)

        # 验证信号存在
        self.assertIsInstance(task.signals, WorkerSignals, "应该有信号对象")
        self.assertTrue(hasattr(task.signals, 'started'), "应该有started信号")
        self.assertTrue(hasattr(task.signals, 'progress'), "应该有progress信号")
        self.assertTrue(hasattr(task.signals, 'finished'), "应该有finished信号")
        self.assertTrue(hasattr(task.signals, 'error'), "应该有error信号")

        print("[PASS] 音频加载任务信号机制测试通过")

    def test_04_audio_cache_mechanism(self):
        """测试音频缓存机制"""
        from core.workers import _get_cached_audio, _cache_audio

        # 测试空缓存
        cached = _get_cached_audio(self.test_audio_path)
        self.assertIsNone(cached, "未缓存的文件应该返回None")

        # 模拟缓存数据
        mock_audio = np.zeros(1000)
        mock_sr = 22050
        _cache_audio(self.test_audio_path, mock_audio, mock_sr)

        # 测试缓存获取
        cached = _get_cached_audio(self.test_audio_path)
        self.assertIsNotNone(cached, "应该能从缓存获取")
        self.assertEqual(len(cached), 2, "缓存应该返回音频数据和采样率")

        print("[PASS] 音频缓存机制测试通过")


class TestScoringCalculation(unittest.TestCase):
    """测试五维评分计算"""

    def test_01_score_bounds(self):
        """测试评分边界值"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()

        # 测试正常数据
        pitch_data = {'frequencies': np.array([440.0, 441.0, 439.0, 442.0])}
        rhythm_data = {'stability': 0.8}
        technique_data = {'vibrato': {'count': 5, 'rate': 5.5}}
        emotion_data = {'confidence': 0.75}
        audio_data = np.ones(22050) * 0.3  # 1秒音频，适中音量

        scores = processor.calculate_scores(pitch_data, rhythm_data,
                                            technique_data, emotion_data)

        # 验证所有分数在0-100范围内
        for key in ['volume', 'pitch', 'rhythm', 'breath', 'emotion']:
            self.assertIn(key, scores, f"应该包含{key}分数")
            self.assertGreaterEqual(scores[key], 0, f"{key}分数应该>=0")
            self.assertLessEqual(scores[key], 100, f"{key}分数应该<=100")

        print("[PASS] 评分边界值测试通过")

    def test_02_empty_pitch_data(self):
        """测试空音高数据时的评分"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()

        pitch_data = {'frequencies': np.array([])}
        rhythm_data = {'stability': 0.5}
        technique_data = {'vibrato': {'count': 0, 'rate': 0}}
        emotion_data = {'confidence': 0.5}
        audio_data = np.zeros(22050)

        scores = processor.calculate_scores(pitch_data, rhythm_data,
                                            technique_data, emotion_data)

        # 空数据时应该有默认分数
        self.assertEqual(scores['pitch'], 50, "空音高数据应该返回默认分数50")

        print("[PASS] 空音高数据评分测试通过")

    def test_03_score_panel_update(self):
        """测试评分面板更新"""
        from PySide6.QtWidgets import QApplication
        from widgets.score_panel import ScorePanel

        # 需要Qt应用实例
        if not QApplication.instance():
            app = QApplication(sys.argv)

        panel = ScorePanel()

        # 测试更新分数
        test_scores = {
            'volume': 85,
            'pitch': 78,
            'rhythm': 92,
            'breath': 70,
            'emotion': 88
        }

        panel.update_scores(test_scores)

        # 验证总分计算
        expected_avg = sum(test_scores.values()) / len(test_scores)
        self.assertEqual(panel.total_score_label.text(), f"{expected_avg:.1f}")

        # 验证各维度分数
        for key, value in test_scores.items():
            label = panel.score_labels.get(key)
            if label:
                self.assertEqual(label.text(), str(value))

        print("[PASS] 评分面板更新测试通过")

    def test_04_advice_generation(self):
        """测试改进建议生成"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()

        # 测试低分情况
        low_scores = {
            'volume': 60,
            'pitch': 55,
            'rhythm': 50,
            'breath': 45,
            'emotion': 40
        }

        advice = processor._generate_advice(low_scores)
        self.assertIn("音准", advice, "应该包含音准建议")
        self.assertIn("节奏", advice, "应该包含节奏建议")

        # 测试高分情况
        high_scores = {
            'volume': 90,
            'pitch': 95,
            'rhythm': 88,
            'breath': 92,
            'emotion': 85
        }

        advice = processor._generate_advice(high_scores)
        self.assertIn("整体表现良好", advice, "高分应该有正面反馈")

        print("[PASS] 改进建议生成测试通过")


class TestEmotionModel(unittest.TestCase):
    """测试情绪模型加载"""

    def test_01_model_path_exists(self):
        """测试模型路径配置"""
        from core.workers import EMOTION_MODEL_PATH

        self.assertIsNotNone(EMOTION_MODEL_PATH, "模型路径应该已配置")
        self.assertIsInstance(EMOTION_MODEL_PATH, str, "模型路径应该是字符串")
        print(f"[INFO] 情绪模型路径: {EMOTION_MODEL_PATH}")

    def test_02_emotion_labels_defined(self):
        """测试情绪标签定义"""
        from core.workers import _emotion_labels

        self.assertIsInstance(_emotion_labels, list, "情绪标签应该是列表")
        self.assertGreater(len(_emotion_labels), 0, "应该至少有一种情绪标签")
        print(f"[INFO] 情绪标签: {_emotion_labels}")

    def test_03_preload_function_exists(self):
        """测试预加载函数存在"""
        from core.workers import preload_emotion_model

        self.assertTrue(callable(preload_emotion_model), "预加载函数应该可调用")

        # 测试调用（可能失败如果模型不存在，但不应抛出异常）
        try:
            result = preload_emotion_model()
            print(f"[INFO] 模型预加载结果: {result}")
        except Exception as e:
            print(f"[WARN] 模型预加载失败（可能模型不存在）: {e}")

        print("[PASS] 预加载函数存在测试通过")

    def test_04_fallback_emotion_analysis(self):
        """测试备用情绪分析"""
        from core.workers import AssessmentTask

        task = AssessmentTask.__new__(AssessmentTask)

        # 创建测试音频数据
        sample_rate = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t) * 0.5

        result = task._fallback_emotion_analysis(audio, sample_rate)

        self.assertIn('dominant', result, "应该返回主导情绪")
        self.assertIn('confidence', result, "应该返回置信度")
        self.assertIn('scores', result, "应该返回情绪分数")

        # 验证情绪类型
        self.assertIn(result['dominant'], ['happy', 'sad', 'angry', 'neutral', 'surprised'])

        print("[PASS] 备用情绪分析测试通过")


class TestUIComponents(unittest.TestCase):
    """测试UI组件"""

    @classmethod
    def setUpClass(cls):
        """创建Qt应用实例"""
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_01_score_panel_creation(self):
        """测试评分面板创建"""
        from widgets.score_panel import ScorePanel

        panel = ScorePanel()
        self.assertIsNotNone(panel, "评分面板应该成功创建")
        self.assertEqual(len(panel.DIMENSIONS), 5, "应该有五个维度")

        # 验证维度定义
        expected_keys = {'volume', 'pitch', 'rhythm', 'breath', 'emotion'}
        actual_keys = {dim['key'] for dim in panel.DIMENSIONS}
        self.assertEqual(expected_keys, actual_keys, "维度键应该匹配")

        print("[PASS] 评分面板创建测试通过")

    def test_02_score_panel_clear(self):
        """测试评分面板清除功能"""
        from widgets.score_panel import ScorePanel

        panel = ScorePanel()

        # 先设置一些分数
        test_scores = {'volume': 80, 'pitch': 75, 'rhythm': 90}
        panel.update_scores(test_scores)
        self.assertNotEqual(panel.total_score_label.text(), "--")

        # 清除
        panel.clear()
        self.assertEqual(panel.total_score_label.text(), "--")
        self.assertEqual(len(panel._scores), 0, "分数应该被清除")

        print("[PASS] 评分面板清除测试通过")

    def test_03_radar_chart_creation(self):
        """测试雷达图创建"""
        from widgets.radar_chart import RadarChart

        radar = RadarChart()
        self.assertIsNotNone(radar, "雷达图应该成功创建")

        # 测试更新分数
        scores = {'volume': 80, 'pitch': 75, 'rhythm': 90, 'breath': 85, 'emotion': 70}
        radar.update_scores(scores)

        print("[PASS] 雷达图创建测试通过")

    def test_04_audio_info_card_creation(self):
        """测试音频信息卡片创建"""
        from widgets.audio_info_card import AudioInfoCard

        card = AudioInfoCard()
        self.assertIsNotNone(card, "音频信息卡片应该成功创建")

        print("[PASS] 音频信息卡片创建测试通过")

    def test_05_loading_overlay_creation(self):
        """测试加载遮罩创建"""
        from widgets.loading_overlay import LoadingOverlay

        overlay = LoadingOverlay(None)
        self.assertIsNotNone(overlay, "加载遮罩应该成功创建")

        print("[PASS] 加载遮罩创建测试通过")


class TestAssessmentWorkflow(unittest.TestCase):
    """测试完整评估流程"""

    @classmethod
    def setUpClass(cls):
        """创建测试音频"""
        cls.test_audio_path = tempfile.mktemp(suffix='.wav')

        # 创建测试音频
        sample_rate = 22050
        duration = 2.0
        num_samples = int(duration * sample_rate)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # 添加一些颤音效果
            freq = 440 + 10 * np.sin(2 * np.pi * 5 * t)  # 5Hz颤音
            sample = np.sin(2 * np.pi * freq * t) * 0.5
            samples.append(sample)

        samples = np.array(samples)

        with wave.open(cls.test_audio_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            samples_int = (samples * 32767).astype(np.int16)
            wav_file.writeframes(samples_int.tobytes())

    @classmethod
    def tearDownClass(cls):
        """清理"""
        if os.path.exists(cls.test_audio_path):
            os.remove(cls.test_audio_path)

    def test_01_vocal_processor_load_audio(self):
        """测试人声处理器加载音频"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()
        result = processor.load_audio(self.test_audio_path)

        self.assertTrue(result, "音频加载应该成功")
        self.assertIsNotNone(processor.audio_data, "音频数据应该已加载")
        self.assertIsNotNone(processor.sample_rate, "采样率应该已设置")

        print("[PASS] 人声处理器加载音频测试通过")

    def test_02_vocal_processor_separate_vocals(self):
        """测试人声分离"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()
        processor.load_audio(self.test_audio_path)

        vocal = processor.separate_vocals()
        self.assertIsNotNone(vocal, "人声分离应该返回数据")
        self.assertEqual(len(vocal), len(processor.audio_data), "人声长度应该与原始音频相同")

        print("[PASS] 人声分离测试通过")

    def test_03_vocal_processor_detect_pitch(self):
        """测试音高检测"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()
        processor.load_audio(self.test_audio_path)
        processor.separate_vocals()

        times, frequencies = processor.detect_pitch()

        self.assertIsNotNone(times, "应该返回时间数组")
        self.assertIsNotNone(frequencies, "应该返回频率数组")
        self.assertEqual(len(times), len(frequencies), "时间和频率数组长度应该相同")

        print("[PASS] 音高检测测试通过")

    def test_04_vocal_processor_analyze_rhythm(self):
        """测试节奏分析"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()
        processor.load_audio(self.test_audio_path)
        processor.separate_vocals()

        rhythm = processor.analyze_rhythm()

        self.assertIn('bpm', rhythm, "应该包含BPM")
        self.assertIn('stability', rhythm, "应该包含稳定性")
        self.assertIn('beat_frames', rhythm, "应该包含节拍帧")

        print("[PASS] 节奏分析测试通过")

    def test_05_vocal_processor_full_process(self):
        """测试完整处理流程"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()
        result = processor.process(self.test_audio_path)

        self.assertIn('scores', result, "应该包含评分")
        self.assertIn('pitch', result, "应该包含音高数据")
        self.assertIn('rhythm', result, "应该包含节奏数据")
        self.assertIn('technique', result, "应该包含技巧数据")
        self.assertIn('emotion', result, "应该包含情绪数据")
        self.assertIn('advice', result, "应该包含建议")

        # 验证五维评分
        scores = result['scores']
        self.assertEqual(len(scores), 5, "应该有五个维度的评分")

        print("[PASS] 完整处理流程测试通过")


class TestEdgeCases(unittest.TestCase):
    """测试边界情况和异常处理"""

    def test_01_invalid_audio_file(self):
        """测试无效音频文件处理"""
        from core.audio_analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()

        # 测试不存在的文件
        result = analyzer.analyze("/nonexistent/file.wav")
        self.assertFalse(result['valid'], "无效文件应该返回valid=False")
        self.assertIsNotNone(result['error'], "应该返回错误信息")

        print("[PASS] 无效音频文件处理测试通过")

    def test_02_empty_audio_data(self):
        """测试空音频数据处理"""
        from core.audio_analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()

        # 手动设置空数据
        analyzer.audio_data = None
        analyzer.sample_rate = None

        volume_info = analyzer._get_volume_info()
        self.assertEqual(volume_info['avg_db'], -80, "空数据应该返回-80 dB")

        pitch_stats = analyzer._get_pitch_stats()
        self.assertEqual(pitch_stats['valid_frames'], 0, "空数据应该有0有效帧")

        print("[PASS] 空音频数据处理测试通过")

    def test_03_score_calculation_edge_cases(self):
        """测试评分计算边界情况"""
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()

        # 测试空频率数组
        pitch_data = {'frequencies': np.array([np.nan, np.nan, np.nan])}
        rhythm_data = {'stability': 0}
        technique_data = {'vibrato': {'count': 0, 'rate': 0}}
        emotion_data = {'confidence': 0}
        audio_data = np.zeros(1000)

        scores = processor.calculate_scores(pitch_data, rhythm_data,
                                            technique_data, emotion_data)

        # 验证分数在有效范围内
        for key, value in scores.items():
            self.assertGreaterEqual(value, 0, f"{key}应该>=0")
            self.assertLessEqual(value, 100, f"{key}应该<=100")

        print("[PASS] 评分计算边界情况测试通过")


class TestPerformance(unittest.TestCase):
    """性能测试"""

    @classmethod
    def setUpClass(cls):
        """创建较长的测试音频"""
        cls.test_audio_path = tempfile.mktemp(suffix='.wav')

        sample_rate = 22050
        duration = 5.0  # 5秒音频
        num_samples = int(duration * sample_rate)

        samples = np.random.randn(num_samples) * 0.3

        with wave.open(cls.test_audio_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            samples_int = (samples * 32767).astype(np.int16)
            wav_file.writeframes(samples_int.tobytes())

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_audio_path):
            os.remove(cls.test_audio_path)

    def test_01_processing_speed(self):
        """测试处理速度"""
        import time
        from core.vocal_processor import VocalProcessor

        processor = VocalProcessor()

        start_time = time.time()
        result = processor.process(self.test_audio_path)
        elapsed = time.time() - start_time

        print(f"[INFO] 5秒音频处理耗时: {elapsed:.2f}秒")
        self.assertLess(elapsed, 30, "处理5秒音频应该在30秒内完成")

        print("[PASS] 处理速度测试通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("声乐评估系统 - 测试验证")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAudioAsyncLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestScoringCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestEmotionModel))
    suite.addTests(loader.loadTestsFromTestCase(TestUIComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestAssessmentWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[OK] 所有测试通过！")
        return 0
    else:
        print("\n[FAIL] 部分测试未通过")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
