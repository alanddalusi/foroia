# Cuentas, comentarios y operación local

## Acceso y permisos

`/cuenta` permite registro, verificación de correo, login, logout y recuperación. Contraseñas Argon2id; sesiones de siete días, revocables y con tokens guardados como SHA-256. La cookie de sesión es HttpOnly/SameSite=Lax; una cookie CSRF legible se combina con el hash de la sesión y comprobación estricta de Origin. Al recuperar contraseña se revocan las sesiones. Los enlaces de un solo uso caducan (24 horas para verificación, 30 minutos para recuperación) y llevan el token en el fragmento para no incluirlo en los logs HTTP.

- Visitante: lectura pública de artículos y comentarios aprobados.
- Miembro con correo verificado: comentar; consultar, editar y retirar sus propios comentarios.
- Moderador: aprobar, rechazar y retirar comentarios.
- Editor: gestionar artículos y su publicación.
- Administrador: permisos editoriales y de moderación.

Los permisos se comprueban de nuevo en FastAPI, no solo en la interfaz o en Nuxt. La cuenta bloqueada no puede usar sus sesiones y sus comentarios no se muestran públicamente. Todo comentario nuevo o editado queda pendiente, incluso si procede de un administrador. Las acciones y decisiones se auditan con el ID del actor, sin copiar el texto ni el correo al registro de auditoría.

Cada decisión de moderación exige la versión que se mostró en la cola. Si el autor edita el comentario mientras se revisa, el servidor rechaza la decisión con 409 y exige volver a revisar; nunca se aprueba silenciosamente un texto distinto.

## Administración por operador

Arrancar con `scripts/local.ps1`; `bootstrap` crea un administrador local desde las variables de entorno y no altera una cuenta existente. Su contraseña es el valor local `EDITORIAL_PASSWORD`; el email, `BOOTSTRAP_EMAIL` o `editor@localhost.test`. No publicar estas variables ni la copia local de la DB.

Para cambiar roles o bloquear una cuenta desde una terminal autorizada:

```text
docker compose exec api python -m app.manage role CORREO moderator
docker compose exec api python -m app.manage block CORREO
docker compose exec api python -m app.manage unblock CORREO
```

Con Toolbox, usar `.local/compose-v2.exe --tls` después de configurar el entorno mediante `scripts/local.ps1 Status -Toolbox`. Los comandos de operador requieren acceso administrativo al servidor. No existe una ruta pública para asignarse roles. Evitar retirar los permisos de la última cuenta administradora sin disponer de acceso al operador.

`LEGACY_EDITORIAL_ENABLED=false` en Compose y por defecto. La compatibilidad por token del antiguo panel solo se habilita en pruebas aisladas; la web ya no admite Basic Auth. El token interno permanece exclusivamente en los servidores.

## Comentarios y paginación

Texto plano de 1 a 5.000 caracteres, escapado por Vue; sin HTML ejecutable. El autor se obtiene de la sesión. Se rechaza un duplicado exacto del último comentario del autor en el artículo. Solo se escribe en artículos publicados con comentarios habilitados. El panel permite cerrar nuevas aportaciones; las ya aprobadas siguen siendo legibles.

Índices por artículo/estado/fecha/ID, autor/fecha/ID y estado/fecha/ID. Páginas de 20 elementos (máximo 50 en lectura pública), cursores por fecha e ID, consultas limitadas y joins para evitar N+1. Los pendientes nunca aparecen en la lectura pública. Archivar el artículo también oculta sus comentarios; las rutas del blog y los comentarios no se cachean.

## Redis y protección de acceso

Contadores compartidos con incremento y caducidad atómicos mediante Lua. Redis no almacena contraseñas ni tokens de sesión. Las claves de límites usan hashes de la identidad y caducan automáticamente. No se confía en X-Forwarded-For del cliente; solo el proxy interno autenticado puede transmitir la IP. Si falla Redis, las escrituras protegidas devuelven 503.

Valores iniciales: login 30 intentos/IP y 10/cuenta cada 15 minutos; registro 10/IP por hora; recuperación/reenvío 10/IP y 3/cuenta por hora; comentarios 10/usuario y 30/IP cada cinco minutos; edición/retirada 20/usuario cada cinco minutos; operaciones editoriales y de moderación 120/usuario cada cinco minutos. Se limitan intentos totales, no solo fallos. No borrar contadores para eludir un bloqueo; esperar el plazo o utilizar una identidad aislada de pruebas.

## Correo

Compose es **solo de desarrollo**: Mailpit recibe el correo dentro de la red Docker y su interfaz se publica únicamente en `127.0.0.1:8025`. No se envían mensajes a proveedores externos. `mail-worker` procesa la bandeja transaccional en PostgreSQL y reintenta si SMTP falla. Los cuerpos enviados se borran y el buzón transaccional se limpia al día; también se purgan sesiones/tokens caducados. El buzón Mailpit de desarrollo conserva los mensajes hasta su limpieza o recreación y no debe usarse para correos personales reales.

Para producción, sustituir Mailpit por SMTP autorizado, configurar `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_STARTTLS=true`, y credenciales únicamente por variables de entorno. El trabajador usa STARTTLS con validación de certificados; no expone los errores SMTP ni direcciones en logs. Revisar entrega, reputación y políticas de retención antes de habilitar registros reales. La cola puede entregar duplicados si un proceso cae después de enviar pero antes de confirmar la transacción; los tokens siguen siendo de un solo uso.

## Alcance de seguridad

Antes de producción: HTTPS y `COOKIE_SECURE=true`, `SITE_URL` canónica, proxy de confianza para que los límites no agrupen a todos los usuarios, SMTP real, backups/restauración, cabeceras, monitorización, dependencia/imagen auditadas, políticas de privacidad y retención. No hay MFA ni borrado de cuenta de autoservicio todavía. No se habilitan anuncios ni investigación nocturna en este bloque.

Referencias: [patrón de límites de Redis](https://redis.io/docs/latest/commands/incr/), [typecheck de Nuxt](https://nuxt.com/docs/api/commands/typecheck), [versiones de Mailpit](https://github.com/axllent/mailpit/releases).
