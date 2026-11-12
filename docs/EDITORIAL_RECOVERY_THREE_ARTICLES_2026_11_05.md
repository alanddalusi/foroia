# Recuperación editorial y objetivo de tres artículos — preparación local

5 de noviembre de 2026. **Implementado y probado en local; no desplegado ni activado en producción. Cero llamadas de pago.** Se reutilizan el trabajador, la cola, los checkpoints, el reservador PostgreSQL, el bloqueo Redis y la publicación existentes.

## Diagnóstico antes de los cambios

La consulta de producción fue de solo lectura. Encontró 46 candidatos: 12 en cola, siete publicados y 27 con estado antiguo `rejected`. De estos últimos, 17 son propuestas de documentación agrupadas/no accionables y **diez son los descartes investigados**. La interfaz anterior devolvía como máximo 40 registros: sus pestañas no representaban toda la cola. Ahora devuelve hasta 100 y avisa si hay truncamiento.

| ID | Candidato registrado | Causa comprobada | Decisión y corrección |
|---|---|---|---|
| 3 | SQLite: guardar respuestas sin duplicados | Primera revisión contradictoria: `approved=true`, `original=false`, sin motivos. La corrección no recibió ese fallo de originalidad. Segunda revisión rechazó afirmaciones prácticas y cobertura de duplicados. | Rechazo real del veredicto, feedback defectuoso. Se transmite cada flag fallido, se reutiliza el borrador y se permite una corrección dirigida adicional como máximo. El ejemplo aislado sí comprueba que dos guardados mantienen un registro; no demuestra concurrencia avanzada ni justifica cualquier consejo. No se ha convertido la revisión antigua en aprobación. |
| 4 | Unicode y espacios | Primera versión demasiado fragmentada. La segunda mezclaba recomendaciones sin apoyo y el revisor reclamó que los tests estuvieran en `initial_fragment_ids`. | Hay problemas reales y un fallo de contrato: esos IDs son sugerencias y el test verificado es evidencia válida de su propio alcance. Contrato aclarado y selección de tests validada; corrección del borrador pendiente de superar una revisión nueva. |
| 5 | Pydantic | Revisión completamente aprobada. Publicación retirada con `publication_not_indexable`: el verificador comparaba una entradilla de 183 caracteres con la descripción SEO recortada. | Falso positivo reproducido y corregido. La recuperación local restaura el mismo artículo #16, su URL y sus fechas sin usar el modelo. Se bloquea ante una edición posterior, aprobación alterada, fuente caducada no revalidada o evidencias distintas. |
| 7 | Separar instrucciones, contexto y datos | `duplicate_topic`; ya existe cobertura publicada de esa tarea. | Mantener rechazo definitivo. No se reinician intentos ni se cambia el titular para evitar la deduplicación. |
| 8 | Prompts de Gemini | `invalid_example`: la selección de ejemplos no coincidía con la permitida. **La respuesta cruda de esa ejecución antigua no se conservó**, por lo que no podemos identificar honestamente el valor exacto devuelto. | Se restringe el esquema a los IDs verificados o a una lista vacía si no hay ejemplo. Se preservan futuras respuestas y fallos. En este caso se reutilizan las fuentes, pero no existe un borrador recuperable guardado: necesitará una generación futura presupuestada. No se simula que ya haya sido recuperado. |
| 10 | Revisar JSON: formato, esquema y fuentes | Revisor exigió citas literales dentro de cada párrafo público pese a existir referencias privadas. Después, la corrección introdujo fragmentación excesiva. | Contradicción del prompt corregida. La estructura sigue siendo un defecto real que debe corregirse y revisarse. Se conserva el borrador ya pagado. |
| 14 | Candidato de noticia «Introducing GPT-6.1 Terra» | `insufficient_independent_topic_sources`, cero intentos de generación. | No hay prueba suficiente en el historial para declarar un falso positivo. Se mantiene rechazado. El título es el de un candidato registrado, no una afirmación nuestra sobre un anuncio. |
| 32 | Recopilación de Google Cloud | Versión inicial insuficiente; versión corregida utiliza «El resumen procede del blog oficial de Google Cloud», pero no supera la expresión de atribución. | Falso positivo de formulación: se admite esa procedencia oficial explícita, sin admitir «un blog sobre Google». Se conservan los controles de vigencia, atribución de promesas y revisión. |
| 33 | NVIDIA y servicios para ciudades | La primera versión menciona ausencia de comparativas y activa el detector de alcance. La corrección termina demasiado fragmentada. | Se distingue una limitación explícita de una comparación objetiva; el revisor sigue comprobando su evidencia. El defecto de estructura permanece sujeto a corrección/revisión. No se publicará una noticia caducada. |
| 34 | Primera petición OpenAI con Python | Dos revisiones rechazan afirmaciones sobre beneficios y sobre lo que la documentación no cubre; la corrección conserva recomendaciones sin respaldo. | Defecto real del texto y corrección insuficiente. Se señala cada frase fallida y se pide eliminarla o respaldarla; escribir «recomendamos» no valida una afirmación factual. Borrador #17 conservado para una corrección acotada. |

