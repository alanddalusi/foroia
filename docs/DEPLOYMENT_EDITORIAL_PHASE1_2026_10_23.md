# Primera fase editorial publicada — 23/10/2026

Despliegue y publicación autorizados expresamente por el propietario. Resultado: frontend actualizado y tres guías públicas verificadas. No fue necesario ejecutar rollback.

## Respaldo nuevo y restauración antes del cambio

Checkpoint privado: `/var/backups/foroia/phase1-20261023-final`, permisos restrictivos. Se crearon cuatro copias cifradas con age: PostgreSQL en formato custom, snapshot Redis, código/configuración incluyendo production.env y volúmenes de Caddy con certificados. Copias fuera del servidor en `.local/deploy/phase1-backup-*.age`; checksums verificados. La identidad privada age permaneció en el equipo local.

El dump de PostgreSQL usa un snapshot exportado de una transacción repeatable read/read only. Las huellas y recuentos se capturaron en ese mismo snapshot: no se confunde una comparación contra tráfico concurrente con la integridad del respaldo.

Antes de desplegar, se descifraron las copias en memoria. PostgreSQL se restauró en un contenedor desechable sin red ni puertos públicos y coincidieron las huellas y recuentos de las 12 tablas de aplicación. Redis pasó redis-check-rdb, arrancó en otro contenedor sin red y respondió PONG. Los archivos de código/configuración y Caddy se leyeron íntegramente, con validación de rutas y presencia de configuración/certificados. Se retiró el contenedor de restauración. Producción no se restauró ni se detuvo para estas pruebas.

## Cambio aplicado

Paquete web selectivo de 11 archivos, SHA256 `5301221f80800e6957a6d962e3749755166b7b726dcd159b450d37e7e770f143`.

- Navegación: función pageKey en web/app.vue para actualizar contenido y metadatos al cambiar de categoría.
- GA4: atribución minimizada, consentimiento y exclusión de rutas privadas en AnalyticsConsent.vue y utils/analytics.ts; medición después de renderizar la cabecera para evitar títulos anteriores. Texto informativo de privacidad actualizado.
- Enlaces de artículos: ArticleBody.vue, nuevo ArticleInline.vue y utils/article-inline.ts. Nodos Vue escapados, destinos validados, código literal y sin v-html.
- Cuatro recursos originales bajo `/recursos/guias-pdf/`: PDF digital, PDF sintético solo imagen, extractor y generador Python.

Imagen web anterior retenida como `foroia-rollback-web:phase1-20261023`. Imagen nueva: `sha256:0ac8b0f090420c7f6ae779e22d394aa9e0183b4ab4599ce518bd61443ff54de5`. Solo se construyó/recreó web con el Compose existente, sin migraciones. La huella de production.env es idéntica antes y después.

## Artículos publicados

Se revisó el inventario editorial privado completo antes de crear contenido: un artículo existente, sin colisiones de slug, título o resumen. Las nuevas piezas se crearon con sesión administrativa y CSRF mediante la API editorial existente; cada una recorrió borrador → revisión → publicado, con auditoría. Sin SQL directo, personas ficticias ni cambios del contenido anterior.

| Artículo | Sección | URL |
| --- | --- | --- |
| Cómo resumir un PDF con IA y comprobar sus citas | Tutoriales | https://foroiaaldia.com/articulos/resumir-pdf-ia-comprobar-citas |
| NotebookLM con un PDF: prepara las fuentes y revisa las citas | Herramientas | https://foroiaaldia.com/articulos/notebooklm-pdf-fuentes-citas |
| Extraer texto de un PDF con Python antes de usar IA | Programación | https://foroiaaldia.com/articulos/extraer-texto-pdf-python |

Los cuerpos publicados coinciden con editorial/phase1/publication.json; enlaces de revisión sustituidos por rutas públicas. Firma editorial explícita con asistencia de IA. Fechas asignadas por el servidor al publicar. El artículo anterior conserva todos los campos de su respuesta pública, sin cambios.

