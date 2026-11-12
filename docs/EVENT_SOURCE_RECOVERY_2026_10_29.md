# Recuperación por acontecimiento — implementada y desplegada

## Corrección

El recuperador ya no depende de que las URL iniciales de OpenAI sean accesibles. Dentro del trabajador y la cola existentes:

1. Identifica el acontecimiento mediante empresa, producto, descripción y fecha, con un identificador estable para la ejecución.
2. Revisa las URL propuestas y consulta gratuitamente los índices oficiales pertinentes, RSS y referencias disponibles. Estas consultas son búsquedas **locales sobre los enlaces de los índices**, no búsquedas web facturadas.
3. Si ninguna candidata queda verificada, puede solicitar **una sola búsqueda alternativa** con Responses `web_search`, para hasta tres acontecimientos ya nominados. Las consultas incluyen empresa, producto, fecha y términos del anuncio. No se introducen temas nuevos ni otro planificador.
4. El modelo devuelve identificadores `event_id` enumerados en el esquema y URL; no vuelve a redactar nombres, acontecimientos o fechas. Se rechazan identificadores desconocidos, cambios de acontecimiento y respuestas incompletas. La respuesta de búsqueda no se acepta como evidencia.
5. Cada documento alternativo se descarga y pasa por los mismos controles de correspondencia, fecha original, organización, duplicados, contenido reproducido y selección temática. La redacción solo recibe las evidencias verificadas.
6. Se conservan las comprobaciones de cada afirmación y cita, la revisión editorial, la publicación y la comprobación pública de URL/SSR/canonical/sitemap existentes.

Se incorporaron las fuentes oficiales verificadas `ir.amd.com`, `newsroom.amd.com` y `help.openai.com`. **Nasdaq y Yahoo no se habilitaron indiscriminadamente.** Dos páginas de AMD siguen perteneciendo a AMD; un comunicado republicado no se convierte en corroboración independiente.

Los documentos identifican su papel como `official_statement` o `independent_reporting`. Esa anotación no acredita por sí sola una afirmación ni sustituye la revisión por fragmentos. Las noticias siguen necesitando dos organizaciones verificadas y distintas y una fuente original; las afirmaciones de una empresa no se presentan como pruebas independientes realizadas por el blog.

## Límites y seguridad

- Una ejecución ordinaria diaria a las **22:30 Europe/Madrid**; sin tareas de media hora.
- Límites intactos: **0,15 USD/día y 10 USD/mes**.
- Como máximo una llamada adicional de recuperación por intento, solicitando una sola acción `web_search`; una respuesta que comunique más búsquedas no se utiliza para redactar.
- La búsqueda alternativa reutiliza la reserva atómica, el libro de uso y la liquidación idempotente de la investigación existente. Mantiene un checkpoint separado `alternative_web_research` y la etapa contable `SourceRecovery`.
- Antes de reservar se exige además un margen para redacción y revisión: 0,04 USD con la configuración actual, calculado a partir de los límites de tokens y tarifas existentes. No es una promesa de que cualquier artículo quepa en ese importe; cada fase conserva su propia reserva obligatoria.
- Las respuestas guardadas se reutilizan. Una llamada de resultado incierto no se repite y conserva su reserva. No se reintentan errores deterministas mediante más búsquedas.
- Máximo 20 descargas de artículos, 5 índices y 11 feeds; la primera fase puede consumir 14 artículos, conservando hasta 6 descargas para las alternativas. Recuperación acotada a 240 segundos de nuevas solicitudes, con límites por petición y 90 segundos de timeout en la conexión OpenAI existente.
- Se mantienen HTTPS, DNS público fijado al socket, verificación TLS, validación de cada redirección y límite de 2 MB. No se eluden 403, paywalls ni restricciones mediante proxies o cambios de identidad.

