# CONTEXTO — El Mundo del Cabello (peluq-project)

> Documento de handoff para retomar el proyecto en una sesión nueva.
> Última actualización: 2026-08-03.

---

## 1. Qué es el proyecto

Plataforma web para un salón de belleza ("El Mundo del Cabello") que digitaliza
el flujo de clientes y la asignación de personal:

- **Cliente** hace *check-in* (datos + servicios) → recibe **número de turno**.
- **Administración** ve la **cola de turnos**, **asigna un especialista por cada
  servicio**, puede **cambiar de especialista** (con PIN) y **finalizar** servicios.
- Todo lo finalizado queda en un **historial** filtrable.

Datos reales cargados desde dos Excel del cliente:
- `PERSONAL COMPLETO.xlsx` → **81 profesionales** (número, alias, nombre, cédula).
- `SISTEMA AUTOMATIZADO.xlsx` → catálogo de servicios con precio en USD.
- Total catálogo: **126 servicios** (incluye "Prueba de Color" $5 agregado a mano).
  Áreas: peluquería 62, hidratación 24, cejas 21, manicure 19.

---

## 2. Estado actual

### ✅ Hecho y verificado en navegador (sin errores de consola)

**Demo v2 "funcional"** en `mockups/v2/` — es la que se muestra al cliente y la
**especificación exacta** para el backend. Usa un mini-backend en `localStorage`
(no requiere servidor de datos). Incluye TODO lo que el cliente pidió:

- Check-in con **observaciones**, selección de servicios por tabs de área, resumen en vivo.
- Confirmación con turno, servicios, observaciones y total.
- Panel maestro con KPIs, cola, **asignación por servicio**, sugerencia de
  "asignar varios servicios al mismo especialista", **cambio con PIN admin + motivo**,
  finalizar por servicio.
- Gestión de personal: **multi-área**, marca **"En prueba"** (toggle + filtro),
  estado **Ocupado automático** (Disponible/Break manuales), búsqueda y filtros.
- **Historial** de servicios finalizados, filtrable por cliente, especialista, servicio y área.

**Demo v1 "clásica"** en `mockups/` (estilo brutalist, más simple). Se mantiene por
comparación. **No comparte** el store con v2 (v1 usa `mockups/store.js`; v2 usa
`mockups/v2/store.js`).

### ✅ Cierre técnico local del 2026-07-04

- Autenticación simple con tokens firmados y roles `admin`/`especialista`; vista cliente pública.
- Permisos de backend para operaciones administrativas y finalización del trabajo propio.
- CRUD administrativo de especialistas y servicios.
- Vista del especialista con sus clientes pendientes.
- Cola pública con refresco y animación discreta cuando cambia el número atendido.
- Situación operativa `normal | ausente | estafa`; los ausentes/estafa no aparecen públicamente.
- Búsqueda exacta por cédula para autocompletar el check-in.
- Catálogo actualizado a 132 servicios con los 7 ítems de la minuta.
- Suite local: 11 tests; lint limpio al cierre.
- Dato pendiente: el número `20` viene duplicado para Stheisy y Argemar. El seed conserva
  ambas y asigna provisionalmente el `82` a Argemar, emitiendo una advertencia visible;
  el cliente debe confirmar el número definitivo.
- Corregido el CORS local para que el frontend documentado en el puerto alternativo `5174`
  pueda iniciar sesión contra la API; quedó cubierto por una prueba de regresión.
- Mejora visual de las vistas API en `app/` aprobada por Juan Pablo el 2026-07-04:
  administración pagina y busca los 81 especialistas y 132 servicios (12 por página),
  el check-in usa un selector buscable por áreas con resumen y limpieza de selección,
  y la vista del especialista muestra un estado vacío explícito. Verificado en navegador
  a 1280×720 y 390×844, sin desbordamiento horizontal ni errores de consola.
- Navegación coherente añadida a las cinco vistas API el 2026-07-04: las pantallas
  públicas enlazan check-in, cola y acceso del equipo según corresponda; administración
  y especialista muestran únicamente destinos compatibles con su rol. Cubierto por test
  estructural; queda pendiente la confirmación visual manual final porque la conexión del
  navegador integrado se reinició durante esa comprobación.

### ⏳ Pendiente (lo que falta para "producto con deploy")

