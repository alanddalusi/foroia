# Despliegue SEO en producción — 23/10/2026

Resultado: paquete `foroia-seo-ready-20261023.tar.gz` aplicado en `/opt/foroia`, SHA256 `2b72cde1203217f21d4d16eb6fbe398d26db15b94d6b0a653ad59075b2a798a4`. API, Nuxt, trabajador de investigación y Caddy actualizados. PostgreSQL y Redis existentes conservados, sin recrear sus volúmenes. Mantenimiento desactivado como estaba. No hubo fallo crítico ni fue necesario ejecutar rollback.

## Respaldo y preservación

Checkpoint privado: `/var/backups/foroia/seo-release-20261023`, permisos 700. Copias cifradas de PostgreSQL, Redis, código/configuración con production.env y volúmenes de Caddy; copias fuera del VPS en `.local/deploy/seo-backup-*.age`. No publicar estos archivos. Las imágenes previas tienen etiquetas `foroia-rollback-api:seo-20261023`, `foroia-rollback-web:seo-20261023` y `foroia-rollback-research:seo-20261023`.

Se descifraron los respaldos localmente manteniendo la clave age fuera del VPS. PostgreSQL se restauró mediante pg_restore en un contenedor sin red: las huellas y recuentos de **todas las tablas** coincidieron con el snapshot previo. Redis pasó redis-check-rdb y se cargó en un servidor desechable sin red; sus claves con TTL ya caducadas se descartan al restaurar, comportamiento esperado de Redis. Los archivos de código/configuración y certificados se descifraron y leyeron íntegramente en memoria; rutas seguras y archivos esperados presentes, sin imprimir claves.

Las cinco migraciones existentes son idénticas byte a byte; cabeza 0005_analytics, sin nuevas migraciones. Tras activar los servicios y antes del login de comprobación, todas las tablas ajenas a analítica coincidieron exactamente con el snapshot previo: usuarios, sesiones, artículos, temas, comentarios, auditoría, correo e investigación. Los contadores pueden crecer por tráfico real. La comprobación posterior de login crea una sesión administrativa nueva normal; no altera cuentas ni contraseñas. La huella de production.env se comprobó antes y después y es idéntica. Se conservó el único artículo publicado y su URL.

## Aplicación y rollback preparado

Se verificó checksum, se aplicó el paquete y se retiró únicamente el archivo de vista sustituido `web/pages/blog/[seccion].vue`. Se validó Compose, se construyeron **api, web y research-worker** (Compose asigna etiquetas distintas a los servicios aunque compartan contexto), se activaron API/web esperando salud, se recreó el trabajador y se validó/recreó Caddy. No se actualizó ni habilitó el envío del mail-worker.

`/var/backups/foroia/seo-release-20261023/rollback.sh` restaura archivos e imágenes anteriores y comprueba que production.env permanece intacto; no restaura la base encima de nuevos datos. Durante la activación hubo una trampa de error que ejecutaría ese rollback si fallaba un paso crítico. Las comprobaciones públicas posteriores también pasaron, por lo que no se invocó. Despliegue con una sola réplica: no se acredita ausencia absoluta de interrupciones breves durante recreación.

## Verificaciones reales

