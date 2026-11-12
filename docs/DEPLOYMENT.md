# Despliegue de Foro IA al Día

Estado vigente (22/10/2026): blog abierto para lectura en https://foroiaaldia.com (HTTP 200). Mantenimiento desactivado por instrucción expresa del propietario. Registro y correo automático deshabilitados; aviso legal y privacidad siguen como borradores pendientes de datos reales. Investigación activa con presupuesto de 5 USD/mes. Las referencias posteriores a mantenimiento describen la preparación anterior.


Destino autorizado por el propietario: Ubuntu 26.04, VPS OVHcloud 4 vCPU/8 GB/75 GB en Varsovia, dominio `foroiaaldia.com`. Estado del 22/10/2026: **DNS y HTTPS operativos; mantenimiento 503/noindex activo**. El propietario actualizó A de @ y www al VPS; se comprobaron localmente, contra DNS autoritativo y desde el servidor. Caddy está arrancado y emitió certificados Let's Encrypt para ambos nombres, válidos hasta el 20/01/2027 y gestionados automáticamente con volúmenes persistentes. HTTP redirige a HTTPS; www redirige al dominio principal preservando ruta y parámetros. Puertos públicos 80/443 comprobados; DB, Redis, API, Nuxt y administrador Caddy no accesibles públicamente. No se ha editado UFW, SSH ni registros DNS desde este equipo. Registro cerrado, SMTP sin configurar y perfil research inactivo.

Persisten TXT de aparcamiento OVHcloud `1|www.foroiaaldia.com` (@) y `3|welcome` (www). No producen redirecciones HTTP mientras A apunta al VPS; las respuestas se han comprobado desde el navegador y el servidor. Se pueden retirar posteriormente esos dos TXT concretos desde OVHcloud, conservando SPF y todos los registros del correo. No se ha borrado ninguno.

## Acceso y DNS

1. Verificar la huella SSH desde la consola del proveedor (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) antes de aceptar la clave del servidor. Autorizar únicamente la clave pública de despliegue; nunca enviar contraseñas ni claves privadas por chat. La clave dedicada local queda en `.local/deploy/foroia-vps`, fuera del repositorio versionable. No desactivar SSH por contraseña hasta comprobar una segunda sesión por clave y acceso de recuperación.
2. En la zona DNS de OVHcloud, cambiar el A de `@` a la IPv4 del VPS y `www` a un CNAME de `foroiaaldia.com.`. Revisar registros AAAA: no dejar IPv6 apuntando a otro servidor. Conservar MX/TXT de correo, SPF/DKIM/DMARC y DNSSEC. No cambiar nameservers innecesariamente.
3. Permitir TCP 22/80/443 y UDP 443, incluyendo el firewall de OVHcloud si está habilitado. PostgreSQL, Redis, API, Nuxt y Docker no publican puertos. Solo Caddy publica 80/443; no confiar únicamente en UFW para proteger puertos publicados por Docker.

## Preparación del servidor

Correo administrativo acordado: `admin@foroiaaldia.com`, mediante redirección de OVHcloud al correo personal del titular. Según el propietario, MX Plan es de tipo Redirect, sin buzones: no proporciona credenciales SMTP de envío. Crear/comprobar esa redirección y su recepción es independiente del SMTP transaccional. La plantilla deja `SMTP_HOST`, `SMTP_USER` y `SMTP_PASSWORD` vacíos. `REGISTRATION_ENABLED=false` bloquea altas en la API de producción, incluso aunque se retire el mantenimiento. El login de cuentas existentes y el bootstrap administrativo siguen disponibles. No activar altas hasta probar verificación y recuperación con un proveedor de envío real.

Actualizar Ubuntu e instalar Docker Engine con su repositorio oficial y plugin Compose; instrucciones oficiales: <https://docs.docker.com/engine/install/ubuntu/>. Instalar también `age` para backups. Registrar versiones e imágenes/digests usados. Aplicar actualizaciones de seguridad y configurar alertas de disco, salud HTTP, backups y trabajadores antes de abrir la web.

