from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"


def test_management_screens_use_search_and_pagination_for_large_catalogs():
    staff_html = (APP_DIR / "admin-staff.html").read_text()
    service_html = (APP_DIR / "admin-services.html").read_text()

    assert 'id="staffSearch"' in staff_html
    assert 'id="staffPagination"' in staff_html
    assert "const PAGE_SIZE=12" in staff_html
    assert 'id="serviceSearch"' in service_html
    assert 'id="servicePagination"' in service_html
    assert "const PAGE_SIZE=12" in service_html
    assert "group.area.key" in service_html
    assert 'id="staffModal"' in staff_html
    assert 'id="serviceModal"' in service_html
    assert "prompt(" not in staff_html
    assert "prompt(" not in service_html


def test_admin_dashboard_prioritizes_status_and_assignment():
    html = (APP_DIR / "admin.html").read_text()

    assert 'class="metric-grid"' in html
    assert "Clientes activos" in html
    assert "Especialistas" in html
    assert "Progreso de asignación" in html
    assert "/staff/eligible?area=" in html
    assert "/services/${serviceId}/assign" in html
    assert 'href="admin-staff.html"' in html
    assert 'href="admin-services.html"' in html


def test_public_queue_preserves_and_recognizes_team_session():
    api_js = (APP_DIR / "api.js").read_text()
    queue_html = (APP_DIR / "queue.html").read_text()
    login_html = (APP_DIR / "login.html").read_text()

    assert "function sessionRole()" in api_js
    assert "sessionHome()" in queue_html
    assert "Volver al panel" in queue_html
    assert "localStorage.setItem('peluq_role',x.role)" in login_html
    assert "localStorage.removeItem('peluq_role')" in api_js


def test_checkin_uses_searchable_checkbox_picker_instead_of_native_multiselect():
    html = (APP_DIR / "checkin.html").read_text()

    assert 'id="serviceGroups"' in html
    assert 'id="selectedServices"' in html
    assert 'id="clearServices"' in html
    assert "selectedIds" in html
    assert "group.area.key" in html
    assert "multiple" not in html


def test_staff_areas_use_visual_multi_selection():
    html = (APP_DIR / "admin-staff.html").read_text()

    assert 'id="createAreaPicker"' in html
    assert 'id="editAreaPicker"' in html
    assert "formData.getAll('areas')" in html
    assert "document.querySelectorAll('.edit-area:checked')" in html
    assert "Áreas, separadas por coma" not in html


def test_specialist_has_an_explicit_empty_state():
    html = (APP_DIR / "specialist.html").read_text()

    assert "No tienes clientes pendientes" in html
    assert "empty-state" in html
    assert 'id="clientSearch"' in html


def test_secondary_screens_use_shared_modern_design():
    for filename in (
        "admin-staff.html",
        "admin-services.html",
        "checkin.html",
        "specialist.html",
        "login.html",
        "queue.html",
    ):
        html = (APP_DIR / filename).read_text()
        assert 'class="modern-page"' in html

    css = (APP_DIR / "styles.css").read_text()
    assert "prefers-reduced-motion" in css
    assert ".modal-backdrop" in css


def test_all_screens_expose_role_appropriate_navigation():
    expected_links = {
        "login.html": ("checkin.html", "queue.html"),
        "queue.html": ("checkin.html", "login.html"),
        "checkin.html": ("queue.html", "login.html"),
        "admin.html": ("checkin.html", "queue.html", "admin-staff.html", "admin-services.html"),
        "admin-staff.html": ("admin.html", "queue.html", "admin-services.html"),
        "admin-services.html": ("admin.html", "queue.html", "admin-staff.html"),
        "specialist.html": ("checkin.html", "queue.html"),
    }

    for filename, links in expected_links.items():
        html = (APP_DIR / filename).read_text()
        assert "site-nav" in html
        for link in links:
            assert f'href="{link}"' in html
