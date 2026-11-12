# Plan maestro: implementación y comprobaciones del 25/10/2026

## Producción y automatización

API, Nuxt SSR y trabajador desplegados; PostgreSQL, Redis y Caddy conservados. No se cambian credenciales, DNS, firewall, presupuesto ni publicidad. No hay nuevas migraciones: se mantienen quince tablas. Los cuatro artículos, usuarios y comentarios anteriores se conservan; se comparan hashes y prefijos de auditoría sin impedir nuevas escrituras legítimas.

El trabajador está activo, con publicación automática y fecha editorial única. La cola mantiene once candidatas, una preparada y cero intentos. La última publicación real comprobada sigue siendo **23/10/2026, 16:45:47 UTC**. El expediente del 24 terminó sin publicación por independencia insuficiente. La siguiente ejecución natural es **25/10/2026, 22:30 Europe/Madrid (UTC+01:00)**. No se fuerza otra llamada de pago para sustituir esa comprobación real. Las simulaciones no se presentan como publicaciones reales.

El flujo conserva fuentes antes de redactar, identificadores estables, revisión por afirmación, duplicados y publicación con comprobaciones SSR/SEO/sitemap y retirada segura. Las noticias requieren organizaciones independientes; los tutoriales admiten documentación oficial suficiente. Las actualizaciones de piezas con expediente verificable conservan URL, fecha inicial e historial. Se limita el mantenimiento a una actualización publicada por semana y 0,06 USD de reservas por operación, dentro de los límites compartidos de 0,15 USD diarios y 5 USD mensuales. Si una actualización agota su asignación, se puede evaluar una pieza nueva; no se vacía todo el presupuesto en mantenimiento.

## Oportunidades y contenido

Las once candidatas tienen ficha persistente: palabra clave, variantes de vocabulario, preguntas propuestas, intención, público, países objetivo, tipo, artículos relacionados, riesgo local de solapamiento, fecha y fuentes. Los volúmenes, dificultad SEO y tendencia quedan en `null` con «dato no disponible». Son hipótesis editoriales, no mediciones inventadas. Se conserva la importación protegida de señales reales de Search Console, con CTR y fecha de importación; los clics superiores a las impresiones se rechazan.

La redacción pide español internacional y evidencia específica para diferencias regionales. No se crean páginas por país ni `hreflang` ficticio. Se actualiza el criterio editorial público para describir el registro actual de fuentes y los motores de noticias/tutoriales.

## Supervisión y medición

Se amplía **el timer de salud existente cada cinco minutos**, sin otro planificador. Comprueba base de datos, señal del trabajador, ejecuciones ausentes/atascadas, presupuesto, verificación pendiente, HTTPS, robots, sitemaps y una muestra rotativa de artículos. El alcance se declara: el recuento del sitemap y las comprobaciones de artículos no se confunden con indexación en Google. Los cambios de incidencias quedan en auditoría; el estado reciente se guarda en Redis y aparece en el panel privado. Los canales activos son journal y panel; no se inventan destinatarios ni se envían mensajes externos.

La advertencia actual `source_http_403` se conserva: una fuente del expediente anterior devolvió 403. No se elude ni se presenta como fallo de toda la infraestructura. La investigación debe continuar con fuentes permitidas alternativas.

El panel distingue reservas, uso comunicado, coste calculado y facturación desconocida. Añade disponibilidad diaria/mensual y reservas por candidata atribuidas a las últimas catorce ejecuciones, con alcance explícito. El panel de estadísticas marca usuarios únicos, sesiones, países y tráfico orgánico como no disponibles, y separa GA4 de Search Console. No se importan las impresiones o el clic mencionados por el propietario como si se hubieran leído de una API.

## Código de tutoriales fuera del VPS

Los seis ejemplos controlados por el servidor pasan en contenedores efímeros **de la VM local**, sin red, secretos, privilegios ni raíz escribible y con límites de recursos. No se ejecutan ejemplos de artículos en producción. El VPS valida un recibo inmutable que liga cada ejemplo a su código/pruebas, archivos de dependencias y versiones exactas de Python/FastAPI/Pydantic. Un cambio de esos datos invalida el recibo; el tiempo transcurrido no exige repetir diariamente ejemplos inmutables. Los recibos antiguos conservan su caducidad de 48 horas.

El servicio existente de las 22:20 solo comprueba recibos. El helper rechaza ejecutar ejemplos desde `/opt/foroia`. El workflow prepara la misma verificación y un artefacto para futuras ejecuciones CI; **no se afirma haber ejecutado GitHub Actions**. La comprobación actual se ejecutó localmente. El paquete de despliegue incluye ahora `scripts/`, necesario para el helper.

## SEO, accesibilidad y pruebas

