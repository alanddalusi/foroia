# Foro IA al Día: diagnóstico y despliegue

Estado vigente (22/10/2026): blog abierto para lectura en https://foroiaaldia.com (HTTP 200). Mantenimiento desactivado por instrucción expresa del propietario. Registro y correo automático deshabilitados; aviso legal y privacidad siguen como borradores pendientes de datos reales. Investigación activa con presupuesto de 5 USD/mes. Las referencias posteriores a mantenimiento describen la preparación anterior.


Estado del 22/10/2026: **DNS y HTTPS operativos; sitio público en mantenimiento intencional (503/noindex)**. Caddy, Nuxt, FastAPI, PostgreSQL y Redis funcionan. Ambos nombres resuelven al VPS y tienen certificados de Let's Encrypt; HTTP redirige a HTTPS y www al dominio principal. Los capítulos siguientes conservan los procedimientos reproducibles de instalación y operación; la evidencia actual está en `docs/VALIDATION.md`. Retirar mantenimiento requiere completar los pendientes de lanzamiento, manteniendo el registro cerrado hasta probar SMTP.

Último bloque verificado: **126 pruebas correctas**; marca y footer definitivos, páginas SSR informativas, categorías vacías fuera del sitemap, altas/recuperación/reenvío bloqueados coherentemente en API e interfaz cuando no hay correo. Investigación activa en el VPS, trabajador local detenido y clave retirada de su `.env`. Se importaron 0,157429 USD de reserva histórica con auditoría; no hay reinicio de presupuesto ni otra ejecución para el mismo día. Primer turno nuevo esperado: 23/10/2026 a las 22:30 Europe/Madrid. Monitor local cada cinco minutos y backup diario activos; copia cifrada actualizada fuera del VPS, aún manual. Ver [correo transaccional](docs/TRANSACTIONAL_EMAIL.md) para Brevo/Resend y prueba sin secretos.

Para abrir: completar privadamente `LEGAL_NAME`, `LEGAL_ADDRESS` y `LEGAL_TAX_ID` con datos reales autorizados y revisar los textos, que actualmente se identifican como borradores. No son decisiones de diseño ni se pueden inventar; no se han tomado de la factura. Para activar las cuentas, además hace falta crear/controlar una cuenta SMTP real, autenticar el remitente y confirmar recepción. La redirección `admin@foroiaaldia.com` no entrega credenciales SMTP. No se han contratado servicios adicionales ni enviado mensajes de prueba sin ellas.

## 1. Diagnóstico técnico

| Área | Comprobado en el código | Pendiente o límite |
| --- | --- | --- |
| Frontend | Nuxt 4.6.2, Vue 3.5.44, TypeScript 5.9.3; SSR público; Node 22 en Docker; marca Foro IA al Día | Sin búsqueda interna ni imágenes OG propias |
| Backend | Python 3.12 en Docker; FastAPI 0.149.0, Pydantic 2.14.1, SQLAlchemy 2.1.5 asíncrono, asyncpg 0.32.0 | Revisión de vulnerabilidades y límites bajo carga real pendientes |
| Datos | PostgreSQL 17; Alembic 1.20.0; cuatro migraciones, última `0004_research` | No importar íntegra la base local: contiene datos de pruebas |
| Redis | Servidor Redis 7, cliente Python 6.4.0; límites atómicos, bloqueo y heartbeat de investigación | Monitorización externa y alertas aún sin configurar; no es una cola de correo |
| Cuentas | Argon2id, sesiones opacas con hashes, roles, verificación y recuperación por email, CSRF; comentarios moderados | SMTP real, pruebas de entrega y endurecimiento operativo antes de abrir registro |
| Foro | Categorías y temas publicados de solo lectura | No hay creación/respuestas del foro para miembros |
| Investigación | Fuentes permitidas OpenAI/Hugging Face/Google, principalmente inglés; redacción española y revisión OpenAI; una corrección automática acotada | No rastrea toda la web ni LinkedIn; las fuentes pueden fallar; un artículo aprobado local necesitó intervención del operador |
| Programación | Proceso continuo `research-worker`, hora 22:30 Europe/Madrid; fecha editorial única y reservas persistidas antes de llamadas | No confundir con cron ni garantizar publicación diaria; conciliar gasto previo y apagar trabajador local antes de activar producción |
| Correo | `mail-worker` lee outbox PostgreSQL; SMTP con STARTTLS configurable | Mailpit solo sirve para desarrollo; no hay proveedor transaccional de producción verificado |
| Archivos | Portadas originales WebP/PNG en `article_assets` y metadatos en `articles.media`; sin subidas arbitrarias ni S3 | Los backups PostgreSQL incluyen los medios; respaldar configuración y secretos por separado. Ver `docs/MULTIMEDIA_2026_10_28.md` |
| SEO | Canonical, metadatos, JSON-LD escapado, robots, sitemap y noindex privados; categorías vacías noindex y fuera del sitemap | Sitemap del foro limitado a 50 temas; no hay RSS, Search Console ni CWV medidos en producción |
| Contenedores | Dockerfiles, lock npm y constraints Python; usuarios no root en API/web | Algunas etiquetas base aún flotantes; registrar/pinar los digests del release y revisar dependencias antes de abrir |
| Producción | Compose, Caddy/Let's Encrypt, DNS, redirecciones, volúmenes, reinicio y servicios verificados; DB/Redis/API/web sin puertos públicos | Mantenimiento 503 activo; faltan requisitos de lanzamiento y funciones dependientes de SMTP |
| Recuperación | Backup diario age, restauraciones aisladas comprobadas, copia externa manual y monitor local | Faltan replicación externa automática, retención y alertas externas |
| Pruebas | pytest, HTTP y Playwright; CI separada backend/frontend; último resultado completo: 126 correctas y verificaciones reales del VPS | SMTP sin probar y datos del titular pendientes; no acredita revisión jurídica ni seguridad absoluta |

