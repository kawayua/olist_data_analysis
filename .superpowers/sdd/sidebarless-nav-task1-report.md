# Sidebarless glass navigation — Task 1 report

## Scope

- Removed all Streamlit filter-control rendering from `app/components/filters.py`.
- Updated the four filtered analysis pages to invoke their cached loaders with `DashboardFilters()` and kept the customer-value page's unfiltered loader unchanged.
- Removed filter-dependent copy and state handling while retaining repository calls, cache decorators, and query contracts.
- Hid the complete Streamlit sidebar and converted the five-page navigation into a centered, sticky glass pill with content-width links, hover, focus-visible, current-page, and mobile wrapping styles.

## TDD evidence

### RED 1

Command:

```powershell
py -3.13 -m pytest tests/visualization/test_dashboard_pages.py tests/visualization/test_navigation.py -v
```

Result: 4 failed, 4 passed. The failures correctly identified the old page filter renderers, missing `DashboardFilters()` calls, sidebar visibility CSS, old navigation dimensions, and `use_container_width` usage.

### GREEN 1

Commands:

```powershell
py -3.13 -m pytest tests/visualization/test_dashboard_components.py tests/visualization/test_dashboard_pages.py tests/visualization/test_navigation.py -v
py -3.13 -m ruff check app tests/visualization
```

Result: 17 passed; Ruff returned `All checks passed!`.

### RED 2

Command:

```powershell
py -3.13 -m pytest tests/visualization/test_dashboard_pages.py -v
```

Result: 1 failed, 4 passed. The new empty-state contract caught the remaining `当前筛选` instruction on the operating-overview page.

### GREEN 2 / final verification

Commands:

```powershell
py -3.13 -m pytest tests/visualization/test_dashboard_components.py tests/visualization/test_dashboard_pages.py tests/visualization/test_navigation.py -v
py -3.13 -m ruff check app tests/visualization
git diff --check
```

Result: all 18 selected tests passed in 1.06s; Ruff returned `All checks passed!`; `git diff --check` returned exit code 0.

## Self-review checklist

- Sidebar is hidden as a whole with `[data-testid="stSidebar"] { display: none; }`.
- Navigation stays limited to the five analysis pages and no longer passes `use_container_width` to `st.page_link`.
- Navigation is sticky at 48px on desktop, centered, constrained to the viewport, has a 28px pill radius, translucent background, border, shadow, 180ms transitions, hover/current/focus-visible states, and mobile wrapping.
- Filter-control functions and Streamlit import were removed from the filters component.
- Cached loaders and repository filter conversion remain intact; each former filtered page supplies a default `DashboardFilters()` instance.
- No unrelated pre-existing documentation changes, untracked plans, or pytest temporary files were staged.