La integración y el filtrado de dominios se contrastaron con la [documentación oficial de web search](https://developers.openai.com/api/docs/guides/tools-web-search). El servicio factura la búsqueda y los tokens; la tarifa consultada es 0,01 USD por llamada de herramienta más tokens, según [precios oficiales](https://developers.openai.com/api/docs/pricing). No se han modificado las tarifas configuradas ni realizado llamadas de pago en este trabajo.

## Reproducción de las cinco propuestas de la última ejecución del 29

`tests/fixtures/news_retry_candidates_20261029.json` conserva los candidatos y diagnósticos reales de la prueba de las 09:32 UTC. `event_http_capture_20261029.json.gz` contiene descargas HTTP gratuitas posteriores desde el VPS, con fecha de captura y hashes. **Esas descargas no se presentan como los bytes originales de aquella ejecución.** Se probaron tanto el reloj de la ejecución original como el de la captura posterior.

| Propuesta registrada | Resultado reproducible |
| --- | --- |
| OpenAI DevDay | La URL inicial devuelve 403. Se mantiene el rechazo sin una alternativa accesible y relacionada. Los snippets no sustituyen el documento. |
| Oracle–OpenAI | El comunicado inicial devuelve 403. La recuperación continúa por el acontecimiento; no acepta documentos sobre otras colaboraciones. La captura no demuestra una pareja de fuentes suficientes. |
| AMD–Meta | Desde una URL inicial de Nasdaq no permitida se encuentran los dos documentos originales de AMD navegando sus índices reales. Ambos se identifican como AMD: **no bastan para publicar**. Con el reloj original son recientes pero falta corroboración; con el reloj posterior ya superan 48 horas y se informa `document_stale`, conservando sus horas originales verificadas. |
| Registro S-1 de Anthropic | Se conserva el descarte por acontecimiento ya publicado, sin gastar en otra búsqueda de ese duplicado. |
| Seguimiento de la salida a bolsa | Continúa necesitando documentación original y corroboración real de otra organización. No se considera que dos artículos de TechCrunch sean dos organizaciones ni se inventa cobertura alternativa. |

La fecha del IR de AMD se comprueba mediante su etiqueta explícita de publicación y la zona EDT/EST mostrada, sin asumir UTC para un `datetime` que carece de zona. No se cambian fechas almacenadas ni se usa `dateModified` para rejuvenecer noticias.

## Prueba positiva de extremo a extremo

Se comprobó **en un entorno aislado y con respuestas simuladas**:

`URL inicial 403 → búsqueda alternativa → documentos de dos organizaciones válidas → catálogo de evidencias → redacción → revisión → publicación → HTTP 200, API, SSR, datos estructurados, imagen y sitemap`.

El transporte Nuxt/FastAPI y la publicación en la base aislada son reales; el proveedor, las respuestas de búsqueda/redacción/revisión y parte de los documentos son fixtures de prueba. No constituye una noticia nueva publicada en producción ni una llamada OpenAI real.

## Validación

- **367 pruebas correctas y 24 omitidas** en la suite general.
- **12 pruebas HTTP/SSR correctas**, incluida la noticia que se publica tras fallar su URL inicial.
- TypeScript, build Nuxt y comprobaciones de bloques de artículos correctos.
- PostgreSQL restaurado y sin red: concurrencia de la búsqueda principal y de `SourceRecovery`, reserva mensual con margen, deduplicación, uso idempotente y conservación de límites comprobados. Sin clave OpenAI ni llamadas de pago.
- Pruebas de JSON incorrecto, fuente insegura, misma organización, respuesta sin búsqueda, identificador de acontecimiento inválido, timeout, presupuesto insuficiente y repetición sin nuevos cargos.
- El panel distingue consultas planificadas, consultas efectivamente comunicadas por la herramienta, enlaces encontrados, etapas, errores HTTP y coste calculado. El HTML de fuentes y las respuestas completas permanecen privados, incluso dentro de historiales anidados.
- Chromium sobre el panel desplegado: escritorio y móvil sin desbordamiento, foco de teclado y ningún error de JavaScript. Para mostrar las nuevas filas se usó una respuesta de diagnóstico sustituida únicamente en ese navegador de prueba; no se escribieron informes ficticios en producción.

## Despliegue y recuperación

Se desplegaron selectivamente nueve archivos: `sources.py`, `news_gate.py`, `event_sources.py`, `news_recovery.py`, `night_web.py`, `editorial.py`, `routes.py`, `web/utils/research-status.ts` y `web/pages/editorial/investigacion.vue`. No hay migraciones, dependencias nuevas ni servicios adicionales.

Checkpoint: `/var/backups/foroia/eventsources-20261029-final`. Se verificaron cuatro copias cifradas y sus copias externas, la restauración de las **20 tablas**, Redis, código/configuración y TLS. `rollback.py`, `rollback.yml` y `before.tar.gz` permiten volver a los archivos e imágenes anteriores sin eliminar artículos ni datos. No se necesitó rollback.

Después del despliegue: siete servicios operativos; siete artículos publicados con HTTP 200, SSR, canonical y sitemap correctos. Borrador, usuarios, registros editoriales, libro de uso y assets conservados. Las huellas de las 19 tablas ajenas al contador de visitas coinciden con el backup; el contador cambia con el tráfico real. PostgreSQL y Redis siguen sin puertos públicos y las variables privadas no han cambiado.

No se reescribieron los informes históricos del 29. Los nuevos diagnósticos se registrarán cuando el trabajador vuelva a ejecutar este flujo.

## Estado pendiente

**Coste OpenAI de este trabajo: 0 USD. Sin publicaciones de prueba en producción.**

Investigación activa; siguiente ejecución ordinaria confirmada: **30/10/2026 a las 22:30 Europe/Madrid**. Reserva de la jornada 29 conservada: 0,067645 USD; capacidad restante diaria 0,082355 USD y mensual 9,404097 USD, según la comprobación posterior. No son una factura del proveedor verificada.

Queda pendiente observar la primera noticia real que esta versión consiga publicar con fuentes alternativas suficientes. El rechazo se mantiene cuando faltan evidencias, las fechas no sirven o el presupuesto no permite completar las fases con seguridad.