La aplicación no usa Next.js. No necesita GPU: las llamadas de generación se ejecutan en OpenAI, no en el VPS. PostgreSQL y Redis sí son necesarios para esta arquitectura.

Inventario principal: `web/`, `api/app/core/`, `api/app/modules/`, `api/app/research/`, `api/alembic/`, `tests/`, `deploy/`, `scripts/`, `.github/workflows/`. `db/schema.sql` es histórico: no ejecutarlo manualmente para instalar producción.

## 2. Estado de la infraestructura

Comprobado por SSH desde este equipo: Ubuntu 26.04 amd64 y sudo no interactivo. Docker Engine 29.9.2, Compose 5.6.1, containerd 2.4.2 y Buildx 0.38.1 instalados desde el repositorio oficial; hello-world correcto. Instalación sin eliminar paquetes ni ejecutar upgrade del sistema. UFW conserva TCP 22/80/443; no se ha editado SSH. Arrancar Docker crea sus propias reglas de red, tal como se había descrito al propietario. Los servicios de la aplicación no publican puertos; las comprobaciones TCP externas de 5432/6379/8000/3000 no consiguieron conexión.

Destino: `146.59.35.127`, VPS `vps-e3e9b9c5.vps.ovh.net`. Aplicación en `/opt/foroia`, configuración nueva de producción en `production.env` (root, 600), sin copiar usuarios de pruebas. Administrador acordado y artículo aprobado transferidos. SMTP sin configurar, registro cerrado e investigación sin activar. El propietario actualizó DNS: @ y www apuntan al VPS; HTTPS y redirecciones están verificados. Caddy devuelve mantenimiento 503/noindex. MX/SPF conservados; no se han modificado DNS desde este equipo. Quedan dos TXT de aparcamiento OVHcloud que actualmente no interfieren con la web; no confundirlos con SPF al limpiarlos.

## 3. Acceso SSH ya comprobado; conservar recuperación

El acceso por clave ya funciona desde este equipo con la identidad predeterminada de Windows. No reemplazarla por la clave dedicada si no está autorizada. Mantener una sesión alternativa y no modificar UFW ni desactivar contraseñas. Para verificar la huella por un canal independiente, desde la consola del proveedor:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compararla con la huella registrada por primer contacto en el equipo del operador. La clave pública dedicada está en `.local/deploy/foroia-vps.pub` en este equipo; añadir **solo su contenido público** a `/home/ubuntu/.ssh/authorized_keys`, conservando las claves anteriores. Directorio 700, archivo 600, propietario `ubuntu`. No enviar claves privadas ni contraseñas por chat.

Desde Windows verificar una nueva sesión:

```powershell
ssh -i .local/deploy/foroia-vps -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=.local/deploy/known_hosts ubuntu@146.59.35.127
```

No aceptar silenciosamente una huella cambiada. Verificar desde la consola del proveedor si ocurre. No desactivar la contraseña hasta comprobar dos accesos por clave y disponer de recuperación del proveedor.

