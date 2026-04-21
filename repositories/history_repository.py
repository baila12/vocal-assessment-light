"""
历史记录仓储
提供历史记录的持久化存储接口

设计原则：
- 抽象接口便于测试时 mock
- 单一职责：只负责数据存取
- 依赖注入：通过构造函数传入文件路径
"""
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json


class HistoryRepository(ABC):
    """
    历史记录仓储接口

    抽象接口设计：
    - 便于测试时创建 mock 实现
    - 便于将来切换存储方式（如 SQLite、MongoDB）
    """

    @abstractmethod
    def get_all(self, limit: int = 20) -> List[Dict]:
        """获取所有历史记录"""
        pass

    @abstractmethod
    def get_paginated(self, page: int = 1, limit: int = 20, date_filter: str = 'all') -> Dict:
        """分页获取历史记录

        Args:
            page: 页码（从1开始）
            limit: 每页数量
            date_filter: 日期筛选 ('today', 'week', 'month', 'all')

        Returns:
            {'records': [...], 'total': int, 'page': int, 'total_pages': int}
        """
        pass

    @abstractmethod
    def get_total_count(self, date_filter: str = 'all') -> int:
        """获取总记录数"""
        pass

    @abstractmethod
    def get_by_date(self, date_filter: str) -> List[Dict]:
        """按日期筛选历史记录

        Args:
            date_filter: 筛选类型 ('today', 'week', 'month', 'all')
        """
        pass

    @abstractmethod
    def save(self, record: Dict) -> Dict:
        """保存历史记录"""
        pass

    @abstractmethod
    def get_by_id(self, record_id: int) -> Optional[Dict]:
        """根据 ID 获取记录"""
        pass

    @abstractmethod
    def delete(self, record_id: int) -> bool:
        """删除记录

        Returns:
            True 如果删除成功，False 如果记录不存在
        """
        pass

    @abstractmethod
    def delete_batch(self, record_ids: List[int]) -> int:
        """批量删除记录

        Returns:
            成功删除的记录数
        """
        pass


class JsonHistoryRepository(HistoryRepository):
    """
    JSON 文件存储实现

    当前使用 JSON 文件存储，将来可无缝切换到数据库
    """

    def __init__(self, filepath: Path, max_records: int = 50):
        """
        初始化仓储

        Args:
            filepath: JSON 文件路径
            max_records: 最大保存记录数
        """
        self.filepath = Path(filepath)
        self.max_records = max_records
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """确保文件和目录存在"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self._write_records([])

    def _read_records(self) -> List[Dict]:
        """读取所有记录"""
        try:
            if not self.filepath.exists():
                return []
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_records(self, records: List[Dict]):
        """写入所有记录"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def get_all(self, limit: int = 20) -> List[Dict]:
        """获取所有历史记录（最新的在前）"""
        records = self._read_records()
        return records[-limit:][::-1]  # 返回最新的 limit 条

    def get_by_date(self, date_filter: str) -> List[Dict]:
        """按日期筛选历史记录"""
        if date_filter == 'all':
            return self._read_records()[::-1]

        records = self._read_records()
        now = datetime.now()
        filtered = []

        for record in records:
            try:
                record_time = datetime.fromisoformat(record['timestamp'])

                if date_filter == 'today':
                    if record_time.date() == now.date():
                        filtered.append(record)
                elif date_filter == 'week':
                    week_ago = now.timestamp() - 7 * 24 * 60 * 60
                    if record_time.timestamp() >= week_ago:
                        filtered.append(record)
                elif date_filter == 'month':
                    if record_time.year == now.year and record_time.month == now.month:
                        filtered.append(record)
            except (KeyError, ValueError):
                # 记录格式错误时仍然包含
                filtered.append(record)

        return filtered[::-1]

    def save(self, record: Dict) -> Dict:
        """保存历史记录"""
        records = self._read_records()

        # 生成唯一 ID（取现有最大 ID + 1）
        max_id = max((r.get('id', 0) for r in records), default=0)
        record['id'] = max_id + 1

        # 添加时间戳（如果没有）
        if 'timestamp' not in record:
            record['timestamp'] = datetime.now().isoformat()

        records.append(record)

        # 限制记录数量
        if len(records) > self.max_records:
            records = records[-self.max_records:]

        self._write_records(records)
        return record

    def get_by_id(self, record_id) -> Optional[Dict]:
        """根据 ID 获取记录"""
        try:
            record_id = int(record_id)
        except (ValueError, TypeError):
            return None

        records = self._read_records()
        for record in records:
            if record.get('id') == record_id:
                return record
        return None

    def delete(self, record_id) -> bool:
        """删除记录

        Returns:
            True 如果删除成功，False 如果记录不存在
        """
        try:
            record_id = int(record_id)
        except (ValueError, TypeError):
            return False

        records = self._read_records()
        original_len = len(records)

        # 过滤掉要删除的记录
        records = [r for r in records if r.get('id') != record_id]

        if len(records) == original_len:
            # 记录不存在
            return False

        self._write_records(records)
        return True

    def delete_batch(self, record_ids: List[int]) -> int:
        """批量删除记录

        Args:
            record_ids: 要删除的记录ID列表

        Returns:
            成功删除的记录数
        """
        # 转换为整数集合并过滤无效值
        valid_ids = set()
        for rid in record_ids:
            try:
                valid_ids.add(int(rid))
            except (ValueError, TypeError):
                pass

        if not valid_ids:
            return 0

        records = self._read_records()
        original_len = len(records)

        # 过滤掉要删除的记录
        records = [r for r in records if r.get('id') not in valid_ids]

        deleted_count = original_len - len(records)
        if deleted_count > 0:
            self._write_records(records)

        return deleted_count

    def get_paginated(self, page: int = 1, limit: int = 20, date_filter: str = 'all') -> Dict:
        """分页获取历史记录

        Args:
            page: 页码（从1开始）
            limit: 每页数量
            date_filter: 日期筛选

        Returns:
            {'records': [...], 'total': int, 'page': int, 'total_pages': int, 'limit': int}
        """
        # 获取筛选后的记录
        if date_filter == 'all':
            records = self._read_records()[::-1]  # 最新的在前
        else:
            records = self.get_by_date(date_filter)

        total = len(records)
        total_pages = max(1, (total + limit - 1) // limit)

        # 确保页码有效
        page = max(1, min(page, total_pages))

        # 计算偏移量
        offset = (page - 1) * limit
        paginated_records = records[offset:offset + limit]

        return {
            'records': paginated_records,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'limit': limit
        }

    def get_total_count(self, date_filter: str = 'all') -> int:
        """获取总记录数"""
        if date_filter == 'all':
            return len(self._read_records())
        else:
            return len(self.get_by_date(date_filter))
