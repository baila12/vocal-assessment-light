"""
上传文件自动清理 — v7.15 P2-14 (uploads/ 永不清理修复)

DEEP_REVIEW E4/V8 (CONFIRMED): uploads/ 目录 36 个文件无清理, 孤儿文件
(历史记录已删/淘汰/从未引用) 永久残留。本模块提供两层清理:

  - unlink_files(upload_dir, filepaths)   — 定向删除: 删除/淘汰记录时调用
  - cleanup_orphans(upload_dir, refs)     — 孤儿扫描: 启动时删除未被任何记录引用的文件
  - run_startup_upload_cleanup(dir, repo) — 启动扫描入口 (无仓储可校验时安全不删)

安全约束 (防误删):
  - 只删除 resolve() 后位于 uploads 目录内的文件 (Prefix 校验)
  - 删除失败仅 WARNING 告警, 不抛出 — 优雅降级, 不阻塞主流程
  - 孤儿扫描不递归子目录 (KISS, 当前无子目录用法)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def _resolve_abs(path: Path) -> Path:
    """防御性 resolve — 路径异常时退回原路径, 不抛出."""
    try:
        return path.resolve()
    except (OSError, ValueError):
        return path


def _is_within(path: Path, root: Path) -> bool:
    """path 是否位于 root 目录内 (均先 resolve)."""
    try:
        return _resolve_abs(path).is_relative_to(_resolve_abs(root))
    except (OSError, ValueError):
        return False


def unlink_files(upload_dir: Path, filepaths: Iterable[Optional[str]]) -> int:
    """删除指定上传文件 — 仅限 uploads 目录内, 失败仅告警.

    返回成功处理 (存在则删除 / 不存在则幂等跳过) 的文件数。
    目录外文件跳过并告警, 防御历史记录误存外部路径 (如测试音频)。
    """
    root = Path(upload_dir)
    count = 0
    for fp in filepaths:
        if not fp:
            continue
        p = Path(fp)
        if not _is_within(p, root):
            logger.warning("跳过删除: 文件不在 uploads 目录内 %s", p)
            continue
        try:
            p.unlink(missing_ok=True)
            count += 1
        except OSError:
            logger.warning("删除上传文件失败: %s", p, exc_info=True)
    return count


def collect_referenced_files(records: Iterable[dict]) -> set[str]:
    """从历史记录提取仍被引用的文件绝对路径集合 (filepath 非空才纳入)."""
    referenced: set[str] = set()
    for record in records or []:
        fp = record.get("filepath")
        if fp:
            referenced.add(str(_resolve_abs(Path(fp))))
    return referenced


def cleanup_orphans(upload_dir: Path, referenced_files: Iterable[str]) -> int:
    """孤儿扫描: 删除 uploads 目录内未被任何记录引用的文件.

    Returns: 删除的文件数。
    目录不存在返回 0; 子目录不递归; 删除失败仅告警。
    """
    root = Path(upload_dir)
    if not root.is_dir():
        return 0
    referenced = {str(_resolve_abs(Path(r))) for r in referenced_files if r}
    deleted = 0
    for p in root.iterdir():
        if not p.is_file():
            continue
        if str(_resolve_abs(p)) in referenced:
            continue
        try:
            p.unlink(missing_ok=True)
            deleted += 1
        except OSError:
            logger.warning("清理孤儿上传文件失败: %s", p, exc_info=True)
    return deleted


def run_startup_upload_cleanup(upload_dir: Path, history_repo) -> int:
    """启动孤儿扫描入口 — 删除 uploads 中未被任何历史记录引用的文件.

    无仓储 (无法校验引用) 时安全不删, 返回 0。
    仓储通过 get_by_date('all') 暴露全量记录 (含 filepath 字段)。
    """
    if history_repo is None:
        return 0
    records = history_repo.get_by_date("all") or []
    referenced = collect_referenced_files(records)
    return cleanup_orphans(upload_dir, referenced)