## 4. Terminar Docker, después de obtener acceso

Procedimiento basado en [Docker Engine para Ubuntu](https://docs.docker.com/engine/install/ubuntu/), que admite Ubuntu 26.04. En la sesión SSH:

```sh
cat /etc/os-release
dpkg --print-architecture
command -v docker || true
ls -l /etc/apt/keyrings/docker.asc
sudo grep -R -n 'download.docker.com' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null || true
```

Si ya hay un repositorio Docker, revisarlo y conservarlo; no crear una entrada duplicada ni sobrescribirlo. Si no existe ninguna entrada, para este Ubuntu:

```sh
sudo test -s /etc/apt/keyrings/docker.asc
. /etc/os-release
printf '%s\n' \
  'Types: deb' \
  'URIs: https://download.docker.com/linux/ubuntu' \
  "Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}" \
  'Components: stable' \
  "Architectures: $(dpkg --print-architecture)" \
  'Signed-By: /etc/apt/keyrings/docker.asc' \
  | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
sudo apt update
apt-cache policy docker-ce docker-compose-plugin
```

Comprobar candidatos disponibles. Si aparece `Candidate: (none)` o error de firma/repositorio, detenerse y diagnosticar; no cambiar a un repositorio de otra versión de Ubuntu ni usar un script remoto improvisado. Con candidatos válidos:

```sh
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin age
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
sudo ufw status verbose
```

No se necesita añadir al usuario al grupo Docker: usar `sudo`; pertenecer a ese grupo equivale prácticamente a root. No exponer el daemon Docker por TCP. Solo Caddy debe publicar puertos; publicar PostgreSQL/Redis y confiar en UFW no es suficiente.

## 5. Instalar y verificar en mantenimiento

Decisión de correo: `admin@foroiaaldia.com` será una redirección al correo personal del propietario, no un buzón SMTP. MX Plan Redirect no debe usarse como credencial de envío. La plantilla fija el correo de bootstrap a esa dirección, deja SMTP vacío y mantiene `REGISTRATION_ENABLED=false`. Verificar que la redirección recibe mensajes y proteger la contraseña administrativa: la recuperación no funcionará sin proveedor transaccional probado. La API rechaza registros con 503 antes de crear cuentas o correos mientras el indicador esté desactivado, sin impedir login de cuentas existentes. Habilitarlo requiere configurar SMTP, probar entrega de verificación/recuperación y recrear la API.

Instrucciones de variables, DNS, aislamiento, presupuesto, backups y apertura en [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). No copiar `.env` ni `.local/`, claves SSH, bases locales, cachés o usuarios de pruebas al VPS. Revisar el paquete antes de transferirlo. Conservar una copia del release anterior fuera del árbol que se vaya a actualizar.

Colocar código en `/opt/foroia` y crear `production.env` con permisos 600 desde `deploy/production.env.example`. No hay secretos válidos por defecto. Configurar PostgreSQL y su URL con la misma contraseña nueva, token interno, correo admin, contraseña de bootstrap y SMTP real. Guardar credenciales en un gestor seguro. Mantener `SITE_MAINTENANCE=true`, `OPENAI_API_KEY` vacío y perfil research desactivado.

```sh
cd /opt/foroia
sudo docker compose --env-file production.env -f compose.production.yml config -q
sudo docker compose --env-file production.env -f compose.production.yml up --build -d --wait
sudo docker compose --env-file production.env -f compose.production.yml exec -T api alembic current
sudo docker compose --env-file production.env -f compose.production.yml exec -T api python -m app.manage bootstrap
sudo docker compose --env-file production.env -f compose.production.yml ps
sudo docker compose --env-file production.env -f compose.production.yml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status)"
sudo docker compose --env-file production.env -f compose.production.yml exec -T web node -e "fetch('http://127.0.0.1:3000/').then(r=>{console.log(r.status);if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
```

La API aplica migraciones Alembic al iniciar, con una sola réplica. Debe mostrar `0004_research`. No usar create_all ni SQL manual. No ejecutar `config` sin `-q` en una salida compartida: expande secretos.

Tras verificar aplicación interna, configurar A de `@` al VPS y CNAME www al dominio, conservando correo/TXT/DNSSEC. No dejar un AAAA ajeno. Caddy emitirá certificados automáticamente cuando ambos nombres y los puertos funcionen; la web seguirá en mantenimiento. Comprobar:

```sh
curl -I http://foroiaaldia.com
curl -I https://foroiaaldia.com
curl -I https://www.foroiaaldia.com
```

Esperado: HTTP redirige a HTTPS, certificado válido, dominio principal 503/noindex durante mantenimiento y www redirige al principal. HSTS solo después de confirmar HTTPS definitivo. No cargar anuncios todavía.

## 6. Comprobaciones antes del lanzamiento

Preparar acceso privado de pruebas antes de quitar mantenimiento global. Verificar frontend y panel, creación/revisión/publicación/archivo, permisos, móvil/teclado, registro/email/recuperación, cookies Secure y CSRF, moderación, rate limiting por IP real y persistencia tras reinicio. No introducir cuentas o debates falsos.

Resolver categorías vacías/noindex y sitemap del foro, verificar canonical/JSON-LD/404 en el dominio real, límites y retirada inmediata, revisar vulnerabilidades y contenido legal/contacto con el titular. Medir rendimiento, no asumir CWV ni indexación por haber pasado pruebas locales.

Ejecutar backup cifrado, copiar fuera del VPS y probar restauración aislada. Instalar programación, retención y alertas de fallo, salud HTTP, espacio y trabajadores. Hasta entonces mantener mantenimiento. No hay aún un servicio de alertas instalado.

Una vez verificado lo anterior y autorizada la apertura, cambiar `SITE_MAINTENANCE=false` y recrear Caddy:

```sh
sudo docker compose --env-file production.env -f compose.production.yml up -d --force-recreate caddy
```

Antes de activar investigación: apagar el trabajador local, conservar reservas del mes o reducir el saldo de presupuesto disponible, configurar la clave de OpenAI de forma privada y verificar fuentes/tarifas. Después activar el perfil, observando un ciclo sin forzar aprobación ni reiniciar contadores:

```sh
sudo docker compose --env-file production.env -f compose.production.yml --profile research up -d research-worker
```

Ver resultado en `/editorial/investigacion`. No ejecutar repetidamente pruebas facturables ni aumentar el límite mensual autorizado de 5 USD. La selección de fuentes, citas y revisión reducen errores; no garantizan que la IA nunca se equivoque.

## 7. Actualizar y recuperar

Antes de actualizar: comprobar disco, guardar release/configuración previos y obtener backup cifrado externo. Subir un release revisado sin sobrescribir `production.env`; conservar permisos. Construir imágenes, aplicar migraciones mediante el arranque y ejecutar `up -d --wait` como arriba. Registrar versiones y repetir comprobaciones. No descargar paquetes ni cambiar tarifas automáticamente sin revisión.

Si falla una versión sin cambio de esquema, recuperar los archivos/imágenes del release anterior y recrear servicios con el mismo proyecto Compose. Si hubo migración incompatible, detenerse y planificar recuperación con el backup: volver solo al código anterior puede no ser suficiente. No ejecutar downgrade ni restaurar sobre producción automáticamente.

Scripts preparados:

```sh
sudo bash deploy/backup.sh
sudo bash deploy/restore-check.sh /ruta/backup.dump.age /ruta/identidad.age
```

El segundo restaura únicamente en un contenedor efímero sin red; no sustituye una recuperación de producción. Identidades privadas y dumps descifrados no deben quedarse en el VPS. La restauración de emergencia exige confirmar punto de recuperación, parar escrituras y preservar la base actual antes de reemplazar datos. Nunca ejecutar `docker compose down -v` para actualizar o diagnosticar.

## 8. Evidencia de esta revisión

La suite completa previa al documento: 122 correctas, TypeScript/build Nuxt y validación de Caddy correctos, según [docs/VALIDATION.md](docs/VALIDATION.md). Esta revisión añade diagnóstico y exclusiones de archivos sensibles/cachés en contextos Docker; no altera tablas ni lógica de la aplicación. Las operaciones remotas de instalación y las pruebas de producción siguen pendientes. No se ha cambiado el firewall, desactivado SSH por contraseña ni editado DNS.


Revisión preparada el 23/10/2026: mejoras SEO, rendimiento, consentimiento y cabeceras probadas en un entorno aislado, aún sin aplicar a la web pública. Ver auditoría y pasos de despliegue en [docs/REVIEW_2026_10_23.md](docs/REVIEW_2026_10_23.md).


Actualización 23/10/2026: bloque SEO desplegado y verificado; resultado en [docs/DEPLOYMENT_2026_10_23.md](docs/DEPLOYMENT_2026_10_23.md). Las referencias anteriores a preparación son históricas.
