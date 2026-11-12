# Correcciones SEO y accesibilidad desplegadas — 23/10/2026

Resultado: cambios autorizados, probados y desplegados; verificación posterior satisfactoria. Solo se recreó web. No fue necesario ejecutar rollback.

## Cambios

- ArticleCard acepta H2/H3: las secciones usan H2 y portada/relacionados mantienen H3 bajo H2. Las clases CSS conservan el aspecto visual. No se cambió el H1 de portada ni se añadieron title a enlaces.
- htmlDateTime normaliza únicamente los atributos HTML a ISO con tres decimales. Se usa en tarjetas, artículos, comentarios y temas. No transforma fechas almacenadas ni modifica la zona horaria del texto visible.
- Los bloques pre/code siguen escapados y enfocables por teclado; se retiró el aria-label no permitido sobre pre, sin introducir regiones ARIA innecesarias.
- Las páginas Contacto, Criterio editorial, Normas y Cookies tienen OG title/description/type/url propios, además de la imagen global existente. La plantilla común también conserva las restricciones de indexación de páginas legales.
- Se añadió el enlace al generador de PDFs en el artículo de Python mediante la API editorial autenticada, con CSRF y auditoría. Solo cambió ese fragmento de cuerpo. published_at y reviewed_at se conservaron; updated_at cambió de forma normal por la corrección editorial. Los demás artículos mantienen cuerpo y fechas.
- La imagen principal del artículo utiliza loading=eager. No se cambió la carga de imágenes adicionales ni se añadió prioridad alta sin necesidad.
- Prefetch: se identificó el origen en vue-bundle-renderer, runtime.mjs, renderResourceHints, que genera as junto a rel=prefetch. Un plugin de Nitro utiliza el hook público render:html y normaliza solo esos link del head. Conserva href, crossorigin, las propias etiquetas prefetch y los preload/modulepreload. No se editaron node_modules, Nuxt, lockfile ni dependencias.

## Comparación controlada de la imagen

Cinco cargas frías por variante, orden alternado, mismo HTML/recursos y solo atributos de imagen diferentes; viewport 390×844, CPU ×4, 150 ms de latencia y descarga de 1,6 Mbps. La respuesta principal se sustituyó únicamente dentro del navegador de prueba, sin cambiar producción para el experimento.

| Variante | Mediana LCP | CLS máximo |
| --- | --- | --- |
| lazy | 1,256 s | 0 |
| eager | 0,960 s | 0 |
| eager y prioridad alta | 0,944 s | 0 |

Se eligió eager; la diferencia adicional de prioridad alta fue pequeña y no justifica añadirla. Son resultados de laboratorio, no una promesa de mejora idéntica para cada usuario ni una medición de INP o percentil 75. Evidencia privada: .local/seo-fix-20261023/image-comparison.json.

Repetición posterior sobre la web desplegada, tres cargas por URL con las mismas condiciones de laboratorio: LCP mediano de 0,984 s en portada y 1,044 s en el artículo Python, CLS máximo 0. No se observó regresión relevante de carga o estabilidad. Los valores no se presentan como datos de usuarios reales.

## Pruebas antes del despliegue

- Suite general: 97 correctas, 42 optativas omitidas. Las pruebas de navegador de esta entrega se ejecutaron después explícitamente: seis de analítica/SSR/navegación/SEO y una de accesibilidad, todas correctas.
- Scripts JS: fechas y prefetch, enlaces seguros, atribución y plugin de analítica correctos; incorporado seo-presentation.cjs a CI.
- Nuxt TypeScript y build correctos con Node 22; construcción de la imagen de producción también ejecuta ambos.
- W3C Nu HTML Checker sobre 12 documentos SSR locales preparados: cero errores. Schema.org sobre los tres cuerpos de ejemplo SSR: dos objetos por artículo, cero errores y advertencias.
- Auditoría local axe-core 4.14.0 en portada, secciones y guía Python: sin violaciones. Se comprobaron foco por teclado de bloques de código, metadatos, canonical, sitemap, generación SSR y conservación de modulepreload.

## Backup nuevo verificado antes de cambiar producción

Checkpoint privado: `/var/backups/foroia/seofix-20261023-final`. Cuatro copias cifradas age: PostgreSQL custom, Redis RDB, código/configuración y volúmenes de Caddy. Copias externas locales con checksums verificados, identidad privada fuera del VPS.

PostgreSQL se respaldó con snapshot exportado y se restauró en un contenedor aislado sin red. Recuentos y huellas de las 12 tablas de aplicación coinciden con el mismo snapshot. Redis pasó redis-check-rdb, restauración aislada y PONG. Código/configuración y certificados se descifraron en memoria y se leyeron íntegramente con comprobación de rutas. No se restauró sobre producción ni se borraron volúmenes existentes.

