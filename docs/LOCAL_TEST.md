# Pruebas locales y arranque reproducible

Verificación final: 21 de octubre de 2026. Entorno de desarrollo, sin despliegue público.

## Arrancar, comprobar y parar

Desde la raíz del proyecto en PowerShell:

```powershell
./scripts/local.ps1 Start -Toolbox
./scripts/local.ps1 Status -Toolbox
./scripts/local.ps1 Tests -Toolbox
./scripts/local.ps1 Browser -Toolbox
./scripts/local.ps1 Stop -Toolbox
```

Con Docker Desktop, omitir `-Toolbox`. `Stop` conserva los volúmenes. No usar `down -v` sobre el proyecto principal.

El script comprueba Compose 2.39.4 contra el SHA256 oficial, mantiene la instalación global y conserva `.env`. Si falta, genera secretos sin mostrarlos. En Toolbox reanuda la VM `default`, recupera su DNS NAT y abre solo los túneles loopback que falten (Docker 23762, web 3000, API 8000 y correo 8025). No detiene servicios ajenos ni borra la base existente. Las claves SSH cuyas rutas contengan espacios necesitan ajustar las comillas de Start-Process.

Los contenedores antiguos creados manualmente se conservaron detenidos como `foroia-api-before-accounts` y `foroia-web-before-accounts`. Hay una copia previa de PostgreSQL en `.local/foroia-before-accounts.dump`. No se ha probado restaurar esa copia y no debe describirse como backup de producción validado.

El esquema se actualiza con Alembic al arrancar la API; no ejecutar `db/schema.sql`. El arranque espera a PostgreSQL y Redis, y la web/trabajador esperan al healthcheck de la API. La cuenta administradora inicial se conserva si ya existe.

## Accesos

- Blog: http://localhost:3000
- Cuenta/login: http://localhost:3000/cuenta
- Panel: http://localhost:3000/editorial
- Moderación: http://localhost:3000/moderacion
- API: http://localhost:8000/docs
- Buzón de desarrollo: http://localhost:8025

Cuenta inicial: `BOOTSTRAP_EMAIL` (por defecto `editor@localhost.test`) y el valor privado `EDITORIAL_PASSWORD` de `.env`. No copiar credenciales en capturas, mensajes o incidencias. Registro/verificación/recuperación usan el buzón local, sin enviar correo al exterior.

## Pruebas

`Tests` prepara `.local/venv` desde `api/requirements-dev.txt` y activa las pruebas HTTP. `Browser` instala Chromium y activa también los recorridos de navegador. Se comprueban escritorio (1280×900), viewport móvil (390×844), navegación con teclado, contraste de botones, creación/revisión/publicación/archivo y el circuito de cuentas/comentarios.

Si la descarga de Chromium falla por certificados del equipo, aportar una cadena de confianza válida mediante `NODE_EXTRA_CA_CERTS`; no desactivar TLS. En esta sesión se exportaron las CA de confianza de Windows a `.local/windows-ca.pem` para permitir la descarga.

Las pruebas HTTP y de navegador se omiten por defecto en CI sin servicios arrancados. Para ejecutarlas directamente:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'api'
$env:FOROIA_LOCAL_HTTP = '1'
$env:FOROIA_BROWSER = '1'
./.local/venv/Scripts/python.exe -m pytest -q
Remove-Item Env:FOROIA_LOCAL_HTTP, Env:FOROIA_BROWSER
```

Las pruebas crean artículos identificados como pruebas y los archivan al terminar. El recorrido de registro crea cuentas técnicas `browser-…@localhost.test`, sin perfiles públicos ni datos de personas reales. Las capturas están en `.local/browser/`; no se guardan trazas de red ni contraseñas. No ejecutar estas pruebas con un dominio/SMTP de producción. Los límites Redis siguen activos; las repeticiones intensivas pueden devolver 429 legítimamente.

Comprobación adicional de Redis real:

```powershell
$env:DOCKER_HOST = 'tcp://127.0.0.1:23762'
Remove-Item Env:DOCKER_TLS_VERIFY -ErrorAction SilentlyContinue
$OutputEncoding = [Text.UTF8Encoding]::new($false)
Get-Content tests/redis_check.py -Raw -Encoding utf8 | ./.local/compose-v2.exe --tls exec -T api python -
```

## Base vacía y reinicio

```powershell
./scripts/verify-clean.ps1 -Toolbox
```

Arranca un proyecto aleatorio aislado sin publicar puertos, con las imágenes construidas por `Start`, PostgreSQL nuevo y secretos propios. Comprueba las cuatro migraciones hasta `0004_research`, categorías, blog vacío, SSR, bootstrap y reinicio. El trabajador de investigación arranca sin clave y sin gasto. Al terminar elimina únicamente los contenedores y volúmenes de ese proyecto temporal, sin tocar los del proyecto principal.

## Archivos y límites

Cambios de este bloque: migración `0003`, modelos, módulos de cuentas/comentarios, seguridad editorial, límites Redis y trabajador de correo; proxies y pantallas Nuxt de cuenta/moderación/comentarios; retirada de SWR del blog; Docker/Compose, scripts de arranque/verificación, lockfile y comprobación TypeScript; pruebas y documentación. Ver `docs/ACCOUNTS.md`.

Los resultados finales se registran en `docs/VALIDATION.md`. La auditoría de accesibilidad es funcional y visual, no una certificación WCAG completa. Faltan SMTP real, MFA, eliminación de cuentas, revisión de dependencias/seguridad, TLS y operación de producción. Investigación nocturna implementada: ver `docs/EDITORIAL_AUTOMATION.md`; requiere configurar la clave para generar artículos reales.

En este equipo el script admite también el binario PE `.local/compose-v2.bin` cuando no se puede escribir el nombre `.exe`: verifica el mismo checksum oficial y lo lanza mediante Python, sin desactivar protecciones del sistema. La comprobación aislada usa el mismo mecanismo.
