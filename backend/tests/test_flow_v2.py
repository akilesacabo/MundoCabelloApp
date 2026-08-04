"""Flujo v2: check-in → asignación por servicio → cambio con PIN → finalizar → historial."""
from __future__ import annotations

import json

import pytest

from src.seed import DATA_PATH, _unique_staff_rows

pytestmark = pytest.mark.asyncio


async def test_seed_preserves_duplicate_staff_with_explicit_provisional_number():
    rows, warnings = _unique_staff_rows(
        [
            {"numero": 20, "alias": "Stheisy"},
            {"numero": 20, "alias": "Argemar"},
        ]
    )
    assert [row["numero"] for row in rows] == [20, 21]
    assert "duplicado 20" in warnings[0]


async def test_master_roster_contains_excel_and_supplemental_staff():
    data = json.loads(DATA_PATH.read_text())
    assert len(data["staff"]) == 90
    assert len({row["numero"] for row in data["staff"]}) == 90
    by_alias = {row["alias"].casefold(): row for row in data["staff"]}
    assert by_alias["marilyn"]["areas"] == ["cejas"]
    assert by_alias["aura"]["areas"] == ["maquillaje"]
    assert by_alias["day"]["areas"] == ["hidratacion"]
    assert "kendry" in by_alias  # incorporación existente conservada
    assert next(area for area in data["areas"] if area["key"] == "cejas")[
        "name"
    ] == "Cejas y depilación"


async def test_health(api):
    r = await api["ac"].get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_cors_allows_documented_demo_port(api):
    r = await api["ac"].options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["access-control-allow-origin"] == "http://localhost:5174"


async def test_checkin_creates_pending_services(api):
    r = await api["ac"].post(
        "/api/queue/checkin",
        json={
            "cedula": "V-14.220.100",
            "nombre": "Rosa Delgado",
            "telefono": "+584141234567",
            "direccion": "Av Principal 123",
            "observacion": "prefiere secado",
            "etiquetas": ["F", "TC"],
            "service_ids": [api["corte_id"], api["hidra_id"]],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "en_espera"
    assert body["observacion"] == "prefiere secado"
    assert body["etiquetas"] == ["F", "TC"]
    assert body["situacion"] == "presente"
    assert body["activo"] is True
    assert body["turno"] >= 13
    assert len(body["servicios"]) == 2
    for sv in body["servicios"]:
        assert sv["estado"] == "pendiente"
        assert sv["staff_numero"] is None
        assert "pendientes_area" in sv


async def test_queue_reports_pending_clients_by_service_area(api):
    ac = api["ac"]
    first = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-31000001",
            "nombre": "Cliente Area Uno",
            "telefono": "04141234567",
            "direccion": "Calle 1",
            "service_ids": [api["corte_id"], api["hidra_id"]],
        },
    )
    assert first.status_code == 201, first.text
    second = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-31000002",
            "nombre": "Cliente Area Dos",
            "telefono": "04141234567",
            "direccion": "Calle 2",
            "service_ids": [api["corte_id"]],
        },
    )
    assert second.status_code == 201, second.text

    queue = await ac.get("/api/queue", headers=api["admin_headers"])
    rows = queue.json()
    first_row = next(row for row in rows if row["id"] == first.json()["id"])
    corte = next(
        service
        for service in first_row["servicios"]
        if service["area_key"] == "peluqueria"
    )
    hidra = next(
        service
        for service in first_row["servicios"]
        if service["area_key"] == "hidratacion"
    )
    assert corte["pendientes_area"] == 2
    assert hidra["pendientes_area"] == 1

    await ac.post(
        f"/api/queue/{first_row['id']}/services/{corte['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    queue = await ac.get("/api/queue", headers=api["admin_headers"])
    rows = queue.json()
    first_row = next(row for row in rows if row["id"] == first.json()["id"])
    second_row = next(row for row in rows if row["id"] == second.json()["id"])
    assigned_corte = next(
        service for service in first_row["servicios"] if service["id"] == corte["id"]
    )
    second_corte = next(
        service
        for service in second_row["servicios"]
        if service["area_key"] == "peluqueria"
    )
    assert assigned_corte["pendientes_area"] == 1
    assert second_corte["pendientes_area"] == 1


async def _checkin(ac, ids):
    r = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-12345678",
            "nombre": "Cliente Uno",
            "telefono": "04141234567",
            "direccion": "Calle 1",
            "service_ids": [ids["corte_id"], ids["hidra_id"]],
        },
    )
    return r.json()


