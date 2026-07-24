# El Mundo del Cabello — Backend (Fase 1)

API FastAPI para el MVP: registro de clientes (check-in) y gestión
manual de la cola con asignación de personal.

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
│   ├── seed.py            # Carga 4 áreas, 12 servicios, 48 profesionales
│   ├── clients/           # Dominio: clientes (5 campos)
│   ├── services/          # Dominio: catálogo (áreas + servicios)
│   ├── staff/             # Dominio: personal con status
│   └── queue/             # Dominio: cola con transiciones
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
python -m src.seed           # carga 4 áreas, 12 servicios, 48 profesionales

uvicorn src.main:app --reload
# docs: http://localhost:8000/docs
```

## Endpoints

| Verbo | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (hace `SELECT 1` contra la DB) |
| GET | `/api/services` | Catálogo agrupado por área (lo consume el check-in) |
| POST | `/api/queue/checkin` | Crea cliente + entry, devuelve turno |
| GET | `/api/queue?status=en_espera` | Lista la cola filtrada por status |
| GET | `/api/queue/{id}` | Detalle de una entry |
| POST | `/api/queue/{id}/assign` | Asigna staff disponible → `en_servicio` |
| POST | `/api/queue/{id}/finish` | Marca `finalizado` y libera al staff |
| GET | `/api/staff?area_id=1&status=disponible` | Personal filtrado |
| GET | `/api/staff/{id}` | Detalle |
| PATCH | `/api/staff/{id}/status` | Cambia status manualmente |
| POST | `/api/clients` | Crea cliente (raro en Fase 1, se usa el check-in) |
| GET | `/api/clients` | Lista clientes (paginado básico) |

## Reglas de negocio (Fase 1)

- **Asignar** requiere: la entry está `en_espera` **y** el staff está
  `disponible`. Cualquier otra combinación devuelve 400 con mensaje
  específico.
- **Finalizar** requiere: la entry está `en_servicio`. Devuelve 400 en
  otro caso.
- Al finalizar, el staff asignado vuelve automáticamente a `disponible`
  (si estaba `ocupado`).
- **Cédula** validada con regex `^[VEve\-]?\d{6,10}$` (acepta prefijo
  V/E venezolano).
- **Teléfono** validado con `^\+?\d[\d\s\-()]{9,18}$`.
- **Check-in** con la misma cédula reusa el cliente y actualiza sus
  datos (Fase 1: prepare el camino para la búsqueda/historial de Fase 2).
- **Turn number** = count de entries + 1 al momento del check-in. Es
  estable durante la vida de la entry.

## Tests

```bash
pytest
```

Cubre: el flujo happy-path completo (check-in → asignar → finalizar),
los 400 cuando se intenta asignar staff ocupado o finalizar entry en
`en_espera`, validación 422 de cédula inválida, e incremento de turn
numbers.

Usa SQLite in-memory por test, así que no toca `peluq.db`.

## Producción (Fase 2+)

Para cambiar a Postgres:

1. Instalar driver: `pip install asyncpg`
2. Setear `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/peluq`
3. `alembic upgrade head`
4. Mismo código, ningún cambio en routers/services.

El `Dockerfile` del template usa gunicorn + uvicorn worker y queda listo
para desplegar el contenedor de la API.
