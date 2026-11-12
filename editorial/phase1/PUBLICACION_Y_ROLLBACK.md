# Publicación preparada: tres guías y correcciones web

Estado actualizado: publicación y despliegue autorizados y completados el 23/10/2026, con respaldo nuevo y restauración aislada verificados antes del cambio. Resultado en ../../docs/DEPLOYMENT_EDITORIAL_PHASE1_2026_10_23.md. El procedimiento siguiente se conserva como registro de preparación. No hubo migraciones ni cambios de API, credenciales, DNS, correo o presupuesto; solo se recreó web.

## Paquete revisable

- publication.json contiene tres ArticleWrite válidos: título, slug, resumen usado como metadescripción, cuerpo, sección, firma editorial con asistencia de IA y fuentes estructuradas. No contiene IDs, contraseñas ni fechas de publicación inventadas.
- prepare_release.py genera el paquete sin conexión a servicios. Elimina el encabezado H1 duplicado y las notas de estado internas; convierte enlaces de revisión en rutas públicas.
- Recursos públicos preparados en web/public/recursos/guias-pdf/: dos PDFs sintéticos, script y generador propios. Hashes en resource-checksums.json.
- Enlaces renderizados como nodos Vue escapados, sin v-html: rutas locales absolutas y HTTPS; rechazo de esquemas activos, credenciales en URL, rutas relativas ambiguas, barras inversas y caracteres de control. Código en línea y bloques no interpretan enlaces.

## Orden después de la autorización

1. Repetir inventario público y comprobar en el panel todos los estados para detectar colisiones de título, resumen o slug, incluidos borradores nocturnos recientes. No sobrescribir ni renombrar contenido existente. Las tres URLs devolvieron 404 en esta revisión; eso no demuestra ausencia de un borrador privado homónimo.
2. Crear un checkpoint nuevo y privado, siguiendo DEPLOYMENT.md y docs/DEPLOYMENT_2026_10_23.md. Registrar etiquetas/digests de imágenes actuales y checksum del código y production.env sin mostrar contenido. No reutilizar el rollback de una versión anterior como si fuera el de esta entrega.
3. Ejecutar deploy/backup.sh para PostgreSQL; copiar el cifrado fuera del VPS. Respaldar asimismo Redis, código/configuración y volúmenes de Caddy con age como en el procedimiento anterior. La clave privada sigue fuera del servidor.
4. Restaurar ese backup NUEVO en PostgreSQL desechable sin red y comparar recuentos y huellas de todas las tablas. Comprobar Redis con redis-check-rdb y restauración aislada; validar lectura de los archivos cifrados. Si falta una copia o la restauración no coincide, detener el despliegue. No se afirma que esta copia nueva exista ya.
5. Construir web con los cambios GA4/navegación y ArticleInline/ArticleBody, recursos y privacidad. No sustituir production.env ni volúmenes. Validar Compose y usar `docker compose --env-file production.env -f compose.production.yml up -d --no-deps web`. Esperar salud y probar primero la navegación y consentimiento sin publicar nada.
6. Crear las tres piezas como borradores mediante el panel autenticado y la API editorial existente, preservando sesión/CSRF/roles. Guardar los IDs y cuerpos de respuesta en un registro privado de esta entrega. No usar SQL directo ni el token interno como permiso editorial. Si ya existe un slug, detener y revisar, sin actualizar automáticamente.
7. Previsualizar los tres cuerpos, fuentes y recursos; pasar cada uno por revisión. Publicarlos consecutivamente, comprobando cada respuesta. Hay una ventana breve de enlaces entre guías aún no publicadas: no declarar terminada la entrega hasta que los tres destinos respondan 200. Si falla un paso, retirar temporalmente solo las nuevas piezas mediante el flujo editorial existente.
8. Confirmar los tres artículos en el sitemap de artículos y sus secciones en sitemap-pages.xml; el índice se genera desde inventario público, sin edición manual. Verificar 200, HTML SSR, H1 único, description, canonical, JSON-LD, enlaces internos/externos y recursos. Comprobar HTTPS, www/HTTP y rutas antiguas 301, cuenta/panel, API y salud de PostgreSQL, Redis, Caddy y trabajador. No reiniciar estos servicios innecesariamente.
9. Verificar GA4 sin petición previa al consentimiento y con título/referrer correctos tras aceptar; no habilitar una propiedad o configuración que esté desactivada sin autorización. Si hay propiedad real habilitada, comprobar sus informes de depuración sin afirmar indexación ni tráfico todavía.

## Rollback de aplicación y contenido

Conservar imagen web anterior con etiqueta de esta entrega y copia de sus archivos/Compose. Si falla salud, SSR, autenticación, navegación o consentimiento, restaurar esa imagen y código con la misma configuración y recrear únicamente web. Comprobar que production.env conserva su hash.

Antes de volver al renderer antiguo, archivar mediante la API/panel solo los tres IDs creados por esta entrega que se hayan hecho públicos. Conservar sus borradores, auditoría y registro de IDs; no borrar artículos ni usuarios. Confirmar que sus URLs desaparecen de listados y sitemap. Verificar de nuevo rutas existentes, API, TLS y trabajador.

No restaurar PostgreSQL o Redis sobre datos recientes como rollback rutinario: perdería sesiones, comentarios o publicaciones legítimas. Una restauración real de datos exige diagnóstico y autorización específica. No ejecutar down -v, podas de volúmenes ni cambios de firewall/SSH/DNS.

## Riesgos y límites

- Un solo frontend: la recreación puede causar una interrupción breve; no se promete cero downtime.
- La publicación de tres piezas no es atómica en la API actual; el registro de IDs y la retirada selectiva cubren fallos parciales.
- Los enlaces internos de artículos pasan a admitir una gramática limitada. No es Markdown general ni un sanitizador de HTML arbitrario.
- La ayuda de NotebookLM se revisó; no se probó una sesión autenticada. Se declara dentro del texto.
- Presupuesto y horario nocturnos se conservan: no ejecutar investigación manual ni pausar el trabajador como parte de esta entrega.
- Copia y prueba de restauración nuevas son condición previa del despliegue autorizado, no operaciones realizadas durante esta revisión local.
