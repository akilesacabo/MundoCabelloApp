# Recetas de prueba local

Arranque la API y obtenga un token administrativo:

```bash
curl -s http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"role":"admin","username":"<admin-user>","password":"<admin-password>"}'

export TOKEN='<access-token>'
```

## Buscar y registrar un cliente

```bash
curl -s 'http://localhost:8000/api/queue/client-search?q=2548'

curl -s -X POST http://localhost:8000/api/queue/checkin \
  -H 'Content-Type: application/json' \
  -d '{
    "cedula":"V-25482938",
    "nombre":"Ambar Vegas",
    "telefono":"04145551212",
    "direccion":"Los Palos Grandes",
    "service_ids":[<service-id>],
    "etiquetas":["XL","CM"],
    "observacion":"Usar producto suave"
  }'
```

Resultado esperado: búsqueda `200`; check-in `201`. La búsqueda devuelve
`active_turno_id` y `active_turno` cuando ya existe una visita activa, y
`alerta_estafa=true` cuando el cliente tiene historial marcado como estafa. Repetir el
mismo check-in sin indicar el identificador debe responder `409`.

Para agregar servicios al turno activo seleccionado:

```bash
curl -s -X POST http://localhost:8000/api/queue/checkin \
  -H 'Content-Type: application/json' \
  -d '{
    "cedula":"V-25482938",
    "nombre":"Ambar Vegas",
    "telefono":"04145551212",
    "direccion":"Los Palos Grandes",
    "service_ids":[<service-id>],
    "active_turno_id":<active-turno-id>
  }'
```

Resultado esperado: `201`, el mismo `id` y número de turno, con el servicio nuevo en
estado `pendiente`.

## Base de clientes y edición de visita

```bash
curl -s http://localhost:8000/api/queue \
  -H "Authorization: Bearer $TOKEN"

curl -s http://localhost:8000/api/queue/clients \
  -H "Authorization: Bearer $TOKEN"

curl -s http://localhost:8000/api/queue/clients/<profile-id> \
  -H "Authorization: Bearer $TOKEN"

curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/details \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"observacion":"Usar producto suave","etiquetas":["F","AC"]}'
```

Resultados esperados: `200`. `/queue` devuelve cada servicio con `pendientes_area`,
calculado con clientes activos y presentes que tienen servicios sin asignar en esa área.
La ficha devuelve las visitas desde la más reciente, con servicios y especialista
asignado. Ambos endpoints `/queue/clients` sin token responden `403`; un `<profile-id>`
inexistente responde `404`.

## Situación y cola pública

```bash
curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/situacion \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"situacion":"ausente"}'

curl -s http://localhost:8000/api/queue/public/status
```

Resultado esperado: ambos `200`; el turno ausente no aparece en `atendiendo` ni
`en_espera`. Cambiarlo a `presente` lo reincorpora si todavía está activo. La respuesta
incluye `por_area`, donde cada servicio tiene su posición propia dentro del área.

## Estado del especialista

```bash
curl -s -X PATCH http://localhost:8000/api/staff/<numero>/manual-status \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"manual_status":"ocupado"}'
```

Resultado esperado: `200`, con `manual_status` y `status` iguales a `ocupado` cuando no
tiene servicios activos.

Para bloquear asignaciones durante el almuerzo:

```bash
curl -s -X PATCH http://localhost:8000/api/staff/<numero>/manual-status \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"manual_status":"almorzando"}'
```

## Reposo y reanudación

```bash
curl -s -X POST \
  http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id>/rest \
  -H "Authorization: Bearer $TOKEN"

curl -s -X POST \
  http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id>/resume \
  -H "Authorization: Bearer $TOKEN"
```

Resultado esperado: el primer llamado deja el servicio en `reposo` y el especialista
vuelve a ser elegible; el segundo devuelve el servicio a `en_atencion`.

## Consultar cuántas personas faltan

```bash
curl -s 'http://localhost:8000/api/queue/position-search?q=20' \
  -H "Authorization: Bearer $TOKEN"
```

La respuesta incluye `posicion`, `personas_delante`, `estado` y `prioridad_int`. La
misma consulta acepta parte del nombre o de la cédula. Además incluye `areas`, con la
posición separada por servicio/área; si un servicio ya está en atención, su `posicion`
será `null`.

## Historial administrativo

```bash
curl -s http://localhost:8000/api/historial \
  -H "Authorization: Bearer $TOKEN"

curl -s 'http://localhost:8000/api/historial/summary?cliente=ambar' \
  -H "Authorization: Bearer $TOKEN"
```

Resultado esperado: ambos `200`. `/historial` devuelve servicios finalizados y
`/historial/summary` devuelve `total_servicios`, `total_usd` y `por_area`. Sin token,
ambos endpoints responden `403`.
