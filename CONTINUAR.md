# Estado del proyecto

## 2026-08-29 — Preparación segura del deploy a Railway

- ✅ Respaldo lógico de PostgreSQL 18 creado antes de migrar, recorrido completamente
  con `pg_restore`, inventario de tablas confirmado y SHA-256 verificado.
- ✅ El `seed` dejó de ejecutarse automáticamente en el arranque de producción: modifica
  datos maestros y queda reservado para uso manual en bases nuevas o de desarrollo.
- ✅ `.gitignore` protege secretos `.env`, bases, respaldos y exportaciones de auditoría.
- ✅ Railway ejecuta `alembic upgrade head` como Pre-Deploy y usa un Start Command
  dedicado únicamente a Gunicorn, sin seed. El redeploy del commit anterior terminó
  `SUCCESS`; los logs confirmaron Alembic y Gunicorn sin seed, `/health` respondió `ok`
  y `/ready` respondió `ready`.
- ✅ El Dockerfile local también queda dedicado únicamente a Gunicorn; las migraciones
  pertenecen al Pre-Deploy y el seed permanece manual.
- ⏳ Deploy y verificación post-deploy todavía pendientes.

## 2026-08-29 — Explicación pública del orden FIFO

- ✅ Causa raíz confirmada: la cola ya ordenaba correctamente por prioridad `INT` y
  fecha de registro, pero el texto de ayuda público conservaba la explicación anterior
  de orden por nombre.
- ✅ El texto ahora comunica que, dentro de cada nivel, quien se registró primero aparece
  primero. Se agregó una regresión para impedir que reaparezca la frase antigua.

## 2026-08-28 — Catálogo dinámico, eliminación lógica, FIFO y recargos

- ✅ Áreas/categorías configurables desde administración, reutilizadas por servicios,
  especialistas, check-in, equipo y cola pública.
- ✅ Áreas, servicios, promociones y especialistas tienen eliminación lógica y
  restauración. Se conserva el historial y se bloquean eliminaciones con dependencias
  operativas activas.
- ✅ Una especialista inactiva no puede iniciar sesión, aparecer en operación ni recibir
  asignaciones.
- ✅ Las colas priorizan `INT` y luego el orden real de registro (FIFO), también por área.
- ✅ Cada servicio normal de una visita admite un único recargo administrativo de USD
  0 a 30 en incrementos de USD 5. Promociones y registros heredados quedan bloqueados.
- ✅ Historial y pantallas muestran precio base, recargo, total y auditoría del cambio.
- ✅ Migración `20260828_catalog_adjustments` probada primero sobre una copia y aplicada
  a la base local; integridad SQLite: `ok`.
- ✅ Suite automatizada y navegación local verificadas. Deploy todavía pendiente.

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

## Pendiente para una versión posterior

- Plantillas.
- Peinado especial con ajuste propio.

## Flujo Git para una etapa futura

- Decisión de Juan Pablo, 2026-08-29: mientras sea el único desarrollador, se permite
  integrar una rama verificada mediante merge directo con `--ff-only` y un gate separado
  antes del push a `master`.
- Cuando haya más desarrolladores, validaciones automáticas o cambios que requieran una
  revisión formal, usar GitHub CLI (`gh`) y Pull Requests antes del merge.
- Comandos útiles: `gh pr create`, `gh pr status` y `gh pr view --web`.

## Deuda técnica observada

- La cola pública carga `/services/areas` enviando el token local cuando existe. Si ese
  token está vencido, el endpoint responde `403` y las áreas quedan sin cargar hasta
  renovar o limpiar la sesión. No afecta una sesión vigente y no forma parte del ajuste
  textual de FIFO.
