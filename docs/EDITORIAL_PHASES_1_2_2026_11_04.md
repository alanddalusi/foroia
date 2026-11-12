# Fases 1 y 2: implementación local, sin activar producción

4 de noviembre de 2026. Complementa el [plan de dos artículos diarios](TWO_DAILY_ARTICLES_PLAN_2026_11_04.md).

## Resultado y alcance

Implementadas la reparación de recibos, las correcciones editoriales concretas y dos líneas persistentes dentro del trabajador existente. La prueba integrada local publica una noticia y un práctico mediante la misma selección, generación, revisión, validación, publicación y comprobación HTTP/SSR actuales. **Las respuestas de modelos son simuladas; no se ha publicado nada en producción ni realizado llamadas a OpenAI.**

La bandera `RESEARCH_TWO_LANES=false` mantiene desactivado el nuevo funcionamiento. El horario sigue siendo 22:30 Europe/Madrid. Los topes efectivos de producción no se han tocado: 0,20 USD diarios y 10 USD mensuales. Las validaciones de configuración todavía rechazan 0,40/12: ese cambio requiere autorización y modificación explícita posteriores.

## Cambios implementados

### Recibos y candidatos bloqueados

- `scripts/verify_editorial_examples.py` comprueba el manifiesto **dentro de la imagen** antes de ejecutar ejemplos: hashes de código y dependencias deben coincidir con el árbol local. El runtime del recibo procede de esa imagen, no del equipo anfitrión.
- Los seis programas revisados se ejecutan en contenedores sin red ni secretos, raíz de solo lectura y límites de CPU/memoria/procesos. No se ejecuta código proporcionado por el modelo.
- El recibo se valida otra vez dentro de la imagen antes de sustituir el archivo anterior. Una imagen desalineada o cualquier prueba fallida conserva el recibo previo y hace fallar el proceso.
- `research.examples.receipt_status` diferencia dependencias, runtime, código, resultado de prueba, caducidad y procedencia incorrectos. `verified_example` valida una única lectura del archivo.
- `queue.recover_verified_examples` reabre únicamente candidatos rechazados/aplazados por `example_not_verified` cuando su ejemplo vuelve a estar verificado, con auditoría y sin reiniciar los límites de intentos pagados. No reabre rechazos por estilo, duplicidad o falta de evidencias.
- `deploy/receipts/verified-examples.json` se ha regenerado **solo en local**. En producción sigue el artefacto anterior hasta un despliegue autorizado.

### Correcciones editoriales

- El corrector recibe número de secciones, palabras, encabezados, defectos locales, veredictos editoriales y acciones concretas. Si el revisor rechaza la estructura de seis apartados, se solicita agruparlos aunque el texto supere 350 palabras.
- El feedback prohíbe rellenar para alcanzar un umbral. Conserva hechos, evidencias, atribuciones necesarias y ejemplos comprobados.
- Una reescritura de estilo con el mismo texto normalizado se rechaza antes de pagar otra revisión idéntica.
- Sigue habiendo como máximo una corrección por candidato. El texto corregido debe superar otra vez la validación local, la revisión y las comprobaciones de evidencias; no se publica por agotar intentos.
- Los fallos guardan código y detalles en el informe privado. No se han eliminado reglas de veracidad, originalidad o atribución.

### Dos líneas, un trabajador y un presupuesto