async def test_assign_and_finish_flow(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)
    corte_sv = next(s for s in cli["servicios"] if s["area_key"] == "peluqueria")
    hidra_sv = next(s for s in cli["servicios"] if s["area_key"] == "hidratacion")

    # 1) Asignar corte a Ana (numero=1, cubre peluquería)
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado"] == "en_atencion"
    assigned = next(s for s in body["servicios"] if s["id"] == corte_sv["id"])
    assert assigned["estado"] == "en_atencion"
    assert assigned["asignado_por_nombre"] == "Administración"

    # 2) Ana ya está OCUPADO por el corte activo
    r = await ac.get("/api/staff/1")
    assert r.json()["status"] == "ocupado"
    assert len(r.json()["activos"]) == 1

    # 3) Beto (numero=2) NO cubre peluquería -> rechazado
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/assign",
        json={"staff_numero": 2},
        headers=api["admin_headers"],
    )
    assert r.status_code == 400

    # 4) Asignar hidratación a Beto
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{hidra_sv['id']}/assign",
        json={"staff_numero": 2},
        headers=api["admin_headers"],
    )
    assert r.status_code == 200

    # 5) Finalizar corte → aparece en historial
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/finish",
        headers=api["admin_headers"],
    )
    assert r.status_code == 200
    r = await ac.get("/api/historial")
    assert r.status_code == 403
    r = await ac.get("/api/historial", headers=api["admin_headers"])
    hist = r.json()
    assert len(hist) == 1
    assert hist[0]["servicio_nombre"] == "CORTE DAMA"
    assert hist[0]["staff_numero"] == 1
    r = await ac.get("/api/historial/summary", headers=api["admin_headers"])
    assert r.status_code == 200
    assert r.json()["total_servicios"] == 1
    assert r.json()["por_area"][0]["area_key"] == "peluqueria"

    # 6) Ana vuelve a DISPONIBLE (no tiene más servicios EN_ATENCION)
    r = await ac.get("/api/staff/1")
    assert r.json()["status"] == "disponible"


async def test_change_specialist_requires_pin(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)
    corte_sv = next(s for s in cli["servicios"] if s["area_key"] == "peluqueria")
    await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )

    # PIN inválido → 403
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/change-specialist",
        json={"staff_numero": 3, "pin": "0000", "motivo": "prefiere otra"},
        headers=api["admin_headers"],
    )
    assert r.status_code == 403

    # PIN correcto pero motivo vacío → validación 422 (pydantic)
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/change-specialist",
        json={"staff_numero": 3, "pin": "1234", "motivo": ""},
        headers=api["admin_headers"],
    )
    assert r.status_code == 422

    await ac.patch(
        "/api/staff/3/manual-status",
        json={"manual_status": "disponible"},
        headers=api["admin_headers"],
    )

    # PIN correcto + motivo → cambio y log
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/change-specialist",
        json={"staff_numero": 3, "pin": "1234", "motivo": "cliente prefiere a Cami"},
        headers=api["admin_headers"],
    )
    assert r.status_code == 200, r.text
    sv = next(s for s in r.json()["servicios"] if s["id"] == corte_sv["id"])
    assert sv["staff_numero"] == 3
    assert sv["asignado_por_nombre"] == "Administración"
    assert len(sv["cambios"]) == 1
    assert sv["cambios"][0]["de_staff"] == 1
    assert sv["cambios"][0]["a_staff"] == 3
    assert sv["cambios"][0]["motivo"] == "cliente prefiere a Cami"
    assert sv["cambios"][0]["cambiado_por_nombre"] == "Administración"


