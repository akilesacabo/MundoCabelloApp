# El Mundo del Cabello — Fase 1 (MVP)

Plataforma web para automatizar el flujo de clientes y la asignación
de personal en un salón de belleza. Esta primera fase digitaliza el
registro de clientes y la gestión visual de la cola con asignación
**manual** desde un panel de administración.

## Estado del proyecto

| Fase | Estado | Descripción |
|---|---|---|
| 0 — Mockups navegables | ✅ Listo | 4 pantallas extraídas de Stitch, servibles como spec visual |
| 1 — Backend FastAPI | ✅ Local | API, roles, perfiles de clientes, cola y 26 tests |

**Próximas fases** (no en este commit):
- 2 — Frontend React + Vite + Tailwind
- 3 — Integración + Docker Compose

## Estructura del repo

```
peluq-project/
├── index.html              # Hub con links a las 4 pantallas
├── mockups/                # Fase 0: HTML estático navegable
│   ├── 01-confirmacion.html
│   ├── 02-panel.html
│   ├── 03-checkin.html
│   ├── 04-staff.html
│   ├── common.js
│   ├── tokens.js
│   ├── tokens.css
│   └── README.md
├── backend/                # Fase 1: FastAPI
│   ├── src/
│   ├── alembic/
│   ├── tests/
│   ├── requirements/
│   ├── README.md           # instrucciones de arranque
│   └── pyproject.toml
└── Pantallas para demo de peluqueria.html  # archivo original de Stitch
```

## Cómo arrancar

### Mockups (no requiere nada instalado)

```bash
cd peluq-project
python3 -m http.server 5173
# abrir http://localhost:5173/
```

### Backend

```bash
cd peluq-project/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
pip install aiosqlite
cp .env.example .env
alembic upgrade head
python -m src.seed
uvicorn src.main:app --reload
# docs: http://localhost:8000/docs
```

## Áreas de servicio (4)

| Área | Personal seed | Color |
|---|---|---|
| Peluquería | 20 | `#ffb4ab` |
| Hidratación | 3 | `#a3defe` |
| Manicure y Pedicure | 20 | `#f5c518` |
| Cejas | 5 | `#c3e88d` |

**Datos actuales:** 81 profesionales y 132 servicios en catálogo.

## Vistas API v2

Servir el repositorio y abrir:

- `app/login.html`: acceso de administración y especialistas.
- `app/admin.html`: asignación de servicios a especialistas.
- `app/admin-team.html`: estado general y disponibilidad del equipo.
- `app/admin-clients.html`: base de clientes existentes.
- `app/admin-staff.html`: alta y edición de especialistas.
- `app/admin-services.html`: alta y edición de servicios y productos.
- `app/checkin.html`: check-in guiado en tres pasos con búsqueda y etiquetas.
- `app/specialist.html`: clientes asignados al especialista autenticado.
- `app/queue.html`: cola pública con animación discreta al avanzar.

Estas vistas consumen la API local en `http://localhost:8000/api`.

## Stack

- **Backend:** FastAPI 0.136 + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
- **DB local:** SQLite (aiosqlite) — Postgres en producción
- **Frontend (próxima fase):** React + Vite + TypeScript + Tailwind + TanStack Query
- **Despliegue (próxima fase):** Docker Compose
