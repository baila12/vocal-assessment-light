"""
单元测试 - 数据层测试
测试 repositories 模块
"""
import pytest
import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from repositories import HistoryRepository
from repositories.history_repository import JsonHistoryRepository


class TestJsonHistoryRepository:
    """JSON 历史记录仓储测试"""

    def setup_method(self):
        """每个测试前创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = Path(self.temp_dir) / 'test_history.json'
        self.repo = JsonHistoryRepository(self.history_file)

    def test_implements_abstract(self):
        """测试实现了抽象接口"""
        assert isinstance(self.repo, HistoryRepository)

    def test_save_and_get_all(self):
        """测试保存和获取记录"""
        record = {
            'filename': 'test.wav',
            'scores': {'volume': 80, 'pitch': 75},
            'totalScore': 77.5
        }

        result = self.repo.save(record)
        assert result['filename'] == 'test.wav'
        assert 'id' in result or 'date' in result  # 应该有元数据

        # 获取所有记录
        records = self.repo.get_all()
        assert len(records) >= 1
        assert records[0]['filename'] == 'test.wav'

    def test_get_all_with_limit(self):
        """测试限制返回数量"""
        # 保存多条记录
        for i in range(5):
            self.repo.save({'filename': f'test_{i}.wav', 'totalScore': i * 10})

        records = self.repo.get_all(limit=3)
        assert len(records) <= 3

    def test_get_all_empty(self):
        """测试空历史记录"""
        records = self.repo.get_all()
        assert isinstance(records, list)
        assert len(records) == 0

    def test_get_by_date(self):
        """测试按日期过滤"""
        record = {
            'filename': 'test.wav',
            'scores': {'volume': 80},
            'totalScore': 80
        }

        self.repo.save(record)

        # 过滤今天
        records = self.repo.get_by_date('today')
        assert isinstance(records, list)

    def test_save_preserves_data(self):
        """测试保存不修改原始数据"""
        record = {
            'filename': 'original.wav',
            'scores': {'volume': 90, 'pitch': 85},
            'totalScore': 87.5
        }

        original_filename = record['filename']
        self.repo.save(record)

        # 原始数据不应被修改
        assert record['filename'] == original_filename


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