- La migración aditiva `0010_editorial_lanes` añade `editorial_lane_runs`: una fila única por jornada y motor (`news`/`evergreen`). No modifica artículos, usuarios ni el libro económico anterior.
- `research.lanes.LaneRun` adapta cada espacio de trabajo al **mismo** `editorial.execute` y `worker.pipeline`. No existe otro motor de redacción, publicador ni planificador.
- Cada línea tiene candidato activo, artículo, errores y checkpoints propios. Se busca una publicación por línea. Las actualizaciones de artículos existentes no llenan estas cuotas de artículos nuevos.
- La selección gratuita comprueba si existe un práctico viable antes de proteger su margen económico. Se reutiliza el cálculo de margen existente —0,04 USD con el modelo/configuración actuales—, que es una protección mínima, no una promesa de que cualquier contexto cabrá en ese importe.
- Las llamadas de investigación y redacción de noticias respetan ese margen además del límite diario/mensual global. Cada llamada sigue calculando su reserva antes de salir a OpenAI.
- Las reservas y liquidaciones continúan usando el bloqueo de fila de `ResearchControl` y `ResearchRun`; las líneas no duplican el saldo global. Los cargos inciertos conservan su reserva.
- Un fallo HTTP, de investigación, generación o estilo de una línea permite continuar la otra. Pausa, pérdida de bloqueo o una inconsistencia económica siguen deteniendo el trabajo global.
- Preflight acotado a 90 segundos y cada línea a 360, dentro del límite de 900 segundos del trabajador actual. Los intentos y la corrección permanecen acotados; no se conceden búsquedas o reintentos ilimitados.
- La transacción final bloquea y comprueba el estado del candidato. Dos transacciones que compiten por él no publican dos artículos.

### Recuperación y observabilidad

- Un borrador recibido antes de una caída puede reutilizarse desde el checkpoint sin repetir la generación. Una revisión pendiente puede continuar otra jornada sin redactar de nuevo.
- Un resultado de pago incierto se conserva y no se repite automáticamente. La otra línea puede utilizar su presupuesto disponible.
- La verificación pública pendiente se recupera sin volver al modelo. Un candidato ya publicado antes de una caída se reconoce al recuperar su línea.
- La comprobación posterior de cada artículo conserva HTTP, API, SSR, canonical, metadatos, sitemap e imagen. Un error crítico mantiene el mecanismo de retirada/restauración existente.
- El informe diario contiene objetivo dos, publicaciones verificadas, estado/motivo por línea y coste calculado con uso comunicado. La investigación compartida aparece separada, sin sumarla otra vez a ambas líneas. Estos importes no se presentan como facturas verificadas.
- Los informes privados de las nuevas líneas se limpian después de 30 días como los anteriores; se conservan los registros económicos y de auditoría.
- La presentación visual completa del panel sigue siendo una fase posterior. En esta fase quedan los estados y resúmenes persistidos en backend/informe diario.

## Validación realizada

| Comprobación | Resultado |
|---|---|
| Suite general local | 446 pruebas correctas; 76 condicionales omitidas en esa ejecución |
| PostgreSQL 17 y Redis 7 reales, aislados sin puertos publicados | 6 pruebas correctas |
| Nuxt real + FastAPI + base aislada, dos publicaciones y verificación HTTP/SSR | 1 prueba integrada correcta; dos URLs locales verificadas |
| Ejemplos ejecutados y recibo validado dentro de la imagen | 6/6 correctos |
| Sintaxis Python y YAML de Compose/CI | Correctos |
| OpenAI / producción | Cero llamadas pagadas, cero publicaciones y cero despliegues |

Las seis pruebas PostgreSQL comprueban reservas diarias y mensuales con conexiones simultáneas, propiedad del bloqueo y margen práctico con Redis real, publicación concurrente del mismo candidato, migración/reversión preservando artículo y saldo, y liquidación concurrente de una reserva exactamente una vez. No se ha sustituido esta validación por SQLite.

Las pruebas de recuperación simulan caída tras recibir el borrador, caída con petición incierta, revisión pendiente entre días y reinicio después de completar la jornada. La prueba de horario pasa de 22:29:59 a 22:30 Madrid y comprueba que el segundo tick no gasta ni publica otra vez.

Los modelos, documentos y anuncios de prueba son fixtures controladas; no demuestran una publicación real actual ni que existan noticias verificables todos los días. Las pruebas PostgreSQL y HTTP se ejecutaron aparte con sus condiciones de aislamiento habilitadas. Los demás tests condicionales de la suite no se anuncian como ejecutados.

Se añadieron estas comprobaciones PostgreSQL a un job específico de CI. Su configuración se validó localmente; no se ha ejecutado un workflow remoto durante esta intervención. La prueba de migración emite dos avisos heredados de Alembic por `path_separator` no configurado; no ha fallado la migración ni la reversión.

