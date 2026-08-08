# Estado del proyecto

## 2026-08-08 — Promociones y búsqueda de catálogo

- ✅ Verificado con pruebas automatizadas: el formulario de promociones ahora bloquea el doble envío,
  informa `Guardando…` mientras espera al API y actualiza la lista con la respuesta
  confirmada de creación o edición.
- ✅ Verificado con pruebas automatizadas: el buscador de promociones prioriza las coincidencias del
  nombre del servicio sobre las coincidencias que existan únicamente en el área.
- ✅ Nueva regresión: edición de una promoción que conserva un servicio y agrega otro.
- ✅ Verificado con pruebas automatizadas: al editar una promoción, sus servicios ya incluidos se
  ordenan antes que los demás resultados del catálogo.
- ✅ Verificado con pruebas automatizadas: al editar una promoción se eliminan primero las asociaciones
  anteriores antes de guardar la lista nueva, evitando la restricción única de la base.
- ✅ Verificado con pruebas automatizadas: los nombres repetidos de promociones responden con un error
  legible en lugar de un error 500.

## Deuda técnica observada

- La prueba visual aislada requiere un segundo puerto local; el entorno actual bloqueó
  ese puerto. Antes del deploy, validar manualmente el flujo crear → editar → agregar
  servicio con el servidor normal.
