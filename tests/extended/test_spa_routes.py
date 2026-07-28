"""
单元测试 — SPA 路由 & 旧页面重定向 (v7.1.3 更新)

测试 Flask 后端 SPA 路由行为:
1. 首页返回 index.html (v7 升级说明页)
2. 旧 HTML 页面 301 重定向
3. index.html fallback
4. API 路由不受影响
5. 静态库文件正常服务
"""
import pytest

from api import create_app


@pytest.fixture(scope='module')
def client():
    """Flask 测试客户端."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestSPAEntryPoint:
    """SPA 单入口路由测试 — v7.1.3 升级说明页"""

    def test_index_returns_html(self, client):
        """首页应返回 index.html."""
        response = client.get('/')
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'text/html' in content_type

    def test_index_is_v7_upgrade_page(self, client):
        """index.html 应是 v7 升级说明页."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '声乐评估系统' in html, \
            'App title missing in index.html'
        assert 'v7' in html.lower(), \
            'v7 upgrade notice missing in index.html'

    def test_index_no_old_spa_references(self, client):
        """index.html 不应引用已删除的旧 SPA 资源."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '/app.js' not in html, \
            'Old SPA entry app.js should not be referenced'
        assert '/css/variables.css' not in html, \
            'Old SPA CSS should not be referenced'
        assert 'type="module"' not in html, \
            'ES module script tag should not be present'


class TestOldPageRedirects:
    """旧 HTML 页面 301 重定向测试"""

    def test_analysis_html_redirects(self, client):
        """GET /analysis.html → 301 → /"""
        response = client.get('/analysis.html')
        assert response.status_code == 301, \
            f'Expected 301, got {response.status_code}'
        assert response.headers.get('Location') == '/'

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
    """API 路由不应受 SPA 清理影响"""

    def test_health_endpoint(self, client):
        """GET /health → 200 or 503."""
        response = client.get('/health')
        assert response.status_code in (200, 503)

    def test_api_upload_returns_json(self, client):
        """POST /api/upload 应返回 JSON (即使无文件)."""
        response = client.post('/api/upload')
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type or response.status_code == 400

    def test_api_history_returns_json(self, client):
        """GET /api/history 应返回 JSON."""
        response = client.get('/api/history')
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type

    def test_gsap_lib_served(self, client):
        """GSAP 本地库文件应可访问 (lib/ 目录保留)."""
        response = client.get('/lib/gsap/gsap.min.js')
        assert response.status_code == 200, \
            'GSAP local file not served — check web/static/lib/gsap/'

    def test_chartjs_lib_served(self, client):
        """Chart.js 本地库文件应可访问."""
        response = client.get('/lib/chart.js/chart.umd.min.js')
        assert response.status_code == 200, \
            'Chart.js local file not served — check web/static/lib/chart.js/'

    def test_favicon_served(self, client):
        """favicon.svg 应可访问."""
        response = client.get('/favicon.svg')
        assert response.status_code == 200


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
        assert 'cdn.jsdelivr.net' not in html, \
            'CDN reference found — should not use CDN'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