## Archivos afectados

- Persistencia/configuración: `api/app/models.py`, `api/alembic/versions/0010_editorial_lanes.py`, `api/app/research/config.py`, `compose.production.yml`, `.env.example`, `deploy/production.env.example`.
- Coordinación y contabilidad: `api/app/research/lanes.py`, `editorial.py`, `worker.py`, `night_web.py`, `checkpoints.py`, `executions.py`, `publication.py` dentro de `research/`.
- Recibos y calidad: `research/examples.py`, `queue.py`, `style.py`, `quality.py`, `scripts/verify_editorial_examples.py`, `deploy/receipts/verified-examples.json`.
- Pruebas: `tests/test_editorial_lanes.py`, `test_editorial_lanes_postgres.py`, `test_editorial_receipts.py`, `test_editorial_style_corrections.py`, extensión de `test_editorial_http.py` y `.github/workflows/checks.yml`.
- Documentación: este informe y referencias en `PROJECT_BRIEF.md`, `README.md`, `docs/ARCHITECTURE.md`.

No se han añadido dependencias de ejecución, cambiado las tarifas, DNS, SSH, firewall, credenciales, publicidad ni analítica. El frontend público no necesita cambios para mostrar ambos artículos: sigue leyendo los artículos publicados existentes.

## Presupuesto propuesto y pasos pendientes

La [simulación de 30 días](TWO_DAILY_ARTICLES_PLAN_2026_11_04.md) sigue siendo una estimación, basada en 46 registros de consumo y reservas representativas. Con costes observados, dos artículos aprobables cabían en 0,20/10. Con costes y reservas duplicados, 0,40/12 permitía el objetivo hipotético de 60; unos 7,37 USD, u 8,02 incluyendo nueve artículos adicionales de depósito. **No es una garantía de coste, disponibilidad de fuentes ni aprobación del modelo.**

Propuesta para evaluar al activar la estrategia completa: **máximo 0,40 USD/día y 12 USD/mes**, sin necesidad demostrada ahora de superar esa cifra. Con 31 días debe gobernar también el techo mensual; el margen diario medio desde saldo íntegro sería aproximadamente 0,387096 USD. No se ha activado este presupuesto ni habilitado su aceptación en configuración.

Antes de producción faltan:

1. Ampliar y renovar el catálogo práctico, rotación entre secciones y deduplicación por tarea. El catálogo actual de 11 temas no sostiene un mes de prácticos distintos.
2. Propagar la ampliación de actualidad hasta siete días por todas las capas. En esta fase se conserva la ventana original de 24–48 horas.
3. Implementar, preparar y reponer los nueve artículos completos de reserva. Los ejemplos verificados y los candidatos con fuentes preparadas **no son ese depósito**.
4. Completar la presentación del panel por línea y de la reserva; medir costes por publicación y rechazos previos a la API.
5. Autorizar el presupuesto definitivo y el despliegue. Generar/transportar una imagen y su recibo compatibles, comprobar el recibo contra la imagen destinada al VPS, crear backup completo y demostrar restauración, aplicar `0010`, desplegar con bandera apagada y verificar servicios/URLs.
6. Activar la bandera únicamente tras las comprobaciones y autorización. Rollback de código/bandera conservando la tabla aditiva, los artículos y el saldo: **no rebobinar reservas ni restaurar una base antigua sobre nuevas publicaciones**.
7. Una prueba OpenAI real y su máximo económico requieren autorización posterior. No se ha suplido con una noticia de prueba publicada.

Producción continuará con el funcionamiento anterior hasta completar esos pasos. Estas dos fases solucionan la base técnica; por sí solas todavía no garantizan dos artículos diarios.

La ampliación del catálogo, el depósito y el panel completan la estrategia y pueden hacerse por fases. Es posible preparar un despliegue separado de las fases 1–2 con la bandera apagada; seguiría requiriendo autorización, backup/restauración, migración y comprobación del recibo contra la imagen del VPS. Esta intervención no ha realizado ese despliegue.
