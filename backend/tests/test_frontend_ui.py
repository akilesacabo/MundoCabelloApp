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
    assert "assignment-only" in html
    assert "Progreso de asignación" in html
    assert "/staff/eligible?area=" in html
    assert "/services/${serviceId}/assign" in html
    assert "applyRoleNavigation()" in (APP_DIR / "api.js").read_text()
    assert 'oninput="highlightSpecialist(this)"' in html
    assert "specialist-selected" in html
    assert 'class="specialist-search"' in html
    assert "<datalist" in html


def test_public_queue_preserves_and_recognizes_team_session():
    api_js = (APP_DIR / "api.js").read_text()
    queue_html = (APP_DIR / "queue.html").read_text()
    login_html = (APP_DIR / "login.html").read_text()

    assert "function sessionRole()" in api_js
    assert "sessionHome()" in queue_html
    assert "Volver a asignaciones" in queue_html
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


def test_checkin_is_three_steps_with_live_client_search_and_submit_lock():
    html = (APP_DIR / "checkin.html").read_text()

    assert 'data-step="1"' in html
    assert 'data-step="2"' in html
    assert 'data-step="3"' in html
    assert "/queue/client-search?q=" in html
    assert "if(submitting)return" in html
    assert 'name="etiquetas"' in html
    assert "normalize(service.nombre).includes(term)" in html
    assert "active_turno_id:selectedProfile?.active_turno_id" in html
    assert "goToStep(2)" in html
    assert "Registrar otra persona" in html
    assert 'id="checkinSuccess"' in html


def test_admin_has_separate_assignment_team_and_client_database_screens():
    assignment = (APP_DIR / "admin.html").read_text()
    team = (APP_DIR / "admin-team.html").read_text()
    clients = (APP_DIR / "admin-clients.html").read_text()
    api_js = (APP_DIR / "api.js").read_text()

    assert "assignment-only" in assignment
    assert "/manual-status" in team
    assert "/queue/clients" in clients
    assert "/queue/clients/${profileId}" in clients
    assert 'id="clientModal"' in clients
    assert "Historial de visitas" in clients
    assert "service.especialista" in clients
    assert 'href="checkin.html"' in assignment
    assert "Registrar nuevo check-in" in assignment
    assert 'href="admin-clients.html"' in assignment
    assert "Clientes registrados" in assignment
    assert "admin-team.html" in api_js
    assert 'class="client-table"' in clients
    assert "downloadClients()" in clients
    assert "text/csv;charset=utf-8" in clients
    assert "const PAGE_SIZE=25" in clients


def test_public_queue_explains_parallel_attention():
    html = (APP_DIR / "queue.html").read_text()

    assert "La atención ocurre en paralelo" in html
    assert "¿Cómo leer esta pantalla?" in html
    assert "Después siguen" in html
    assert 'class="queue-topbar"' in html


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


def test_specialist_tablet_controls_have_touch_sized_targets():
    css = (APP_DIR / "styles.css").read_text()

    assert ".specialist-service button { min-width:104px;min-height:44px" in css
    assert "@media (min-width:700px) and (max-width:900px)" in css
    assert ".specialist-grid { grid-template-columns:1fr }" in css
    assert "@media (hover:none) and (pointer:coarse)" in css


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
        assert 'class="modern-page' in html

    css = (APP_DIR / "styles.css").read_text()
    assert "prefers-reduced-motion" in css
    assert ".modal-backdrop" in css


def test_all_screens_expose_role_appropriate_navigation():
    filenames = (
        "login.html",
        "queue.html",
        "checkin.html",
        "admin.html",
        "admin-staff.html",
        "admin-services.html",
        "specialist.html",
        "admin-team.html",
        "admin-clients.html",
    )
    for filename in filenames:
        html = (APP_DIR / filename).read_text()
        assert "site-nav" in html

    api_js = (APP_DIR / "api.js").read_text()
    for link in (
        "checkin.html",
        "queue.html",
        "admin.html",
        "admin-team.html",
        "admin-staff.html",
        "admin-services.html",
        "specialist.html",
    ):
        assert link in api_js
    assert 'href="admin-clients.html"' in (APP_DIR / "admin.html").read_text()