Paquete selectivo de 11 archivos: SHA256 `30882877f5a64e34bedab00c96c42c0358000be362997092fb70eec83e19d39a`. Imagen web desplegada: `sha256:06fd0f652b399728980b1873d0b3feab0e3063409842fed86b44432ad966c3da`.

## Verificación pública después del despliegue

- Las 13 páginas del sitemap responden 200 y pasan W3C Nu: cero errores y mensajes en la revisión registrada. Los errores auditados de datetime, heading-order, pre y prefetch ya no se reproducen.
- Los cuatro artículos pasan Schema.org Markup Validator: Article/BlogPosting y BreadcrumbList, dos objetos por artículo, cero errores y advertencias.
- Axe sobre las 13 páginas: cero violaciones y ninguna comprobación incompleta en esa ejecución. Esto no sustituye una auditoría manual completa con tecnologías de asistencia.
- H1 de portada exacto, H2 en las cuatro secciones, H3 en tarjetas de portada, estilos conservados. Datetime HTML de tres decimales, bloques de código enfocables y sin atributos ARIA inválidos. OG correcto en las cuatro páginas solicitadas.
- Enlace al generador visible y descarga 200. Fecha de publicación de los cuatro artículos intacta. No se crearon artículos duplicados ni se cambiaron URLs, fuentes, títulos, categorías o resúmenes.
- Pruebas generales públicas: HTTPS, redirecciones HTTP/www y /blog/...; robots, sitemap y canonical, enlaces entre artículos, descargas y hashes, móvil sin desbordamiento y sin errores JavaScript.
- API, web, PostgreSQL y Redis saludables; Caddy validó configuración y /health de API devolvió 200. API, Caddy, DB, Redis y trabajador conservan ID/hora de inicio; solo se recreó frontend. PostgreSQL y Redis continúan sin puertos públicos.
- production.env mantiene exactamente su huella. Investigación habilitada con heartbeat, 22:30 Europe/Madrid y 5 USD/mes conservados. No se forzó una ejecución ni se modificó su presupuesto, pausa o publicación automática.
- GA4 y publicidad siguen desactivados, sin IDs nuevos ni peticiones a Google observadas. Ningún cambio de credenciales, DNS, firewall o SSH.
- Huellas de datos ajenos a artículos, auditoría, sesiones y contadores de tráfico coinciden con el respaldo. El número de artículos se conserva en cuatro. En artículos solo cambió el enlace solicitado y su updated_at normal; no se alteraron fechas para corregir el formato HTML.

## Recuperación preparada

Imagen anterior retenida como `foroia-rollback-web:seofix-20261023`. El checkpoint contiene rollback.sh, archivos previos y override Compose con imagen fija; se validaron sintaxis y configuración antes de activar la nueva versión. La activación ejecutaría rollback si fallaba. Las comprobaciones posteriores también estaban protegidas por reversión del fragmento editorial y rollback web.

La reversión editorial comprueba que el cuerpo aún coincide con el cambio aplicado antes de restaurarlo, evitando sobrescribir ediciones ajenas. No borra contenido ni restaura bases sobre actividad reciente. Las comprobaciones pasaron, por lo que no se invocó rollback.

## Archivos y seguimiento

Aplicación: web/components/ArticleCard.vue, ArticleBody.vue, ArticleComments.vue; web/utils/blog.ts; web/pages/[seccion].vue, articulos/[slug].vue, tema/[slug].vue, informacion/[slug].vue; web/assets/css/main.css; web/server/plugins/prefetch.ts y server/utils/prefetch.ts.

Validación/documentación local: tests/seo-presentation.cjs, tests/test_analytics_local.py, .github/workflows/checks.yml, borrador Python y sus payload/vista de revisión en editorial/phase1/. No se despliegan tests, evidencias privadas ni credenciales.

Pendiente: datos de campo de Core Web Vitals, seguimiento de consultas/indexación en Search Console y comprobar las incidencias exactas restantes de herramientas externas cuando estén disponibles. El adaptador de prefetch debe reevaluarse al actualizar Nuxt/vue-bundle-renderer; no es motivo para una actualización automática. No se acredita ranking, tráfico ni una nueva puntuación de herramientas externas. La revisión manual exhaustiva de accesibilidad sigue siendo una tarea aparte.

Evidencia privada: .local/deploy/seofix-* y .local/seo-fix-20261023/. No versionar backups, archivos de sesión ni diagnósticos privados.
