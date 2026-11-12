# Comprobaciones de la primera fase editorial

Actualización de producción: las tres piezas y las correcciones web se publicaron con autorización el 23/10/2026. Backup nuevo restaurado antes del cambio; comprobaciones públicas satisfactorias. Véase [resultado del despliegue](../../docs/DEPLOYMENT_EDITORIAL_PHASE1_2026_10_23.md). Las referencias a «sin desplegar» que siguen describen la revisión previa.

## Actualización: revisión final de publicación

La adaptación del renderer pendiente en la primera revisión está terminada en local. ArticleInline.vue y utils/article-inline.ts crean enlaces mediante nodos Vue escapados; ArticleBody.vue los utiliza en párrafos, títulos y listas. No hay v-html. Código, HTML literal y destinos inseguros no se ejecutan. La CI incorpora tests/article-inline.cjs.

publication.json contiene tres payloads validados con ArticleWrite, sin H1 duplicado ni notas internas de borrador, con enlaces públicos, categorías tutoriales/herramientas/programacion y firma que declara asistencia de IA. prepare_release.py los genera sin conexión ni escrituras a servicios. Los cuatro recursos propios están preparados en web/public/recursos/guias-pdf/, con hashes registrados.

Se revisaron ortografía, claridad, estructura y separación de objetivos. No se inventan sesiones de NotebookLM ni respuestas de modelos. Títulos, descripciones y slugs son únicos entre los tres. Las tres URLs propuestas devolvieron 404 en producción; antes de crear los borradores hay que repetir la comprobación y revisar colisiones privadas en el panel.

Cuatro fuentes externas respondieron 200 por HTTPS, sin desactivar verificación TLS; evidencia en FINAL_LINK_CHECKS.json. Una consulta del navegador de investigación recibió un bloqueo temporal de Google, resuelto en la comprobación directa posterior.

Resultados finales: 21 pruebas API de artículos/SEO correctas, 4 comprobaciones PDF correctas y 4 pruebas de navegador/SSR correctas. Las últimas verifican los cuerpos reales mediante API simulada: H1, title, description, canonical, dos enlaces internos por artículo, descargables, sitemap y móvil. Los scripts de enlaces, atribución y plugin pasan. Typecheck y build correctos. La prueba ampliada detectó una carrera de GA4 con el título anterior: se corrigió midiendo después de renderizar la cabecera del documento.

El procedimiento actualizado está en PUBLICACION_Y_ROLLBACK.md. El backup nuevo de producción y su restauración aislada son condiciones previas del despliegue autorizado; no se han ejecutado durante esta revisión. No hay nuevas dependencias, migraciones, cambios de presupuesto, publicación ni despliegue. Esta actualización sustituye los pendientes de enlaces y las cifras de pruebas de la revisión inicial que se conserva debajo.

Fecha: 23 de octubre de 2026. Estado: revisión local, sin publicación ni despliegue.

## Entrega

- Diez briefs en PLAN.md, con intención, estructura, fuentes y diferencia editorial.
- Tres artículos íntegros en los archivos 01, 02 y 03; lectura conjunta en review.html.
- Documento ficticio original y script descargables dentro de resources/. No representan un evento real.
- Enlaces entre los tres textos preparados como referencias locales. Las URLs públicas son propuestas, todavía no existen.
- Las fuentes se contrastaron con documentación primaria. No se atribuyen volúmenes de búsqueda ni resultados de herramientas no probadas.

## Evidencia ejecutada

- Python 3.13.2 y pypdf 6.21.2: cuatro comprobaciones correctas: extracción digital, página solo imagen, rechazo de sobrescritura y archivo ausente. Versiones y hashes en EXAMPLE_VERIFICATION.json.
- La página solo imagen es sintética. No se ha probado OCR ni una respuesta de un modelo.
- NotebookLM: revisión documental, sin sesión autenticada ni prueba de carga; el propio artículo lo indica.
- Vista local: tres artículos, anclas internas válidas y sin desbordamiento horizontal a 390 px; inspección visual de la captura móvil.
- Nuxt: typecheck y build correctos con Node 22.23.4 portátil. Node 21 del sistema no se utilizó para estas comprobaciones.
- Scripts analytics-attribution.cjs y analytics-plugin.cjs correctos.
- Playwright/pytest: 3 pruebas correctas en 11,56 segundos. Servidor Nuxt local y API simulada de solo lectura. Peticiones a Google interceptadas: no se enviaron eventos a una propiedad real.

## Corrección local de GA4

Antes de aceptar no se carga la etiqueta. Se conserva en memoria el origen externo de entrada, eliminando ruta, consulta y fragmento. Las campañas admitidas se limitan a una lista explícita; no se envían valores arbitrarios. Las páginas privadas quedan excluidas. Se comprueba también retirada del consentimiento y rechazo de consentimientos con fecha futura.

Las páginas virtuales usan como referrer la anterior página pública medida. Se eliminan consultas salvo la paginación admitida. Esto corrige la pérdida de atribución causada por vaciar siempre page_referrer; no demuestra todavía la clasificación final de los informes de Google.

La prueba descubrió además que la clave reactiva de NuxtPage podía cambiar la URL sin actualizar el contenido entre categorías. Se sustituyó por una función pageKey y se verificaron título, contenido y eventos al navegar.

Archivos de aplicación modificados: web/app.vue, web/components/AnalyticsConsent.vue, web/pages/informacion/[slug].vue y nuevo web/utils/analytics.ts. Pruebas: tests/analytics-attribution.cjs, tests/test_analytics_local.py y ejecución añadida a .github/workflows/checks.yml. Los demás archivos de esta entrega están dentro de editorial/phase1/.

## Reproducir

Desde la raíz, con los entornos locales preparados:

```powershell
.local/editorial-venv/Scripts/python.exe editorial/phase1/verify_examples.py
.local/venv/Scripts/python.exe editorial/phase1/build_review.py
$env:FOROIA_ANALYTICS_LOCAL='1'
$env:FOROIA_NODE_BINARY=Join-Path $PWD '.local/node-v22.23.4-win-x64/node.exe'
.local/venv/Scripts/python.exe -m pytest tests/test_analytics_local.py -q
```

Las pruebas del navegador requieren Chromium de Playwright y un build local actualizado. Los paquetes de los ejemplos se instalaron en un entorno aislado; no añaden dependencias al despliegue.

## Pendiente antes de publicar

1. Aprobación del propietario de los textos y de los cambios de aplicación.
2. Adaptar los enlaces internos al renderer seguro existente: actualmente no convierte enlaces Markdown. No importar los borradores sin esa adaptación ni activar HTML arbitrario.
3. Publicar juntos o enlazar únicamente destinos ya públicos; asignar autoría y fechas reales, revisar metadatos y canonical.
4. Tras un despliegue autorizado, verificar consentimiento y atribución en GA4 con la propiedad real. Los tests locales no sustituyen esa comprobación.

No se han modificado producción, base de datos, credenciales, DNS, investigación nocturna ni presupuesto. No se ha invocado OpenAI ni publicado contenido de prueba. No se ha ejecutado una suite completa del backend: esta entrega no modifica la API.
