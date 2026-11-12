# Despliegue y prueba real: fases 1 y 2

4 de noviembre de 2026. Resultado: **desplegado; un artículo práctico real publicado y verificado; ninguna noticia publicada**. El objetivo de dos publicaciones diarias todavía no está demostrado en producción.

## Qué está activo

- API y trabajador editorial actualizados; migración aditiva `0010_editorial_lanes` aplicada.
- `RESEARCH_TWO_LANES=true` en producción; horario 22:30 Europe/Madrid.
- Topes conservados: **0,20 USD diarios y 10 USD mensuales**. No se ha activado 0,40/12.
- Recibos de los seis ejemplos válidos dentro de la imagen del VPS. Se transportó la imagen probada localmente; el importador Docker cambió su identificador, pero se comprobaron las mismas capas raíz, configuración y huellas de 50 archivos de aplicación/dependencias.
- Solo se recrearon API y trabajador. Frontend, Caddy, PostgreSQL y Redis conservaron sus contenedores; datos privados sin puertos publicados.
- El único cambio de `production.env` fue añadir la bandera. Se verificó por hash que el resto de sus bytes, incluidas credenciales, permanecía intacto. No se modificaron DNS, firewall, SSH, publicidad ni GA4.

Se desplegaron 17 archivos de backend, migración, coordinación, recibos y Compose. No se enviaron cambios pendientes ajenos del frontend ni se reconstruyó su imagen.

## Backup y rollback

Antes del cambio: `/var/backups/foroia/lanesprod-20261104-final`. Cuatro archivos cifrados —PostgreSQL, Redis, código/configuración y volúmenes de Caddy— copiados fuera del VPS y contrastados por SHA256. Restauración aislada correcta: las 20 tablas originales coincidían con el snapshot; Redis y los archivos de configuración/certificados también pasaron.

Los 12 artículos que ya existían, incluidos los borradores privados, conservan sus huellas originales después de la prueba. No se ha eliminado ni editado ese contenido.

Después de publicar se creó otro backup completo en `/var/backups/foroia/lanespost-20261104-final`, también copiado cifrado fuera del VPS. Su restauración aislada verificó las **21 tablas**, incluyendo la publicación y los registros económicos nuevos, además de Redis, configuración y certificados.

Rollback preparado en `rollback.py`/`rollback.yml` dentro del checkpoint. Recupera fuentes, imágenes y bandera anteriores sin restaurar una base antigua sobre las publicaciones nuevas ni rebobinar reservas. Conserva la migración aditiva. La API antigua se lanza sin su paso de Alembic antiguo para evitar que rechace una revisión `0010` desconocida. No fue necesario ejecutarlo: las comprobaciones críticas de despliegue pasaron.

## Ejecución diaria real #15

Iniciada manualmente el 4/11 a las 19:45 Madrid mediante `python -m app.research.worker --once`, con la misma cuenta económica y bloqueo de la jornada. No se usaron mocks ni respuestas prefabricadas.

La investigación utilizó Responses/web_search real: dos acciones de búsqueda comunicadas, 10.360 tokens de entrada y 2.434 de salida. Se verificaron fuentes y llegaron a redacción dos candidatas de noticias. Ambas fueron descartadas después de su corrección:

- Google Cloud: primera versión demasiado breve; la corregida no superó el detector de atribución oficial.
- NVIDIA/ciudades: primera versión rechazada por el detector de alcance; la corregida quedó demasiado fragmentada. No se publicó.

La línea práctica continuó independientemente y probó SQLite y normalización de texto. También fueron rechazadas por la revisión tras la corrección. No se reutilizó un rechazo como aprobación ni se desactivó ningún control.

Consumo calculado con uso comunicado de esta pasada: **0,098546 USD**. La jornada #15 mantiene sus descartes en el historial, con resultado `no_verified_publication`.

## Ejecución manual controlada #7: publicación real

Con el saldo restante, se preparó gratuitamente una candidata existente de FastAPI —sin repetir la búsqueda web— mediante el mecanismo autenticado de ejecuciones del panel. Preflight válido, dos documentos oficiales y recibo verificado. Se confirmó una reserva máxima de **0,101454 USD**, exactamente el saldo diario restante; no se aumentó ningún límite.

El mismo trabajador realizó generación, revisión y publicación. Resultado `completed / quality_checks_passed`, artículo **15**:

**[Validar entradas de texto para una API de IA con FastAPI y Pydantic](https://foroiaaldia.com/articulos/fastapi-validar-peticiones-ia)**

- Publicado el 4/11/2026 a las **19:53 Madrid**.
- Categoría: Programación.
- Fuentes: documentación oficial de [request body](https://fastapi.tiangolo.com/tutorial/body/) y [body fields](https://fastapi.tiangolo.com/tutorial/body-fields/) de FastAPI.
- Verificación del trabajador y comprobación externa independiente: HTTP 200, API, contenido SSR, canonical absoluto correcto, metadatos y datos estructurados coherentes, imagen accesible y presencia en el sitemap.
- Sin `noindex` en meta robots o `X-Robots-Tag` de la página.

Es una publicación real obtenida por el flujo automático en una **ejecución disparada manualmente**. No se insertó un artículo terminado a mano. No debe confundirse su éxito con el de la pasada diaria anterior, que no publicó. El panel registra la publicación en la ejecución #7.

## Coste y siguiente turno

| Concepto | USD |
|---|---:|
| Uso comunicado, pasada diaria #15 | 0,098546 |
| Uso comunicado adicional de FastAPI | 0,010711 |
| Total diario calculado con uso comunicado | **0,109257** |
| Reserva diaria acumulada, incluida la conservadora de la ejecución manual | **0,138232** |
| Saldo diario disponible según reservas | **0,061768** |
| Reserva acumulada del mes | 0,249516 |
| Saldo mensual disponible según reservas | **9,750484** |

Estos importes se calculan con tokens/herramientas comunicados y tarifas configuradas; no son una factura del proveedor comprobada. No se liberaron reservas manuales arbitrariamente ni se borró historial para repetir la jornada.

El trabajador queda vivo, la investigación habilitada y la siguiente jornada automática prevista para el **5 de noviembre a las 22:30 Europe/Madrid**. La jornada de hoy ya se consumió y no se repetirá a las 22:30. El bloqueo de concurrencia estaba libre al terminar.

## Pendientes identificados con evidencia real

1. Mejorar los contratos de corrección más allá de los cuatro flags de estilo: SQLite recibió un veredicto `approved=true` junto con `original=false` y sin motivos; el backend rechazó correctamente la combinación, pero el corrector recibió poco feedback útil.
2. Revisar falsos positivos del modo oficial sin relajar corroboración: la primera propuesta NVIDIA mencionaba ausencia de evaluaciones comparativas; el detector de palabras activó igualmente su regla. La propuesta corregida tuvo después un defecto real de estructura. El detector de atribución también necesita cubrir fórmulas naturales sin obligar a repetir «Según».
3. Alinear mejor al redactor/revisor con las evidencias de los ejemplos comprobados. Las revisiones rechazaron consejos no respaldados y reclamaron referencias de tests que el contrato ya ofrecía; no deben confundirse los fragmentos iniciales con una lista cerrada de evidencias permitidas.
4. Ampliar y rotar el catálogo práctico, propagar la ventana de noticias hasta siete días, preparar el depósito de nueve artículos y completar la presentación del panel. Las fases 1–2 por sí solas no resuelven estos requisitos de regularidad.

No se ha afirmado que Google haya indexado el nuevo artículo. No se ha inventado una noticia para completar la cuota ni declarado conseguido el objetivo de dos publicaciones diarias.
