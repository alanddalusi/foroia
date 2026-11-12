# Auditoría y correcciones de selección editorial — 31/10/2026

Estado: **implementado, probado y desplegado**. Cola revisada sin borrar registros ni modificar artículos existentes. No se han realizado llamadas de pago ni publicaciones de prueba en producción.

## Problemas confirmados y correcciones

| Prioridad | Hallazgo reproducible | Corrección |
| --- | --- | --- |
| Alta | `discover_document_opportunities` construía temas con «Uso de [encabezado] con [organización]», incluso para Input, Constraints o Choosing a model. Había 17 propuestas así, todas sin intentos. | Se deja de convertir encabezados en artículos. Las 17 propuestas se conservan como historial/material agrupado bajo tareas del catálogo existente; salen de la cola activa. |
| Alta | Cinco títulos pendientes podían expresar mejor la aplicación práctica a IA. | Se actualizan título, intención y palabra clave de candidatos sin intentos ni artículo asociado. Identificadores, fuentes y fingerprints se conservan; no se reinician intentos ni se reactivan candidatos agotados. |
| Media | El panel imprimía el identificador del artículo como «Publicaciones verificadas: 10». En realidad era una sola publicación, con ID 10. | Se muestra la cantidad de eventos de esa ejecución y, por separado, los identificadores con `#`. No había diez artículos publicados ni un error en el recuento de la tabla de artículos. |
| Media | La ficha SEO mostraba intención, fuentes y solapamiento, pero no diferenciaba suficientemente utilidad, cobertura y datos de demanda ausentes. | Se añade una evaluación explícita: tarea, aplicación a IA, ejemplo previsto, cobertura de títulos y resúmenes, solapamiento local, vigencia pendiente/verificada y potencial de tráfico **no medido**. El escritor y revisor reciben esa ficha, no solo el panel. |
| Baja | El estilo profesional y la reescritura ya estaban implementados; no hacía falta otro revisor o planificador. | Se reutiliza la revisión actual y se precisan los prompts para rechazar títulos copiados de índices, falta de contexto y tutoriales técnicos sin aplicación útil a IA. No se añade ninguna llamada ni una nueva capa editorial. |