1. **Frontend de producción**: las vistas API en `app/` ya funcionan sin framework y
   tienen comportamiento responsivo; falta decidir si se consolidan en React+Vite o se
   mantienen estáticas.
2. **Mockups históricos**: usan **Tailwind vía CDN** (sale un
   warning). Para deploy conviene un frontend React+Vite (ya previsto en el plan
   original) o al menos compilar Tailwind. Reutilizar los tokens de `mockups/v2/app.js`
   y `app.css`.
3. **Deploy**: Docker Compose (backend ya tiene `Dockerfile`).
4. **Validación del cliente**: confirmar áreas reales y completar la nómina desde 81
   hasta la cifra contractual aproximada de 120, si aplica.
5. **Entregables no técnicos**: mapeo formal de procesos y capacitación presencial.

---

## 3. Estructura de archivos

```
peluq-project/
├── index.html                     # Hub raíz (link destacado a v2 + v1 clásica)
├── CONTEXTO.md                    # (este archivo)
├── README.md
├── PERSONAL COMPLETO.xlsx / SISTEMA AUTOMATIZADO.xlsx   # (en ~/Downloads originalmente)
│
├── mockups/                       # v1 clásica + datos compartidos
│   ├── data.json / data.js        # DATOS REALES (81 staff, 126 servicios) ← fuente de verdad
│   ├── store.js                   # store v1 (NO tocar, lo usa la v1)
│   ├── tokens.js / tokens.css / common.js
│   ├── 01-confirmacion / 02-panel / 03-checkin / 04-staff .html   # v1
│   └── v2/                        # ★ DEMO FUNCIONAL v2 ★
│       ├── app.js                 # theme Tailwind + helpers (V2.areaColor, titleCase, etc.)
│       ├── app.css                # design system "Soft Luxe"
│       ├── store.js               # ★ mini-backend v2 (modelo por-servicio) — LEER PRIMERO
│       ├── index.html             # hub v2
│       ├── 03-checkin.html
│       ├── 01-confirmacion.html
│       ├── 02-panel.html          # pantalla más compleja (asignar/cambiar/finalizar)
│       ├── 04-staff.html
│       └── 05-historial.html
│
└── backend/                       # FastAPI (necesita rework, ver §4)
    ├── src/{clients,queue,services,staff}/  # 4 dominios
    ├── src/seed.py                # datos sintéticos (reemplazar por reales)
    ├── alembic/                   # migraciones
    ├── peluq.db                   # SQLite local
    └── Dockerfile / Makefile / pyproject.toml
```

---

## 4. Modelo de datos v2 (la especificación para el backend)

Definido en `mockups/v2/store.js`. Clave localStorage: `peluq.demo.v2`. PIN admin demo: `1234`.

**Staff (especialista)**
```
{ numero, alias, nombre, cedula, initials,
  areas: [string],          // MULTI-ÁREA (peluqueria|hidratacion|manicure|cejas)
  manualStatus: 'DISPONIBLE'|'BREAK',
  en_prueba: bool }         // etiqueta, no afecta asignación
// status EFECTIVO se deriva: 'OCUPADO' si tiene ≥1 servicio EN_ATENCION, si no manualStatus
```

**Cliente / turno**
```
{ id, ts, turno, cedula, nombre, telefono, direccion, observacion,
  estado,                   // derivado: EN_ESPERA | EN_ATENCION | FINALIZADO
  servicios: [ {
    id, area, nombre, precio_usd,
    staff_id,               // especialista asignado A ESE SERVICIO (nullable)
    estado: 'PENDIENTE'|'EN_ATENCION'|'FINALIZADO',
    cambios: [ { ts, de: staff_id, a: staff_id, motivo } ]   // log de reasignaciones
  } ] }
// estado del turno: FINALIZADO si todos los servicios FINALIZADO;
//                   EN_ATENCION si alguno != PENDIENTE; si no EN_ESPERA
```

**Historial** (un registro por servicio finalizado)
```
{ id, ts, cliente_id, cliente_nombre, cliente_cedula,
  servicio_nombre, area, precio_usd, staff_id, staff_nombre, cambios: [...] }
```

