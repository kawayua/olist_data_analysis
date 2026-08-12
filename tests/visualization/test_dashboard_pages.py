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
