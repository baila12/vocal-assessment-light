"""
FastAPI 依赖注入容器

使用 Depends() 实现构造函数注入，所有服务延迟初始化。
绞杀者模式: 委托到现有 Flask business 层。
"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import sys
import os

# 确保项目根目录可导入旧模块
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.infrastructure.config import Settings
from backend.shared.event_bus import EventBus
from backend.domain.assessment.services import ScoringDomainService


# ===== 单例 (lifespan 初始化) =====
_event_bus = EventBus()


@lru_cache()
def get_settings() -> Settings:
    """配置单例 — Pydantic Settings, 支持 VAS_* 环境变量"""
    return Settings()


def get_event_bus() -> EventBus:
    """EventBus 单例"""
    return _event_bus


def get_scoring_service() -> ScoringDomainService:
    """评分领域服务 — 注入 EventBus (Phase 1 实现)"""
    return ScoringDomainService(event_bus=_event_bus)


# ===== 旧模块延迟导入 — 绞杀者模式委托到现有 business 层 =====

def get_history_repo():
    """JSON 历史记录仓储 — 委托到旧 repositories 模块"""
    from repositories import JsonHistoryRepository
    from config import config as flask_config
    return JsonHistoryRepository(flask_config.HISTORY_FILE, flask_config.HISTORY_MAX_RECORDS)


def get_separation_service():
    """人声分离服务 — 委托到旧 services 模块"""
    from services import SeparationService
    from config import config as flask_config
    return SeparationService(flask_config.SEPARATED_DIR)


def get_report_service():
    """报告生成服务 — 委托到旧 services 模块"""
    from services import ReportService
    from config import config as flask_config
    return ReportService(flask_config.REPORTS_DIR)


def get_flask_config():
    """旧 Flask 配置 — 兼容现有业务逻辑"""
    from config import config as flask_config
    return flask_config
