# Recuperación y verificación de noticias — 29 de octubre de 2026

Corrección desplegada en producción. No se ha ejecutado investigación, generación ni publicación de pago durante este trabajo. No se han insertado artículos ni reiniciado la jornada editorial.

## Problemas técnicos corregidos

- `sources.py`: registro explícito de SEC, Microsoft Dev Blogs y documentación oficial de xAI. SEC admite únicamente rutas de documentos HTML de EDGAR; no es un proxy genérico. Se mantienen HTTPS, DNS público fijado al socket, verificación TLS, validación de cada redirección, límite de 2 MB y timeouts. Un 403 no se elude.
- Los documentos presentados en SEC pertenecen al emisor, no a SEC como organización independiente. Para el caso verificado se exige CIK `2130357` y la identificación de Anthropic en la portada. Otros emisores requieren incorporación y comprobación explícitas; no se acepta la etiqueta del modelo como autoría.
- Los índices conocidos y las páginas `CollectionPage` se resuelven a documentos individuales. Se conserva únicamente la paginación `page` válida, eliminando parámetros de seguimiento. Los índices no se convierten en evidencia y sus errores ya no se ocultan como resultados vacíos.
- Se extrae el cuerpo editorial explícito cuando existe. El comunicado real de NVIDIA usaba `div.article-body`; los elementos `article` eran tarjetas de noticias relacionadas. La extracción anterior podía quedarse con una tarjeta de 80 caracteres.
- Cada documento se contrasta localmente con la entidad, el producto y el acontecimiento propuestos antes de seleccionar fuentes. Se distinguen, entre otros, DevDay, resultados trimestrales, versiones de Grok Voice y registro de salida a bolsa. Un titular es una pista para recuperar el documento; nunca sustituye la comprobación del cuerpo.
- Una fecha que solo identifica el día conserva esa precisión. En el límite de la ventana se comparan días naturales, sin atribuir falsamente una hora de medianoche. Las fechas con hora mantienen la ventana de 48 horas. No se usa `dateModified` para rejuvenecer noticias.
- Recuperación acotada con RSS, referencias públicas y enlaces de la búsqueda ya realizada; caché de descargas y errores, prioridades por correspondencia y diversidad de organización. No se añade ninguna llamada a OpenAI ni otro planificador.
- Se conservan la selección temática, la exclusión de reproducciones, los identificadores de evidencia, la revisión final y la publicación existentes. Sigue siendo obligatorio citar efectivamente dos organizaciones independientes para noticias.
- La presentación inicial de una salida a bolsa ya publicada se detecta aunque cambien las URL. Esta comprobación es deliberadamente estrecha: no descarta automáticamente enmiendas, precios u otras novedades posteriores.
- El panel muestra motivos concretos, URL, etapa y estado HTTP cuando existe. Los cuerpos verificados y sus hashes se conservan privadamente en el informe de investigación para reproducir futuros fallos; no se envían al navegador mediante el resumen del panel.

## Reproducción de las cinco propuestas

Se conserva la salida registrada de la ejecución 9 en `tests/fixtures/news_candidates_20261029.json`. Su HTML original **no se conservó**, por lo que no se ha inventado una reproducción de aquellos bytes ni estados HTTP ausentes.

La segunda prueba utiliza respuestas HTTP reales descargadas desde el VPS el 29/10, aproximadamente a las 09:07 UTC, guardadas en `tests/fixtures/news_http_capture_20261029.json.gz`. Se reproducen sin red ni modelo. Estas respuestas actuales no se presentan como las respuestas históricas de la ejecución 9.

| Propuesta del modelo | Error técnico corregido / comprobación real | Qué sigue impidiendo publicarla |
| --- | --- | --- |
| Anthropic: registro S-1 | El índice SEC responde y se identifica como índice. El documento completo excede 2 MB: se conserva el límite. El alojamiento SEC no se cuenta como otro autor. | La presentación inicial ya está cubierta por el artículo publicado. No corresponde generar un duplicado. El antiguo `source_error` no contenía un estado HTTP: no se convierte retrospectivamente en un 403. |
| OpenAI: supuesto resumen DevDay | Se reconoce el índice y se registra su 403 real desde el VPS. | Esa URL no aporta una noticia individual verificable. No se ha demostrado el conjunto de anuncios propuesto por el modelo. |
| NVIDIA: Vera Rubin / Oracle | Se conserva `page=2`, se localiza el comunicado individual y se recupera su cuerpo real. La fecha publicada es 27/10 con precisión de día. Se rechaza Anthropic AI for Science como corroboración de NVIDIA. | La captura aislada contiene el comunicado oficial, pero no una segunda organización que corrobore el mismo acontecimiento. No acredita que sea imposible encontrarla: la recuperación nocturna real volverá a utilizar las fuentes permitidas disponibles. |
| xAI: Grok Voice 3.0 | El índice permite localizar el artículo individual. El documento sobre socios no corresponde a este lanzamiento. | La página original de Grok Voice 3.0 está fechada el **14/10**, fuera de la ventana; no es un anuncio del 27/10 como proponía el modelo. |
| Alphabet: resultados Q3 | La página oficial corresponde al trimestre y tiene fecha original verificable, 28/10 a las 21:05 UTC. | En la reproducción acotada falta una segunda organización independiente. No se considera falsa la noticia por ese motivo; queda sin corroboración suficiente para publicar. |

