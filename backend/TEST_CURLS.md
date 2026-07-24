# Recetas de prueba local

Primero arranque la API y exporte el token obtenido en el login.

```bash
curl -s http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"role":"admin","username":"<admin-user>","password":"<admin-password>"}'

export TOKEN='<access-token>'

curl -s http://localhost:8000/api/queue \
  -H "Authorization: Bearer $TOKEN"

curl -s http://localhost:8000/api/queue/public/status

curl -s -X PATCH http://localhost:8000/api/queue/<cliente-id>/situacion \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"situacion":"ausente"}'
```

Resultados esperados: login `200`; cola administrativa `200` con token y `403` sin token;
cola pública `200` sin token; cambio de situación `200` y el turno ausente deja de aparecer
en la cola pública.
