"""
模型诊断工具

提供模型加载失败的详细诊断信息
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ModelDiagnostic:
    """
    模型诊断工具 v1.0

    提供模型加载失败的详细诊断信息
    """

    # 常见错误模式和建议
    ERROR_SOLUTIONS = {
        'ImportError': {
            'torch': [
                'PyTorch 未安装，请运行: pip install torch',
                '如果使用CUDA，请安装对应版本: pip install torch --index-url https://download.pytorch.org/whl/cu121'
            ],
            'onnxruntime': [
                'ONNX Runtime 未安装，请运行: pip install onnxruntime',
                'ONNX模型将无法加载'
            ]
        },
        'RuntimeError': {
            'CUDA out of memory': [
                'GPU显存不足，尝试释放其他程序的显存',
                '或使用CPU模式运行'
            ],
            'No CUDA GPUs are available': [
                '未检测到CUDA GPU，将使用CPU模式',
                '如需GPU加速，请检查CUDA安装'
            ]
        },
        'FileNotFoundError': {
            'default': [
                '模型文件不存在，请检查模型路径',
                '模型可能需要预先下载'
            ]
        },
        'HttpError': {
            'default': [
                '网络连接失败，无法下载模型',
                '请检查网络连接或配置HF镜像: export HF_ENDPOINT=https://hf-mirror.com'
            ]
        }
    }

    @classmethod
    def diagnose(cls, model_name: str, error: Exception) -> Dict[str, Any]:
        """
        诊断模型加载失败原因

        Args:
            model_name: 模型名称
            error: 异常对象

        Returns:
            诊断结果字典
        """
        error_type = type(error).__name__
        error_msg = str(error)

        result = {
            'model': model_name,
            'error_type': error_type,
            'error_message': error_msg,
            'suggestions': [],
            'severity': 'warning',
            'fallback_available': True
        }

        # 查找匹配的解决方案
        if error_type in cls.ERROR_SOLUTIONS:
            type_solutions = cls.ERROR_SOLUTIONS[error_type]
            # 检查是否有特定的模块建议
            for key, suggestions in type_solutions.items():
                if key != 'default' and key.lower() in error_msg.lower():
                    result['suggestions'] = suggestions
                    break

            # 使用默认建议
            if not result['suggestions'] and 'default' in type_solutions:
                result['suggestions'] = type_solutions['default']

        # 根据错误类型判断严重性
        if error_type in ['ImportError', 'ModuleNotFoundError']:
            result['severity'] = 'warning'  # 可以降级
        elif error_type in ['RuntimeError'] and 'CUDA' in error_msg:
            result['severity'] = 'info'  # 可以使用CPU
        elif error_type in ['FileNotFoundError']:
            result['severity'] = 'error'  # 需要下载模型
        else:
            result['severity'] = 'warning'

        return result

    @classmethod
    def check_dependencies(cls) -> Dict[str, Dict[str, Any]]:
        """
        检查所有依赖项状态

        Returns:
            依赖项状态字典
        """
        dependencies = {}

        # 检查PyTorch
        try:
            import torch
            dependencies['torch'] = {
                'installed': True,
                'version': torch.__version__,
                'cuda_available': torch.cuda.is_available(),
                'cuda_version': torch.version.cuda if torch.cuda.is_available() else None
            }
        except ImportError:
            dependencies['torch'] = {
                'installed': False,
                'version': None,
                'cuda_available': False
            }

        # v7.1: wvmos/speechbrain/s3prl 依赖检查已移除 (SingMOS 已在 v5.15 移除)

        # 检查onnxruntime
        try:
            import onnxruntime
            dependencies['onnxruntime'] = {
                'installed': True,
                'version': onnxruntime.__version__
            }
        except ImportError:
            dependencies['onnxruntime'] = {
                'installed': False
            }

        return dependencies

    @classmethod
    def get_installation_guide(cls) -> str:
        """获取安装指南 (v7.1: DL模型精简)"""
        return """
# 深度学习模型安装指南

## 必需依赖
pip install torch librosa numpy

## 可选依赖

### ONNX Runtime (人声检测 + 唱法分类)
pip install onnxruntime

### Demucs (人声分离)
pip install demucs

### torchfcpe (高精度基频检测, v7.1)
pip install torchfcpe

### ONNX Runtime（可选，用于ONNX模型）
pip install onnxruntime

## CUDA 支持
# 如果有NVIDIA GPU，安装CUDA版本的PyTorch:
pip install torch --index-url https://download.pytorch.org/whl/cu121

## 镜像配置（中国大陆）
export HF_ENDPOINT=https://hf-mirror.com
"""