- API, web, PostgreSQL y Redis saludables; Caddy y ambos trabajadores en ejecución. Monitor systemd Result=success. Esquema 0005_analytics. Solo Caddy expone 80/443; los puertos internos siguen sin publicación en Internet.
- HTTP 308 a HTTPS; www HTTPS 301 al principal. TLS verificado. Cabeceras HSTS y CSP Report-Only presentes (no se confunde Report-Only con bloqueo).
- `/foro`, `/actualidad`, `/herramientas`, `/programacion`, `/tutoriales`: 200. Las cuatro `/blog/<seccion>`: 301 a su canonical corto; parámetros de paginación conservados. Ruta desconocida: 404.
- Sitemap índice y todos sus archivos 200/XML válido. Siete URLs canónicas en el estado actual; todas responden 200, sin noindex ni fragmentos, con canonical coincidente. El artículo publicado coincide con la API. No hay temas públicos actualmente, por lo que no se anuncia un archivo de temas vacío. Las consultas de inventario/entradas incorporan automáticamente artículos publicados y temas aprobados futuros; prueba aislada previa con 55 temas confirmó que se supera el antiguo límite de 50.
- robots permite rastrear y anuncia el mismo `/sitemap.xml` enviado por el propietario. Comprobaciones sin sesión con agente identificable de verificación tipo Googlebot correctas. Esto acredita acceso público; no equivale a observar una nueva visita de Google ni confirmar indexación/posición desde su cuenta. La verificación y envío de Search Console fueron comunicados por el propietario; no se modificaron DNS ni identificadores.
- Panel sin sesión redirige a cuenta; API editorial devuelve 401. Login real de administrador y dashboard correctos; periodos, tabla diaria, teclado y móvil comprobados.
- Chromium real móvil: portada y navegación interna a sección/artículo, canonical actualizado, ilustración visible, sin desbordamiento horizontal ni errores JavaScript. No hubo peticiones a GA4 ni publicidad. GA4 y ads.txt siguen sin ID configurado; ads.txt devuelve 404 de forma intencionada.
- Comprobación backend previa a la activación: 94 pruebas correctas en 17,12 s, incluidas investigación, permisos, artículos, analítica y sitemaps. La revisión anterior completa dio 97 correctas y 36 optativas omitidas, más 2 pruebas HTTP/navegador aisladas. Typecheck y build se repitieron satisfactoriamente en la imagen de producción.

## Investigación y publicación

Trabajador nuevo iniciado a las 10:01:52 UTC (12:01:52 Madrid), en ejecución y sin reinicios inesperados. La huella del módulo de redacción coincide entre API y trabajador. Señal Redis activa, configuración válida, clave presente sin mostrarla, enabled=true y auto_publish=true. Se conservan reservas e historial previos; no se forzó ninguna llamada ni publicación.

Próximo inicio previsto: **23/10/2026 a las 22:30 Europe/Madrid** (20:30 UTC en esa fecha). El bucle comprueba el horario cada 30 segundos y respeta el cambio estacional. La publicación sucede al terminar satisfactoriamente redacción, validación y revisión, no a una hora exacta fija. Máximo una ejecución editorial diaria y presupuesto mensual 5 USD; límite diario 0,15 USD. Si las fuentes, controles o presupuesto fallan, queda borrador/revisión o no hay publicación. No hay aprobación humana diaria obligatoria en el modo autorizado actual.

Al comprobar a las 12:02 Madrid solo existían las dos reservas históricas importadas, no una ejecución nocturna nueva. Las pruebas verifican el planificador y los controles; sigue pendiente observar el primer ciclo nocturno real completo. No se afirma que ya se haya generado y publicado un nuevo artículo automáticamente. No existe generación automática de temas del foro.

## Dependencias y pendientes

Los avisos GHSA-vfj7-8cjw-p6xm (braces) y GHSA-86w9-cpqp-85rv (node-forge) siguen publicados sin parche. npm audit del árbol de compilación identifica 11 paquetes high derivados de esos dos avisos; no se rebajó Nuxt ni se aplicó fix --force. No se identificaron los paquetes afectados entre los de la imagen final; el riesgo residual de compilación sigue abierto. La auditoría Python del bloque anterior no encontró avisos conocidos. No es una garantía de seguridad exhaustiva.

Pendientes: datos reales autorizados del titular y revisión legal, SMTP probado antes de abrir altas/recuperación, configuración y consentimiento de GA4 si se quiere habilitar, aprobación AdSense/CMP antes de anuncios, métricas de campo y primer ciclo nocturno observado. Copia externa automatizada, política de retención de backups y alertas externas continúan pendientes. No se modificaron credenciales, DNS, SSH, UFW ni servicios Google.

Evidencia privada: `.local/deploy/seo-backup-complete.log`, `seo-restore-verified.json`, `seo-data-comparison.log`, `seo-production-build.log`, `seo-production-activate.log`, `seo-production-http.json`, `seo-worker-final.log` y capturas móviles. No versionar `.local`.

Fuentes de los avisos revisados:

- https://github.com/advisories/GHSA-vfj7-8cjw-p6xm
- https://github.com/advisories/GHSA-86w9-cpqp-85rv
