"""
深度学习模型管理器

管理 ONNX 模型的加载、缓存和推理
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DLModelManager:
    """
    深度学习模型管理器（单例模式）

    管理的模型：
    - voice_quality: 人声质量检测模型 (~2MB)
    - style_classifier: 唱法分类模型 (~10MB)
    v5.12: CREPE 模型配置已移除（未在评分管线中使用）
    """

    _instance = None
    _initialized = False

    # 模型配置
    MODEL_CONFIG = {
        'voice_quality': {
            'path': 'models/voice_quality/model.onnx',
            'size_mb': 2,
            'download_url': 'https://huggingface.co/your-repo/voice-quality-detector/resolve/main/model.onnx'
        },
        'style_classifier': {
            'path': 'models/style_classifier/model.onnx',
            'size_mb': 10,
            'download_url': 'https://huggingface.co/your-repo/singing-style-classifier/resolve/main/model.onnx'
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DLModelManager._initialized:
            return

        self._models: Dict[str, Any] = {}
        self._model_status: Dict[str, bool] = {}
        self._onnx_session = None

        # 尝试导入ONNX Runtime
        try:
            import onnxruntime as ort
            self._ort = ort
            logger.info("[DLModelManager] ONNX Runtime loaded successfully")
        except ImportError:
            self._ort = None
            logger.warning("[DLModelManager] ONNX Runtime not available, all models will use heuristic fallback")

        DLModelManager._initialized = True

    def is_onnx_available(self) -> bool:
        """检查ONNX Runtime是否可用"""
        return self._ort is not None

    def load_model(self, model_name: str) -> bool:
        """
        加载指定模型

        Args:
            model_name: 模型名称 (voice_quality, style_classifier, crepe)

        Returns:
            是否加载成功
        """
        if model_name in self._models:
            return self._model_status[model_name]

        if not self.is_onnx_available():
            self._model_status[model_name] = False
            return False

        config = self.MODEL_CONFIG.get(model_name)
        if not config:
            logger.error(f"[DLModelManager] Unknown model: {model_name}")
            self._model_status[model_name] = False
            return False

        model_path = config['path']

        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            logger.warning(f"[DLModelManager] Model file not found: {model_path}")
            self._model_status[model_name] = False
            return False

        try:
            # 创建ONNX推理会话
            sess_options = self._ort.SessionOptions()
            sess_options.intra_op_num_threads = 1  # 单线程，避免竞争
            sess_options.graph_optimization_level = self._ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            session = self._ort.InferenceSession(
                model_path,
                sess_options,
                providers=['CPUExecutionProvider']
            )

            self._models[model_name] = session
            self._model_status[model_name] = True
            logger.info(f"[DLModelManager] Model loaded: {model_name}")
            return True

        except Exception as e:
            logger.error(f"[DLModelManager] Failed to load model {model_name}: {e}")
            self._model_status[model_name] = False
            return False

    def get_model(self, model_name: str) -> Optional[Any]:
        """
        获取已加载的模型

        Args:
            model_name: 模型名称

        Returns:
            ONNX推理会话或None
        """
        if model_name not in self._models:
            self.load_model(model_name)

        return self._models.get(model_name)

    def is_model_available(self, model_name: str) -> bool:
        """
        检查模型是否可用

        Args:
            model_name: 模型名称

        Returns:
            模型是否可用
        """
        if model_name not in self._model_status:
            self.load_model(model_name)

        return self._model_status.get(model_name, False)

    def run_inference(self, model_name: str, inputs: Dict[str, Any]) -> Optional[Any]:
        """
        运行模型推理

        Args:
            model_name: 模型名称
            inputs: 输入数据字典

        Returns:
            推理结果或None
        """
        model = self.get_model(model_name)
        if model is None:
            return None

        try:
            output_names = [o.name for o in model.get_outputs()]
            results = model.run(output_names, inputs)
            return results
        except Exception as e:
            logger.error(f"[DLModelManager] Inference failed for {model_name}: {e}")
            return None

    def get_model_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有模型状态信息

        Returns:
            模型状态字典
        """
        info = {}
        for name, config in self.MODEL_CONFIG.items():
            info[name] = {
                'path': config['path'],
                'size_mb': config['size_mb'],
                'loaded': self.is_model_available(name),
                'onnx_available': self.is_onnx_available()
            }
        return info
