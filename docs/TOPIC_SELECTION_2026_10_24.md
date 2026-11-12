# Selección temática e independencia antes de generar

24/10/2026. Corrección posterior al despliegue de evidencias. No cambia presupuesto, horario, dependencias ni esquema.

## Problema reproducido

El catálogo anterior contenía siete documentos de cuatro organizaciones. El modelo eligió ThinkingBox y Flint-interactive, ambos de Microsoft, y su corrección repitió la misma elección. Tener organizaciones distintas disponibles no aseguraba que hubiera un tema común ni que el artículo las citara.

La reproducción local del catálogo real, sin proveedor ni escrituras, separa los siete documentos en candidatos sin corroboración independiente. Ninguno debe generarse con esas evidencias. Se evita encargar la redacción de ese conjunto; no se sustituye por una mezcla de anuncios ni se añade una fuente irrelevante para alcanzar una cuota.

## Comportamiento preparado

1. Tras recuperar documentos y antes de reservar dinero, `selection.py` comprueba organización, contenido suficiente y procedencia. Dominios oficiales corresponden a una organización curada; Hugging Face exige el namespace/firma ya verificados. Dos documentos Microsoft, incluso alojados en hosts distintos, tienen una sola organización.
2. El colector atribuye las redirecciones al dominio final, sin conservar por error la organización del feed original. No se infiere una organización nueva a partir de un namespace desconocido.
3. Se excluyen misma URL/procedencia canónica explícita, contenido idéntico y reproducción casi literal mediante shingles. La procedencia externa declarada se usa para detectar reproducción, nunca para seguir una URL fuera de la allowlist.
4. Se agrupan temas con anclas específicas, contexto y equivalencias conceptuales bilingües versionadas. «IA», «modelos» o «agentes» por sí solos no relacionan noticias. Todos los documentos de un grupo deben relacionarse entre sí; no se unen cadenas transitivas que acaben mezclando temas distintos.
5. Cada candidato recibe identificador, título, documentos, organizaciones, relaciones medidas y motivo. Los no válidos se descartan antes de generar y se evalúa el siguiente. Se escoge un único candidato válido por ejecución y un representante por organización para equilibrar el contexto.
6. La primera pasada del trabajador recupera como máximo seis documentos, reservando dos plazas para la búsqueda complementaria. Si no hay candidato válido, prioriza entradas RSS relacionadas aún no descargadas y después prueba los siguientes temas del inventario autorizado. Se mantienen **12 intentos de descarga de artículos y 8 documentos recuperados**, compartidos con la recuperación inicial. No se repite ninguna URL ya intentada, incluidos los 403. Si no hay entradas pendientes o se agotaron los límites, queda registrado. Una prueba específica comprueba que las dos plazas se utilizan realmente cuando hay candidatos pendientes.
7. Un título RSS solo puede proponer una descarga; no pasa como evidencia. La página debe descargarse, tener contenido suficiente y superar la selección final. La recuperación no usa búsquedas abiertas, APIs de pago, proxies ni accesos privados.
8. Solo el conjunto seleccionado llega al catálogo de fragmentos y al generador. No se cambian IDs de fuentes o fragmentos. El control final sigue exigiendo **dos organizaciones realmente citadas**; elegir dos documentos no basta si ambos son de la misma organización. La revisión semántica y los demás controles permanecen activos.
9. Los borradores pendientes de revisión conservan su conjunto y orden. Las continuaciones del nuevo flujo revalidan ese conjunto; no cambian a otro tema para publicar el artículo antiguo.

## Qué significa «semántico» aquí

La agrupación usa conceptos equivalentes explícitos en español e inglés, anclas de producto/tema y solapamiento de contexto. Es un filtro determinista, sin embeddings descargados ni otra llamada al modelo. Es deliberadamente conservador y no constituye comprensión general de cualquier noticia. Puede descartar relaciones válidas que todavía no reconozca. Se amplía con regresiones y ejemplos, no bajando umbrales para conseguir publicaciones.

Las huellas y la procedencia detectan copias idénticas, reproducciones con poco texto añadido y reimpresiones con canonical compartido. No demuestran independencia editorial de una paráfrasis encubierta ni respaldo semántico por sí solas. La revisión final continúa rechazando fuentes que solo repitan un anuncio o no corroboren el mismo tema; no se promete detectar todas las formas de reproducción automática.

## Registro y supervisión

`ResearchRun.report.selection` contiene candidatos, exclusiones y conjunto elegido. Se conserva también la selección anterior a la recuperación relacionada cuando esta fue necesaria. El panel privado explica descartes y organizaciones seleccionadas, con todo el texto escapado.

`generation_calls_avoided` cuenta **0 o 1** encargos iniciales de redacción evitados por la puerta de selección en esa ejecución diaria. No suma una llamada por documento RSS ni inventa ahorro de revisión/corrección. `candidate_drafts_suppressed` cuenta los candidatos rechazados antes de redactar, como métrica separada. No son descuentos ni importes devueltos por el proveedor. `generation_calls_started` señala la entrada al camino de redacción, no confirma facturación o respuesta del proveedor.

## Pruebas sin coste

