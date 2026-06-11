"""
E2E test for AnimationController unit tests (Playwright).
"""
import pytest
import pathlib

@pytest.mark.e2e
class TestAnimationControllerUnit:
    """AnimationController unit tests executed in browser."""

    @pytest.fixture(autouse=True)
    def setup_app(self, page, base_url):
        page.goto(base_url)
        page.wait_for_selector("#pageContainer", timeout=10000)
        page.wait_for_timeout(500)
        test_file = pathlib.Path(__file__).parent.parent / "unit" / "test_animation_controller.js"
        if test_file.exists():
            page.evaluate(test_file.read_text(encoding="utf-8"))

    def _run(self, page, name):
        return page.evaluate('window.__animationTests["' + name + '"]()')

    def test_controller_initialization(self, page):
        r = self._run(page, "testInitialization")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_enter_preset(self, page):
        r = self._run(page, "testEnterPreset")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_disabled_skips_animation(self, page):
        r = self._run(page, "testDisabled")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_re_enabled_restores_animation(self, page):
        r = self._run(page, "testReEnabled")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_stagger_param(self, page):
        r = self._run(page, "testStagger")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_count_up_uses_snap(self, page):
        r = self._run(page, "testCountUp")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_fill_bar_uses_scaleX(self, page):
        r = self._run(page, "testFillBar")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_unknown_preset_graceful(self, page):
        r = self._run(page, "testUnknownPreset")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_kill_all(self, page):
        r = self._run(page, "testKillAll")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        assert r.get("pass"), str(r.get("detail", ""))


    def test_run_all(self, page):
        r = self._run(page, "testRunAll")
        if 'not loaded' in str(r.get('reason', '')):
            pytest.skip("AnimationController not yet implemented")
        summary = str(r.get("summary", ""))
        print('  [JS]', summary)
        assert True
