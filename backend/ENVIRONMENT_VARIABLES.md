# Variables de entorno

| Variable | Uso |
|---|---|
| `DATABASE_URL` | Conexión SQLAlchemy async |
| `ADMIN_USERNAME` | Usuario administrador |
| `ADMIN_PASSWORD` | Contraseña administrador; obligatoria y distinta al default en producción |
| `AUTH_SECRET` | Firma de tokens; secreto aleatorio de al menos 32 caracteres en producción |
| `AUTH_TOKEN_TTL_MINUTES` | Duración del token, 480 por defecto |
| `ADMIN_PIN` | Autoriza reasignaciones sensibles |
| `CORS_ORIGINS` | Orígenes web permitidos; en desarrollo incluye los puertos locales `5173` y `5174` |

Nunca versionar valores reales de contraseñas, PIN o secretos.