**Operaciones (API a replicar en backend):**
- `addCliente(payload)` — crea turno con servicios en PENDIENTE.
- `assignService(clienteId, servicioId, staffId)` — asigna 1 servicio.
- `assignMany(clienteId, [servicioIds], staffId)` — varios al mismo especialista.
- `finishService(clienteId, servicioId)` — finaliza → escribe historial.
- `changeSpecialist(clienteId, servicioId, newStaffId, pin, motivo)` — **valida PIN
  admin + motivo obligatorio**, registra en `cambios`.
- `setStaffManualStatus(numero, 'DISPONIBLE'|'BREAK')`.
- `toggleEnPrueba(numero)`.
- Consultas de historial con filtros por cliente / especialista / servicio / área.
- `eligibleStaff(area)` — personal cuyas `areas` incluyen `area` y está DISPONIBLE.

---

## 5. Decisiones de features confirmadas por el cliente (2026-06-30)

- **Asignación por servicio**: cada servicio se asigna individual; especialista puede
  estar en varias áreas; si cubre varios servicios del turno, se ofrece asignárselos todos.
- **Cambio de especialista** a mitad de turno → **PIN admin (1234)** + motivo obligatorio; queda en historial.
- **Prueba de Color $5** → solo un ítem más del catálogo (peluquería).
- **Estilista en prueba** → etiqueta "En prueba" en la ficha, NO afecta estado ni asignación.
- **Observaciones** en check-in.
- **Historial** filtrable por cliente, especialista y servicio.

---

## 6. Cómo arrancar

**Demo (lo que se muestra hoy):**
```bash
cd peluq-project
python3 -m http.server 5174      # 5173 puede estar ocupado
# abrir http://localhost:5174/mockups/v2/
```
- Flujo demo: Check-in → Confirmación → Panel (asignar/cambiar/finalizar) → Historial.
- PIN admin: **1234**. Botón "Reset" en el panel limpia los turnos e historial del día.

**Backend (estado actual, aún no refleja v2):**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt && pip install aiosqlite openpyxl
cp .env.example .env
alembic upgrade head && python -m src.seed
uvicorn src.main:app --reload   # docs: http://localhost:8000/docs
```

---

## 7. Plan sugerido para la próxima sesión

Objetivo: **backend real que refleje la v2** y camino a deploy.

1. **Rediseñar el esquema** (SQLAlchemy + Alembic) según §4:
   - `staff` con relación **muchos-a-muchos** a `area` (tabla `staff_area`); campos
     `manual_status`, `en_prueba`.
   - `turno` (cliente) + `turno_servicio` (cada servicio con `staff_id`, `estado`).
   - `servicio_cambio` (log de reasignaciones con motivo).
   - `historial` o vista derivada de servicios finalizados.
2. **Endpoints** que espejen las operaciones del §4 (incluida validación de PIN admin
   para el cambio de especialista; el PIN debe ir a variable de entorno, no hardcode).
3. **Seed real** desde `mockups/data.json` (81 staff, 126 servicios). Asignar áreas
   a cada especialista (hoy es heurístico en el mock; idealmente el cliente confirma
   las áreas reales de cada persona).
4. **Frontend**: decidir React+Vite o servir los HTML compilando Tailwind. Conectar a la API.
5. **Deploy**: Docker Compose (Postgres + backend + frontend).

**Preguntas abiertas para el cliente:**
- ¿Áreas reales de cada especialista? (el mock las asigna por heurística de número).
- ¿El PIN admin es único global o por administrador? ¿Quién lo gestiona?
- ¿Frontend nuevo en React o seguir con los HTML estáticos servidos?

---

## 8. Notas técnicas importantes

- Colores de área v2 (en `app.js`, `window.V2.areaColor`): peluqueria `#e26fae`,
  hidratacion `#4bb6e8`, manicure `#e6a93d`, cejas `#4fbf8f`.
- Tipografías: Fraunces (display) + Plus Jakarta Sans (body), vía Google Fonts.
- Tailwind por **CDN** (warning esperado en consola; irrelevante para demo, cambiar en prod).
- `data.json`/`data.js` se regeneran con un script Python + openpyxl (ver historial de
  la sesión); son la **fuente de verdad** de personal y catálogo.
- El seed del historial (`seedHistorial` en `store.js`) mete ~5 servicios de ejemplo
  para que el historial no arranque vacío en la demo.

---

## 9. Estado de la interfaz administrativa (2026-07-04)

