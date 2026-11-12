# Estilo editorial natural — 31/10/2026

## Causa y cambio

La política anterior exigía atribuir todas las afirmaciones desde el inicio de cada párrafo. Esa restricción del backend provocó que el artículo de Microsoft repitiera «Según Microsoft» doce veces, incluidos seis encabezados. La instrucción se ha eliminado tanto de los prompts como de la validación y de las políticas antiguas enviadas al modelo.

La fuente oficial se identifica en la entradilla o al presentar el anuncio. La atribución se repite cuando hace falta distinguir rendimiento, beneficios, previsiones o resultados que solo declara el fabricante. Se mantiene la trazabilidad privada de cada afirmación mediante fragmentos de evidencia estables; las noticias oficiales nuevas incluyen un enlace a la fuente original añadido por el servidor, sin permitir URLs inventadas por el modelo.

No se exigen cuatro o seis secciones: el esquema admite desde dos y los prompts piden una estructura proporcionada. Las noticias breves suelen necesitar dos o tres secciones; las guías pueden ser más extensas. Se mantienen los controles de contenido mínimo, fuentes, cifras, seguridad, originalidad y duplicados.

## Revisión automática para todos los motores

`style.py` comprueba encabezados de atribución, inicios mecánicos, repetición de párrafos y exceso de secciones breves. Los fallos se corrigen mediante la reescritura existente, limitada por los mismos reintentos y presupuesto.

El revisor existente incorpora cuatro veredictos JSON obligatorios: `natural`, `non_repetitive`, `well_structured` y `attribution_clear`. No se añade una llamada extra. Si cualquiera falla, se solicita una reescritura dentro del límite existente; si no se corrige o no queda presupuesto, no se publica. Las respuestas incompletas y las revisiones antiguas sin estos veredictos no se consideran aprobaciones de estilo.

Estos controles se aplican a noticias, tutoriales, guías, comparativas y actualizaciones que atraviesan el trabajador existente. La evaluación semántica sigue siendo probabilística; las comprobaciones locales ayudan a detectar problemas reproducibles, no garantizan por sí solas la calidad literaria.

## Artículo de Microsoft

La revisión preparada conserva título, URL, fuente, categoría, autor e imagen. Reorganiza el texto en tres secciones, elimina la fórmula repetida y distingue las afirmaciones empresariales de las mediciones independientes. Se contrasta con el comunicado original guardado durante la investigación real. No se inventan pruebas de producto, precios ni resultados.

La actualización se ha aplicado mediante el endpoint editorial autenticado existente, cambiando solo `summary` y `body`. La fecha original de publicación (`2026-10-29T22:24:31.262531Z`), título, slug, canonical, fuentes, autor e imagen permanecen intactos. `updated_at` registra la edición real del 31/10 a las 10:39:58 UTC (11:39:58 Madrid). Snapshot previo: `.local/deploy/naturalstyle-article-before.json`; texto revisado: `editorial/revisions/microsoft-copilot-harness-natural.json`.

## Seguridad y despliegue

Backup completo cifrado y restaurado en entorno aislado: `/var/backups/foroia/naturalstyle-20261031-final`, 20 tablas coincidentes, Redis, configuración y certificados. Copias fuera del VPS y hashes verificados. Despliegue selectivo; rollback de código e imágenes disponible, sin borrar artículos ni consumo. La revisión del artículo tiene snapshot y rollback propios.

Se conservan **0,20 USD/día**, **10 USD/mes** y **22:30 Europe/Madrid**. No se ejecutan llamadas de pago ni se lanza una investigación extraordinaria. No se modifican DNS, firewall, SSH, credenciales, publicidad ni registros públicos.

## Archivos

- Backend: `api/app/research/style.py`, `editorial_policy.py`, `writing.py`, `quality.py`.
- Panel: `web/pages/editorial/investigacion.vue`, `web/utils/research-status.ts`.
- Pruebas: `tests/test_editorial_style.py` y fixtures existentes de investigación, anuncios oficiales, recuperación, publicación HTTP y motores editoriales.
- Contenido: `editorial/revisions/microsoft-copilot-harness-natural.json`.

## Resultado final

**Desplegado y comprobado en producción.** El [artículo de Microsoft](https://foroiaaldia.com/articulos/microsoft-presenta-copilot-harness-foundry) tiene tres secciones y cero apariciones de «Según Microsoft», frente a las seis secciones y doce repeticiones anteriores. La fuente se enlaza al presentar el anuncio; las afirmaciones de rendimiento se atribuyen expresamente al fabricante y no se presentan como mediciones propias.

Comprobación anónima: HTTP 200, SSR, tres H2 de contenido, URL y canonical originales, fecha original preservada, datos estructurados y Open Graph actualizados con la nueva entradilla, imagen accesible y presencia en sitemap. La API pública devuelve el mismo texto corregido. Se comprobó antes de editar que los nueve artículos públicos seguían accesibles; el total de artículos no cambia (diez, incluido el borrador anterior).

Pruebas generales: **413 correctas y 24 omitidas**. Ocho regresiones específicas de estilo y conservación de fecha/URL correctas (incluyen una prueba añadida posteriormente a la ejecución general). Dos pruebas HTTP con Nuxt SSR/FastAPI correctas: anuncio oficial y tutorial de programación. TypeScript y build correctos. Las simulaciones comprueban reescritura por repetición, rechazo semántico de estilo, agotamiento de correcciones sin publicación y contrato JSON de revisión con todos los campos obligatorios. No son ejecuciones reales de OpenAI ni publicaciones de prueba en producción.

Tras desplegar y editar, las huellas de `generation_usage`, `research_runs`, `research_control` y `article_assets` coinciden con el backup. **Cero llamadas de pago adicionales** y ninguna investigación forzada. Los siete servicios están ejecutándose; PostgreSQL y Redis siguen sin exposición pública. El trabajador está habilitado y la siguiente ejecución ordinaria está prevista para **31/10/2026 a las 22:30 Europe/Madrid**, con 0,20 USD/día y 10 USD/mes intactos.

Se conservan rollback de código/imágenes y rollback de la edición mediante la API (`.local/deploy/naturalstyle-article-rollback.py`), protegido contra sobrescribir cambios posteriores. No fue necesario ejecutarlos. Hubo una interrupción temporal de SSH durante la preparación; se volvió a comprobar el acceso por clave antes de continuar, sin cambiar SSH ni firewall.

Evidencias locales: `.local/naturalstyle-release-tests.log`, `.local/naturalstyle-focused-complete.log`, `.local/naturalstyle-ssr-tests.log`, `.local/naturalstyle-typecheck.log`, `.local/naturalstyle-build.log`, `.local/deploy/naturalstyle-public-verified.json` y `.local/deploy/naturalstyle-final-integrity.json`.
