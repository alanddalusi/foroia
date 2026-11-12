# Sistema editorial autónomo — 24 octubre 2026

## Funcionamiento

El trabajador conserva las 22:30 Europe/Madrid, 5 USD mensuales y 0,15 USD diarios. La fecha editorial única impide repetir automáticamente una jornada ya consumida. Publica como máximo una pieza diaria y cinco semanales; 3–5 por semana es una referencia editorial, no una cuota que anule controles.

Dos motores comparten presupuesto y una cola PostgreSQL persistente. Noticias exige evidencias pertinentes de dos organizaciones independientes realmente citadas. Tutoriales y guías pueden apoyarse en una documentación oficial suficiente; comparativas requieren dos organizaciones. Si no hay noticia viable, continúa con evergreen. Una indisponibilidad global del proveedor o falta de presupuesto detiene llamadas sin borrar las reservas.

La cola inicial contiene once intenciones prácticas. El descubrimiento amplía oportunidades desde secciones sustanciales de documentación oficial accesible, hasta dos nuevas al día y cuarenta candidatas activas. Son hipótesis editoriales, no volúmenes de búsqueda medidos. El endpoint privado `POST /editorial/research/signals` admite señales agregadas de una exportación real de Search Console. La conexión automática a Search Console requiere credenciales y no se ha inventado ni activado.

El preflight filtra duplicados, antigüedad, independencia y documentación antes de gastar. Guarda fragmentos identificados de forma estable; el generador elige identificadores, y el servidor resuelve las citas. La revisión comprueba título, resumen y afirmaciones. Las correcciones están acotadas a una por versión; hay como máximo una candidata de noticias y dos evergreen con generación por jornada, siempre sujetas al presupuesto compartido.

Los documentos tienen caché de 24 horas y los fallos de dos horas. Se permiten cuatro nuevas recuperaciones de documentación por jornada. Las noticias tienen sus límites existentes de recuperación. Un 403 se registra y no se intenta eludir. Las fuentes científicas de autoría no identificada no se convierten en una organización independiente por estar alojadas en arXiv.

## Código y actualizaciones

Solo se ejecutan seis ejemplos controlados por el servidor, nunca código arbitrario redactado por el modelo. Se verifican mediante contenedores efímeros sin red, secretos, privilegios ni escritura en el sistema de archivos, con límites de CPU, memoria y procesos. Un recibo incluye hash del código y pruebas, imagen inmutable, versiones y fecha; caduca a las 48 horas. El timer auxiliar `foroia-editorial-examples.timer` lo renueva a las 22:20 Europe/Madrid. No cambia la hora de investigación. El trabajador recibe el directorio de recibos en solo lectura y no tiene socket Docker.

Las actualizaciones automáticas se aplican únicamente a contenido de esta cola, de al menos treinta días, cuando cambia una evidencia citada. Requieren revisión específica de cambio sustancial; conservan URL y fecha original. La comprobación optimista impide sobrescribir una edición humana concurrente. Se conserva la versión previa para recuperación.

## Publicación y observabilidad

Después de publicar se comprueban HTTP, HTML SSR, contenido de API, título, descripción, canonical, Open Graph, fechas y citas de BlogPosting, migas, imagen y sitemap. Los errores transitorios tienen tres comprobaciones acotadas sin llamadas al modelo. Un error crítico archiva la pieza nueva o restaura la revisión anterior, siempre que nadie haya cambiado entretanto el artículo. La comprobación pendiente se reanuda tras reiniciar.

El panel `/editorial/investigacion` muestra cola, estados, fuentes, motivos y próxima fecha. `/editorial/estadisticas` conserva el seguimiento de visitas. `generation_usage` guarda tokens reportados y coste estimado; las reservas conservadoras siguen siendo el límite de gasto. Ninguno sustituye la factura del proveedor. Se preserva el historial previo.

## Archivos principales

- `api/app/research/{editorial,queue,documents,blueprints,examples,publication}.py`: coordinación, cola, fuentes oficiales, ejemplos y comprobación pública.
- `api/app/research/{writing,quality,worker,evidence,sources,selection,routes}.py`: evidencias, revisión, ejecución y observabilidad.
- `api/app/models.py`, `api/alembic/versions/0006_editorial_queue.py`: tres tablas nuevas, sin modificar las doce originales.
- `api/app/manage.py`: `editorial-seed` idempotente y `editorial-preview` sin llamadas al proveedor.
- `scripts/verify_editorial_examples.py`, `deploy/foroia-editorial-examples.*`, `compose.production.yml`: aislamiento y recibos.
- `web/pages/editorial/investigacion.vue`, `web/utils/research-status.ts`, `web/server/api/editorial/[...path].ts`: panel privado y proxy autorizado.

## Validación y operación

Suite Python: 181 correctas y 45 omitidas por requerir entornos opcionales. Las nueve pruebas específicas con Nuxt construido, SSR real y consentimiento pasan por separado. TypeScript y build pasan. Los seis ejemplos pasan en aislamiento real en el VPS. Las doce URLs oficiales de documentación consultadas son accesibles, sin llamadas de generación.

Backup cifrado completo: `/var/backups/foroia/autonomous-20261024-final`, con cuatro copias cifradas descargadas y hashes comprobados. Restauración PostgreSQL con las doce tablas idénticas; Redis, archivo de código/configuración y certificados comprobados. La migración se ensayó en PostgreSQL aislado restaurado: doce tablas intactas, tres nuevas y once candidatas tras dos inicializaciones.

Rollback de aplicación: `sudo python3 /var/backups/foroia/autonomous-20261024-final/rollback.py`. Recupera archivos e imágenes anteriores y desactiva el timer auxiliar. Conserva tablas nuevas, contenido y reservas; no ejecuta downgrade ni restaura la base antigua sobre escrituras recientes.

No se fuerzan generaciones de pago ni se publica contenido de prueba. La simulación completa utiliza proveedor simulado y base aislada, con el flujo real hasta SSR y sitemap. La primera ejecución natural confirmará la calidad de la respuesta del proveedor en vivo: las pruebas no garantizan aprobación ni publicación diaria.

No se cambian credenciales, DNS, firewall, anuncios ni consentimiento. GA4 y publicidad permanecen desactivados. SMTP transaccional e identificación legal real siguen pendientes. No se garantiza tráfico, ingresos ni posición en buscadores.

## Resultado del despliegue

API, web y trabajador nuevos están activos; PostgreSQL, Redis y Caddy conservan sus contenedores. Las diecisiete fuentes Python desplegadas coinciden con sus hashes locales. PostgreSQL y Redis no tienen puertos publicados. HTTPS, redirección HTTP y www, robots y sitemap responden correctamente. Los cuatro artículos anteriores pasan el verificador público completo, sin cambios de contenido ni reservas históricas.

El panel autenticado pasa en navegador móvil y teclado, sin errores JavaScript ni desbordamiento horizontal. Hay once candidatas iniciales y una preparada con documentación oficial y ejemplo verificado. El preview se detiene antes del proveedor: cero llamadas, reserva máxima estimada de la primera llamada 0,020058 USD, sin añadir esa reserva al historial. El total mensual reservado sigue siendo 0,235788 USD.

La próxima ejecución elegible indicada por el servidor es **25/10/2026 a las 22:30 Europe/Madrid (UTC+01:00)**. El 24 ya tiene expediente, por lo que no se repite para forzar una publicación. Falta observar la primera respuesta real del proveedor con esta versión durante la ejecución natural. El modelo actual responde a la consulta de disponibilidad, pero figura deprecado en su documentación: se conserva y debe vigilarse su disponibilidad, sin cambiarlo silenciosamente.