async def test_assign_many_to_same_staff(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)
    ids = [s["id"] for s in cli["servicios"]]
    # Ana cubre ambas áreas → puede tomarse los dos
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/assign-many",
        json={"servicio_ids": ids, "staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert r.status_code == 200
    for sv in r.json()["servicios"]:
        assert sv["staff_numero"] == 1
        assert sv["estado"] == "en_atencion"
        assert sv["asignado_por_nombre"] == "Administración"


async def test_admin_updates_visit_details_are_audited(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)

    details = await ac.patch(
        f"/api/queue/{cli['id']}/details",
        json={"observacion": "Color sensible", "etiquetas": ["INT"]},
        headers=api["admin_headers"],
    )
    assert details.status_code == 200, details.text
    assert details.json()["actualizado_por_nombre"] == "Administración"

    situation = await ac.patch(
        f"/api/queue/{cli['id']}/situacion",
        json={"situacion": "ausente"},
        headers=api["admin_headers"],
    )
    assert situation.status_code == 200, situation.text
    assert situation.json()["actualizado_por_nombre"] == "Administración"


async def test_eligible_staff_excludes_break_and_wrong_area(api):
    ac = api["ac"]
    # Peluquería: Ana (DISPONIBLE, cubre) sí; Cami (BREAK) no; Beto (no cubre) no.
    r = await ac.get("/api/staff/eligible", params={"area": "peluqueria"})
    assert r.status_code == 200
    numeros = {s["numero"] for s in r.json()}
    assert numeros == {1}


async def test_toggle_en_prueba_and_manual_status(api):
    ac = api["ac"]
    r = await ac.post(
        "/api/staff/1/toggle-en-prueba", headers=api["admin_headers"]
    )
    assert r.json()["en_prueba"] is True
    r = await ac.patch(
        "/api/staff/1/manual-status",
        json={"manual_status": "break"},
        headers=api["admin_headers"],
    )
    assert r.json()["status"] == "break"


async def test_manual_busy_status_is_selectable_and_excluded_from_eligible(api):
    ac = api["ac"]
    changed = await ac.patch(
        "/api/staff/1/manual-status",
        json={"manual_status": "ocupado"},
        headers=api["admin_headers"],
    )
    assert changed.status_code == 200
    assert changed.json()["manual_status"] == "ocupado"
    assert changed.json()["status"] == "ocupado"

    eligible = await ac.get("/api/staff/eligible", params={"area": "peluqueria"})
    assert 1 not in {row["numero"] for row in eligible.json()}

    client = await _checkin(ac, api)
    service = next(
        item for item in client["servicios"] if item["area_key"] == "peluqueria"
    )
    rejected = await ac.post(
        f"/api/queue/{client['id']}/services/{service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert rejected.status_code == 400
    assert "no está disponible" in rejected.json()["detail"]


async def test_progressive_profile_search_client_database_and_duplicate_guard(api):
    ac = api["ac"]
    created = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-25.482.938",
            "nombre": "Ambar Vegas",
            "telefono": "04145551212",
            "direccion": "Los Palos Grandes",
            "observacion": "Primera visita",
            "etiquetas": ["XL", "CM"],
            "service_ids": [api["corte_id"]],
        },
    )
    assert created.status_code == 201, created.text

    matches = await ac.get("/api/queue/client-search", params={"q": "2548"})
    assert matches.status_code == 200
    assert matches.json()[0]["nombre"] == "Ambar Vegas"
    assert matches.json()[0]["cedula"] == "V-25482938"
    assert matches.json()[0]["active_turno_id"] == created.json()["id"]
    assert matches.json()[0]["active_turno"] == created.json()["turno"]

    profiles = await ac.get(
        "/api/queue/clients", headers=api["admin_headers"]
    )
    assert profiles.status_code == 200
    profile = next(row for row in profiles.json() if row["cedula"] == "V-25482938")
    assert profile["visitas"] == 1
    assert profile["etiquetas"] == ["CM", "XL"]

    duplicate = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V25482938",
            "nombre": "Ambar Vegas",
            "telefono": "04145551212",
            "direccion": "Los Palos Grandes",
            "service_ids": [api["corte_id"]],
        },
    )
    assert duplicate.status_code == 409
    assert "turno activo" in duplicate.json()["detail"]

    await ac.patch(
        f"/api/queue/{created.json()['id']}/situacion",
        json={"situacion": "estafa"},
        headers=api["admin_headers"],
    )
    flagged = await ac.get("/api/queue/client-search", params={"q": "2548"})
    assert flagged.status_code == 200
    assert flagged.json()[0]["alerta_estafa"] is True


