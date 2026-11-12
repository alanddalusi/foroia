# Preparación de apertura, correo e investigación en VPS — 22/10/2026

Se desplegó la marca Foro IA al Día, footer con contacto/normas/criterio editorial/cookies/aviso legal/privacidad y seis páginas SSR. Aviso legal/privacidad siguen identificados como borradores noindex: no se han inventado titular, domicilio o NIF ni se han publicado los de la factura. El propietario delegó la presentación de la marca, pero no aportó la identificación real restante. Campos preparados en configuración; mantenimiento global permanece activo. No afirmar que el blog ya está abierto ni que los textos tienen aprobación jurídica.

Categorías: recuento de temas publicados mediante agregado y join, sin N+1; las vacías llevan noindex y se excluyen del sitemap. Las páginas de información desconocidas, incluidos nombres de propiedades del prototipo, dan 404 real. Registro y correo de cuentas comparten indicadores coherentes entre API y Nuxt; sin `ACCOUNT_EMAIL_ENABLED`, registro/recuperación/reenvío rechazan antes de crear tokens o mensajes y la interfaz no ofrece esas acciones. Login existente sigue disponible. SMTP configurable; CLI de prueba requiere credenciales y STARTTLS y solo enviaría al contacto administrativo. Con credenciales ausentes se comprobó rechazo previo, **sin envío real**. Comparación gratuita y pasos en `TRANSACTIONAL_EMAIL.md`; cuenta del proveedor sigue pendiente.

- Suite completa: **126 correctas en 43,23 segundos**, `.local/deploy/launch-full-verified.log`, incluidos HTTP y Chromium. Incluye regresiones de recuentos/visibilidad de temas y bloqueo de correo sin tokens/mensajes. Primera pasada: 25 fallos por web local todavía sin iniciar; se corrigió el arranque, no se cambió la prueba para ocultarlos. Backend previo: 92 correctas/33 omitidas.
- Typecheck/build local y en VPS correctos. Release base desplegado: SHA256 `5cac626a8e33b736059427687a048fc51188bba76c51676de7ea5218f0c6267e`. Ajuste posterior acotado en `health.sh` para finales de línea CRLF de Windows; primer fallo de monitorización era detección de mantenimiento, no caída de aplicación. Resultado posterior `success`.
- Verificación real privada del VPS por SSH: páginas SSR/canonical, campos legales pendientes/noindex, categorías vacías fuera de sitemap, 404, recuperación/reenvío cerrados, login admin e investigación con heartbeat. Chromium comprobó marca, móvil y selector de cuenta limitado al login; captura `.local/deploy/prelaunch-home-mobile.png`.
- Investigación trasladada: clave fuera del `.env` local y trabajador local detenido, clave privada en entorno de producción (sin mostrarla). Dos reservas históricas importadas con auditoría y fecha única, estado explícito `migrated_local_budget`; total 157429 microUSD (0,157429 USD). No se importaron borradores ni expedientes para reintentar. Panel confirma límite 5 USD/mes, reserva conservada y worker activo. GET del modelo desde VPS devolvió 200; no es una nueva generación y no demuestra aún un ciclo autónomo de producción. Primer día nuevo esperado: 23/10/2026 a las 22:30 Europe/Madrid.
- `foroia-health.timer` cada cinco minutos, comprobación manual correcta de contenedores/HTTPS/backup reciente. Backup diario activo. Se crearon checkpoints cifrados antes/después del despliegue. Copias externas manuales actualizadas de DB y código/configuración: SHA256 `3cd40018b88dea900ffa2030fcef464d090ae153c349aec9b6d16eab7ccd0440` y `7919ea55fd366990d950c934d0ffefc5f2afb73b5d0753656a4e5d63864f2539`, contrastadas con VPS. Clave age solo fuera del servidor. Replicación externa automática/retención/alertas aún pendientes.

Auditoría en contenedores efímeros dentro del VPS, sin modificar las imágenes en servicio: pip-audit contra constraints Python fijadas, sin vulnerabilidades conocidas. npm audit del árbol completo de compilación: 11 paquetes marcados por **dos avisos de severidad alta**, `braces` y `node-forge`, sin versión parcheada indicada en [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) y [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv). No se ejecutó el downgrade de Nuxt propuesto por audit fix. Inventario de la imagen final y búsqueda de marcadores en `.output`: no contiene esos paquetes ni sus marcadores; Nuxt completo se usa solo al compilar. Esto acota la exposición observada, **no elimina los avisos de las herramientas de construcción ni constituye prueba formal de ausencia de toda vulnerabilidad**. Mantener seguimiento de parches y entradas de compilación confiables. Reportes privados en `/var/log/foroia/` y `.local/deploy/`.

Archivos: API config/cuentas/foro/mail_worker; Nuxt app/config/cuenta/comentarios/categoría/información/sitemap/estilos; ambos Compose y plantilla; pruebas y documentación; nuevas unidades y script de salud. Sin migraciones. No se modificaron UFW, SSH ni DNS/correo. El sitio sigue en mantenimiento por identificación legal/revisión pendiente; correo y altas permanecen cerrados hasta proveedor real y recepción probada. No se ha declarado completa la operación externa ni la monetización.

