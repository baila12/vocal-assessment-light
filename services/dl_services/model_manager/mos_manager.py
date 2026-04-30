"""
MOS 模型管理器

支持热切换、健康检查、优雅降级的 MOS 评估模型管理
"""
import threading
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .types import ModelStatus, ModelInfo, MOSPredictorProtocol

logger = logging.getLogger(__name__)


class MOSModelManager:
    """
    MOS模型管理器 - 支持热切换、健康检查、优雅降级

    功能：
    1. 模型注册与管理
    2. 自动健康检查
    3. 失败重试机制
    4. 优雅降级策略
    5. 运行时切换
    """

    def __init__(
        self,
        health_check_interval: int = 300,  # 5分钟
        max_failures: int = 3,
        retry_delay: int = 60
    ):
        """
        初始化模型管理器

        Args:
            health_check_interval: 健康检查间隔（秒）
            max_failures: 最大失败次数，超过则禁用
            retry_delay: 失败后重试延迟（秒）
        """
        self._models: Dict[str, Any] = {}
        self._model_info: Dict[str, ModelInfo] = {}
        self._lock = threading.RLock()
        self._health_check_interval = health_check_interval
        self._max_failures = max_failures
        self._retry_delay = retry_delay

        # 默认降级链（按优先级）
        self._fallback_chain: List[str] = []

        # 统计信息
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'fallback_requests': 0,
            'heuristic_requests': 0
        }

    def register(
        self,
        name: str,
        model: Any,
        priority: int = 10
    ) -> bool:
        """
        注册模型

        Args:
            name: 模型名称
            model: 模型实例
            priority: 优先级（数字越小优先级越高）

        Returns:
            是否注册成功
        """
        with self._lock:
            try:
                logger.info(f"[MOSModelManager] Registering model: {name}")

                self._models[name] = model
                self._model_info[name] = ModelInfo(
                    name=name,
                    status=ModelStatus.LOADING,
                    priority=priority,
                    load_time=time.time()
                )

                # 执行健康检查
                if self._health_check(name):
                    self._model_info[name].status = ModelStatus.AVAILABLE
                    logger.info(f"[MOSModelManager] Model {name} registered and healthy")
                else:
                    self._model_info[name].status = ModelStatus.FAILED
                    logger.warning(f"[MOSModelManager] Model {name} failed health check")

                # 更新降级链
                self._update_fallback_chain()

                return self._model_info[name].status == ModelStatus.AVAILABLE

            except Exception as e:
                logger.error(f"[MOSModelManager] Failed to register model {name}: {e}")
                if name in self._model_info:
                    self._model_info[name].status = ModelStatus.FAILED
                    self._model_info[name].last_error = str(e)
                return False

    def unregister(self, name: str) -> bool:
        """
        注销模型

        Args:
            name: 模型名称

        Returns:
            是否注销成功
        """
        with self._lock:
            if name in self._models:
                del self._models[name]
                del self._model_info[name]
                self._update_fallback_chain()
                logger.info(f"[MOSModelManager] Model {name} unregistered")
                return True
            return False

    def _health_check(self, name: str) -> bool:
        """
        执行模型健康检查

        Args:
            name: 模型名称

        Returns:
            是否健康
        """
        model = self._models.get(name)
        if not model:
            return False

        try:
            # 检查模型是否可用
            if hasattr(model, 'is_available') and not model.is_available:
                return False

            if hasattr(model, '_model_available') and not model._model_available:
                return False

            self._model_info[name].last_health_check = time.time()
            return True

        except Exception as e:
            logger.warning(f"[MOSModelManager] Health check failed for {name}: {e}")
            self._model_info[name].last_error = str(e)
            return False

    def _update_fallback_chain(self):
        """更新降级链（按优先级排序）"""
        available_models = [
            (name, info.priority)
            for name, info in self._model_info.items()
            if info.status == ModelStatus.AVAILABLE
        ]
        # 按优先级排序
        available_models.sort(key=lambda x: x[1])
        self._fallback_chain = [name for name, _ in available_models]
        logger.debug(f"[MOSModelManager] Fallback chain updated: {self._fallback_chain}")

    def get_available_model(self) -> Optional[tuple]:
        """
        获取可用的模型（按优先级）

        Returns:
            (模型名称, 模型实例) 或 None
        """
        with self._lock:
            for name in self._fallback_chain:
                model = self._models.get(name)
                info = self._model_info.get(name)
                if model and info and info.status == ModelStatus.AVAILABLE:
                    return name, model
            return None

    def assess_with_fallback(self, audio_path: str) -> Any:
        """
        带降级策略的评估

        Args:
            audio_path: 音频文件路径

        Returns:
            评估结果
        """
        self._stats['total_requests'] += 1

        # 尝试使用注册的模型
        model_tuple = self.get_available_model()
        if model_tuple:
            name, model = model_tuple
            try:
                result = model.predict(audio_path)
                if result and hasattr(result, 'confidence') and result.confidence > 0:
                    self._stats['successful_requests'] += 1
                    return result
                elif result and hasattr(result, 'mos_score'):
                    self._stats['successful_requests'] += 1
                    return result

                # 结果无效，记录失败
                self._record_failure(name, "Invalid result")

            except Exception as e:
                logger.warning(f"[MOSModelManager] Model {name} prediction failed: {e}")
                self._record_failure(name, str(e))

        # 所有模型都不可用，尝试降级
        self._stats['fallback_requests'] += 1

        # 检查是否有已注册但暂时失败的模型可以重试
        for name, info in self._model_info.items():
            if info.status == ModelStatus.FAILED:
                if info.failure_count < self._max_failures:
                    # 尝试恢复
                    if self._try_recover(name):
                        model = self._models.get(name)
                        if model:
                            try:
                                result = model.predict(audio_path)
                                if result:
                                    self._stats['successful_requests'] += 1
                                    return result
                            except Exception:
                                pass

        # 最终降级：启发式方法
        logger.warning("[MOSModelManager] All ML models unavailable, using heuristic fallback")
        self._stats['heuristic_requests'] += 1
        return self._heuristic_assess(audio_path)

    def _record_failure(self, name: str, error: str):
        """记录模型失败"""
        with self._lock:
            if name in self._model_info:
                info = self._model_info[name]
                info.failure_count += 1
                info.last_error = error

                if info.failure_count >= self._max_failures:
                    info.status = ModelStatus.DISABLED
                    logger.warning(f"[MOSModelManager] Model {name} disabled after {info.failure_count} failures")
                    self._update_fallback_chain()

    def _try_recover(self, name: str) -> bool:
        """尝试恢复失败的模型"""
        info = self._model_info.get(name)
        if not info:
            return False

        # 检查是否过了重试延迟
        if time.time() - info.last_health_check < self._retry_delay:
            return False

        if self._health_check(name):
            info.status = ModelStatus.AVAILABLE
            info.failure_count = 0
            self._update_fallback_chain()
            logger.info(f"[MOSModelManager] Model {name} recovered")
            return True

        return False

    def _heuristic_assess(self, audio_path: str) -> Any:
        """
        启发式评估（无模型时的降级方案）

        基于音频特征推断质量
        """
        try:
            import librosa
            import numpy as np

            y, sr = librosa.load(audio_path, sr=16000)

            # 能量特征
            rms = librosa.feature.rms(y=y)[0]
            energy_mean = np.mean(rms)
            energy_std = np.std(rms)

            # 过零率
            zcr = librosa.feature.zero_crossing_rate(y=y)[0]
            zcr_mean = np.mean(zcr)

            # 频谱质心
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            brightness = np.mean(spectral_centroids)

            # 频谱平坦度
            flatness = librosa.feature.spectral_flatness(y=y)[0]
            flatness_mean = np.mean(flatness)

            # 基于特征的简单质量推断
            energy_score = min(100, energy_mean * 500)
            clarity_score = max(0, 100 - zcr_mean * 100)
            naturalness_score = max(0, 100 - abs(flatness_mean - 0.1) * 200)

            # 综合估计 MOS
            estimated_mos = 2.5 + (
                energy_score * 0.15 +
                clarity_score * 0.2 +
                naturalness_score * 0.1
            ) / 100

            estimated_mos = min(5.0, max(1.0, estimated_mos))
            mos_normalized = (estimated_mos - 1) * 25

            # 返回简单的结果对象
            @dataclass
            class HeuristicResult:
                mos_score: float
                mos_normalized: float
                naturalness: float
                clarity: float
                timbre_quality: float
                confidence: float
                method: str

            return HeuristicResult(
                mos_score=estimated_mos,
                mos_normalized=mos_normalized,
                naturalness=naturalness_score,
                clarity=clarity_score,
                timbre_quality=energy_score,
                confidence=0.3,
                method='heuristic_fallback'
            )

        except Exception as e:
            logger.error(f"[MOSModelManager] Heuristic assessment failed: {e}")

            @dataclass
            class ErrorResult:
                mos_score: float = 3.0
                mos_normalized: float = 50.0
                naturalness: float = 50.0
                clarity: float = 50.0
                timbre_quality: float = 50.0
                confidence: float = 0.1
                method: str = 'error_fallback'

            return ErrorResult()

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        with self._lock:
            return {
                'models': {
                    name: {
                        'status': info.status.name,
                        'priority': info.priority,
                        'failure_count': info.failure_count,
                        'last_error': info.last_error,
                        'last_health_check': info.last_health_check
                    }
                    for name, info in self._model_info.items()
                },
                'fallback_chain': self._fallback_chain,
                'stats': self._stats.copy()
            }

    def enable_model(self, name: str) -> bool:
        """启用模型"""
        with self._lock:
            if name in self._model_info:
                self._model_info[name].status = ModelStatus.AVAILABLE
                self._model_info[name].failure_count = 0
                self._update_fallback_chain()
                logger.info(f"[MOSModelManager] Model {name} enabled")
                return True
            return False

    def disable_model(self, name: str) -> bool:
        """禁用模型"""
        with self._lock:
            if name in self._model_info:
                self._model_info[name].status = ModelStatus.DISABLED
                self._update_fallback_chain()
                logger.info(f"[MOSModelManager] Model {name} disabled")
                return True
            return False

    def refresh_health(self) -> Dict[str, bool]:
        """刷新所有模型的健康状态"""
        results = {}
        with self._lock:
            for name in list(self._models.keys()):
                results[name] = self._health_check(name)
                if results[name]:
                    self._model_info[name].status = ModelStatus.AVAILABLE
                else:
                    self._model_info[name].status = ModelStatus.FAILED
            self._update_fallback_chain()
        return results


# 全局MOS模型管理器实例
_mos_model_manager: Optional[MOSModelManager] = None
_mos_manager_lock = threading.Lock()


def get_mos_model_manager() -> MOSModelManager:
    """获取全局MOS模型管理器实例（单例）"""
    global _mos_model_manager
    if _mos_model_manager is None:
        with _mos_manager_lock:
            if _mos_model_manager is None:
                _mos_model_manager = MOSModelManager()
    return _mos_model_manager


def reset_mos_model_manager():
    """重置MOS模型管理器（用于测试）"""
    global _mos_model_manager
    with _mos_manager_lock:
        _mos_model_manager = None