async def test_admin_can_update_visit_tags_and_observation(api):
    client = await _checkin(api["ac"], api)
    initial = await api["ac"].patch(
        f"/api/queue/{client['id']}/details",
        json={"observacion": "Primera nota", "etiquetas": ["F"]},
        headers=api["admin_headers"],
    )
    assert initial.status_code == 200

    updated = await api["ac"].patch(
        f"/api/queue/{client['id']}/details",
        json={"observacion": "Usar producto suave", "etiquetas": ["F", "AC"]},
        headers=api["admin_headers"],
    )
    assert updated.status_code == 200
    assert updated.json()["observacion"] == "Usar producto suave"
    assert updated.json()["etiquetas"] == ["AC", "F"]


async def test_selected_profile_can_append_services_to_active_turn(api):
    ac = api["ac"]
    client = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-25482938",
            "nombre": "Ambar Vegas",
            "telefono": "04145551212",
            "direccion": "Los Palos Grandes",
            "etiquetas": ["INT"],
            "service_ids": [api["corte_id"]],
        },
    )
    assert client.status_code == 201
    original = client.json()

    appended = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V25482938",
            "nombre": "Ambar Vegas",
            "telefono": "04145551212",
            "direccion": "Los Palos Grandes",
            "observacion": "Agregar hidratación",
            "etiquetas": ["F"],
            "service_ids": [api["hidra_id"]],
            "active_turno_id": original["id"],
        },
    )

    assert appended.status_code == 201, appended.text
    body = appended.json()
    assert body["id"] == original["id"]
    assert body["turno"] == original["turno"]
    assert len(body["servicios"]) == 2
    assert body["observacion"] == "Agregar hidratación"
    assert body["etiquetas"] == ["F", "INT"]


async def test_admin_can_open_detailed_client_history(api):
    client = await _checkin(api["ac"], api)
    service = next(
        item for item in client["servicios"] if item["area_key"] == "peluqueria"
    )
    assigned = await api["ac"].post(
        f"/api/queue/{client['id']}/services/{service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert assigned.status_code == 200

    profiles = await api["ac"].get(
        "/api/queue/clients", headers=api["admin_headers"]
    )
    profile = next(
        row for row in profiles.json() if row["cedula"] == client["cedula"]
    )
    detail = await api["ac"].get(
        f"/api/queue/clients/{profile['id']}", headers=api["admin_headers"]
    )

    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["nombre"] == "Cliente Uno"
    assert len(body["visitas"]) == 1
    visit = body["visitas"][0]
    assert visit["turno"] == client["turno"]
    assert visit["estado"] == "en_atencion"
    assert visit["situacion"] == "presente"
    assigned_service = next(
        item for item in visit["servicios"] if item["id"] == service["id"]
    )
    assert assigned_service["staff_numero"] == 1
    assert assigned_service["especialista"] == "Ana"

    await api["ac"].patch(
        f"/api/queue/{client['id']}/situacion",
        json={"situacion": "estafa"},
        headers=api["admin_headers"],
    )
    second_visit = await api["ac"].post(
        "/api/queue/checkin",
        json={
            "cedula": client["cedula"],
            "nombre": "Cliente Uno",
            "telefono": "04141234567",
            "direccion": "Calle 1",
            "service_ids": [api["hidra_id"]],
        },
    )
    assert second_visit.status_code == 201
    updated_detail = await api["ac"].get(
        f"/api/queue/clients/{profile['id']}", headers=api["admin_headers"]
    )
    assert [item["turno"] for item in updated_detail.json()["visitas"]] == [
        second_visit.json()["turno"],
        client["turno"],
    ]

    denied = await api["ac"].get(f"/api/queue/clients/{profile['id']}")
    assert denied.status_code == 403
    missing = await api["ac"].get(
        "/api/queue/clients/999999", headers=api["admin_headers"]
    )
    assert missing.status_code == 404


async def test_finished_or_estafa_turn_is_not_active(api):
    ac = api["ac"]
    client = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-19990000",
            "nombre": "Cliente Final",
            "telefono": "04141112222",
            "direccion": "Calle Final",
            "service_ids": [api["corte_id"]],
        },
    )
    body = client.json()
    service = body["servicios"][0]
    await ac.post(
        f"/api/queue/{body['id']}/services/{service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    finished = await ac.post(
        f"/api/queue/{body['id']}/services/{service['id']}/finish",
        headers=api["admin_headers"],
    )
    assert finished.json()["activo"] is False

    repeated = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V19990000",
            "nombre": "Cliente Final",
            "telefono": "04141112222",
            "direccion": "Calle Final",
            "service_ids": [api["corte_id"]],
        },
    )
    assert repeated.status_code == 201


