# Pendientes futuros

## Sesiones simultáneas y edición concurrente

**Estado:** pendiente para una fase posterior al piloto.

El sistema permite que varios dispositivos usen la aplicación al mismo tiempo,
incluso con el mismo usuario administrador. Las acciones se guardan de forma
atómica, pero todavía no existe control de concurrencia: dos sesiones que editan
el mismo registro pueden dejar el último guardado como resultado.

### Alcance acordado

- Agregar versión o marca `updated_at` a clientes/turnos, servicios de turno,
  promociones, catálogo y especialistas.
- Enviar esa versión desde la pantalla en cada escritura.
- Responder `409 Conflict` si otra sesión modificó el registro desde que se leyó;
  la interfaz debe pedir recargar antes de volver a guardar.
- Usar bloqueo transaccional de fila en PostgreSQL para asignar, cambiar,
  finalizar, poner en reposo o reanudar el mismo servicio simultáneamente.
- Crear usuarios nominales por operador para que la auditoría identifique a la
  persona y dispositivo responsable, en vez de registrar todo como `admin`.
- Definir refresco visible o actualización en tiempo real para las pantallas
  operativas, sin borrar formularios que el usuario esté editando.

### Criterio de aceptación

Si dos dispositivos abren el mismo registro y uno guarda primero, el segundo no
puede sobrescribirlo silenciosamente: recibe un aviso claro, recarga el estado
actual y decide cómo continuar.