- ✅ **Navegación de cola sin falsa salida de sesión.** Causa raíz confirmada: la cola
  pública conservaba el token, pero siempre mostraba `Acceso del equipo`. Ahora guarda
  también el rol al iniciar sesión y muestra `Volver al panel` o `Volver a mis clientes`.
- ✅ **Panel administrativo operativo.** `app/admin.html` muestra primero el resumen y
  estado del equipo (en una zona desplazable para no ocultar los clientes) y luego los
  clientes activos con asignación por servicio a especialistas elegibles por área.
- ✅ **Edición separada.** Personal en `app/admin-staff.html`; servicios y productos en
  `app/admin-services.html`. Ambas pantallas conservan búsqueda y paginación de 12 filas.
- ✅ **Verificación local.** 17 tests pasan, Ruff limpio, sintaxis JavaScript limpia.
  Inspección real en navegador: panel carga 1 cliente activo, personal 81/81, catálogo
  132/132 y la cola pública ofrece retorno a `admin.html` durante la sesión administrativa.
- Decisión de Juan Pablo, 2026-07-04: la pantalla inicial del administrador debe ser el
  panel operativo; las altas y ediciones pertenecen a pantallas independientes.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

---

## 10. Estado operativo reciente (2026-08-03)

- ✅ Panel principal ajustado para ser la pantalla de asignación: se eliminó el buscador
  superior de cliente/especialista.
- ✅ La consulta rápida ahora busca por turno, nombre o cédula con autocompletado en vivo;
  al seleccionar una coincidencia hace scroll y resalta la tarjeta del cliente activo.
- ✅ Cada servicio del panel muestra cuántos clientes activos y presentes tienen servicios
  pendientes sin asignar en esa misma área (`pendientes_area` en `GET /api/queue`).
- ✅ La regla existente de finalización se conserva: al terminar todos los servicios,
  el turno queda inactivo y cada servicio finalizado se registra en historial.
- Estado: implementado y probado en local. **Pendiente desplegar.**

### Bloque 1 MVP operativo

- ✅ Búsqueda/autocomplete de asignaciones unificada en la consulta rápida.
- ✅ Alerta de estafa previa en búsqueda de cliente y check-in.
- ✅ Observación visible directamente en la tarjeta activa del cliente.
- ✅ Colores claros por situación operativa: presente, ausente y estafa.
- ✅ Botón directo para agregar servicios a un turno activo desde asignaciones.
- ✅ KPI de especialistas almorzando en el panel principal.
- ✅ Número de especialista autogenerado en creación de perfiles.
- ⏭ Bloque 2 pendiente: auditoría/usuarios individuales/historial administrativo.
- ⏭ Bloque 3 pendiente: cola real por servicio/área con posiciones separadas.

### Prototipo visual moderno del panel (2026-07-04)

- ✅ Primera etapa aprobada: rediseño exclusivo de `app/admin.html`, sin cambiar API,
  autenticación, datos ni lógica de asignación.
- ✅ Nuevo sistema visual: sidebar, buscador, métricas operativas, progreso por cliente,
  colores por área, filtros de especialistas, estados compactos y responsive móvil.
- ✅ Verificación automática: 17 tests, Ruff y sintaxis JavaScript limpios.
- ⏸ Inspección visual automatizada pendiente: el navegador integrado agotó el tiempo de
  conexión dos veces después del cambio. El usuario puede recargar la pestaña local para
  evaluar el prototipo; no extender el diseño a otras pantallas hasta su aprobación.
- ✅ Ajuste aprobado por Juan Pablo, 2026-07-04: conservar la estructura moderna y
  recuperar la paleta original (`#dc6fa8` rosa, `#1d2330` tinta, `#f8f6f3` marfil y
  `#e6dfd9` bordes cálidos). Verde queda reservado para el estado disponible y se
  mantienen colores funcionales por área. 17 tests y Ruff limpios.

### Extensión del sistema visual a todas las pantallas (2026-07-04)

- ✅ Decisión de Juan Pablo: extender el diseño moderno, interactivo y llamativo del
  panel a especialistas, servicios/productos, check-in, vista del especialista,
  acceso y cola pública, sin modificar backend ni contratos API.
- ✅ `app/styles.css` incorpora una capa compartida para pantallas secundarias:
  sidebar responsive, tarjetas, métricas, formularios, modales, notificaciones,
  microinteracciones, entrada de página y soporte para `prefers-reduced-motion`.