# DNS, certificados y acceso HTTPS — 22/10/2026

Tras la confirmación del propietario de los cambios DNS, se comprobaron @ y www apuntando a `146.59.35.127`, consulta autoritativa y resolución desde el VPS incluidas. No se ha modificado la zona DNS desde este equipo. MX y SPF conservados. Persisten los TXT de aparcamiento OVHcloud `1|www.foroiaaldia.com` y `3|welcome`; no interfieren actualmente con HTTP/HTTPS porque A dirige al VPS. Su limpieza posterior no debe borrar TXT SPF ni registros de correo.

Se arrancó Caddy desde el Compose existente, conservando mantenimiento. Let's Encrypt completó HTTP-01 y emitió certificados para los dos nombres. Verificación independiente desde el VPS con curl y OpenSSL: cadena válida, `ssl_verify_result=0`, emisor Let's Encrypt YE2, caducidad 20/01/2027 13:52:07 UTC. Caddy gestiona renovación y almacena certificados/cuenta en volúmenes persistentes; no se ha probado una renovación futura ni se han expuesto claves privadas.

- HTTP de @ y www devuelve 308 a HTTPS. HTTPS www devuelve 301 al dominio principal. Probado con ruta y parámetros, que se conservan.
- HTTPS principal responde **503 intencional** con página de preparación, `noindex, nofollow`, `no-store` y Retry-After 3600. No se ha publicado el blog fuera del mantenimiento.
- Chromium verifica el certificado sin ignorar errores TLS y confirma la cadena de redirecciones completa. Captura `.local/deploy/https-maintenance.png`.
- API interna `/health` 200; PostgreSQL acepta conexiones; Redis PONG; servicios saludables; temporizador de backups activo.
- Sondas TCP externas: 80/443 accesibles; 5432/6379/8000/3000/2019 no accesibles. Solo Caddy publica puertos del host. Sin cambios manuales de UFW ni SSH.
- Incidencia local de verificación: httpx con su almacén de certificados rechazaba el certificado interceptado por Avast Web/Mail Shield. El almacén del sistema Windows y Chromium lo validan. Se contrastó el certificado real desde el VPS (Let's Encrypt) sin desactivar la validación TLS ni cambiar la configuración del servidor para eludirla.

Logs privados locales: `.local/deploy/caddy-start.log`, `caddy-certificates.log`, `https-services-verified.log`. Se corrigieron comprobaciones de shell/entrada estándar antes de registrar los resultados; no eran errores de la API. No se repitió la suite local por este arranque sin cambios de código. Actualizados `DEPLOYMENT.md`, `docs/DEPLOYMENT.md` y este registro. Pendientes de lanzamiento: legales/SEO, SMTP antes de abrir registros, automatización externa de backups/alertas y presupuesto de investigación conciliado. Mantenimiento permanece activo.

# Instalación interna en producción — 22/10/2026

Tras la nueva instrucción de continuar con Docker y servicios, se instaló Docker Engine 29.9.2, Compose 5.6.1, containerd 2.4.2, Buildx 0.38.1 y age desde los repositorios verificados. Hello-world correcto. No se editó UFW, SSH ni DNS; Docker crea sus reglas de red normales. Se conserva el acceso SSH existente y UFW TCP 22/80/443. Logs locales privados: `.local/deploy/docker-install.log`, `production-build.log`.

Release `b446485a7cabb72077ac7072d68ed8dfbcdff93ff47b709282ff549ad1847c8e` transferido con SHA256 comprobado y extraído inicialmente en `/opt/foroia`. Nuevas credenciales de producción generadas sin mostrarlas; `production.env` root/600, copia local con ACL restringida. SMTP y clave OpenAI vacíos; registro cerrado y perfil research inactivo. Se creó el administrador acordado sin asumir que la redirección de correo haya recibido mensajes.

- PostgreSQL, Redis, API y Nuxt saludables. Alembic `0004_research (head)`. Build/typecheck Nuxt correctos en el propio VPS.
- Verificados por túnel SSH privado: SSR, canonical HTTPS, 404, registro rechazado con 503, login del admin, cookies Secure, permisos de panel, acceso al historial de investigación y CSRF inválido rechazado con 403. Ningún secreto enviado a logs de verificación.
- Traslado selectivo del artículo local aprobado 28 a artículo 1 de producción mediante API editorial autenticada: borrador → revisión → publicado, con nota de transferencia e intervención de operador. No se importaron cuentas, sesiones, debates ni contenido de pruebas. Visible solo por acceso interno mientras no se abra Caddy.
- Chromium contra el VPS por túnel: artículo, canonical, escritorio y móvil 320 px sin desbordamiento. Capturas privadas locales `vps-article-desktop.png` y `vps-article-mobile.png`.
- `docker ps` sin puertos de host para DB/Redis/API/Nuxt. Sondas TCP externas a 5432/6379/8000/3000 sin conexión.
- Caddy: validación real correcta dentro del VPS. No arrancado ni certificado emitido: @ y www aún apuntan a `213.186.33.5`. El siguiente paso DNS se ha solicitado al propietario, sin tocar MX/TXT ni acceder al panel OVHcloud desde aquí.

Backup age real y dos restauraciones desechables sin red correctas. La última recupera migración `0004_research` y un artículo; no modifica producción. Copia externa local cifrada contrastada: SHA256 `f05c4eee7288a6786c465d02167940e1deff92716ba2ed1710c52cbb07c8f853`. Identidad privada guardada fuera del VPS con permisos restringidos, comparada con la original; copia temporal del servidor retirada. Timer diario 03:15 UTC activo y servicio ejecutado correctamente. Pendientes replicación externa automática, retención y alertas; no se presenta la copia manual como una política completa de backups externos.

Cambios del ajuste en repositorio: unidades `deploy/foroia-backup.service`, `.timer` y documentación de estado. No hay cambios de lógica ni migraciones; no se repitió la suite local de 123 casos por estas unidades. Se realizaron las comprobaciones reales del VPS descritas arriba. Pendientes DNS, emisión HTTPS/redirecciones, SMTP, legales/SEO, monitorización externa y conciliación presupuestaria antes de activar investigación.

# Correo administrativo y bloqueo de altas — 22/10/2026

El propietario elige `admin@foroiaaldia.com` mediante redirección de MX Plan Redirect al correo personal. No se han creado credenciales SMTP ni se ha afirmado recepción comprobada. Plantilla de producción actualizada con ese correo y SMTP vacío. Nueva opción de servidor `REGISTRATION_ENABLED`, desactivada por defecto en Compose de producción y activada por defecto en desarrollo. La API rechaza altas con 503 antes de escribir o encolar correo; login de usuarios existentes permanece operativo. Mantener también el mantenimiento de Caddy hasta completar los demás requisitos.

Pruebas: **19 correctas de cuentas**, con regresión de altas cerradas/sin usuarios ni correo creados y login existente permitido. Suite sin servicios externos: **90 correctas y 33 omitidas en 16,27 segundos**, `.local/deploy/registration-gate-tests.log`. HTTP/navegador no repetidos en este cambio de backend/configuración. Compose validado con credenciales ficticias: correo correcto, registro cerrado, SMTP vacío y DB/Redis/API/web sin puertos publicados. Archivos: `api/app/core/config.py`, `api/app/modules/accounts.py`, `tests/test_accounts_api.py`, ambos Compose, plantillas de entorno y documentación. Sin migraciones. Docker todavía no instalado/arrancado en el VPS; autorización sobre reglas de red pendiente. No se han modificado firewall, SSH ni DNS en este ajuste.

# Acceso al VPS y repositorio Docker — 22/10/2026

Acceso SSH por clave desde este entorno confirmado usando la identidad predeterminada de Windows; sudo no interactivo disponible. Ubuntu 26.04 amd64 y UFW TCP 22/80/443 comprobados. Solo SSH escuchaba públicamente. No se ha cambiado SSH, firewall ni DNS.

Ejecutado `deploy/prepare-docker.sh`: comparación de la clave GPG con la descarga oficial, creación del repositorio resolute si no existía, actualización de índices y simulación de instalación. Candidatos válidos: Docker Engine 29.9.2, Compose 5.6.1, containerd 2.4.2 y Buildx 0.38.1. La simulación elimina cero paquetes. Registro privado local `.local/deploy/docker-repository.log`. Instalación y arranque pendientes de autorización expresa por las reglas de red que crea Docker; no se ha arrancado ningún servicio de la aplicación.

Añadidos `deploy/install-docker.sh` con versiones verificadas y `--no-remove`, y `deploy/make-release.py` para empaquetar código excluyendo secretos/cachés/datos. Sintaxis Bash comprobada; el instalador real no se ha ejecutado. Se ha generado un paquete de preparación en `.local/deploy/`; no se ha transferido al VPS. No hay cambios en lógica de aplicación ni migraciones y no se ha repetido la suite por estos scripts de operación.

# Preparación de despliegue OVHcloud — 22/10/2026

Se prepara `compose.production.yml` independiente, `deploy/Caddyfile`, plantilla de variables de producción, scripts de backup cifrado/restauración aislada y `docs/DEPLOYMENT.md`. Solo Caddy publica puertos; cookies Secure y URL HTTPS fijas; mantenimiento 503/noindex por defecto. Correo real pendiente de configurar; investigación opt-in, sin clave ni perfil activados para evitar duplicar gastos con el trabajador local. El proxy Nuxt puede aceptar la IP validada que Caddy sobrescribe, únicamente con configuración privada explícita y Nuxt inaccesible directamente.

- Compose v2: `config --format json` validado con variables ficticias. Comprobados servicios, ausencia de puertos de DB/Redis/API/Nuxt, cookies Secure, origen canónico, mantenimiento y límite de 5 USD.
- Caddy: `validate --adapter caddyfile` correcto en imagen oficial `caddy:2-alpine`, digest observado `sha256:24ec7b05bc532c7bb57f727030c5056e257ff7138b4b50460306819ff79362bd`.
- `bash -n` correcto para backup/restauración. **No se ha ejecutado todavía backup ni restauración**; requieren instalación/configuración y acceso al VPS.
- TypeScript y build Nuxt correctos, `.local/deploy-local-build.log`.
- Suite completa HTTP/Chromium: **122 correctas en 42,64 segundos**, `.local/deploy-regression.log`.

No desplegado: SSH responde, pero la autenticación por clave existente se rechaza. Se ha generado una clave exclusiva local, aún no autorizada en el VPS. La clave del host se ha registrado por primer contacto (TOFU); su huella todavía no está contrastada desde la consola del proveedor. El dominio A consultado sigue apuntando al aparcamiento de OVHcloud. No se han cambiado DNS, archivos ni servicios remotos. Pendientes acceso SSH, SMTP, secretos nuevos, revisión de dependencias/seguridad, monitorización, legales y backup/restauración antes de abrir al público.

# Última validación local — 22/10/2026

Servicios recuperados mediante `scripts/local.ps1 Start -Toolbox`, incluyendo arranque de la VM apagada, Compose verificado y recreación de los servicios con el cambio. Registro: `.local/resume-oct22-fix-start.log`.

La ejecución del nuevo día trasladó el borrador 28 sin duplicarlo ni borrar reservas. La recuperación falló antes de contactar al proveedor: una fuente descartada devolvía un error. Ahora `sources.restore` admite identificadores requeridos y el trabajador obtiene esos identificadores de las citas: consulta todas las fuentes citadas, conserva sus IDs y rechaza ausencias o fallos; las fuentes no usadas no bloquean la revisión. Regresión con fuente descartada inaccesible y fuentes citadas inaccesibles/ausentes: **50 pruebas de investigación correctas**.

La fuente de OpenAI citada también presentó errores de acceso posteriores. Se acotó **por intervención del operador Codex** el borrador a una comparación entre demanda comercial y evaluación técnica, usando los originales accesibles de Google y de IBM Research en Hugging Face. Acción `research_narrow_scope` auditada, contador de correcciones automáticas y reservas anteriores conservados. Esta intervención no se presenta como redacción completamente autónoma.

OpenAI completó la revisión real con todos los indicadores aprobados. El servidor publicó el mismo artículo 28 mediante el flujo normal: `published/quality_checks_passed`. Título final: «Agentes de IA: distinguir el interés comercial de la fiabilidad técnica». La reserva conservadora del 22/10 es **0,011192 USD**; sumada a la del 21/10, **0,157429 USD**. No es el cargo real facturado. Límites mantenidos: 0,15 USD/día y 5 USD/mes.

- Suite completa con HTTP y Chromium: **122 correctas en 41,64 segundos**, `.local/resume-oct22-full.log`.
- Publicación real comprobada por API y web (200), sitemap, canonical absoluto y JSON-LD parseable. Chromium muestra el artículo a 1280 y 320 px, sin desbordamiento horizontal; capturas `.local/design/published-28-desktop.png` y `published-28-mobile.png`.
- URL local: `http://localhost:3000/articulos/agentic-commerce-anuncios-agentes-servicio-asia`. Se conserva el slug del borrador; el cuerpo y el título finales tienen un alcance más reducido.
- Cambios de código: `api/app/research/sources.py`, `api/app/research/worker.py`, `tests/test_research.py`; documentación: este archivo y `EDITORIAL_AUTOMATION.md`. Sin migraciones ni dependencias nuevas.

El flujo nocturno sigue programado a las 22:30 Europe/Madrid con los servicios encendidos. La ejecución manual ya consumió el turno del día 22, por lo que no creará una segunda publicación esa noche. Publicar este artículo demuestra revisión y publicación reales, pero no garantiza que los ciclos futuros sin intervención superen los controles ni que haya contenido publicable cada día. El despliegue público y la publicidad quedan pendientes.

# Validación del bloque de cuentas y comentarios

Resultado final del 21 de octubre de 2026: **72 pruebas correctas, sin fallos ni pruebas omitidas** al activar HTTP y navegador. No es una declaración de aptitud para producción.

## Evidencia

- Estado recibido: la suite completa se repitió antes de modificar código y dio 51 correctas. La prueba corregida por el trabajo anterior sí pasaba; comprobaba la API, no la retirada en la web.
- Se retiró SWR de portada, artículos y secciones y se estableció `no-store` también en sitemap y APIs. La regresión prepara contenido publicado y calienta las rutas; después archiva y exige 404 en web/API y ausencia en portada, sección, listado y sitemap, sin esperar 60 segundos.
- Suite final: `PYTHONPATH=api FOROIA_LOCAL_HTTP=1 FOROIA_BROWSER=1 pytest -q` → **72 passed in 38.30s**. Incluye 39 pruebas de API/contrato, 30 HTTP y 3 de navegador. En Windows se ejecutó con `.local/venv/Scripts/python.exe`; instrucciones en LOCAL_TEST.md.
- Chromium real: panel completo (login, borrador, vista previa, revisión, publicación, archivo) en escritorio 1280×900 y viewport móvil 390×844. Se usó el teclado para controles y salto al contenido; se comprobó ausencia de errores JS y desbordamiento horizontal. El contraste medido del botón principal supera 4,5:1.
- Tercer recorrido de navegador: registro, correo recogido en Mailpit, verificación del enlace, login de miembro, rechazo de acceso editorial, comentario pendiente invisible al visitante, aprobación por administrador, renderizado escapado, edición que vuelve a revisión y retirada. Se corrigió la lectura del token cuando cambia el fragmento en la misma pestaña.
- Concurrencia de moderación: una decisión solo puede aprobar la versión revisada; si el autor la cambia antes, devuelve 409. Hay regresión de API para este caso.
- Redis real: 20 peticiones concurrentes con límite 5 admiten exactamente 5 y rechazan 15; TTL válido y contador compartido con una segunda conexión. Las claves de la comprobación se eliminan. La suite verifica además el rechazo de escrituras cuando Redis no está disponible.
- `pip check`: sin dependencias incompatibles; compilación Python correcta. Las imágenes se construyen con versiones directas/transitivas fijadas para API, lockfile npm, `npm ci`, typecheck TypeScript y build Nuxt. Typecheck y build correctos.
- Compose 2.39.4 recuperado y contrastado con el SHA256 oficial. Arranque mediante `scripts/local.ps1 Start -Toolbox` probado. Se rechazó un segundo arranque concurrente antes de modificar servicios mediante el bloqueo de operación.
- `scripts/verify-clean.ps1 -Toolbox`: proyecto temporal con PostgreSQL nuevo, migraciones hasta `0003_accounts_comments`, cuatro categorías, blog vacío, SSR, bootstrap y reinicio correctos. Se eliminaron únicamente sus contenedores y volúmenes temporales; la base principal se conservó.
- La web activa corresponde a la última imagen construida. La migración principal está en `0003_accounts_comments`.

## Artefactos locales

Logs y herramientas en `.local/` (excluidos de Git): `final-suite.log`, `unit-final.log`, `script-start.log`, `script-start-final.log`, `clean-check.log`, `typecheck-build.log`, `compose-v2.exe` y checksum. Los logs intermedios pueden contener intentos fallidos ya corregidos; el resultado final es el indicado arriba.

Capturas: `.local/browser/editorial-1280.png`, `editorial-390.png`, `article-1280.png` y `article-390.png`. Se tomaron después del login, sin mostrar contraseñas. Las pruebas generan contenido identificado como prueba y lo archivan; las cuentas técnicas de registro no tienen perfiles públicos ni representan usuarios reales.

La copia previa `.local/foroia-before-accounts.dump` y los contenedores antiguos detenidos se conservaron para operación local. No se ha ejecutado una restauración de esa copia.

## Archivos principales modificados o añadidos

- Backend: `api/app/models.py`, `main.py`, `core/config.py`, `core/limits.py`, `modules/accounts.py`, `modules/comments.py`, `modules/articles/editorial.py`, `modules/articles/schemas.py`, `mail_worker.py`, `manage.py` y `api/alembic/versions/0003_accounts_comments.py`.
- Dependencias/arranque: `api/requirements.txt`, `requirements-dev.txt`, `constraints.txt`, ambos Dockerfiles, `docker-compose.yml`, `.env.example`, `scripts/local.ps1`, `scripts/verify-clean.ps1`, `web/package.json`, `package-lock.json`, `tsconfig.json` y `.github/workflows/checks.yml`.
- Frontend: `web/nuxt.config.ts`, `app.vue`, `server/utils/community.ts`, proxies `server/api/community/[...path].ts` y `server/api/editorial/[...path].ts`, `server/middleware/editorial.ts`, `composables/useAccount.ts`, `utils/account.ts`, `utils/blog.ts`, `pages/cuenta.vue`, `pages/moderacion.vue`, `pages/articulos/[slug].vue`, componentes `ArticleComments.vue`, `ArticleBody.vue`, `EditorialForm.vue` y `assets/css/main.css`.
- Pruebas/documentación: `tests/test_accounts_api.py`, `test_articles_api.py`, `test_local_http.py`, `test_browser.py`, `redis_check.py`, README y documentos ARCHITECTURE, ACCOUNTS, LOCAL_TEST y VALIDATION.

No hay repositorio Git inicializado en esta carpeta; no se ha creado ningún commit. Los secretos permanecen en `.env` y no se han mostrado.

## Límites y siguiente bloque

La evaluación de accesibilidad cubre uso funcional, teclado, contraste de botones y revisión visual; no constituye una auditoría WCAG completa ni prueba en un teléfono físico. No hay pruebas de carga ni garantía de rendimiento en producción. Sin caché compartida en el blog aumenta la carga de lectura; medir antes de introducir caché y mantener la retirada inmediata. Las pestañas ya abiertas no reciben actualizaciones en tiempo real.

Correo exclusivamente local. Para producción faltan SMTP real, TLS/cookies Secure, proxy de confianza, MFA, eliminación de cuentas, revisión de dependencias, backups/restauración, alertas y cumplimiento. Las imágenes base siguen usando etiquetas de versión y deben revisarse antes de desplegar. No se ha publicado el sitio ni integrado publicidad.

Ese bloque se implementó posteriormente: ver la comprobación del 21/10/2026 a continuación.

## Investigación autónoma — 21/10/2026

- Suite completa, incluyendo HTTP y Chromium: **105 pruebas correctas en 41,64 segundos**, sin omisiones. Comando: `PYTHONPATH=api FOROIA_LOCAL_HTTP=1 FOROIA_BROWSER=1 pytest tests -q`; en PowerShell asignar las variables mediante `$env:`. Log `.local/research-complete.log`.
- 33 pruebas nuevas de investigación: destinos/DNS/redirects y tamaño, XML, fechas, horario de verano/invierno, evidencias, independencia de organizaciones, cifras, duplicados, transparencia, reservas antes de llamadas, límite mensual, reinicio sin repetir gasto, salida estructurada, permisos y CSRF. También rechazo si se pierde el bloqueo, se pausa o cambia el artículo durante la revisión.
- Los dos recorridos editoriales de navegador incorporan `/editorial/investigacion`, comprobación de desbordamiento en escritorio/móvil y pausa/reanudación por teclado. Capturas `.local/design/research-1280.png` y `research-390.png`. Sin contraseñas ni claves visibles.
- TypeScript y build Nuxt correctos en `.local/research-build-final.log`. `pip check` del contenedor API sin incompatibilidades. Compilación Python correcta. Nueva dependencia fijada `tzdata==2026.5` para horario Madrid también en Windows.
- Comprobación adicional de errores de configuración sin mostrar claves; se ocultan entradas en los errores Pydantic. Tras ese ajuste, las 33 pruebas de investigación vuelven a pasar y se reconstruyen los servicios API/trabajador.
- `scripts/local.ps1 Start -Toolbox` completado con las imágenes finales (`.local/research-start-verified.log`). API en `0004_research (head)`, trabajador levantado y heartbeat real en Redis. El fallback al PE `.bin` verificado resuelve la incidencia local del nombre de Compose sin cambiar protecciones de Windows.
- `scripts/verify-clean.ps1 -Toolbox`: cuatro migraciones, categorías, SSR, cuenta inicial, servicios y reinicio correctos con PostgreSQL y Redis aislados; limpieza de sus contenedores y volúmenes completada. Log `.local/research-clean.log`. La base principal se conserva.
- Consulta real sin IA ni gasto: tres RSS accesibles, 11 candidatos en la ventana de consulta y cinco documentos legibles de Google/Hugging Face. Tres descargas de páginas de OpenAI rechazadas por el sitio; se omiten. Esto comprueba la recolección actual, no garantiza acceso futuro ni relevancia de los temas.
- **No hay clave OpenAI configurada**: trabajador en espera. Redacción y revisión verificadas con dobles de prueba, no con una generación facturable real. No se publicó ningún artículo generado por IA durante estas comprobaciones. La calidad factual y editorial real debe evaluarse al configurar la clave; no se presenta como verificada.

Archivos: nuevo paquete `api/app/research/`, migración `0004_research.py`, modelos y registro API; página Nuxt de investigación, enlace editorial y proxy; Compose, `.env.example`, dependencias y scripts locales; pruebas `test_research.py` y ampliación de `test_browser.py`; README, PROJECT_BRIEF y documentos ARCHITECTURE, EDITORIAL_AUTOMATION, LOCAL_TEST y VALIDATION. El `.env` local incorpora las nuevas opciones con clave vacía, sin exponer secretos.

Riesgos: revisor y redactor pueden compartir errores; solo tres fuentes y corroboración estricta pueden producir días sin publicación. El límite monetario depende de mantener las tarifas y no cubre otros usos de la clave. El equipo debe permanecer encendido. No hay scraping de LinkedIn, acceso a cuentas privadas ni cobertura global de tendencias. No se ha desplegado en público ni añadido publicidad.

## Primera conexión real con clave — 21/10/2026

El propietario añadió una clave local y se recrearon API y trabajador para cargarla. Consulta autenticada del modelo: HTTP 200. Ejecución real a demanda registrada con diez candidatos; no produjo artículo y terminó como `skipped/provider_unavailable`. Una petición diagnóstica mínima de Responses, con reserva persistida previamente dentro del presupuesto, recibió HTTP 429. El código específico no quedó identificado: no se puede distinguir con esta comprobación entre saldo/cuota y límite de frecuencia. Revisar facturación y límites del proyecto antes de repetir. No se ha mostrado la clave, no se ha publicado contenido ni eliminado la ejecución o su reserva. El éxito de autenticación no constituye una prueba de generación satisfactoria. Registro privado consultable en `/editorial/investigacion`; arranque en `.local/openai-trial-start.log`.

## Prueba tras añadir saldo — 21/10/2026

El propietario confirmó saldo en el proveedor y autorizó retomar la prueba. Se reanudó manualmente la misma ejecución, manteniendo fecha única y todas las reservas; acción `research_retry_after_billing` auditada. OpenAI completó una generación estructurada, pero el control determinista la rechazó como `invalid_evidence`, sin crear artículo ni publicar. Se aclaró en `writing.py` que las citas deben copiarse de `text` en el idioma original, sin traducciones ni reconstrucciones. `worker.py` conserva ahora la propuesta en el expediente privado antes de validar, incluso si la rechaza; no se relaja la validación.

Regresión añadida en `test_research.py`: una propuesta inválida persiste tras rollback, mantiene el gasto reservado y no crea artículo ni aparece en la API pública. Pruebas de investigación: **34 correctas**. Suite sin servicios HTTP/navegador: **73 correctas y 33 omitidas**, 32,02 segundos, `.local/research-evidence-suite.log`. Reconstrucción/arranque en `.local/research-evidence-start.log`. La reanudación adicional tras este ajuste se audita como `research_retry_after_quality_fix`; no se han borrado reservas, aumentado límites ni activado reintentos automáticos.

En esa reanudación las citas superaron la validación, pero el resumen de 389 caracteres superó el máximo de 300 del blog (`invalid_article`). Se corrigió `Draft` para exigir en el JSON generado los mismos límites de título, resumen y slug que `ArticleWrite`, con tres regresiones adicionales. Resultado final de pruebas: **37 de investigación correctas** y **76 correctas/33 omitidas** en la suite sin servicios externos, 29,27 segundos. No se ha repetido la suite de navegador en este ajuste exclusivamente backend.

Se reutilizó la propuesta guardada, acortando únicamente el resumen a su primera cláusula completa y recuperando las mismas fuentes con sus identificadores originales. La operación `research_repair_metadata` se auditó y solo pagó la revisión pendiente, sin volver a redactar. Resultado real: artículo **28** en estado **draft**, investigación `draft/review_rejected`. El revisor detectó imprecisiones en magnitudes, alcance geográfico y afirmaciones no respaldadas. No se publicó ni se forzó la aprobación. También emitió objeciones formales sobre las citas del título/resumen; la revisión automática puede producir falsos positivos y requiere evaluación continuada.

Reserva conservadora acumulada del día: **0,123156 USD**, incluidos los intentos anteriores y diagnóstico; no es la factura real. Límites diario de 0,15 USD y mensual de 5 USD intactos. Todos los pasos reales (recopilación, redacción, validación, persistencia y revisión) se han ejercitado; no se presenta esta prueba como una publicación automática satisfactoria ni como garantía de calidad factual. Borrador local en `/editorial/28` y motivos en `/editorial/investigacion`.

## Corrección automática y revisión aplazada — 21/10/2026

Se añade `api/app/research/quality.py`: valida, revisa y puede corregir una vez los errores concretos antes de volver a revisar. Mantiene el mismo artículo, versiones privadas, auditoría y contador persistente. No se publica una versión que haya cambiado después de revisarla ni se sobrescribe una edición manual. Se corrige la exigencia contradictoria del revisor sobre citas en título/resumen; solo `evidence.quote` conserva el idioma original, mientras el texto público debe redactarse en español natural.

- Suite completa: **121 correctas en 83,90 segundos**, con HTTP y Chromium activados, `.local/corrections-full.log`. Incluye 49 pruebas de investigación: corrección aprobada, rechazo persistente, falta de presupuesto, fallo del proveedor, edición concurrente, reanudación sin volver a redactar y traslado de revisión una sola vez sin borrar reservas anteriores.
- TypeScript y build Nuxt correctos en `.local/corrections-start.log`; imágenes y servicios finales levantados mediante el script, `.local/corrections-final-start.log`.
- Prueba real con el artículo 28: se ejecutó una corrección automática, que actualizó el título para concretar «Sudeste Asiático». La llamada de revisión posterior devolvió una respuesta incompleta y no constituye una aprobación. Se amplió su máximo de salida de 2.000 a 4.000 tokens; no se acepta una respuesta incompleta como válida.
- Reserva final del día: **0,146237 USD**, incluyendo todos los intentos y diagnóstico. Se mantiene 0,15 USD/día y 5 USD/mes. No se ha vuelto a ejecutar una llamada de pago una vez alcanzado ese margen.
- Borrador 28 marcado `pending_review=true` tras comprobar que el contenido persistido coincide con la propuesta validada, con auditoría de operador. No se ha publicado. La ejecución del **22/10/2026 a las 22:30 Europe/Madrid**, si los servicios permanecen encendidos y las fuentes siguen accesibles, intentará retomar solo su revisión, con cargo al nuevo día y sin reiniciar el contador de correcciones. La continuación y su aprobación no se presentan como ya ejecutadas.

Archivos del ajuste: `research/quality.py`, `worker.py`, `writing.py`, `config.py`, `sources.py`, `tests/test_research.py`, pantalla privada `web/pages/editorial/investigacion.vue` y documentación ARCHITECTURE, EDITORIAL_AUTOMATION y VALIDATION. Sin migraciones ni nuevas dependencias. Riesgo: la IA todavía puede redactar mal o pasar por alto errores; la corrección acotada reduce rechazos evitables, pero no garantiza publicaciones diarias ni exactitud absoluta.


## Apertura pública — 22/10/2026

SITE_MAINTENANCE=false y Caddy recreado. Portada, artículo real, sitemap y cuenta: 200. HTTP: 308 a HTTPS; www: 301 al dominio principal. Chromium real a 390×844 sin desbordamiento horizontal; captura privada public-home-mobile.png. Aviso legal y privacidad mantienen borrador/noindex. Monitor foroia-health: Result=success. Servicios sanos; PostgreSQL y Redis sin puertos publicados. Registro y correo deshabilitados. Suite previa: 126 correctas; apertura comprobada mediante HTTP, navegador y monitor. No se han inventado identidad, testimonios ni credenciales. Pendientes: datos legales reales, SMTP y alertas externas.


## Dashboard privado — 23/10/2026

Implementados modelo DailyPageView, migración 0005_analytics, API interna de incremento y consulta editorial autorizada; plugin Nitro para contar cargas HTML y panel `/editorial/estadisticas`. Documentación en ANALYTICS.md. Sin dependencias nuevas ni cambios de DNS, SSH, firewall, SMTP o registro.

95 pruebas backend correctas, typecheck y build Docker correctos. Test del plugin: exclusión de bots, sesiones, rutas privadas, errores HTTP y peticiones no HTML; elimina parámetros y no transmite identificadores; un fallo de colección no interrumpe la lectura. Chromium real en producción: login administrador, dashboard, selector de 7 días, tabla diaria, teclado y móvil 390px sin desbordamiento. Una primera ejecución del guion falló por seleccionar un atributo type inexistente en el botón; corregido el selector por nombre accesible y repetido satisfactoriamente. No se crearon cargas ficticias en las estadísticas de producción.

Portada 200, panel sin sesión 302 a cuenta, API sin sesión 401, endpoint interno no expuesto por Nuxt (404). Compose API/web healthy, monitor Result=success y Alembic 0005_analytics head. Backup cifrado previo y posterior, código/configuración cifrados y copias fuera del VPS verificadas por SHA256; la restauración aislada anterior cubre 0004, no se ha repetido con 0005. DB/Redis permanecen sin puertos públicos. Logs y capturas privados en .local/deploy/analytics-*.

Límites: cargas HTML aproximadas, no usuarios únicos; navegación interna Vue sin recargar no cuenta y el filtro de bots no es absoluto. Sin datos históricos, Search Console ni ingresos conectados. Siguen pendientes SMTP, identificación legal real y alertas externas.


## Revisión SEO / rendimiento / seguridad / monetización — 23/10/2026

Cambios verificados en proyecto Docker aislado foroia-seo-review; producción sin actualizar. Suite Python: 97 correctas, 36 optativas omitidas; compileall correcto. Nuxt typecheck y build final correctos. Pruebas HTTP/Chromium sobre el entorno aislado: 2 correctas en última ejecución (21,13 s), con sitemap índice y todos sus archivos, SSR, 301, canonical, paginación, privacidad/consentimiento y móvil. Test del plugin de contadores correcto con rutas canónicas nuevas. Caddyfile validado sin cambiar Caddy de producción.

Auditoría pública: DNS @ y www a 146.59.35.127, HTTPS 200, HTTP 308, www 301; servicios sanos, monitor y backup activo. Investigación 22:30 Europe/Madrid y publicación condicionada, sin ejecuciones nuevas al auditar. No llamadas OpenAI en este bloque. pip-audit sin avisos conocidos; npm conserva 11 paquetes high por dos avisos raíz sin parche, no identificados entre los paquetes de la imagen final. No se afirma que la cadena de compilación esté libre de vulnerabilidades.

Laboratorio móvil: una muestra CPU ×4/red simulada con LCP 2320 ms, CLS 0, TTFB ~480 ms; no equivale a datos de campo ni acredita INP. Sin nuevos servicios externos, cambios de credenciales/DNS/SSH/firewall ni anuncios. Informe y pasos manuales completos en REVIEW_2026_10_23.md. Evidencia privada en .local/deploy/seo-*.


## Despliegue real SEO — 23/10/2026

Bloque aplicado tras verificar la restauración aislada de PostgreSQL (todas las tablas iguales), Redis y lectura completa de archivos cifrados. Datos existentes y production.env preservados. API/web/worker/Caddy actualizados, esquema 0005 sin cambios, salud correcta y 7 URLs canónicas del sitemap accesibles. 301, robots, SSR, seguridad y navegador/panel verificados. No fue necesario rollback. Investigación habilitada a las 22:30 Madrid, primer ciclo nocturno nuevo aún pendiente de observar. Informe completo en DEPLOYMENT_2026_10_23.md.