Subir únicamente código y configuración revisada a `/opt/foroia`; excluir `.local/`, `.env`, claves, bases locales, node_modules y cachés. Mantener propietario/permisos restringidos. Crear `production.env` desde `deploy/production.env.example` con permisos 600 y contraseñas nuevas. No copiar credenciales locales.

- PostgreSQL: generar una contraseña hexadecimal de al menos 32 bytes; usar exactamente la misma en `POSTGRES_PASSWORD` y `DATABASE_URL`.
- Token interno y contraseña admin: nuevos valores aleatorios; correo administrador controlado por el propietario. Guardarlos en un gestor de contraseñas.
- Correo: servidor SMTP real STARTTLS 587, credenciales y remitente autorizados. No asumir que el correo incluido permite envío automático ilimitado. Verificar límites y entrega de verificación/recuperación con SPF/DKIM/DMARC.
- `SITE_MAINTENANCE=true`: devuelve 503/noindex; es la configuración inicial. No abrir al público hasta completar las comprobaciones. Caddy gestiona HTTPS cuando el DNS y los puertos funcionan.
- `OPENAI_API_KEY` vacío y perfil `research` sin activar inicialmente. No arrancar dos automatizaciones independientes que puedan sumar presupuestos. Desactivar el trabajador local y trasladar las reservas del mes con una importación auditada, o reducir el presupuesto restante antes de activar producción. No reiniciar el historial económico para recuperar presupuesto.

```sh
cd /opt/foroia
docker compose --env-file production.env -f compose.production.yml config -q
docker compose --env-file production.env -f compose.production.yml up --build -d --wait
docker compose --env-file production.env -f compose.production.yml exec -T api python -m app.manage bootstrap
```

No usar `docker compose config` sin `-q` en logs porque expande secretos. No exponer Mailpit ni importar usuarios, sesiones o contenido de pruebas. El artículo local aprobado requiere transferencia selectiva de contenido con auditoría, no restaurar toda la base local.

## Backups y restauración

Crear una identidad age en un equipo seguro externo y guardar su copia privada de recuperación. Instalar únicamente el destinatario público en `/etc/foroia/backup-recipients.txt`. `deploy/backup.sh` genera un dump PostgreSQL cifrado en `/var/backups/foroia`, con permisos privados y error si falla cualquier fase. Copiarlo a otro equipo/almacenamiento; el backup en el mismo VPS no cubre la pérdida del servidor. Definir retención, automatizar y alertar ante fallos.

Probar con `deploy/restore-check.sh BACKUP.dump.age IDENTIDAD.age`: descifra y restaura en un PostgreSQL desechable sin red, verifica migraciones y lectura de artículos, y elimina solo ese contenedor con su volumen. La identidad de prueba debe retirarse del VPS después. No escribir sobre la base de producción para hacer esta prueba. Respaldar por separado `production.env` y configuración del despliegue en un almacén cifrado seguro.

**Ejecutado el 22/10/2026**: backup cifrado y dos restauraciones aisladas correctas; la segunda recupera el artículo transferido y migración `0004_research`. Una copia cifrada está fuera del VPS en `.local/deploy/postgres-offsite.age`; SHA256 contrastado con el original. La identidad privada de recuperación se guardó fuera del VPS con ACL restringida y se retiró la copia temporal del servidor tras comparar sus huellas. Conservar esa identidad en un gestor/almacén seguro: sin ella no se podrá descifrar.

Timer `foroia-backup.timer` instalado y activo: 03:15 UTC cada día, con hasta cinco minutos de dispersión. Unidad `foroia-backup.service` ejecutada correctamente. Los originales están en `deploy/foroia-backup.service` y `deploy/foroia-backup.timer`. Comprobar con `systemctl list-timers foroia-backup.timer` y `journalctl -u foroia-backup.service`. La copia externa realizada es manual; **faltan replicación externa automática, retención y alertas**. No considerar completo el plan de continuidad hasta configurarlas.

## Antes de abrir al público

