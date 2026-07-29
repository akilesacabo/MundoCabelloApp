# El Mundo del Cabello — Backend (Fase 1)

API FastAPI para el MVP: autenticación por roles, registro e historial de
clientes, check-in y gestión de la cola con asignación de especialistas.

## Stack

- **FastAPI** (async) + **Pydantic v2**
- **SQLAlchemy 2.0 async** + **Alembic** para migraciones
- **SQLite** en local (driver `aiosqlite`, cero setup) — switch a
  Postgres en producción cambiando `DATABASE_URL` a
  `postgresql+asyncpg://...`
- **pytest + httpx.AsyncClient** para tests async

## Estructura

```
backend/
├── src/
│   ├── config.py          # Settings (pydantic-settings)
│   ├── database.py        # engine async + get_db
│   ├── models.py          # SQLAlchemy Base + naming convention
│   ├── exceptions.py      # AppError, NotFound, BadRequest, Conflict
│   ├── dependencies.py    # DbSession typed alias
│   ├── pagination.py      # PageParams / Page (no usado en Fase 1)
│   ├── main.py            # FastAPI app, lifespan, CORS, exception handler
│   ├── seed.py            # Carga el catálogo, especialistas y usuarios demo
│   ├── auth/              # Login y autorización por roles
│   ├── historial/         # Historial detallado de servicios por cliente
│   ├── services/          # Dominio: catálogo (áreas + servicios)
│   ├── staff/             # Dominio: personal con status
│   └── turnos/            # Clientes, turnos, etiquetas y transiciones
├── alembic/               # migraciones async
├── tests/                 # tests async con DB en memoria
├── requirements/          # base / dev / prod
├── .env.example
└── pyproject.toml
```

Cada dominio sigue la convención del skill `fastapi-project`:
`router.py` (HTTP wiring) + `schemas.py` (Pydantic) + `models.py`
(SQLAlchemy) + `service.py` (lógica + DB) + `dependencies.py`
(validación) + `exceptions.py`.

## Arranque local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
pip install aiosqlite        # driver SQLite async

cp .env.example .env         # DATABASE_URL apunta a sqlite+aiosqlite:///./peluq.db

alembic upgrade head         # crea las tablas
python -m src.seed           # carga catálogo, especialistas y usuarios demo

uvicorn src.main:app --reload
# docs: http://localhost:8000/docs
```

## Endpoints

| Verbo | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (hace `SELECT 1` contra la DB) |
| POST | `/api/auth/login` | Autentica administrador o especialista |
| GET | `/api/auth/me` | Devuelve el usuario autenticado |
| GET | `/api/services` | Catálogo agrupado por área |
| POST | `/api/queue/checkin` | Crea un turno o agrega servicios al turno activo |
| GET | `/api/queue` | Lista clientes activos |
| GET | `/api/queue/public/status` | Estado público de la cola |
| GET | `/api/queue/position-search` | Busca un turno y calcula personas por delante |
| GET | `/api/queue/client-search` | Busca perfiles y señala su turno activo |
| GET | `/api/queue/clients` | Lista la base de clientes registrados |
| GET | `/api/queue/clients/{id}` | Ficha e historial de un cliente |
| POST | `/api/queue/{id}/services/{service_id}/assign` | Asigna un especialista elegible |
| POST | `/api/queue/{id}/services/{service_id}/finish` | Finaliza un servicio |
| POST | `/api/queue/{id}/services/{service_id}/rest` | Pone el servicio en reposo |
| POST | `/api/queue/{id}/services/{service_id}/resume` | Reanuda el servicio |
| PATCH | `/api/queue/{id}/details` | Actualiza etiquetas y observación |
| GET | `/api/staff/eligible` | Especialistas elegibles por servicio |
| PATCH | `/api/staff/{numero}/manual-status` | Cambia el estado operativo |
| GET | `/api/historial` | Consulta el historial de servicios |

## Reglas de negocio (Fase 1)

- **Asignar** requiere que el servicio esté pendiente y el especialista sea
  elegible por área y estado.
- **Finalizar** requiere que el servicio esté en atención.
- **Reposo** libera al especialista para atender otra persona, pero conserva el
  servicio visible en su carga. Se puede reanudar después.
- **Almorzando** bloquea nuevas asignaciones igual que `ocupado` y `break`.
- La etiqueta **INT** tiene prioridad; después la cola se ordena por nombre, no por
  número de turno.
- Al finalizar, el staff asignado vuelve automáticamente a `disponible`
  (si estaba `ocupado`).
- **Cédula** validada con regex `^[VEve\-]?\d{6,10}$` (acepta prefijo
  V/E venezolano).
- **Teléfono** validado con `^\+?\d[\d\s\-()]{9,18}$`.
- **Check-in** con una cédula existente reutiliza el perfil. Si el frontend
  confirma su `active_turno_id`, los servicios nuevos se agregan al mismo
  turno en vez de duplicarlo.
- Las etiquetas de una visita se sincronizan: conservar una etiqueta ya
  guardada no intenta insertarla nuevamente.
- El número de turno se conserva durante toda la visita activa.

## Tests

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

La suite actual contiene 34 pruebas y cubre autenticación, check-in,
asignación/finalización, perfiles e historial, etiquetas, validaciones,
adición de servicios a un turno activo y contratos esenciales del frontend.

Usa SQLite in-memory por test, así que no toca `peluq.db`.

## Producción (Fase 2+)

Para cambiar a Postgres:

1. Instalar driver: `pip install asyncpg`
2. Setear `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/peluq`
3. `alembic upgrade head`
4. Mismo código, ningún cambio en routers/services.

El `Dockerfile` del template usa gunicorn + uvicorn worker y queda listo
para desplegar el contenedor de la API.
