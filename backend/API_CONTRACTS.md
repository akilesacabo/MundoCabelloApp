# Contratos API — Fase 1

Base local: `http://localhost:8000/api`. Los endpoints protegidos reciben
`Authorization: Bearer <token>`.

## Autenticación

- `POST /auth/login`: body `{role, username, password}`. Roles: `admin` y
  `especialista`. Para el especialista, `username` es su número y `password` su cédula.
- `GET /auth/me`: identidad contenida en el token.

## Cliente y cola pública

- `POST /queue/checkin`: crea un turno con uno o más `service_ids`.
- `POST /queue/lookup?cedula=<cedula>`: recupera el último perfil exacto para autocompletar.
- `GET /queue/public/status`: público; devuelve `atendiendo`, `en_espera` y `ultimo_cambio`.

## Administración

Requieren rol `admin`:

- `GET /queue`: cola completa.
- `POST /queue/{cliente_id}/services/{servicio_id}/assign`.
- `POST /queue/{cliente_id}/services/assign-many`.
- `POST /queue/{cliente_id}/services/{servicio_id}/change-specialist`.
- `PATCH /queue/{cliente_id}/situacion`: `normal`, `ausente` o `estafa`.
- `POST /staff` y `PATCH /staff/{numero}`: alta y edición de especialistas.
- `POST /services` y `PATCH /services/{id}`: alta y edición del catálogo.

Errores: `400` regla de negocio, `403` autenticación/permisos, `404` recurso inexistente,
`409` duplicado y `422` validación del contrato.

## Especialista

- `GET /queue/specialist/mine`: solamente sus servicios pendientes/en atención.
- `POST /queue/{cliente_id}/services/{servicio_id}/finish`: el especialista solamente
  puede finalizar servicios asignados a su propia identidad; el admin puede finalizar cualquiera.