Implementado y verificado el 22/10/2026: identidad visual Foro IA al Día; páginas `/informacion/contacto`, `/informacion/criterio-editorial`, `/informacion/normas`, `/informacion/cookies`, `/informacion/aviso-legal` y `/informacion/privacidad`. Aviso legal y privacidad tienen aviso de preparación/noindex hasta completar y revisar los datos reales del responsable. Campos `LEGAL_NAME`, `LEGAL_ADDRESS`, `LEGAL_TAX_ID` en `production.env`; son datos destinados a publicación, no poner una marca como si identificara una entidad inexistente. No se publicaron datos de factura. Fuentes de referencia: [LSSI art. 10](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758#a10) y [AEPD](https://www.aepd.es/derechos-y-deberes/ejerce-tus-derechos). Estos borradores no acreditan revisión jurídica ni cumplimiento final.

`ACCOUNT_EMAIL_ENABLED=false` bloquea también recuperación/reenvío en servidor y oculta acciones sin servicio en la interfaz; `REGISTRATION_ENABLED=false` sigue cerrando altas. SMTP configurable por host, puerto, STARTTLS, login, clave y remitente, con CLI `python -m app.mail_worker --test` que solo envía al correo administrativo tras disponer de credenciales y STARTTLS. Actualmente no se envía. Guía: `TRANSACTIONAL_EMAIL.md`.

Investigación: clave y reservas trasladadas al VPS; trabajador local detenido y `.env` local sin clave. Reserva histórica de 0,157429 USD importada con auditoría y fecha única; máximo mensual sigue 5 USD. No se ejecutó otra redacción al migrar; se comprobó heartbeat y acceso HTTP 200 al modelo. La próxima fecha nueva es el 23/10/2026 a las 22:30 Europe/Madrid. No reactivar el trabajador local con otra clave/presupuesto independiente.

`foroia-health.timer` comprueba cada cinco minutos salud de contenedores, respuesta HTTPS esperada (503 durante mantenimiento) y existencia de backup PostgreSQL cifrado de menos de 48 horas. Resultado actual success; fallos en journal. No manda alertas externas aún. Soporta finales de línea Windows en `production.env`. Ver `journalctl -u foroia-health.service` y `systemctl list-timers foroia-health.timer`.

Copia externa manual actualizada de PostgreSQL y código/configuración cifrados en `.local/deploy/launch-postgres.age` y `launch-code-config.age`; SHA256 comprobados contra el VPS. La identidad privada de recuperación permanece fuera del VPS. Siguen pendientes la replicación externa automática y su política de retención/alertas.

- HTTPS válido y redirección www a dominio canónico; añadir HSTS después de validar la configuración definitiva. Revisar CSP con Nuxt y comprobar que no rompe hidratación ni panel.
- Registro/verificación/cambio de contraseña, permisos, CSRF y cookies Secure; rate limits por IP real a través de Caddy. Nuxt solo confía en `X-ForoIA-Client-IP` cuando la opción privada está activada y Caddy sobrescribe esa cabecera. Nunca publicar Nuxt directamente con esa opción.
- Revisión de dependencias e imágenes, monitorización/alertas, backup externo y restauración probada.
- Información legal, privacidad, cookies y contacto revisados por el titular; no añadir publicidad ni analítica no esencial antes del consentimiento/aprobación necesarios.
- Contenido público real, sitemap/canonical del dominio, 404 y retirada inmediata; ningún contenido o cuenta de prueba en producción.
- Registrar comprobaciones reales y ruta de rollback en `VALIDATION.md`. Conservar release anterior y backup previo a migraciones; no borrar volúmenes ni ejecutar `down -v`.

Solo después desactivar mantenimiento (`SITE_MAINTENANCE=false`) y recrear Caddy. Activar el perfil research con presupuesto reconciliado y observar un ciclo real. La investigación está programada a las 22:30 Europe/Madrid; el VPS encendido sustituye al ordenador local.


Revisión preparada el 23/10/2026: mejoras SEO, rendimiento, consentimiento y cabeceras probadas en un entorno aislado, aún sin aplicar a la web pública. Ver auditoría y pasos de despliegue en [REVIEW_2026_10_23.md](REVIEW_2026_10_23.md).


Actualización 23/10/2026: bloque SEO desplegado y verificado; resultado en [DEPLOYMENT_2026_10_23.md](DEPLOYMENT_2026_10_23.md). Las referencias anteriores a preparación son históricas.
