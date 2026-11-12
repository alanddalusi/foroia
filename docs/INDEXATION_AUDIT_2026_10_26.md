# Indexabilidad de las guías anteriores — 26/10/2026

## Resultado

**Las tres URLs son técnicamente indexables en las comprobaciones actuales. No se ha encontrado un error reproducible que justifique modificar o desplegar la aplicación.** No se ha cambiado contenido, títulos, fechas, canonical, configuración de rastreo ni el sistema editorial. No se han solicitado indexaciones ni realizado llamadas a OpenAI.

El estado de Search Console y el último rastreo del 23/10/2026 proceden de la información facilitada por el propietario. Esta auditoría no tiene acceso a la inspección privada de Google ni confirma que las páginas se hayan indexado posteriormente.

## Comprobaciones directas

Peticiones HTTPS sin sesión, validando el certificado. HTML inicial analizado antes de ejecutar JavaScript. Segundo contraste en Chromium móvil con JavaScript desactivado. Respuestas comparadas con identificadores Googlebot de escritorio y móvil.

| URL | HTTP y SSR | Indexabilidad y datos estructurados | Descubrimiento | Error confirmado / corrección |
| --- | --- | --- | --- | --- |
| [resumir-pdf-ia-comprobar-citas](https://foroiaaldia.com/articulos/resumir-pdf-ia-comprobar-citas) | 200; texto, H1 y apartados en HTML inicial y visibles sin JavaScript | Canonical propio; robots permite rastreo; sin `noindex`; Article/BlogPosting y BreadcrumbList coherentes | Una aparición en sitemap; enlace desde portada y `/tutoriales`; enlaces a las otras guías | Ninguno / ninguna |
| [extraer-texto-pdf-python](https://foroiaaldia.com/articulos/extraer-texto-pdf-python) | 200; texto y código en HTML inicial; visible sin JavaScript | Canonical propio; robots permite rastreo; sin `noindex`; Article/BlogPosting y BreadcrumbList coherentes | Una aparición en sitemap; enlace desde portada y `/programacion`; descargas accesibles | Ninguno / ninguna |
| [notebooklm-pdf-fuentes-citas](https://foroiaaldia.com/articulos/notebooklm-pdf-fuentes-citas) | 200; texto, H1 y apartados en HTML inicial y visibles sin JavaScript | Canonical propio; robots permite rastreo; sin `noindex`; Article/BlogPosting y BreadcrumbList coherentes | Una aparición en sitemap; enlace desde portada y `/herramientas`; enlaces a las otras guías | Ninguno / ninguna |
| [validar-json-ia-python](https://foroiaaldia.com/articulos/validar-json-ia-python) | 200; texto y código visibles sin JavaScript | Canonical propio; rastreo permitido; sin `noindex`; datos estructurados coherentes | Una aparición en sitemap; enlace desde portada y `/programacion` | Ninguno / ninguna; publicación automática preservada |

Detalle común:

- `Content-Type: text/html;charset=utf-8` y una única URL canónica absoluta correcta por artículo.
- No hay meta `robots`/`googlebot` restrictiva ni cabecera `X-Robots-Tag` en las páginas examinadas. Su ausencia no impide indexarlas: no es necesario añadir `index, follow` para corregir nada.
- `robots.txt` devuelve 200 e incluye `User-agent: *`, `Allow: /` y la URL correcta de `sitemap.xml`.
- Índice de sitemap y sus dos documentos accesibles; 14 URLs públicas únicas, sin repeticiones. Cada artículo examinado aparece exactamente una vez.
- Los títulos y resúmenes de los cinco artículos públicos son distintos. No hay páginas vacías ni mensajes de mantenimiento en las respuestas examinadas.
- JSON-LD parseable, con tipos Article y BlogPosting, titular, descripción, autor visible, URL, citas y fechas coincidentes con los datos públicos; BreadcrumbList apunta a inicio, categoría y artículo. Las imágenes de las tres categorías responden 200. Esto verifica coherencia del marcado, no promete resultados enriquecidos ni equivale a una validación privada de Google.
- Con User-Agent Googlebot de escritorio y móvil: 200, mismo texto visible y misma canónica que las peticiones ordinarias. No aparece autenticación, desafío ni bloqueo por identificador. Estas peticiones no proceden de una IP de Google; no sustituyen la prueba de URL publicada de Search Console.
- Diez URLs internas/de descarga únicas presentes en los cuerpos examinados responden 200, incluidas las guías, categorías, PDF de práctica, PDF de imagen, script de extracción y generador de ejemplos.
- HTTP redirige a HTTPS mediante 308 y `www` al dominio principal mediante 301, conservando la ruta del artículo.

## Contenido e intención

| Artículo | Intención principal observada | Valor propio y límites |
| --- | --- | --- |
| Resumir PDF | Obtener un resumen y contrastar cifras y citas, independientemente de la herramienta | Procedimiento completo, petición de ejemplo, PDF original y respuestas de control; explica qué se ha comprobado y qué no |
| Extraer PDF con Python | Recuperar y comprobar texto localmente antes de usar una IA | Instrucciones de entorno, código y script descargable, archivos de práctica, tratamiento de páginas sin texto y límites de la extracción/OCR |
| NotebookLM | Preparar fuentes y revisar citas en una herramienta concreta | Secuencia basada en documentación oficial, selección de fuentes, preguntas de comprobación, permisos y alcance; no inventa una prueba del producto |

Los cuerpos contienen aproximadamente 803, 796 y 887 palabras respectivamente, excluidos los bloques de código según el recuento local. No son páginas vacías ni simples resúmenes de pocas líneas. El número de palabras no demuestra calidad ni constituye un umbral de Google; no se propone alargarlos.

Los artículos comparten el PDF del taller y algunos conceptos, pero tienen objetivos y procedimientos distintos. No se encontraron títulos, resúmenes o cuerpos idénticos entre los cinco artículos, ni párrafos de prosa exactamente repetidos de más de 120 caracteres, excluidos bloques de código. Esta comprobación local no es una evaluación semántica de Google ni un detector de duplicación en toda Internet.

Existe solapamiento temático entre resumen de PDF y NotebookLM; está explicado mediante enlaces recíprocos y la especialización de cada guía. **No hay evidencia suficiente para afirmar canibalización**, cambiar las canónicas, fusionar contenidos o reescribir títulos. Harían falta las consultas y páginas de Search Console para comprobar si compiten por las mismas búsquedas.

## Qué significa el estado de Google

Google describe «Rastreada: actualmente sin indexar» como una página ya rastreada que podría indexarse o no posteriormente. No equivale por sí mismo a un bloqueo técnico, ni exige reenviarla continuamente. [Documentación oficial del informe de indexación](https://support.google.com/webmasters/answer/7440203?hl=en).

Permitir el rastreo mediante robots.txt tampoco obliga a indexar una página. [Documentación de robots.txt de Google](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=es).

No se puede deducir la causa exacta de exclusión a partir de las respuestas actuales. Tampoco se ha reconstruido el HTML que Google descargó el 23/10. El hecho de que el artículo comercial figure indexado, según el propietario, no prueba un defecto en las otras tres páginas.

Comprobación manual útil en Search Console: inspeccionar cada URL y contrastar la canónica declarada con la seleccionada por Google, la fecha del último rastreo y el HTML rastreado. La prueba de URL publicada permite contrastar la accesibilidad desde Google. No se han usado envíos automáticos ni se afirma que solicitar indexación garantice inclusión.

## Conservación del sistema editorial

- El trabajador sigue activo, con heartbeat presente e investigación habilitada.
- Mismo contenedor, misma imagen, misma hora de arranque y mismos hashes de todos sus módulos de investigación antes y después de la auditoría: no se ha reiniciado ni modificado.
- Configuración intacta: `22:30`, `0.15 USD/día` y `5 USD/mes`.
- Reservas totales sin cambios: 358.222 microUSD. Se mantienen seis registros de consumo informado; el último corresponde a la revisión autorizada de las 18:02 UTC, anterior a esta auditoría.
- Texto, títulos, descripciones, fuentes, categorías y fechas de los cinco artículos públicos iguales al principio y al final.

Se contrastó el código público desplegado con el local. Plantilla de artículo, configuración Nuxt, robots, sitemaps y Caddy coinciden. La portada local difiere de la desplegada; se ha revisado la versión real del VPS, que muestra hasta doce artículos y utiliza las rutas de sección actuales. Esta diferencia operativa no es un bloqueo SEO actual y no se ha sobrescrito la portada de producción. Antes de un futuro despliegue amplio habrá que conciliar esa copia local para evitar regresiones.

## Cambios y validación

**Sin correcciones de aplicación ni despliegue.** No procede añadir regresiones de negocio para errores que no se han encontrado, ejecutar builds o restaurar la base de datos. Tampoco se han creado backups adicionales innecesarios: no hubo mutaciones ni operación que requiriera rollback.

Se añade únicamente este informe al proyecto. Los resultados y el comprobador reproducible de solo lectura se guardan localmente en `.local/deploy/indexation-audit-20261026/` y `.local/deploy/indexation-public-audit.py`. No hay dependencias ni servicios nuevos. Permanecen pendientes exclusivamente las comprobaciones de estado y canónica elegida por Google en Search Console; no puede garantizarse cuándo ni si Google indexará estas URLs.
