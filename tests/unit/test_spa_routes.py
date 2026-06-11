"""
单元测试 — SPA 路由 & 旧页面重定向

测试 Flask 后端新的 SPA 路由行为:
1. 首页返回 index.html
2. 旧 HTML 页面 301 重定向
3. index.html fallback
4. API 路由不受影响
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api import create_app


@pytest.fixture(scope='module')
def client():
    """Flask 测试客户端."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestSPAEntryPoint:
    """SPA 单入口路由测试"""

    def test_index_returns_html(self, client):
        """首页应返回 index.html (SPA 入口)."""
        response = client.get('/')
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'text/html' in content_type

    def test_index_contains_app_container(self, client):
        """index.html 应包含 SPA 容器元素."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'id="pageContainer"' in html, \
            'SPA page container missing in index.html'
        assert 'id="toastWrap"' in html, \
            'Toast container missing in index.html'

    def test_index_loads_local_gsap(self, client):
        """index.html 应从本地加载 GSAP."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '/lib/gsap/gsap.min.js' in html, \
            'GSAP local script tag missing'

    def test_index_loads_local_chartjs(self, client):
        """index.html 应从本地加载 Chart.js."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '/lib/chart.js/chart.umd.min.js' in html, \
            'Chart.js local script tag missing'

    def test_index_loads_app_module(self, client):
        """index.html 应加载 app.js 模块入口."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'type="module"' in html, \
            'ES Module script tag missing'
        assert '/app.js' in html, \
            'app.js entry not found in index.html'


class TestOldPageRedirects:
    """旧 HTML 页面 301 重定向测试"""

    def test_analysis_html_redirects(self, client):
        """GET /analysis.html → 301 → /"""
        response = client.get('/analysis.html')
        assert response.status_code == 301, \
            f'Expected 301, got {response.status_code}'
        assert response.headers.get('Location') == '/', \
            f'Expected redirect to /, got {response.headers.get("Location")}'

    def test_compare_html_redirects(self, client):
        """GET /compare.html → 301 → /"""
        response = client.get('/compare.html')
        assert response.status_code == 301
        assert response.headers.get('Location') == '/'

    def test_settings_html_redirects(self, client):
        """GET /settings.html → 301 → /"""
        response = client.get('/settings.html')
        assert response.status_code == 301
        assert response.headers.get('Location') == '/'

    def test_index_html_fallback(self, client):
        """GET /index.html → 200 (serves index.html)."""
        response = client.get('/index.html')
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'text/html' in content_type


class TestAPIRoutesUnaffected:
    """API 路由不应受 SPA 重构影响"""

    def test_health_endpoint(self, client):
        """GET /health → 200 or 503."""
        response = client.get('/health')
        assert response.status_code in (200, 503)

    def test_api_upload_returns_json(self, client):
        """POST /api/upload 应返回 JSON (即使无文件)."""
        response = client.post('/api/upload')
        # 无文件时可能返回 400 或处理错误
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type or response.status_code == 400

    def test_api_history_returns_json(self, client):
        """GET /api/history 应返回 JSON."""
        response = client.get('/api/history')
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type

    def test_static_files_served(self, client):
        """静态文件 (CSS/JS) 应正常服务."""
        # Test a known static file
        response = client.get('/css/variables.css')
        assert response.status_code == 200

    def test_gsap_lib_served(self, client):
        """GSAP 本地库文件应可访问."""
        response = client.get('/lib/gsap/gsap.min.js')
        assert response.status_code == 200, \
            'GSAP local file not served — check web/static/lib/gsap/'

    def test_chartjs_lib_served(self, client):
        """Chart.js 本地库文件应可访问."""
        response = client.get('/lib/chart.js/chart.umd.min.js')
        assert response.status_code == 200, \
            'Chart.js local file not served — check web/static/lib/chart.js/'


class TestSPAContentSecurity:
    """SPA 内容安全检查"""

    def test_no_old_page_references(self, client):
        """index.html 不应引用旧 HTML 页面."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'analysis.html' not in html, \
            'index.html should not reference analysis.html'
        assert 'compare.html' not in html, \
            'index.html should not reference compare.html'
        assert 'settings.html' not in html, \
            'index.html should not reference settings.html'

    def test_no_cdn_references(self, client):
        """index.html 不应引用 CDN (离线优先)."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        # chart.js CDN
        assert 'cdn.jsdelivr.net/npm/chart.js' not in html, \
            'Chart.js CDN reference found — should use local copy'
        # We allow local GSAP reference
        assert 'lib/gsap/gsap.min.js' in html, \
            'No local GSAP reference found'

    def test_toast_container_present(self, client):
        """index.html 应包含 Toast 容器."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'toastWrap' in html, 'Toast container missing'

    def test_global_progress_bar_present(self, client):
        """index.html 应包含全局进度条."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'globalProgressBar' in html, 'Global progress bar missing'

    def test_nav_containers_present(self, client):
        """index.html 应包含导航容器."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'topNavContainer' in html, 'Top nav container missing'
        assert 'bottomNavContainer' in html, 'Bottom nav container missing'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
