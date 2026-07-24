# Contratos API — Fase 1

Base local: `http://localhost:8000/api`. Los endpoints protegidos reciben
`Authorization: Bearer <token>`.

## Glosario

- **Perfil de cliente:** ficha permanente y única por cédula.
- **Turno/check-in:** visita concreta del cliente; conserva servicios, etiquetas,
  observación y situación.
- **Situación:** `presente`, `ausente` o `estafa`.
- **Estado del turno:** `en_espera`, `en_atencion` o `finalizado`; se deriva de sus servicios.
- **Estado del especialista:** `disponible`, `ocupado` o `break` (En pausa).

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
`active_turno_id` y `active_turno` cuando el cliente ya tiene una visita activa.

### `POST /queue/checkin`

Público. Crea la ficha del cliente o actualiza sus datos y registra una visita:

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
{"atendiendo":[13,14],"en_espera":[15,16],"ultimo_cambio":"2026-07-24T10:00:00"}
```

Solo incluye turnos `presente`.

## Administración

Todos requieren rol `admin`:

- `GET /queue`: turnos completos.
- `GET /queue/clients`: perfiles únicos con cantidad de visitas, etiquetas recientes
  y número de turno activo cuando corresponde.
- `GET /queue/clients/{profile_id}`: ficha permanente y visitas ordenadas de la más
  reciente a la más antigua. Cada visita incluye turno, fecha, estado, situación,
  etiquetas, observación y servicios con precio y especialista asignado.
- `PATCH /queue/{cliente_id}/details`: body `{observacion, etiquetas}`.
- `PATCH /queue/{cliente_id}/situacion`: body `{situacion}` con `presente`,
  `ausente` o `estafa`.
- `POST /queue/{cliente_id}/services/{servicio_id}/assign`.
- `POST /queue/{cliente_id}/services/assign-many`.
- `POST /queue/{cliente_id}/services/{servicio_id}/change-specialist`.
- `PATCH /staff/{numero}/manual-status`: `disponible`, `ocupado` o `break`.
- `POST /staff` y `PATCH /staff/{numero}`.
- `POST /services` y `PATCH /services/{id}`.

Un especialista marcado manualmente como `ocupado` o `break` no acepta nuevas
asignaciones. Si tiene servicios activos, su estado efectivo permanece `ocupado` aunque
su estado manual se cambie a `disponible`.

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
    "activo": true,
    "estado": "en_atencion",
    "servicios": [{
      "id": 22,
      "area_key": "peluqueria",
      "nombre": "CORTE DAMA",
      "precio_usd": "15.00",
      "staff_numero": 1,
      "especialista": "Ana",
      "estado": "en_atencion"
    }]
  }]
}
```

Un perfil inexistente responde `404`; una petición sin rol administrador responde `403`.

## Especialista

- `GET /queue/specialist/mine`: solamente sus servicios pendientes o en atención.
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