- Caso real mínimo de los dos documentos Microsoft en dominios distintos.
- Duplicados exactos, reproducción con añadidos y canonical de origen compartido.
- Identidad incoherente, autor no verificado y redirección entre organizaciones.
- Noticias no relacionadas y equivalencias específicas entre idiomas.
- Un candidato rechazado seguido de otro válido, con contexto equilibrado.
- Recuperación de una entrada relacionada, agotamiento de límites y no repetir un 403.
- El artículo final que solo cita una organización sigue rechazándose.
- Recorrido completo con el adaptador real y transporte simulado: selección, fragmentos, reservas, redacción, revisión y publicación en SQLite aislado. Otro caso no válido hace cero llamadas y conserva cero gasto.
- Panel privado probado en navegador con datos simulados: razones y contador de llamadas evitadas.

Los fixtures previos usaban dos «fuentes» de texto idéntico. Se separaron sus contextos para representar dos documentos independientes; el contenido idéntico tiene ahora su propia prueba de rechazo. Las pruebas de compatibilidad de expedientes antiguos se mantienen.

## Despliegue y verificación

Archivos de producción: `api/app/research/selection.py` (nuevo), `sources.py`, `worker.py`, `web/pages/editorial/investigacion.vue` y `web/utils/research-status.ts`. No se modifica la configuración económica ni el calendario. Las pruebas nuevas están en `tests/test_topic_selection.py`; también se actualizan fixtures, pruebas de panel y etiqueta de estado.

Checkpoint preparado: `/var/backups/foroia/topicfix-20261024-final`. Cuatro respaldos cifrados, copia fuera del VPS y restauración aislada de PostgreSQL coincidente en las 12 tablas, Redis restaurado y comprobación de archivos/certificados. Las imágenes previas de API, web y trabajador quedan etiquetadas antes de construir. Rollback de código e imágenes sin restaurar la base sobre escrituras nuevas.

Tras desplegar: verificar módulos, contenedores, HTTPS, redirecciones, API, sitemap, privacidad de PostgreSQL/Redis y configuración intacta. Ejecutar únicamente el colector y selector de lectura para comprobar los diagnósticos actuales; no llamar al pipeline, a tick ni a ningún reintento de generación.

La próxima ejecución natural deberá registrar su selección antes de pagar. Si existe candidato válido, se observarán redacción y controles finales; si no, deberá terminar sin reservar más dinero y explicar el descarte. Hoy ya hay una ejecución registrada: este despliegue no la borra ni la repite.

## Resultado comprobado

Desplegados los cinco archivos indicados en API, web y trabajador. PostgreSQL, Redis y Caddy conservan sus contenedores. Los módulos de API y trabajador coinciden con sus hashes locales y los servicios están saludables. No fue necesario ejecutar rollback; las tres imágenes anteriores están disponibles y la configuración de recuperación está validada.

- Suite completa final: **156 pruebas correctas, 44 omitidas** por entornos opcionales. Incluye 18 casos nuevos de selección temática y capacidad de recuperación.
- TypeScript, build Nuxt y prueba JS de etiquetas correctos. Prueba local del panel en Chromium: **1 correcta**, con refresco, historial, razones, descartes y contador de llamadas evitadas.
- Simulación válida completada hasta publicación y lectura pública de la API en la base aislada; la simulación inválida termina con cero llamadas y cero reservas.
- Backup/restauración y copia externa verificados antes de desplegar; rollback disponible sin sobrescribir la base de producción.
- Última comprobación real **solo del colector y selector**, después de desplegar la reserva de capacidad: nueve candidatos RSS, cinco documentos y cinco temas sin corroboración independiente, con cuatro fallos de descarga. Ninguno se selecciona. Se habría suprimido un encargo inicial de redacción; no se llama al modelo. Se intentaron las nueve entradas y no quedaban candidatas sin usar para recuperación. El inventario actual varía; la reproducción histórica sobre el snapshot anterior de siete documentos sigue siendo una comprobación separada.
- Web, API, cuatro artículos, sitemap y robots responden correctamente. HTTP→HTTPS sigue 308 y www→dominio principal sigue 301. API editorial devuelve 401 sin sesión.
- Artículos, usuarios, historial de investigación y reservas coinciden con el respaldo. Durante la comprobación se añadió un comentario y su registro de auditoría: se verificó por huellas que el prefijo histórico seguía intacto y se conservaron las nuevas escrituras. No se publicaron pruebas ni se alteró la investigación de hoy. Configuración económica y horario idénticos; bases de datos sin puertos públicos y GA4/publicidad desactivados.

La comprobación sobre fuentes reales demuestra que el filtro se ejecuta y evita gasto sobre este conjunto insuficiente; **no demuestra todavía una publicación real con este selector**. Esa comprobación requiere que una ejecución natural encuentre un conjunto válido. El historial antiguo no se reescribe para aparentar una selección nueva; las próximas ejecuciones mostrarán los nuevos detalles en el panel.

Evidencias privadas locales: `.local/deploy/topicfix-production-dry-run.json`, `topicfix-final-verification.json`, `topic-selection-historical-replay.json` y manifiestos de backup/restauración. No versionar esos expedientes privados.
