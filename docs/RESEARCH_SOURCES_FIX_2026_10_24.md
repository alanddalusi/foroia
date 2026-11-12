# Investigación nocturna: diagnóstico y corrección de fuentes

Desplegado el 24/10/2026. No se ejecutó una generación de pago ni se reabrió una fecha ya finalizada.

## Causa reproducida

La ejecución del 23/10 comenzó a las 22:30:27 de Madrid y terminó a las 22:30:31 sin artículo, con insufficient_sources y reserva de 0 USD. El expediente contenía 11 candidatos, cuatro consultas fallidas y cuatro documentos agrupados como huggingface.

El diagnóstico de solo lectura desde el VPS reprodujo cuatro respuestas HTTP 403 de páginas de OpenAI. El RSS de OpenAI sí devolvió 200. Los feeds de Hugging Face y Google también respondieron; Google redirige dentro de blog.google y en el momento del diagnóstico no aportó candidatos en la ventana de 48 horas. No hay evidencia suficiente para atribuir la denegación a una regla concreta del proveedor.

Se comprobó además un defecto de atribución: todas las publicaciones alojadas en Hugging Face recibían la organización de la plataforma, incluyendo las de organizaciones distintas. Esto impedía superar el mínimo de dos grupos aun cuando existían documentos atribuibles a organizaciones diferentes.

## Cambios aplicados

- Se diferencian plataforma y organización. Microsoft y Ai2 se reconocen solo en namespaces concretos, con metadatos BlogAuthorsByline que coincidan en nombre e identificador de organización con un registro curado.
- Se contrastaron los perfiles de organización de Hugging Face: microsoft y allenai figuraban verificados. IBM Research no figuraba verificado en esa consulta y no se añadió como organización adicional. El nombre de una URL por sí solo no basta.
- Las publicaciones propias de Hugging Face se reconocen mediante la marca de personal isHf del bloque de autoría y su ruta de publicación. Un espacio desconocido conserva agrupación conservadora y no suma una organización independiente confirmada.
- El mínimo de dos organizaciones se exige tanto antes de redactar como sobre las fuentes realmente citadas en el borrador. Se excluyen de ese recuento las atribuciones nuevas no confirmadas. Esto no garantiza corroboración temática por sí mismo: siguen activos revisión, citas, originalidad y demás controles.
- La revisión aplazada vuelve a comprobar los nuevos metadatos de atribución; si cambia la identidad, se detiene. Los expedientes anteriores sin esos campos conservan su agrupación original.
- Se prueban hasta 12 candidatos por ejecución en vez de cortar la lista tras ocho intentos, conservando un máximo de ocho evidencias. Así pueden evaluarse candidatos adicionales cuando fallan descargas. No se reintentan cobros ni se reabre la ejecución del día.
- Los expedientes nuevos incluyen fetch_errors con URL pública canónica, fase, código controlado y estado HTTP cuando exista. Nunca contienen cuerpos de respuesta, claves o textos de excepciones del proveedor. El panel incorpora un desplegable de consultas fallidas y las organizaciones confirmadas.

Se mantienen HTTPS, DNS público fijado al socket, verificación TLS/SNI, hosts exactos, rechazo de redirecciones no permitidas, límite de 2 MB y formatos acotados. No se eluden los 403 ni se añaden proxies o fuentes sin revisar. Presupuesto mensual 5 USD, límite diario 0,15 USD, modelo y horario 22:30 Europe/Madrid intactos.

## Verificación sin generación

El recolector corregido se probó primero en memoria en un proceso efímero del VPS, sin sustituir archivos de producción. Después del despliegue se repitió únicamente la descarga con el módulo desplegado.

Resultado posterior: nueve candidatos, cuatro documentos recuperados, tres organizaciones confirmadas —ai2, huggingface y microsoft— y cinco descargas de OpenAI denegadas con 403. El quinto error aparece porque se probó un candidato adicional que antes quedaba fuera del corte de ocho. El documento de IBM se conserva como material auxiliar, pero no suma otra organización confirmada.

Estos resultados acreditan recuperación y atribución; no que ya exista un artículo nuevo aprobado. No se llamó a Responses API ni se creó un research_run. Las huellas de research_runs y research_control permanecen idénticas al respaldo, igual que artículos, auditoría, usuarios y las demás tablas salvo sesiones y contadores de tráfico.

Los expedientes históricos no se reescriben. El detalle nuevo de descargas aparecerá en las próximas ejecuciones reales, no retrospectivamente en el registro del día 23.

## Pruebas

- Suite general: 106 correctas y 44 optativas omitidas.
- Nuevas pruebas de namespaces y metadatos coincidentes, autoría ausente/malformada, grupos no confirmados, preservación de expedientes anteriores, límites de intentos/evidencias, clasificación de HTTP 403 sin volcar respuestas y revalidación de autoría en revisión aplazada.
- Prueba explícita de que una organización no confirmada no cuenta para aprobar la corroboración del artículo.
- Prueba de navegador del panel: historial importado, actualización automática y visualización de URL/HTTP 403/organizaciones en expediente simulado.
- TypeScript y build correctos. Construcción de API, web y research-worker satisfactoria. Los hashes de sources.py, worker.py y writing.py coinciden entre API, trabajador y archivos probados.
- Comprobaciones públicas posteriores de artículos, metadatos, categorías, enlaces, recursos, sitemap, navegación móvil y ausencia de peticiones de analítica/publicidad satisfactorias.

## Backup, despliegue y rollback

Checkpoint nuevo privado: `/var/backups/foroia/sourcesfix-20261024-final`. Cuatro respaldos age: PostgreSQL custom, Redis RDB, código/configuración y certificados/volúmenes de Caddy, con copias externas y checksums coincidentes. Restauración PostgreSQL aislada con coincidencia de las 12 tablas de aplicación; Redis restaurado y comprobado; lectura íntegra de archivos cifrados y clave privada fuera del VPS.

Paquete selectivo de cuatro archivos, SHA256 `0ce1f46175818349a1305ccd73d0b698997394b45d0298bfcd40b3dd09a9dae9`. Se comprobaron ausencia de trabajo en curso y disponibilidad de imágenes anteriores antes de reconstruir/recrear API, web y research-worker. No se modificaron migraciones ni datos. PostgreSQL, Redis y Caddy mantuvieron contenedor/hora de inicio y siguen saludables; los puertos internos no se exponen.

production.env conserva su huella; anuncios y GA4 siguen desactivados. El trabajador está activo y conserva señal de vida. Rollback preparado con imágenes fijas de los tres servicios y archivos previos, validado antes del despliegue y conectado a los fallos de activación/comprobación. No fue necesario ejecutarlo. No se restauraría la base sobre actividad reciente como reversión rutinaria.

Archivos de aplicación modificados: api/app/research/sources.py, worker.py y writing.py; web/pages/editorial/investigacion.vue. Pruebas: tests/test_source_attribution.py y tests/test_analytics_local.py. Evidencia privada: .local/source-diagnosis-20261024/ y .local/deploy/sourcesfix-*. No versionar copias, credenciales o diagnósticos privados.

## Pendientes y límites

Los HTTP 403 de OpenAI persisten y no se presentan como resueltos. La corrección permite aprovechar fuentes con atribución confirmada cuando estén disponibles; no garantiza un artículo diario ni elimina los controles de calidad. Pendiente observar la próxima ejecución real, prevista el 24/10 a las 22:30 de Madrid, y su resultado. No hay notificaciones externas de fallos ni cola de artículos de reserva en esta entrega.