- **13 URLs en 2 sitemaps**, cuatro artículos. Todas las URLs del sitemap responden 200, con canonical correcto, H1 único, títulos y descripciones únicos y Open Graph. Robots y redirecciones HTTP/www comprobados; sin enlaces internos rotos ni artículos huérfanos en el rastreo actual.
- Los cuatro artículos pasan el verificador público de HTML SSR, API, BlogPosting/Article, BreadcrumbList, citas, fechas, imágenes y presencia en sitemap.
- **210 pruebas generales correctas; 66 omitidas** por requerir entornos optativos. **19 pruebas SSR/navegador correctas**, incluidas las once candidatas con proveedor simulado. **11 preflights con documentación oficial correctos**, sin llamadas de generación. **6 ejemplos aislados correctos** fuera del VPS. TypeScript y build correctos.
- Comprobación móvil real de portada y un artículo: sin desbordamiento ni infracciones automáticas axe en la muestra; CLS de laboratorio 0. Son mediciones de laboratorio, sin datos de campo de INP/Core Web Vitals y sin extrapolar a todos los visitantes.
- Cero peticiones de Analytics/AdSense durante la comprobación sin consentimiento. No se activan esas integraciones.

## Dependencias y riesgos residuales

Se actualiza `serialize-javascript` de 7.1.2 a **7.1.3**, que corrige [el aviso de serialización](https://github.com/advisories/GHSA-m5mm-p8h7-m29v). Se usa `pip==26.2.2` en construcción y se elimina el instalador del backend final; sus 32 distribuciones restantes se auditan sin vulnerabilidades conocidas en la consulta realizada. Eso no constituye una garantía de seguridad absoluta.

`npm audit` mantiene siete entradas de dependencia propagadas por **un aviso de node-forge sin parche publicado**, no siete fallos distintos de la aplicación. [Aviso y ausencia de parche](https://github.com/advisories/GHSA-86w9-cpqp-85rv). La biblioteca no se encuentra en el artefacto runtime de Nuxt; Docker y CI impiden incorporar su paquete al contenedor servido. No se aplica la degradación automática sugerida de Nuxt 4.6.2 a 4.1.3. El aviso de las herramientas de construcción se mantiene documentado, sin ocultarlo cambiando su clasificación a dependencia de desarrollo.

## Copias y rollback

Dos checkpoints completos cifrados y restaurados: `/var/backups/foroia/master-20261025-final` y `/var/backups/foroia/masterdeps-20261025-final`. Cada uno verifica las quince tablas, Redis, código/configuración y certificados; cuatro archivos cifrados descargados con hashes comprobados.

Rollback de la actualización final de dependencias: `sudo python3 /var/backups/foroia/masterdeps-20261025-final/rollback.py`. Para revertir el bloque maestro: `sudo python3 /var/backups/foroia/master-20261025-final/rollback.py`. Se conservan datos y reservas, sin restaurar una base antigua sobre escrituras actuales. El rollback del bloque maestro desactiva el antiguo timer de ejemplos para impedir ejecutar código en el VPS.

Presupuesto reservado: **0,235788 USD**; capacidad para nuevas reservas mensual **4,764212 USD**, diaria **0,150000 USD** en la comprobación previa a la ejecución del 25. No hay respuestas nuevas con tokens registrados. La facturación histórica real no se conoce: no se presenta como cero.

## Archivos cambiados

- `api/app/research/opportunities.py`, `queue.py`: fichas de oportunidades, fuentes y relación con contenido existente.
- `api/app/research/editorial.py`, `worker.py`: protección del presupuesto de artículos nuevos frente a mantenimiento.
- `api/app/research/monitor.py`, `publication.py`: supervisión acotada y lectura semántica de enlaces/HTML.
- `api/app/research/routes.py`, `api/app/modules/analytics.py`: estado y costes con procedencia; métricas no disponibles explícitas.
- `api/app/research/examples.py`, `scripts/verify_editorial_examples.py`: recibos ligados a código/dependencias/runtime y ejecución fuera de producción.
- `api/app/research/writing.py`: español internacional y hechos regionales respaldados.
- `web/pages/editorial/investigacion.vue`, `estadisticas.vue`, `web/utils/research-status.ts`: panel, alertas y límites de medición.
- `web/utils/information.ts`: criterio editorial actualizado.
- `deploy/health.sh`, `deploy/foroia-editorial-examples.service`, `deploy/make-release.py`: reutilización de timers y paquete reproducible.
- `api/Dockerfile`, `web/Dockerfile`, `web/package-lock.json`, `.github/workflows/checks.yml`: instalación segura, runtime reducido, parche y controles CI.
- `tests/test_master_consolidation.py`: oportunidades, alertas, deduplicación de incidencias, URLs, métricas, señales inválidas, límites de mantenimiento y recibos.
- `README.md`, `PROJECT_BRIEF.md` y este informe: estado y operación.

## Acciones que requieren al propietario

Confirmar los datos legales reales autorizados; configurar y probar SMTP antes de abrir cuentas; proporcionar/autorizaciones para conectar métricas de Search Console y, si se desea activar GA4, propiedad y revisión de privacidad/consentimiento; cuenta y autorización de AdSense antes de cargar anuncios. Ninguno de esos pasos exige revisión diaria de los artículos ni bloquea el motor editorial actual.