Los estados antiguos no se han modificado en producción. La reclasificación se ejecutará dentro del trabajador después de un despliegue autorizado; es idempotente y no pone a cero intentos ni costes.

## `article_seo_mismatch`: URLs afectadas

La comprobación pública directa encontró HTTP 200, canonical correcto y ausencia de `noindex` en las once páginas publicadas consultadas. Las seis diferencias de descripción corresponden al recorte legítimo de Nuxt:

- `/articulos/agentic-commerce-anuncios-agentes-servicio-asia`
- `/articulos/validar-json-ia-python`
- `/articulos/convertir-json-csv-python-seguro`
- `/articulos/organizar-instrucciones-claude-documentos`
- `/articulos/separar-instrucciones-contexto-datos-openai-gemini-claude`
- `/articulos/fastapi-validar-peticiones-ia`

El monitor y el verificador comparten ahora una proyección equivalente a `seoDescription` de Nuxt. Una descripción ajena, un canonical incorrecto o un `noindex` siguen causando rechazo. El monitor incluye la URL y los campos concretos que fallan. No se han cambiado las entradillas ni las metadescripciones de los artículos públicos para esquivar el error; tampoco se ha afirmado indexación en Google.

La prueba SSR detectó además una incompatibilidad entre el `NewsArticle` correcto de las noticias y la exigencia antigua de `BlogPosting` del verificador. Se aceptan los tipos de artículo correspondientes, manteniendo la comprobación de título, fechas, fuentes y canonical.

## Funcionamiento implementado

- Estados explícitos: `rejected`, `correction_pending`, `budget_pending`, `publication_error` y `technical_error`. Cobros inciertos y ediciones posteriores no se reintentan a ciegas.
- Borradores, revisión, catálogo de evidencias, feedback y respuestas recibidas se conservan al rechazar una corrección. Se reanuda la etapa pendiente, sin repetir la investigación ni una primera redacción disponible.
- Hasta **dos correcciones pagadas en total por borrador**, con los mismos límites económicos; ninguna se aprueba por agotamiento. Una corrección que no llega a reservar presupuesto no consume un intento. Una llamada de resultado incierto conserva su reserva y no se repite automáticamente.
- Una aprobación guardada se vuelve a validar localmente antes de recuperar visibilidad. Se comprueba que no haya cambios posteriores y se conserva la misma fila, URL, fecha y contenido. La recuperación requiere las comprobaciones públicas habituales.
- La evidencia guardada de documentación puede revalidarse por HTTP sin modelo. Si los bytes preparados han cambiado, no se reutiliza la aprobación antigua. Las noticias conservan sus límites de vigencia.
- Se priorizan las correcciones y publicaciones recuperables antes de nuevos encargos. Los duplicados, material no verificable y agrupaciones no se reabren indiscriminadamente.
- Plan diario persistido: una noticia y hasta dos prácticos, con `slot` independiente para cada práctico. Un fallo de un espacio no bloquea el siguiente. Los slots terminados no vuelven a gastar después de reiniciar.
- Cuota final bajo bloqueo PostgreSQL: una noticia y dos prácticos como máximo cuando se active esa configuración, contando también publicaciones manuales y recuperaciones. La restricción única impide duplicar slots.
- Reserva de margen para los prácticos antes de investigar noticias y para el segundo práctico mientras trabaja el primero. Se mantienen reservas atómicas diarias/mensuales y liquidación solo ante consumo conocido.
- El panel muestra objetivo configurable, resultados por slot, coste calculado de redacción/revisión, motivos técnicos, correcciones usadas y material reutilizable. La búsqueda compartida se contabiliza aparte. El consumo calculado no se presenta como factura confirmada.

