from pathlib import Path

from app.components.navigation import NAVIGATION_PAGES


def test_navigation_contains_only_five_analysis_pages():
    assert [path for path, _ in NAVIGATION_PAGES] == [
        "app/pages/1_经营总览.py",
        "app/pages/2_增长诊断.py",
        "app/pages/3_留存复购.py",
        "app/pages/4_客户价值.py",
        "app/pages/5_商品与履约.py",
    ]


def test_every_page_uses_shared_navigation():
    for path in [Path("app/Home.py"), *Path("app/pages").glob("*.py")]:
        assert "render_navigation" in path.read_text(encoding="utf-8")
