"""
历史记录管理 - 本地JSON存储
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, filepath: str = "data/history.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not self.filepath.exists():
            self._write([])

    def _read(self) -> list:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, data: list):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_record(self, record: dict) -> int:
        records = self._read()
        record['id'] = len(records) + 1
        record['timestamp'] = datetime.now().isoformat()
        records.append(record)
        self._write(records)
        return record['id']

    def get_all(self, limit: Optional[int] = None) -> list:
        records = self._read()
        if limit:
            return records[-limit:][::-1]
        return records[::-1]

    def get_by_id(self, record_id: int) -> Optional[dict]:
        records = self._read()
        for r in records:
            if r.get('id') == record_id:
                return r
        return None

    def delete_by_id(self, record_id: int) -> bool:
        records = self._read()
        for i, r in enumerate(records):
            if r.get('id') == record_id:
                records.pop(i)
                self._write(records)
                return True
        return False

    def clear_all(self):
        self._write([])
