"""
集成测试 - API 层测试
测试 Flask 路由和响应
"""
import pytest
import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api import create_app
from config import config


class TestAPIRoutes:
    """API 路由测试"""

    def setup_method(self):
        """每个测试前创建测试客户端"""
        self.app = create_app()
        self.client = self.app.test_client()

    def test_history_endpoint_returns_json(self):
        """测试历史记录接口返回 JSON"""
        response = self.client.get('/api/history')

        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_history_endpoint_returns_list(self):
        """测试历史记录接口返回列表"""
        response = self.client.get('/api/history')
        data = json.loads(response.data)

        # API 返回 {'history': [...], 'success': True} 格式
        assert 'history' in data or isinstance(data, list)
        if 'history' in data:
            assert isinstance(data['history'], list)

    def test_audio_endpoint_missing_file(self):
        """测试音频接口缺少文件参数"""
        response = self.client.get('/api/audio')

        assert response.status_code == 404  # 或 400

    def test_audio_endpoint_invalid_path(self):
        """测试音频接口无效路径"""
        response = self.client.get('/api/audio?file=/invalid/path.wav')

        # 应该返回 404 或 403
        assert response.status_code in [404, 403, 400]

    def test_upload_no_file(self):
        """测试上传接口无文件"""
        response = self.client.post('/api/upload')

        # 应该返回错误
        assert response.status_code >= 400


class TestErrorHandling:
    """错误处理测试"""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_404_handling(self):
        """测试 404 处理"""
        response = self.client.get('/api/nonexistent')

        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