async def test_roles_public_queue_and_operational_situation(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)
    corte = next(s for s in cli["servicios"] if s["area_key"] == "peluqueria")

    denied = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte['id']}/assign",
        json={"staff_numero": 1},
    )
    assert denied.status_code == 403

    await ac.post(
        f"/api/queue/{cli['id']}/services/{corte['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    public = await ac.get("/api/queue/public/status")
    assert cli["turno"] in public.json()["atendiendo"]
    by_area = {area["area_key"]: area for area in public.json()["por_area"]}
    assert by_area["peluqueria"]["atendiendo"][0]["turno"] == cli["turno"]

    await ac.patch(
        f"/api/queue/{cli['id']}/situacion",
        json={"situacion": "ausente"},
        headers=api["admin_headers"],
    )
    public = await ac.get("/api/queue/public/status")
    assert cli["turno"] not in public.json()["atendiendo"]


async def test_public_queue_and_position_search_are_split_by_service_area(api):
    ac = api["ac"]
    first = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-41000001",
            "nombre": "Cliente Multi Area",
            "telefono": "04141234567",
            "direccion": "Calle 1",
            "service_ids": [api["corte_id"], api["hidra_id"]],
        },
    )
    second = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-41000002",
            "nombre": "Cliente Peluqueria",
            "telefono": "04141234567",
            "direccion": "Calle 2",
            "service_ids": [api["corte_id"]],
        },
    )
    first_body = first.json()
    second_body = second.json()
    first_corte = next(
        service
        for service in first_body["servicios"]
        if service["area_key"] == "peluqueria"
    )
    await ac.post(
        f"/api/queue/{first_body['id']}/services/{first_corte['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )

    public = await ac.get("/api/queue/public/status")
    assert public.status_code == 200
    by_area = {area["area_key"]: area for area in public.json()["por_area"]}
    assert by_area["peluqueria"]["atendiendo"][0]["turno"] == first_body["turno"]
    assert by_area["peluqueria"]["en_espera"][0]["turno"] == second_body["turno"]
    assert by_area["peluqueria"]["en_espera"][0]["posicion"] == 1
    assert by_area["hidratacion"]["en_espera"][0]["turno"] == first_body["turno"]
    assert by_area["hidratacion"]["en_espera"][0]["personas_delante"] == 0

    position = await ac.get(
        "/api/queue/position-search",
        params={"q": str(first_body["turno"])},
        headers=api["admin_headers"],
    )
    assert position.status_code == 200
    areas = {area["area_key"]: area for area in position.json()[0]["areas"]}
    assert areas["peluqueria"]["estado"] == "en_atencion"
    assert areas["peluqueria"]["posicion"] is None
    assert areas["hidratacion"]["posicion"] == 1
    assert areas["hidratacion"]["personas_delante"] == 0


async def test_specialist_only_sees_and_finishes_own_work(api):
    ac = api["ac"]
    cli = await _checkin(ac, api)
    corte = next(s for s in cli["servicios"] if s["area_key"] == "peluqueria")
    await ac.post(
        f"/api/queue/{cli['id']}/services/{corte['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    login = await ac.post(
        "/api/auth/login",
        json={"role": "especialista", "username": "1", "password": "V-1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    mine = await ac.get("/api/queue/specialist/mine", headers=headers)
    assert [row["id"] for row in mine.json()] == [cli["id"]]
    assert [service["id"] for service in mine.json()[0]["servicios"]] == [corte["id"]]
    finished = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte['id']}/finish", headers=headers
    )
    assert finished.status_code == 200


async def test_reposo_releases_specialist_and_allows_parallel_attention(api):
    ac = api["ac"]
    first = await _checkin(ac, api)
    first_service = next(
        service for service in first["servicios"] if service["area_key"] == "peluqueria"
    )
    assigned = await ac.post(
        f"/api/queue/{first['id']}/services/{first_service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert assigned.status_code == 200

    resting = await ac.post(
        f"/api/queue/{first['id']}/services/{first_service['id']}/rest",
        headers=api["admin_headers"],
    )
    assert resting.status_code == 200
    assert resting.json()["estado"] == "reposo"
    staff = await ac.get("/api/staff/1")
    assert staff.json()["status"] == "disponible"
    assert staff.json()["activos"][0]["estado"] == "reposo"

    second = await ac.post(
        "/api/queue/checkin",
        json={
            "cedula": "V-24681357",
            "nombre": "Cliente Dos",
            "telefono": "04141234567",
            "direccion": "Calle 2",
            "service_ids": [api["corte_id"]],
        },
    )
    second_body = second.json()
    second_service = second_body["servicios"][0]
    assigned_second = await ac.post(
        f"/api/queue/{second_body['id']}/services/{second_service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert assigned_second.status_code == 200

    resumed = await ac.post(
        f"/api/queue/{first['id']}/services/{first_service['id']}/resume",
        headers=api["admin_headers"],
    )
    assert resumed.status_code == 200
    staff = await ac.get("/api/staff/1")
    assert staff.json()["status"] == "ocupado"
    assert len(staff.json()["activos"]) == 2


async def test_almorzando_is_not_eligible_or_assignable(api):
    ac = api["ac"]
    changed = await ac.patch(
        "/api/staff/1/manual-status",
        json={"manual_status": "almorzando"},
        headers=api["admin_headers"],
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "almorzando"
    eligible = await ac.get("/api/staff/eligible", params={"area": "peluqueria"})
    assert 1 not in [row["numero"] for row in eligible.json()]

    client = await _checkin(ac, api)
    service = next(
        item for item in client["servicios"] if item["area_key"] == "peluqueria"
    )
    rejected = await ac.post(
        f"/api/queue/{client['id']}/services/{service['id']}/assign",
        json={"staff_numero": 1},
        headers=api["admin_headers"],
    )
    assert rejected.status_code == 400


async def test_int_priority_name_order_position_and_registrar(api):
    ac = api["ac"]

    async def create(cedula: str, nombre: str, tags: list[str]):
        response = await ac.post(
            "/api/queue/checkin",
            json={
                "cedula": cedula,
                "nombre": nombre,
                "telefono": "04141234567",
                "direccion": "Calle",
                "etiquetas": tags,
                "service_ids": [api["corte_id"]],
            },
            headers=api["admin_headers"],
        )
        assert response.status_code == 201, response.text
        return response.json()

    zeta = await create("V-11111111", "Zeta Pérez", [])
    ana = await create("V-22222222", "Ana Pérez", [])
    beta = await create("V-33333333", "Beta Pérez", ["INT"])

    queue = await ac.get("/api/queue", headers=api["admin_headers"])
    assert [row["nombre"] for row in queue.json()] == [
        "Beta Pérez",
        "Ana Pérez",
        "Zeta Pérez",
    ]
    assert beta["registrado_por_nombre"] == "Administración"
    assert zeta["registrado_por_role"] == "admin"

    position = await ac.get(
        "/api/queue/position-search",
        params={"q": str(zeta["turno"])},
        headers=api["admin_headers"],
    )
    assert position.status_code == 200
    assert position.json()[0]["posicion"] == 3
    assert position.json()[0]["personas_delante"] == 2
    assert position.json()[0]["prioridad_int"] is False

    updated = await ac.patch(
        f"/api/queue/{ana['id']}/details",
        json={"etiquetas": ["INT"], "observacion": ""},
        headers=api["admin_headers"],
    )
    assert updated.status_code == 200
    queue = await ac.get("/api/queue", headers=api["admin_headers"])
    assert [row["nombre"] for row in queue.json()] == [
        "Ana Pérez",
        "Beta Pérez",
        "Zeta Pérez",
    ]