- ✅ `app/admin-staff.html` y `app/admin-services.html` conservan búsqueda y paginación
  y reemplazan los `prompt` por formularios modales completos con los campos que
  admiten `StaffUpdate` y `ServiceUpdate`.
- ✅ `app/checkin.html` presenta un flujo visual de dos pasos sin cambiar el payload;
  `app/specialist.html` añade búsqueda local por cliente o servicio; login y cola
  pública adoptan el mismo lenguaje visual conservando sesión y navegación.
- ✅ Verificación automática: 18 tests pasan, Ruff limpio y sintaxis JavaScript limpia
  en todos los HTML y en `api.js`.
- ✅ Flujos reales verificados en navegador: especialistas carga 81 perfiles, búsqueda
  `Sonia` reduce a 1 resultado y abre el modal; catálogo carga 132 servicios, búsqueda
  `manicure` devuelve 19 y el modal abre `CAMBIO ESMALTE`; check-in carga 4 grupos;
  cola pública conserva `Volver al panel`; login ofrece ambos roles.
- ⏸ La captura visual de especialistas se completó correctamente. La captura adicional
  de check-in agotó la conexión del navegador integrado por segunda vez; no se usó una
  herramienta externa como sustituto. La inspección DOM del check-in sí fue correcta.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

### Corrección de legibilidad y áreas múltiples (2026-07-05)

- ✅ Causa raíz confirmada por captura y CSS: `.modern-page input { width: 100% }`
  tenía igual especificidad y aparecía después de `.service-option input`, por lo que
  ensanchaba cada checkbox del check-in y desplazaba nombres y precios fuera de vista.
- ✅ `app/styles.css` ahora limita explícitamente el checkbox del servicio a 18 px,
  protege el texto con `min-width: 0` y mantiene nombre y precio dentro de la fila.
- ✅ `app/admin-staff.html` reemplaza la entrada de áreas separadas por coma por cuatro
  opciones múltiples visuales en creación y edición: Peluquería, Hidratación, Manicure
  y Cejas. El contrato sigue enviando `areas: string[]`; no cambió el backend.
- ✅ Pruebas: 19 tests pasan, Ruff y sintaxis JavaScript limpios.
- ✅ Verificación real: 132 opciones de servicio renderizadas, checkbox de 18 px,
  nombre/precio visibles y sin overflow; selección simultánea de `peluqueria` y
  `manicure` comprobada en navegador sin desbordamiento.
- Estado: corregido y probado en local. **Pendiente desplegar en producción.**

### Comentarios de operación y check-in (2026-07-24)

- ✅ Repositorio Git creado. Respaldo anterior a estos cambios:
  `d0ce50e chore: respaldar estado inicial de fase 1`.
- ✅ Causa de registros repetidos confirmada: el backend insertaba siempre un turno y
  el botón continuaba habilitado durante la petición. Ahora el backend rechaza con
  `409` una cédula con turno activo y el frontend bloquea envíos repetidos.
- ✅ Nueva tabla `cliente_perfil`, única por cédula normalizada. La migración
  `20260724_profiles` conserva todos los turnos y vincula cada uno con su ficha.
- ✅ Check-in convertido en tres pasos: cliente, servicios, etiquetas/observación.
  La búsqueda progresiva comienza con cuatro caracteres y devuelve máximo ocho fichas.
- ✅ Etiquetas admitidas: `INT`, `F`, `CORTO`, `LAVADO`, `AC`, `TC`, `XL`, `CM`, `DC`.
  Se pueden registrar en check-in y editar desde la tarjeta del turno.
- ✅ Situaciones operativas: `presente`, `ausente`, `estafa`. La migración convirtió
  todos los valores anteriores `normal` a `presente`.
- ✅ Estado manual del equipo admite Disponible, Ocupado y En pausa. Los especialistas
  con servicio activo siguen apareciendo Ocupados; un estado manual Ocupado/En pausa
  impide nuevas asignaciones.
- ✅ Interfaces separadas: asignaciones (`admin.html`), estado del equipo
  (`admin-team.html`), clientes (`admin-clients.html`) y edición de especialistas
  (`admin-staff.html`). La navegación superior se genera según el rol y empieza con
  Nuevo check-in.