## Comprobaciones en producción

- Las tres URLs responden 200 por HTTPS, entregan contenido SSR y un H1 único, título y descripción propios, canonical y Open Graph correctos. JSON-LD contiene BlogPosting y BreadcrumbList.
- Secciones correctas, piezas visibles en sus listados. Las tres URLs aparecen en el sitemap de artículos y las secciones pobladas en sitemap-pages.xml, dentro del índice existente. No hubo edición manual de sitemap.
- Dos enlaces entre guías por artículo; todos los destinos responden 200. Descargables 200 y SHA256 idénticos a los recursos aprobados. Las cuatro fuentes externas responden 200.
- Navegador Chromium móvil de 390 px: contenido, navegación entre categorías, teclado, sin desbordamiento horizontal ni errores JavaScript. Capturas privadas por sección.
- Cero peticiones a GA4, Tag Manager o redes publicitarias. ANALYTICS_ENABLED sigue false; sin identificadores GA4/AdSense. ads.txt sigue 404 intencionadamente. No se activó analítica ni publicidad.
- HTTP redirige 308 a HTTPS; www redirige 301 al dominio principal. Las cuatro rutas antiguas /blog/<seccion> devuelven 301. HTTPS y cabeceras HSTS/CSP Report-Only comprobados. Robots y sitemaps accesibles; ruta inexistente 404; panel sin sesión protegido.
- Web, API, PostgreSQL y Redis saludables. Caddy valida su configuración; API /health devuelve 200. PostgreSQL y Redis no publican puertos al exterior.
- API, DB, Redis, Caddy y trabajador conservan sus IDs y horas de inicio: solo web se recreó. Investigación con heartbeat activo, habilitada y publicación automática conservadas, horario 22:30 Europe/Madrid y presupuesto mensual de 5 USD. No se ejecutó una generación de pago ni se modificó su programación.
- Fuera de las tablas de artículos, auditoría, sesiones y contadores de tráfico, todas las huellas coinciden con el respaldo. Las variaciones previstas corresponden a las tres publicaciones, operaciones editoriales, accesos administrativos y comprobaciones HTTP. Usuarios, comentarios, temas, categorías, correo e investigación permanecen intactos.

Validación previa local: TypeScript/build, 21 pruebas de API/SEO, cuatro pruebas de navegador/SSR, cuatro comprobaciones de ejemplos y scripts de enlaces/analítica correctos. Construcción de la imagen de producción satisfactoria.

## Recuperación preparada y límites

`/var/backups/foroia/phase1-20261023-final/rollback.sh` conserva archivos anteriores y usa una imagen web fija con override Compose. Sintaxis Bash y configuración Compose validadas. La activación tenía reversión automática si fallaba; las comprobaciones posteriores estaban protegidas por retirada selectiva de estas tres piezas y rollback web. No se produjo un fallo crítico ni se invocó ese mecanismo.

No se restauraría PostgreSQL sobre actividad reciente como rollback rutinario. Los artículos se archivarían sin borrar contenido, cuentas o auditoría. No hubo cambios de credenciales, DNS, firewall, SSH ni servicios externos.

Pendiente: observar rastreo/indexación y resultados en Search Console; aparecer en sitemap no acredita indexación. GA4 y publicidad continúan desactivados por instrucción. Siguen pendientes los datos legales reales, SMTP probado antes de altas y automatización externa de copias/alertas. La guía NotebookLM es documental y lo declara, sin pruebas de una sesión autenticada. Un frontend único puede sufrir una interrupción breve al recrearse; no se acredita cero downtime.

Evidencia privada en `.local/deploy/phase1-*`: manifest de backup, restauración, paquete, activación, IDs de artículos, comprobaciones HTTP/navegador y estado final de datos/servicios. No versionar estos archivos, copias ni credenciales.