La revisión se centra en contenido útil para personas y títulos descriptivos, como recomienda [Google Search Central](https://developers.google.com/search/docs/fundamentals/creating-helpful-content). La automatización no demuestra utilidad por sí sola: la [guía de Google sobre contenido generativo](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content) insiste en exactitud y valor, también en metadatos. Estas prácticas no permiten prometer posiciones ni tráfico.

## Cambios concretos en la cola

Se conservan los **31 registros**. Los candidatos agrupados son: **12, 13, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 30 y 31**. Siguen incluyendo el título original, fuente, foco documental y decisión de auditoría con el candidato de referencia. La documentación completa ya estaba en las fuentes de esas tareas; no se ha fabricado ni fusionado contenido publicado.

| ID | Nuevo título pendiente |
| --- | --- |
| 3 | Cómo guardar respuestas de un asistente de IA en SQLite sin duplicados |
| 4 | Cómo comparar respuestas de IA sin errores por espacios y Unicode |
| 6 | Cómo validar entradas para una API de IA con FastAPI |
| 10 | Cómo revisar una respuesta JSON de IA: formato, esquema y fuentes |
| 11 | Prompts en OpenAI, Gemini y Claude: cómo separar instrucciones y documentos |

Estado después: **2 en cola, 4 pospuestos, 5 publicados y 20 descartados**. Diecisiete de los descartados corresponden a esta agrupación; los tres anteriores se mantienen. Los candidatos activos aparecen antes que el historial en el panel. Una segunda auditoría no vuelve a agrupar propuestas ni crea duplicados.

Los temas anteriores son hipótesis editoriales basadas en tareas y documentación, no búsquedas con volumen demostrado. No se han añadido temas de agentes, PDFs o comparaciones de rendimiento sin disponer de fuentes y ejemplos apropiados. Las noticias siguen teniendo prioridad; los tutoriales conservan sus comprobaciones, ejemplos reproducibles y cooldown técnico existentes.

## Qué cuenta cada métrica

| Dato de producción | Valor comprobado | Significado |
| --- | ---: | --- |
| Artículos publicados | 9 | Filas actualmente públicas, excluyendo borradores y archivados. |
| Artículos actuales con verificación registrada del trabajador | 5 | Artículos distintos y públicos cuyo candidato tiene comprobaciones de API, HTML, SEO y sitemap registradas. No es otro total de publicaciones. |
| Trabajos manuales del panel completados | 3 | Trabajos de la tabla de ejecuciones del panel en estado `completed`, histórico. No incluye por definición toda ejecución CLI o investigación nocturna. |
| Eventos de verificación | 6 | Registros históricos `publication_verified`. No son artículos únicos ni visitas; un artículo puede verificarse más de una vez o actualizarse. |
| URLs del sitemap | 18 | URLs canónicas públicas, incluidos otros tipos de página. No equivalen al número de artículos. |
| Publicación de la ejecución del 30/10 | 1, artículo #10 | El número 10 era el identificador que causaba la confusión. |

Los recuentos actuales se consultan a la base de datos. Las comprobaciones SEO del monitor mantienen su fecha y ámbito de muestra: no se presentan como una validación reciente de cada página en cada petición del panel.

## SEO público: qué se comprobó y qué no se cambió

Auditoría anónima de los nueve artículos publicados: HTTP 200, contenido SSR y H1, títulos y metadescripciones únicos, canonical propio, Open Graph y JSON-LD parseable de artículo/migas, enlaces internos a otros artículos y presencia en sitemap. No se detectó un problema que justificara cambiar títulos, descripciones, URLs, fechas o cuerpos publicados.

No se ha confirmado nueva indexación en Google. No se han solicitado indexaciones, creado páginas vacías, cambiado el sitemap, añadido palabras artificialmente ni producido contenido masivo. Los hashes de artículos y activos multimedia coinciden exactamente con el backup previo.

## Pruebas y despliegue

- Cuatro pruebas nuevas para los errores reales: no crear temas desde índices; agrupación idempotente sin pérdida de fuentes; cambios de título limitados a trabajo no iniciado; evaluación sin volúmenes inventados; y conteos que distinguen IDs, artículos únicos, archivados y eventos. Se agrupan estas comprobaciones en cuatro casos, sin añadir una gran batería independiente.
- Suite general: **418 correctas, 24 omitidas**. Comprobación adicional de contratos/editorial: **54 correctas**. No se han sustituido los modelos reales por simulaciones en producción: las simulaciones son exclusivamente pruebas aisladas.
- Dos pruebas HTTP/FastAPI/Nuxt SSR correctas: anuncio oficial y tutorial de programación. TypeScript y build correctos.
- Copia de producción restaurada en PostgreSQL aislado, **sin red externa**: 17 agrupaciones, cinco títulos mejorados, 31 registros conservados, artículos y consumo intactos; segunda pasada sin nuevas agrupaciones. La consulta de recuento JSON funcionó también en PostgreSQL.
- Navegador Chromium con datos reales del panel, sin respuestas interceptadas: contador 9 correcto, artículo #10 mostrado como una publicación, cero temas de encabezados en la cola activa, sin errores JavaScript ni desbordamiento en escritorio/móvil y con foco de teclado.
- Verificación final: artículos, imágenes, historial de investigaciones, configuración de control y consumo de API con los mismos hashes que antes; 31 candidatos conservados. Siete servicios en marcha y PostgreSQL/Redis sin exposición pública.

Backup completo cifrado y restaurado: `/var/backups/foroia/seoselection-20261031-final`, con 20 tablas coincidentes, Redis, código/configuración y certificados; copias fuera del VPS verificadas. Despliegue selectivo de ocho archivos, con imágenes anteriores y rollback de código. La cola dispone de snapshots antes/después y rollback ORM protegido contra cambios posteriores. No fue necesario ejecutar rollback.

Se mantienen **gpt-5-mini**, **0,20 USD/día**, **10 USD/mes**, publicación automática habilitada y **22:30 Europe/Madrid**. La siguiente ejecución real sigue programada para el **31/10/2026 a las 22:30**. No se ha forzado una investigación ni alterado credenciales, DNS, firewall, anuncios o servicios externos.

## Riesgos pendientes y medición posterior

1. **Demanda y competencia externa no medidas.** No hay consultas/impresiones/CTR importadas de Search Console ni una fuente de volumen disponible en esta integración. Las fichas lo indican expresamente; no se asignan puntuaciones de tráfico o dificultad inventadas.
2. **Solapamiento semántico.** La comparación local de títulos/resúmenes y el detector de cuerpos ayudan, pero no equivalen a una auditoría semántica completa. El revisor debe justificar utilidad y diferenciación; los formatos próximos de JSON/Pydantic requieren especial atención.
3. **Catálogo finito.** Se conservan once planes de tareas, algunos agotados o en cooldown. Harán falta nuevas tareas concretas con evidencia suficiente a medida que se consuma el catálogo; no se compensa con artículos derivados de cualquier encabezado.
4. **Fuentes inaccesibles.** Los 403 y la falta de evidencia de determinadas noticias siguen siendo limitaciones reales. No se eliminan comprobaciones ni se promete una publicación diaria.
5. **Calidad editorial.** La evaluación automática sigue siendo probabilística. Las nuevas comprobaciones se han validado sin coste, pero su calidad en nuevas ejecuciones reales deberá supervisarse en los resultados habituales, sin pruebas pagadas extraordinarias.

Medición útil sobre periodos comparables de 28 días en Search Console: clics e impresiones por URL/consulta, CTR con contexto de posición, consultas realmente captadas y páginas que se solapan. En el panel: temas aceptados/descartados y su motivo, diversidad de necesidades cubiertas, artículos que requieren corrección, coste comunicado por fase y duplicados evitados. Comparar cohortes por fecha y tipo de contenido; no atribuir cualquier cambio de tráfico a esta intervención sin evidencia. El objetivo de 100.000 visitas mensuales sigue siendo una aspiración, no una previsión demostrada.

## Archivos y evidencias

Backend: `blueprints.py`, `queue.py`, `opportunities.py`, `style.py`, `writing.py` y `routes.py` dentro de `api/app/research/`. Panel: `web/pages/editorial/investigacion.vue` y `web/utils/research-status.ts`. Pruebas nuevas: `tests/test_editorial_selection_cleanup.py`.

Evidencias locales: `.local/deploy/seo-selection-before.json`, `seo-selection-public-audit.json`, `seoselection-preview.json`, `seoselection-queue-before.json`, `seoselection-queue-after.json`, `seoselection-browser-verified.json`, `seoselection-final.json`; logs `.local/seo-selection-all-tests.log`, `seo-selection-contract-tests.log`, `seo-selection-ssr-tests.log`, `seo-selection-typecheck.log` y `seo-selection-build.log`.
