# Anuncios oficiales: política editorial — 29/10/2026

Estado actualizado: **desplegado y comprobado mediante una publicación real** tras autorización posterior. [Resultado, costes y recuperación del borrador](OFFICIAL_NEWS_DEPLOY_REAL_2026_10_29.md). Las pruebas descritas a continuación corresponden a la preparación sin coste.

## Política aplicada

El flujo existente distingue `official_announcement` de `independently_corroborated`. Un anuncio de la propia organización puede usar una sola fuente oficial. La excepción se deriva en el servidor, no de etiquetas del modelo: organización y host verificados, documento individual accesible, cuerpo y hash conservados, correspondencia con el acontecimiento, fecha original verificable dentro de la ventana editorial y ausencia de duplicación.

Se conservan el registro explícito de dominios, DNS público y fijado, TLS, restricciones de redirección, tamaños y tiempos. Una página con HTTP 403 no se convierte en evidencia de página mediante texto de RSS: el recuperador debe encontrar otra evidencia accesible. RSS sigue sirviendo para descubrir enlaces.

Rumores, filtraciones, acusaciones y comparaciones no reciben la excepción. El modo corroborado conserva dos organizaciones realmente independientes y la deduplicación de comunicados reproducidos. Un dominio corporativo no basta para validar anuncios de terceros.

## Redacción y publicación

La misma política pasa por selección, cola, preparación, generación, corrección, revisión y validación final. El título atribuye el anuncio; resumen y párrafos atribuyen explícitamente las afirmaciones a la empresa. Se permiten fórmulas naturales como «Según OpenAI» y «OpenAI afirma». Rendimiento, beneficios, previsiones y resultados se presentan como afirmaciones de la organización, nunca como resultados comprobados por la redacción.

El revisor continúa comprobando cada título, encabezado y afirmación contra fragmentos estables del catálogo. Rechaza afirmaciones sin respaldo, atribución insuficiente, afirmaciones de terceros sin corroborar y alcances ajenos al anuncio. El servidor comprueba otra vez el alcance, la atribución, las referencias realmente citadas, cifras, originalidad, formato y duplicados. La publicación sigue siendo automática cuando supera todo el flujo; no se introduce aprobación manual.

Los informes y el panel muestran «Anuncio oficial verificado» o «Noticia corroborada por varias organizaciones». Los registros históricos no se reinterpretan como publicaciones verificadas bajo la nueva política.

## Pruebas y alcance

Las pruebas usan páginas históricas guardadas, transporte y respuestas de modelos simulados, bases de datos desechables y el trabajador existente. No constituyen una publicación nueva en producción ni prueban la disponibilidad futura de proveedores externos.

Se reproduce AMD/Meta con su página oficial guardada: en el reloj histórico válido ya puede entrar en cola sin una segunda organización. Con el reloj posterior al límite de 48 horas sigue rechazándose. No se han cambiado las fechas reales ni publicado noticias históricas como actuales.

La captura anterior de NVIDIA también pasa ahora a cola con su documento oficial válido; se actualiza la expectativa histórica que exigía una segunda organización. En la prueba que parte de una única URL oficial no se recupera una segunda fuente ni se realiza una búsqueda adicional innecesaria.

Hay casos de fuente única válida, cita ausente, identidad inconsistente, contenido modificado, fuente ajena al acontecimiento, fechas antiguas/futuras, texto sindicado, rumores, comparaciones, política manipulada y falta de atribución. La prueba integrada recorre investigación simulada, recuperación, selección, generación, revisión y publicación aislada con una fuente. La suite HTTP incluye el mismo caso a través de FastAPI y Nuxt SSR, comprobando API, HTML, metadatos, imagen y sitemap.

El caso de revisión rechazada confirma que el anuncio no se publica. Si la corrección produce exactamente el mismo borrador, se reutiliza la revisión rechazada mediante el checkpoint existente: no se repite el gasto ni se aprueba por agotar intentos. Las pruebas de rendimiento empresarial atribuido permiten informar de esas declaraciones sin presentarlas como mediciones independientes.

Los límites siguen siendo **0,20 USD/día, 10 USD/mes** y el único horario diario **22:30 Europe/Madrid**. No se cambian credenciales, migraciones, contenido existente ni configuración publicitaria.

Resultados finales: suite general **394 correctas, 24 omitidas** (excluye las suites HTTP con arranque específico); regresiones de recuperación y política **110 correctas**. En HTTP, los 12 casos previos pasan y el caso adicional de anuncio oficial con una fuente pasa tras ajustar su fixture para devolver únicamente esa fuente: HTTP 200, SSR, API, SEO, imagen y sitemap. Nuxt TypeScript y build completados correctamente. Logs locales: `.local/official-release-tests.log`, `.local/official-regression-final.log`, `.local/official-single-ssr.log`, `.local/official-typecheck.log` y `.local/official-build-final.log`.

## Despliegue posterior

Desplegar únicamente los módulos Python afectados y los dos archivos del panel, con backup completo y restauración verificada, imágenes anteriores y rollback conservador. No necesita migración. Evitar copiar en bloque el frontend local: hay diferencias previas con producción. Tras activar, comprobar configuración y salud del trabajador, API y frontend, artículos existentes, canonical y sitemap. No relanzar llamadas de pago como parte de la comprobación sin autorización específica.

## Archivos afectados

- Backend: `api/app/research/editorial_policy.py` (nuevo), `selection.py`, `news_recovery.py`, `event_sources.py`, `queue.py`, `worker.py`, `quality.py`, `writing.py` y `routes.py`, en el mismo directorio.
- Panel: `web/pages/editorial/investigacion.vue`, `web/utils/research-status.ts`.
- Pruebas: `tests/test_official_announcements.py` (nuevo), `test_nightly_web.py`, `test_event_sources.py`, `test_news_recovery.py`, `test_editorial_http.py`.
- Documentación: este informe, `PROJECT_BRIEF.md`, `README.md` y `docs/ARCHITECTURE.md`.

Limitación: las reglas locales de clasificación y atribución son deliberadamente conservadoras y la revisión semántica sigue siendo necesaria. Una fuente oficial no demuestra por sí misma rendimientos independientes ni hechos de terceros. El cambio elimina el requisito automático de segunda organización para el anuncio acotado, sin garantizar una noticia diaria ni que una fuente bloqueada vuelva a ser accesible.
