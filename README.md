# El Mundo del Cabello — Fase 1 (MVP)

Plataforma web para automatizar el flujo de clientes y la asignación
de personal en un salón de belleza. Esta primera fase digitaliza el
registro de clientes y la gestión visual de la cola con asignación
**manual** desde un panel de administración.

## Estado del proyecto

| Fase | Estado | Descripción |
|---|---|---|
| 0 — Mockups navegables | ✅ Listo | 4 pantallas extraídas de Stitch, servibles como spec visual |
| 1 — Backend FastAPI | ✅ Local | API, roles, perfiles, cola operativa y 34 tests |

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

## Áreas de servicio (5)

| Área | Personal seed | Color |
|---|---|---|
| Peluquería | Según nómina | `#ffb4ab` |
| Hidratación | Aplicadoras | `#a3defe` |
| Manicure y Pedicure | Manicuristas | `#f5c518` |
| Cejas y depilación | Lashistas | `#c3e88d` |
| Maquillaje | Maquilladoras | `#e8b7d4` |

**Datos actuales:** 90 profesionales activos: las 80 personas del listado validado
más 10 especialistas complementarios que ya existían. Las lashistas atienden cejas y
todas las depilaciones.

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

El panel administrativo usa **Asignar clientes** como inicio. Desde allí se accede a
**Registrar nuevo check-in** y **Clientes registrados**. El check-in recupera fichas
existentes, agrega servicios al turno activo cuando corresponde y ofrece registrar otra
persona al finalizar. La base de clientes se presenta como tabla paginada y se puede
descargar como CSV compatible con Excel.

La cola prioriza `INT` y luego ordena alfabéticamente por cliente. El panel permite
consultar por turno, nombre o cédula cuántas personas hay delante. Los servicios pueden
pasar a **Reposo** sin bloquear al especialista y el estado **Almorzando** impide nuevas
asignaciones. Cada visita conserva quién realizó el registro.

## Stack

- **Backend:** FastAPI 0.136 + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
- **DB local:** SQLite (aiosqlite) — Postgres en producción
- **Frontend:** HTML, CSS y JavaScript responsive consumiendo la API
- **Despliegue (próxima fase):** Docker Compose
