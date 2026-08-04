# Contratos API — Fase 1

Base local: `http://localhost:8000/api`. Los endpoints protegidos reciben
`Authorization: Bearer <token>`.

## Glosario

- **Perfil de cliente:** ficha permanente y única por cédula.
- **Turno/check-in:** visita concreta del cliente; conserva servicios, etiquetas,
  observación y situación.
- **Situación:** `presente`, `ausente` o `estafa`.
- **Estado del turno:** `en_espera`, `en_atencion`, `reposo` o `finalizado`; se deriva
  de sus servicios.
- **Estado del especialista:** `disponible`, `ocupado`, `break` (En pausa) o
  `almorzando`.

## Autenticación

### `POST /auth/login`

Público. Body:

```json
{"role":"admin","username":"<admin-user>","password":"<admin-password>"}
```

Roles admitidos: `admin` y `especialista`. Para un especialista, `username` es su
número y `password` su cédula. Responde `200` con `access_token`; credenciales inválidas,
`403`.

### `GET /auth/me`

Requiere token. Devuelve identidad, rol y nombre visible.

## Recepción y clientes

### `GET /queue/client-search?q=<texto>`

Público para la estación de recepción. Requiere entre 4 y 30 caracteres y devuelve
como máximo ocho coincidencias por cédula. Cada coincidencia incluye
`active_turno_id` y `active_turno` cuando el cliente ya tiene una visita activa, y
`alerta_estafa=true` cuando alguna visita histórica del perfil fue marcada como
`estafa`.

### `POST /queue/checkin`

Público. Crea la ficha del cliente o actualiza sus datos y registra una visita. Si
recibe un token válido, también guarda el rol, identificador y nombre visible de quien
realizó el registro:

```json
{
  "cedula": "V-25482938",
  "nombre": "Ambar Vegas",
  "telefono": "04145551212",
  "direccion": "Los Palos Grandes",
  "service_ids": [1, 8],
  "etiquetas": ["XL", "CM"],
  "observacion": "Usar producto suave",
  "active_turno_id": null
}
```

Etiquetas admitidas: `INT`, `F`, `CORTO`, `LAVADO`, `AC`, `TC`, `XL`, `CM`, `DC`.
Responde `201`. Para un cliente sin visita activa crea un turno nuevo. Si la búsqueda
devolvió un `active_turno_id`, enviarlo agrega los servicios al mismo turno y combina
las etiquetas sin duplicarlas. Si la cédula ya posee un turno activo y el identificador
no fue enviado o no coincide, responde `409`.

### `POST /queue/lookup?cedula=<cedula>`

Compatibilidad con clientes anteriores: recupera una ficha exacta. Responde `404` si
no existe.

## Cola pública

### `GET /queue/public/status`

Público. Devuelve:

```json
{"atendiendo":[13,14],"en_reposo":[18],"en_espera":[15,16],"ultimo_cambio":"2026-07-29T10:00:00"}
```

Solo incluye turnos `presente`.

## Administración

Todos requieren rol `admin`:

- `GET /queue`: turnos completos. Cada servicio incluye `pendientes_area`, el número
  de clientes activos y presentes que todavía tienen servicios sin asignar en esa misma
  área.
- `GET /queue/clients`: perfiles únicos con cantidad de visitas, etiquetas recientes
  y número de turno activo cuando corresponde.
- `GET /queue/clients/{profile_id}`: ficha permanente y visitas ordenadas de la más
  reciente a la más antigua. Cada visita incluye turno, fecha, estado, situación,
  etiquetas, observación y servicios con precio y especialista asignado.
- `PATCH /queue/{cliente_id}/details`: body `{observacion, etiquetas}`.
- `PATCH /queue/{cliente_id}/situacion`: body `{situacion}` con `presente`,
  `ausente` o `estafa`.
- `GET /queue/position-search?q=<texto>`: busca por turno exacto, nombre o cédula e
  informa la posición y cuántas personas hay delante.
- `POST /queue/{cliente_id}/services/{servicio_id}/assign`.
- `POST /queue/{cliente_id}/services/assign-many`.
- `POST /queue/{cliente_id}/services/{servicio_id}/change-specialist`.
- `PATCH /staff/{numero}/manual-status`: `disponible`, `ocupado`, `break` o
  `almorzando`.
- `POST /staff` y `PATCH /staff/{numero}`.
- `POST /services` y `PATCH /services/{id}`.

Un especialista marcado manualmente como `ocupado`, `break` o `almorzando` no acepta
nuevas asignaciones. Un servicio `en_atencion` ocupa al especialista; un servicio en
`reposo` permanece visible en su carga, pero lo libera para atender otra persona.

La cola administrativa ordena primero los turnos con etiqueta `INT` y luego por nombre
del cliente, con fecha e identificador como desempate estable. El número de turno se
conserva como identificador, pero no define la prioridad.

Ejemplo abreviado de la ficha:

```json
{
  "id": 1,
  "cedula": "V-25482938",
  "nombre": "Ambar Vegas",
  "telefono": "04145551212",
  "direccion": "Los Palos Grandes",
  "visitas": [{
    "id": 14,
    "turno": 16,
    "created_at": "2026-07-24T10:00:00",
    "observacion": "Usar producto suave",
    "etiquetas": ["CM", "XL"],
    "situacion": "presente",
    "registrado_por_nombre": "Administración",
    "activo": true,
    "estado": "en_atencion",
    "servicios": [{
      "id": 22,
      "area_key": "peluqueria",
      "nombre": "CORTE DAMA",
      "precio_usd": "15.00",
      "staff_numero": 1,
      "especialista": "Ana",
      "estado": "en_atencion",
      "pendientes_area": 3
    }]
  }]
}
```

Un perfil inexistente responde `404`; una petición sin rol administrador responde `403`.

## Especialista

- `GET /queue/specialist/mine`: solamente los servicios asignados a su identidad que
  estén pendientes, en atención o en reposo.
- `POST /queue/{cliente_id}/services/{servicio_id}/rest`: pasa un servicio en atención
  a reposo y libera al especialista para otra asignación.
- `POST /queue/{cliente_id}/services/{servicio_id}/resume`: reanuda un servicio en
  reposo; admite trabajo simultáneo cuando la operación lo requiere.
- `POST /queue/{cliente_id}/services/{servicio_id}/finish`: un especialista solo puede
  finalizar servicios asignados a su identidad; el administrador puede finalizar cualquiera.

Cuando finaliza el último servicio, el turno deja de estar activo y la misma cédula puede
realizar un nuevo check-in.

## Errores

- `400`: regla de negocio.
- `403`: autenticación o permisos.
- `404`: recurso inexistente.
- `409`: turno activo o recurso duplicado.
- `422`: payload o parámetros inválidos.