No se añadió un planificador: sigue siendo el único turno a las **22:30 Europe/Madrid**. La opción `RESEARCH_PRACTICAL_PUBLICATIONS` vale **1 por defecto** y debe establecerse explícitamente en 2 para el nuevo objetivo.

El esquema restringe los identificadores mediante `enum` y la longitud de la lista mediante `minItems`/`maxItems`, conforme a [OpenAI Docs: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Esto controla el formato; no demuestra veracidad. Se mantiene la validación de evidencias y la revisión posterior. No se cambió de modelo ni se contrataron servicios.

## Viabilidad económica

Se usaron **68 llamadas registradas**: 13 investigaciones, seis recuperaciones, 29 redacciones/correcciones y 20 revisiones. Los importes son calculados con tokens/herramientas informados y tarifas configuradas, no facturas independientes.

| Escenario, tres artículos válidos por jornada | 30 días | 31 días |
|---|---:|---:|
| Costes medianos; sin correcciones | 1,720650 USD | 1,778005 USD |
| Máximos observados; búsqueda alternativa y una corrección por artículo | 4,821870 USD | 4,982599 USD |
| Dos correcciones por artículo, máximos observados | 6,468960 USD | 6,684592 USD |
| Caso anterior con todos los costes multiplicados por dos | **12,937920 USD** | **13,369184 USD** |

El último escenario alcanza una reserva diaria máxima modelada de **0,438048 USD**, por debajo de 0,50. El techo mensual de 15 USD también se respeta en meses de 31 días. Si se gastaran realmente 0,50 cada día, un mes de 31 días exigiría 15,50: el reservador debe y seguirá bloqueando lo que supere el techo mensual.

**Propuesta: 0,50 USD/día y 15 USD/mes. No hay justificación observada para pedir más ahora.** Estas simulaciones suponen candidatos y revisiones válidos; no prueban una tasa real de 90 publicaciones ni eliminan fallos de recuperación HTTP. Las reservas inciertas, cambios de longitud de contexto y rechazos adicionales pueden reducir las publicaciones. No se gasta el saldo por obligación.

## Verificaciones realizadas

- Suite general: **506 correctas, 107 omitidas**. Las omisiones corresponden a integraciones y comprobaciones que necesitan activación explícita; no se contabilizan como aprobadas.
- PostgreSQL 17 y Redis 7 reales, en contenedores locales aislados y sin puertos publicados: **10 pruebas correctas**. Incluyen presupuestos diarios/mensuales concurrentes, reserva para prácticos, reclamación única de ambos slots, carrera de publicaciones distintas contra la cuota, deduplicación final, liquidación idempotente y round-trip de migraciones con contenido/presupuesto conservados. Dos avisos de deprecación previos de Alembic sobre `path_separator`; no hubo errores.
- Nuxt SSR y FastAPI reales con base aislada y respuestas del modelo simuladas: **2 pruebas correctas**, Pydantic y tres slots. Verifican HTTP, contenido inicial, API, canonical, datos estructurados, imagen y sitemap. Estas pruebas **no son publicaciones reales de producción**.
- **19 regresiones nuevas** dentro de la suite: diez fallos históricos, descripciones reales, recuperación del mismo artículo Pydantic sin modelo, bloqueo de edición posterior, originalidad contradictoria, corrección al día siguiente, presupuesto pendiente, IDs/test verificado, tres slots y simulación económica. Se comprueba que `noindex`, descripción ajena y referencia de test inventada siguen siendo rechazados.
- TypeScript de Nuxt: correcto. Build de frontend: correcto. No se añadieron dependencias.

Comandos reproducibles sin proveedor:

```powershell
$env:PYTHONPATH='api'
.local/venv/Scripts/python.exe -m pytest tests -q
.local/venv/Scripts/python.exe scripts/simulate_editorial_capacity.py --fixture tests/fixtures/editorial_capacity_20261105.json --practical-articles 2 --corrections 2 --output .local/editorial-capacity.json
```

Las integraciones PostgreSQL usan `FOROIA_ISOLATED_DB=lanes-phase12`, la base dedicada `foroia_lanes_phase12` y **ninguna clave OpenAI**. No ejecutar esos tests contra una base de aplicación. SSR requiere el build local, `FOROIA_ANALYTICS_LOCAL=1` y `FOROIA_NODE_BINARY`. TypeScript y build se ejecutan con los scripts existentes de `web/package.json`.

## Archivos y activación

Backend: `research/recovery.py`, `quota.py`, `seo.py`, `queue.py`, `quality.py`, `writing.py`, `editorial.py`, `lanes.py`, `publication.py`, `monitor.py`, `executions.py`, `routes.py`, `config.py` y `models.py`.

Persistencia: migración aditiva `0011_recoverable_editorial`. Añade estados y slot, conserva filas y reservas. El downgrade se niega a eliminar un segundo slot con historial; para un rollback se debe conservar el esquema aditivo y usar la imagen anterior compatible, sin restaurar datos antiguos encima de publicaciones nuevas.

Interfaz: `web/pages/editorial/investigacion.vue` y `web/utils/research-status.ts`. Configuración: Compose y archivos de ejemplo, sin modificar los `.env` reales. Pruebas: `test_editorial_recoverable.py`, `test_editorial_lanes_postgres.py`, `test_editorial_http.py`, fixtures anonimizadas de fallos/costes y comprobaciones de límites actualizadas. Simulador: `scripts/simulate_editorial_capacity.py`.

Antes de activar: autorización del propietario; backup completo y restauración aislada; construir API/worker/frontend, generar recibo de ejemplos contra la imagen nueva, aplicar Alembic y configurar explícitamente `RESEARCH_TWO_LANES=true`, `RESEARCH_PRACTICAL_PUBLICATIONS=2`, `RESEARCH_DAILY_USD=0.50`, `RESEARCH_MONTHLY_USD=15`. Revisar la recuperación gratuita del artículo #16 y los demás candidatos conservados, salud, privacidad de PostgreSQL/Redis, HTTP/SSR/canonical/sitemap, presupuesto y próximo turno. Conservar rollback de imágenes/configuración y **no borrar artículos, checkpoints o reservas**.

Si se vuelve a una imagen que desconoce `0011`, su arranque de API debe omitir el Alembic antiguo y arrancar Uvicorn con el comando documentado del despliegue; no ejecutar un downgrade ni una restauración sobre datos nuevos. Restaurar el plan/configuración anterior y comprobar la compatibilidad de su trabajador con los estados pendientes. Este procedimiento de despliegue se concretará contra el estado real del VPS tras la autorización, antes de efectuar cambios.

Producción sigue con **0,20 USD diarios, 10 USD mensuales y las 22:30**. No se autorizó ni ejecutó una prueba pagada o despliegue en esta intervención. El objetivo de tres publicaciones diarias todavía necesita demostrarse en funcionamiento real después de la autorización.