- ✅ Cola pública explica la atención simultánea y separa los números atendidos de los
  próximos turnos.
- ✅ Base local migrada: 4 turnos existentes, 2 perfiles únicos, 0 situaciones
  `normal` y 0 turnos sin perfil. Respaldo temporal:
  `/private/tmp/peluq-before-20260724.db`.
- ✅ Verificación automática: 26 tests, Ruff limpio y sintaxis JavaScript limpia.
- ✅ Inspección real en navegador: el check-in mantuvo el menú administrativo, buscó
  `2548` y completó la ficha de Ámbar; recorrió los tres pasos y mostró el `409` del
  turno #14 sin borrar el formulario. El panel cargó 4 turnos, la pantalla de equipo
  81 especialistas/81 controles de estado, clientes 2/2 y la cola mostró #13 en
  atención y #14–#16 en espera. Consola sin errores.
- ⏸ Pendiente: despliegue en producción.
- Decisión de Juan Pablo, 2026-07-24: estos comentarios se entregan en un commit
  separado del respaldo inicial.

### Selección de especialista y validación en tablet (2026-07-24)

- ✅ Al seleccionar un especialista en una asignación, el menú queda resaltado en rosa,
  el botón cambia de énfasis y aparece el mensaje `Seleccionado: …`. La asignación
  todavía requiere pulsar **Asignar**, para evitar cambios accidentales.
- ✅ La vista del especialista incorpora objetivos táctiles de al menos 44 px y usa
  una sola columna en tablet vertical; en horizontal aprovecha dos columnas.
- ✅ Inspección real en navegador a 768×1024 y 1024×768: navegación completa,
  sin desbordamiento horizontal, botón **Finalizar** de 48 px en vertical y 44 px
  en horizontal. Consola sin errores ni advertencias.
- ✅ Verificación automática: 27 tests, Ruff y sintaxis JavaScript limpios.
- ⏸ No forma parte de este ajuste limpiar los turnos históricos duplicados #14–#16.
  El sistema ya previene nuevos duplicados; la ficha histórica se resolvió en el
  siguiente cambio.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

### Ficha detallada e historial del cliente (2026-07-24)

- ✅ Causa confirmada: `GET /queue/clients` y `admin-clients.html` solo exponían el
  resumen del perfil, aunque la base ya conservaba visitas, servicios, precios,
  estados, observaciones, etiquetas y asignaciones. No fue necesaria una migración.
- ✅ Nuevo contrato administrativo `GET /queue/clients/{profile_id}`. Devuelve los
  datos actuales del perfil y las visitas desde la más reciente; cada visita incluye
  turno, fecha, estado, situación, observación, etiquetas y servicios con especialista.
- ✅ La pantalla **Clientes** abre una ficha detallada desde cada tarjeta. El historial
  es de solo lectura y muestra fielmente los datos existentes, incluidos los turnos
  históricos duplicados #14–#16 de Ámbar.
- ✅ El orden usa fecha e identificador descendentes. Esto resuelve el desempate de
  visitas creadas con la misma marca de tiempo.
- ✅ Verificación automática: 28 tests, Ruff y sintaxis JavaScript limpios. El endpoint
  exige rol administrador, devuelve `404` para perfiles inexistentes y tiene cobertura
  del orden entre visitas.
- ✅ Inspección real: Ámbar mostró #16, #15 y #14; Pedro mostró una visita, tres
  servicios y `#4 Yurbi`. En tablet 768×1024 no hubo desbordamiento horizontal,
  el botón mide 44 px y el modal desplaza internamente. Consola sin errores.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

### Ajustes finales de operación, búsqueda y tablet (2026-07-24)

- ✅ **Asignar clientes** queda como vista administrativa principal. Los accesos
  **Registrar nuevo check-in** y **Clientes registrados** están encima de Flujo de hoy;
  se retiraron del menú superior para evitar desplazamiento lateral.
- ✅ El check-in selecciona progresivamente la ficha existente y avanza a Servicios.
  Si existe un turno activo, envía su identificador y agrega los servicios a esa misma
  visita. El backend valida cédula e identificador y desempata turnos históricos por
  fecha e ID descendentes.
- ✅ Al completar el flujo aparece una confirmación con número de turno, **Registrar otra
  persona** y, para administración, **Volver a asignar clientes**.
