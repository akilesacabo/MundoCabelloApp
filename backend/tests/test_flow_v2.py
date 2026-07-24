"""Flujo v2: check-in → asignación por servicio → cambio con PIN → finalizar → historial."""
from __future__ import annotations

import pytest

from src.seed import _unique_staff_rows

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
            "service_ids": [api["corte_id"], api["hidra_id"]],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "en_espera"
    assert body["observacion"] == "prefiere secado"
    assert body["turno"] >= 13
    assert len(body["servicios"]) == 2
    for sv in body["servicios"]:
        assert sv["estado"] == "pendiente"
        assert sv["staff_numero"] is None


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
    hist = r.json()
    assert len(hist) == 1
    assert hist[0]["servicio_nombre"] == "CORTE DAMA"
    assert hist[0]["staff_numero"] == 1

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

    # PIN correcto + motivo → cambio y log
    r = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte_sv['id']}/change-specialist",
        json={"staff_numero": 3, "pin": "1234", "motivo": "cliente prefiere a Cami"},
        headers=api["admin_headers"],
    )
    assert r.status_code == 200, r.text
    sv = next(s for s in r.json()["servicios"] if s["id"] == corte_sv["id"])
    assert sv["staff_numero"] == 3
    assert len(sv["cambios"]) == 1
    assert sv["cambios"][0]["de_staff"] == 1
    assert sv["cambios"][0]["a_staff"] == 3
    assert sv["cambios"][0]["motivo"] == "cliente prefiere a Cami"


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

    await ac.patch(
        f"/api/queue/{cli['id']}/situacion",
        json={"situacion": "ausente"},
        headers=api["admin_headers"],
    )
    public = await ac.get("/api/queue/public/status")
    assert cli["turno"] not in public.json()["atendiendo"]


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
    finished = await ac.post(
        f"/api/queue/{cli['id']}/services/{corte['id']}/finish", headers=headers
    )
    assert finished.status_code == 200
