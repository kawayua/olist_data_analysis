from pathlib import Path

from app.components.navigation import NAVIGATION_PAGES


def test_navigation_contains_only_five_analysis_pages():
    assert [path for path, _ in NAVIGATION_PAGES] == [
        "pages/1_经营总览.py",
        "pages/2_增长诊断.py",
        "pages/3_留存复购.py",
        "pages/4_客户价值.py",
        "pages/5_商品与履约.py",
    ]


def test_every_page_uses_shared_navigation():
    for path in [Path("app/Home.py"), *Path("app/pages").glob("*.py")]:
        assert "render_navigation" in path.read_text(encoding="utf-8")


def test_navigation_css_hides_entire_sidebar_and_centers_glass_pill():
    content = Path("app/components/layout.py").read_text(encoding="utf-8")

    assert '[data-testid="stSidebar"],' in content
    assert 'display: none !important;' in content
    assert "justify-content: center" in content
    assert "top: 12px" in content
    assert "margin: 48px 0 1rem" in content
    assert "border-radius: 28px" in content


def test_navigation_uses_content_width_links_with_interaction_states():
    layout = Path("app/components/layout.py").read_text(encoding="utf-8")
    navigation = Path("app/components/navigation.py").read_text(encoding="utf-8")

    assert "width: fit-content" in layout
    assert "max-width: calc(100vw - 2rem)" in layout
    assert ":hover" in layout
    assert ":focus-visible" in layout
    assert '[aria-current="page"]' in layout
    assert "transform: translateX(-50%)" in layout
    assert "use_container_width" not in navigation