- ✅ El buscador de servicios filtra por nombre y no por el nombre general del área.
  `CEJA` devuelve únicamente los tres servicios que contienen esa palabra.
- ✅ La edición de etiquetas sincroniza altas y bajas, conservando las existentes; se
  eliminó el `IntegrityError` por código duplicado.
- ✅ El selector de especialista sigue consultando `/staff/eligible?area=...`, pero ahora
  permite buscar por nombre o número y conserva el resaltado antes de confirmar.
- ✅ Clientes registrados usa tabla de 25 filas por página, ficha histórica y descarga
  CSV compatible con Excel. La consulta de perfiles usa carga agrupada y elimina el
  patrón de una consulta adicional por cliente.
- ✅ La cola pública comparte la cabecera oscura del producto. El panel conserva los
  datos visibles ante un fallo de actualización y muestra **Reintentar**.
- ✅ Base real inspeccionada: integridad `ok`, 4 turnos activos y 2 perfiles; no hubo
  eliminación de datos. La pantalla vacía reportada fue una carga fallida no comunicada,
  no una pérdida confirmada.
- ✅ Verificación automática: 29 tests, Ruff, sintaxis JavaScript y `git diff --check`
  limpios.
- ✅ Flujo real validado con una copia temporal de la base: selección de Ámbar, filtro
  `PIGMENTO DE CEJAS`, adición al turno #16, confirmación y reinicio para otra persona.
- ✅ Tablet: 1024×768 y 768×1024 sin desbordamiento de página; menú sin scroll lateral.
  La vista del especialista mostró una tarjeta y botones Finalizar de 48 px.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

### Reposo, prioridad y nómina validada (2026-07-29)

- ✅ Nuevo estado de servicio **Reposo**: mantiene visible a la clienta en la carga,
  libera al especialista para otra atención y permite reanudar el servicio.
- ✅ Nuevo estado de especialista **Almorzando**; impide nuevas asignaciones.
- ✅ La etiqueta `INT` sube automáticamente el turno. Después se ordena por nombre del
  cliente, con fecha e ID como desempate; el ticket queda solo como identificador.
- ✅ Consulta administrativa por turno, nombre o cédula para informar posición y
  cantidad real de personas por delante.
- ✅ El check-in autenticado registra el rol, identificador y nombre del usuario que
  creó la visita. El historial muestra ese dato.
- ✅ Los especialistas **En prueba** se identifican con un color y distintivo especial.
- ✅ Nómina reconciliada con `LISTADO PERSONAL PARA SISTEMA AUTOMATIZADO.xlsx`: 80/80
  coincidencias exactas más 10 especialistas complementarios existentes, para 90
  activos. No se eliminó ni desactivó a nadie.
- ✅ Mapeo acordado: estilistas → Peluquería, manicuristas → Manicure, aplicadoras →
  Hidratación, maquillaje → Maquillaje y **lashistas → Cejas y depilación**. En este
  salón las lashistas atienden todas las depilaciones.
- ✅ Se añadió el área Maquillaje y se corrigieron registros incompletos sin cambiar
  los números globales ya existentes.
- ✅ Migración real aplicada a `peluq.db`; integridad `ok`. Respaldo previo:
  `/private/tmp/peluq-before-20260729.db`.
- ✅ Verificación de migración desde base vacía, pruebas automáticas, Ruff, sintaxis
  JavaScript y revisión responsive en tablet.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**

### Bloque 2 — control administrativo (2026-08-03)

- ✅ Historial global protegido: `/api/historial` y `/api/historial/summary` requieren
  rol administrador.
- ✅ Auditoría base añadida para acciones administrativas: asignación de servicios,
  asignación múltiple, cambio de especialista, edición de etiquetas/observación y
  cambio de situación guardan el nombre/rol/identificador del operador cuando hay token.
- ✅ Nueva vista `app/admin-history.html`: filtros por cliente, especialista, servicio
  y área; tabla de servicios finalizados; métricas de servicios, total USD y totales por
  área.
- ✅ Migración `20260803_audit_actions` preparada con columnas nullable para no romper
  bases existentes.
- ✅ Verificación automática: compileall, Ruff, checks estáticos de frontend y 37 tests.
- Estado: implementado y probado en local. **Pendiente desplegar en producción.**
