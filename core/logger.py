"""
结构化日志模块

提供统一的日志配置和结构化输出（JSON格式）
支持标准库 logging，可配置输出格式
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为 JSON"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        log_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        }

        # 添加可选字段
        for attr in ["port", "filepath", "duration", "user_id", "request_id",
                     "filename", "free_space_mb", "extra_data", "error"]:
            if hasattr(record, attr):
                value = getattr(record, attr)
                if isinstance(value, Path):
                    value = str(value)
                log_data[attr] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class SimpleFormatter(logging.Formatter):
    """简单文本格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化为简洁的文本格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        extra_parts = []
        for attr in ["port", "filepath", "duration", "filename", "error"]:
            if hasattr(record, attr):
                value = getattr(record, attr)
                if isinstance(value, Path):
                    value = str(value)
                extra_parts.append(f"{attr}={value}")

        extra_str = f" | {', '.join(extra_parts)}" if extra_parts else ""

        return f"[{timestamp}] [{record.levelname:8}] [{record.module}] {record.getMessage()}{extra_str}"


_log_configured = False


def setup_logger(
    name: Optional[str] = None,
    level: int = logging.INFO,
    json_format: bool = False,
    log_file: Optional[Path] = None,
    propagate: bool = False
) -> logging.Logger:
    """设置并获取配置好的日志记录器"""
    logger = logging.getLogger(name)

    if hasattr(logger, '_structured_configured'):
        return logger

    logger.setLevel(level)
    logger.propagate = propagate
    logger.handlers = []

    formatter = JSONFormatter() if json_format else SimpleFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger._structured_configured = True  # type: ignore

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取已配置的日志记录器"""
    return setup_logger(name)


def configure_root_logger(
    level: int = logging.INFO,
    json_format: bool = False,
    log_file: Optional[Path] = None
) -> None:
    """配置根日志记录器"""
    global _log_configured

    if _log_configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = JSONFormatter() if json_format else SimpleFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _log_configured = True
