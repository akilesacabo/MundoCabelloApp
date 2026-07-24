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

Resultado esperado: búsqueda `200`; check-in `201`. Repetir el mismo check-in antes de
finalizarlo debe responder `409` con el número del turno activo.

## Base de clientes y edición de visita

```bash
curl -s http://localhost:8000/api/queue/clients \
  -H "Authorization: Bearer $TOKEN"

curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/details \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"observacion":"Usar producto suave","etiquetas":["F","AC"]}'
```

Resultados esperados: `200`. `/queue/clients` sin token responde `403`.

## Situación y cola pública

```bash
curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/situacion \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"situacion":"ausente"}'

curl -s http://localhost:8000/api/queue/public/status
```

Resultado esperado: ambos `200`; el turno ausente no aparece en `atendiendo` ni
`en_espera`. Cambiarlo a `presente` lo reincorpora si todavía está activo.

## Estado del especialista

```bash
curl -s -X PATCH http://localhost:8000/api/staff/<numero>/manual-status \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"manual_status":"ocupado"}'
```

Resultado esperado: `200`, con `manual_status` y `status` iguales a `ocupado` cuando no
tiene servicios activos.
