from pathlib import Path


def test_dashboard_contains_five_governed_analysis_pages():
    page_directory = Path("app/pages")
    expected_pages = {
        "1_经营总览.py",
        "2_增长诊断.py",
        "3_留存复购.py",
        "4_客户价值.py",
        "5_商品与履约.py",
    }

    assert {path.name for path in page_directory.glob("*.py")} == expected_pages

    for page in page_directory.glob("*.py"):
        content = page.read_text(encoding="utf-8")
        assert "render_filters" in content
        assert "get_repository" in content
        assert "st.info" in content


def test_dashboard_pages_apply_shared_theme_and_header():
    dashboard_files = [Path("app/Home.py"), *Path("app/pages").glob("*.py")]

    for page in dashboard_files:
        content = page.read_text(encoding="utf-8")
        assert "apply_dashboard_theme()" in content
        assert "render_page_header(" in content


def test_dashboard_tables_use_display_ready_dataframes():
    for page in [
        Path("app/Home.py"),
        Path("app/pages/3_留存复购.py"),
        Path("app/pages/5_商品与履约.py"),
    ]:
        content = page.read_text(encoding="utf-8")
        assert "display_dataframe(" in content
