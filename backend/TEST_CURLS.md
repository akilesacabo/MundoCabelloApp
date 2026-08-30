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
    "ajustes":[{"service_id":<service-id>,"ajuste_usd":5}],
    "etiquetas":["XL","CM"],
    "observacion":"Usar producto suave",
    "staff_numeros_preseleccion":[<staff-numero-1>,<staff-numero-2>],
    "acepta_otro_estilista":true
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

El campo `ajustes` requiere añadir `-H "Authorization: Bearer $TOKEN"`. Sin token
administrativo responde `403`; si el servicio pertenece a una promoción o el valor no
está entre `0, 5, 10, 15, 20, 25, 30`, la operación se rechaza.

## Áreas dinámicas y eliminación lógica del catálogo

```bash
curl -s -X POST http://localhost:8000/api/services/areas \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Trenzas","color":"#8B5CF6"}'

curl -s -X POST http://localhost:8000/api/services \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"nombre":"TRENZA ESPECIAL","area_key":"trenzas","precio_usd":20}'

curl -s -X DELETE http://localhost:8000/api/services/<service-id> \
  -H "Authorization: Bearer $TOKEN"

curl -s 'http://localhost:8000/api/services?include_inactive=true' \
  -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8000/api/services/<service-id>/restore \
  -H "Authorization: Bearer $TOKEN"
```

Resultados esperados: creación `201`, eliminación `204` y restauración `200`. El
servicio eliminado no aparece en el catálogo operativo, pero sí con
`include_inactive=true`. Un área con asociaciones activas y un servicio incluido en una
promoción activa no se pueden eliminar.

Promociones y especialistas siguen el mismo patrón:

```bash
curl -s -X DELETE http://localhost:8000/api/services/promotions/<promotion-id> \
  -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/api/services/promotions/<promotion-id>/restore \
  -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE http://localhost:8000/api/staff/<numero> \
  -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/api/staff/<numero>/restore \
  -H "Authorization: Bearer $TOKEN"
```

Una especialista eliminada no puede iniciar sesión ni recibir asignaciones. Si conserva
trabajo activo, la eliminación responde `400`.

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

## Controles de la pantalla de asignación

```bash
# Asignar a una especialista ocupada: primero devuelve 409, luego confirmar.
curl -s -X POST http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id>/assign \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"staff_numero":<staff-ocupada>}'

curl -s -X POST http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id>/assign \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"staff_numero":<staff-ocupada>,"confirmar_ocupado":true}'

# Preferencias, reemplazo y anulación auditable; todo requiere token admin, no PIN.
curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/staff-preferences \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"staff_numeros":[1,2,3],"acepta_otro_estilista":true}'

curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id> \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"catalog_service_id":<nuevo-servicio-id>}'

curl -s -X DELETE http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id> \
  -H "Authorization: Bearer $TOKEN"

# Aplicar o quitar el único ajuste monetario del servicio.
curl -s -X PATCH \
  http://localhost:8000/api/queue/<cliente-id>/services/<servicio-id>/adjustment \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"ajuste_usd":10}'
```

Resultado esperado: se aceptan hasta tres especialistas; al anular, el servicio deja de
aparecer en asignaciones pero se conserva su registro. Un turno con solo manicure recibe
automáticamente la etiqueta `SOLO UÑAS`; esta se quita al agregar o editar un servicio de
otra área.

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

Resultado esperado: ambos `200`. `/historial` devuelve servicios finalizados con
`precio_base_usd`, `ajuste_usd` y `precio_usd` total; y
`/historial/summary` devuelve `total_servicios`, `total_usd` y `por_area`. Sin token,
ambos endpoints responden `403`.