La documentación oficial de [SEC](https://www.sec.gov/about/developer-resources) describe EDGAR, RSS y acceso eficiente. Se comprobó también la procedencia de [Microsoft Foundry](https://devblogs.microsoft.com/foundry/) y [documentación de xAI](https://docs.x.ai/developers/release-notes). Permitir un dominio no valida automáticamente todos sus documentos ni las afirmaciones del modelo.

## Pruebas y comprobaciones

- Suite final: **348 pruebas correctas y 24 omitidas** por requisitos de entorno. Las verificaciones HTTP/SSR se ejecutaron aparte: **12 correctas**. Los casos PostgreSQL bajo concurrencia también se ejecutaron aparte en la copia restaurada, sin red ni credenciales de OpenAI.
- Regresiones sobre las cinco propuestas, respuestas HTTP actuales, SSRF/rutas, atribución de SEC, índices, paginación, caché de 403, correspondencia, antigüedad, duplicados y privacidad del informe.
- Pruebas integradas del trabajador existente con modelos simulados y base aislada: investigación → evidencias → generación → revisión → publicación. Son simulaciones, no publicaciones reales.
- PostgreSQL restaurado y aislado sin red: presupuesto diario/mensual bajo concurrencia, deduplicación y liquidación idempotente. Cero llamadas de pago.
- TypeScript y build Nuxt correctos; 12 pruebas HTTP/SSR correctas. Prueba del panel real en Chromium: cinco propuestas históricas visibles, escritorio y móvil sin desbordamiento, foco de teclado y ningún error de página.
- Siete servicios funcionando. Los siete artículos publicados conservan HTTP 200, SSR, canonical y presencia en sitemap. Borrador, usuarios, fuentes, fechas y libro de costes conservados. Las 19 tablas ajenas al contador de visitas coinciden con las huellas del backup anterior al despliegue; el contador cambia con el tráfico real.
- PostgreSQL y Redis continúan sin puertos públicos. Configuración privada sin cambios; no se han modificado DNS, SSH, firewall, credenciales, publicidad ni analítica.

## Backup, despliegue y recuperación

Checkpoint privado: `/var/backups/foroia/newsrecovery-20261029-final`. Cuatro copias cifradas: PostgreSQL, Redis, código/configuración y volúmenes TLS de Caddy. Copias externas y hashes comprobados. Restauración real de PostgreSQL con coincidencia de las **20 tablas**, Redis cargado correctamente y archivos/configuración/TLS verificados.

Se desplegaron selectivamente ocho archivos: `sources.py`, `selection.py`, `news_gate.py`, `news_recovery.py`, `night_web.py`, `routes.py`, `web/utils/research-status.ts` y `web/pages/editorial/investigacion.vue`. Sin migraciones ni sustitución de contenido editorial. La portada y los demás archivos de producción no se sobrescribieron.

Rollback preparado en el checkpoint: `rollback.py`, `rollback.yml` y `before.tar.gz`. El operador puede ejecutar `sudo python3 /var/backups/foroia/newsrecovery-20261029-final/rollback.py` para restaurar únicamente esos archivos y las imágenes anteriores. No elimina artículos, reservas ni datos. La compatibilidad con el esquema actual se comprobó en PostgreSQL aislado. No fue necesario activar el rollback en producción.

## Estado económico y próxima ejecución

- Límite diario: **0,15 USD**. Mensual: **10 USD**. Sin cambios.
- Jornada 29/10 ya ejecutada previamente: reserva/uso liquidado conservado **0,050452 USD**. Resto de capacidad de reserva diaria **0,099548 USD** y mensual **9,421290 USD**, en la comprobación posterior al despliegue. No equivale a una factura del proveedor verificada.
- Única próxima ejecución: **30/10/2026 a las 22:30 Europe/Madrid**, confirmada por el panel y el heartbeat del trabajador. No se reabrió el día 29 ni se habilitaron tareas de media hora.
- Coste adicional OpenAI de estas correcciones y pruebas: **0 USD**.

No hay una nueva publicación real con esta versión: la validación gratuita demuestra recuperación y controles; la siguiente ejecución real deberá demostrar si encuentra una noticia actual con fuentes suficientes. No se promete publicación diaria a costa de esos controles.
