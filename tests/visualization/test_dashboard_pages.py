from pathlib import Path


def test_dashboard_contains_seven_governed_analysis_pages():
    page_directory = Path("app/pages")
    expected_pages = {
        "1_经营总览.py",
        "2_增长诊断.py",
        "3_留存复购.py",
        "4_客户价值.py",
        "5_商品与履约.py",
        "6_营销ROI模拟器.py",
        "7_AI分析助手.py",
    }

    assert {path.name for path in page_directory.glob("*.py")} == expected_pages

    for page in page_directory.glob("*.py"):
        content = page.read_text(encoding="utf-8")
        assert "render_filters" not in content
        assert "render_state_filter" not in content
        assert "render_month_filter" not in content
        assert "render_cohort_filter" not in content
        assert "render_category_filter" not in content
        assert "filters =" not in content
        assert "st.info" in content

    for page in page_directory.glob("[1-6]_*.py"):
        assert "get_repository" in page.read_text(encoding="utf-8")

    ai_assistant = (page_directory / "7_AI分析助手.py").read_text(encoding="utf-8")
    assert "AnalysisTools" in ai_assistant
    assert "AnalysisAgent" in ai_assistant


def test_filtered_analysis_loaders_use_default_dashboard_filters():
    for page in [
        Path("app/pages/1_经营总览.py"),
        Path("app/pages/2_增长诊断.py"),
        Path("app/pages/3_留存复购.py"),
        Path("app/pages/5_商品与履约.py"),
    ]:
        assert "DashboardFilters()" in page.read_text(encoding="utf-8")


def test_empty_states_do_not_instruct_users_to_change_removed_filters():
    for page in Path("app/pages").glob("*.py"):
        content = page.read_text(encoding="utf-8")
        assert "当前筛选" not in content
        assert "请清除" not in content


def test_dashboard_pages_apply_shared_theme_and_header():
    dashboard_files = [Path("app/Home.py"), *Path("app/pages").glob("*.py")]

    for page in dashboard_files:
        content = page.read_text(encoding="utf-8")
        assert "apply_dashboard_theme()" in content
        assert "render_navigation()" in content
        assert "render_page_header(" in content
        assert content.index("apply_dashboard_theme()") < content.index("render_navigation()")
        assert content.index("render_navigation()") < content.index("render_page_header(")


def test_dashboard_tables_use_display_ready_dataframes():
    for page in [
        Path("app/Home.py"),
        Path("app/pages/3_留存复购.py"),
        Path("app/pages/5_商品与履约.py"),
    ]:
        content = page.read_text(encoding="utf-8")
        assert "display_dataframe(" in content
