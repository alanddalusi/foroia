# Despliegue de evidencias y prueba autorizada — 24/10/2026

El propietario autorizó «Desplegar y preparar prueba real» para comprobar la corrección de `invalid_evidence`. Se desplegaron cinco módulos de investigación: evidence.py, sources.py, writing.py, quality.py y worker.py. No hay cambios de esquema, dependencias, frontend, horario, presupuesto, DNS, SSH, firewall, correo, analítica ni publicidad.

## Respaldo y comprobaciones anteriores a la prueba

- Checkpoint: `/var/backups/foroia/evidencefix-20261024-final`.
- Cuatro respaldos cifrados: PostgreSQL, Redis, código/configuración y volúmenes Caddy. Copiados fuera del VPS, con hashes comprobados.
- Restauración aislada de PostgreSQL con huellas idénticas en las 12 tablas. Redis restaurado y respondiendo PONG. Integridad de código, configuración y certificados comprobada.
- Suite local: 138 pruebas correctas y 44 omitidas; incluye siete casos del reintento controlado, además de las pruebas de catálogo y publicación simulada.
- Rollback preparado en `rollback.py` y `rollback.yml` dentro del checkpoint. Restaura módulos e imágenes anteriores de API/trabajador, conservando datos y reservas.
- Solo API y research-worker reconstruidos/recreados. Web, PostgreSQL, Redis y Caddy conservan sus contenedores. API saludable y heartbeat del trabajador presente.
- Huella de production.env idéntica. PostgreSQL y Redis sin puertos publicados. Datos anteriores iguales, salvo contadores/sesiones que pueden variar por tráfico normal.
- HTTPS público, portada, API de artículos, sitemap y robots responden 200. HTTP redirige 308 a HTTPS; www redirige 301 al dominio principal.
- Las cinco fuentes RSS responden desde el transporte TLS con IP fijada del VPS. Microsoft Research y NVIDIA proporcionan contenido completo.

La comprobación de módulos detectó permisos 600 en el nuevo evidence.py, que impedían leerlo al usuario del contenedor. Se corrigieron a 644, se reconstruyeron las imágenes y se verificaron los cinco hashes en ambos contenedores antes de cualquier llamada de generación. El sitio público permaneció operativo; no se relajaron permisos de secretos.

## Un reintento excepcional sin borrar el historial

Nuevo comando de consola privilegiada: `python -m app.research.worker --retry-failed-run ID`. No es un endpoint web ni una tarea programada. Solo admite un rechazo finalizado `invalid_evidence` de la fecha actual, sin artículo asociado y sin reintento anterior. Rechaza procesos en curso, fechas anteriores, publicaciones, borradores asociados y resultados inciertos del proveedor.

Usa el bloqueo Redis existente, conserva el mismo registro/fecha y la reserva acumulada. Guarda el expediente anterior en `prior_attempts`, anota el inicio y registra `research_manual_retry` en auditoría. La publicación usa las transacciones y controles existentes. El límite de una corrección sigue vigente para el nuevo intento. Los fallos no disparan más reintentos.

Ejecución real autorizada iniciada el 24/10/2026 a las 12:16:06 Europe/Madrid, registro 4. Conserva los 0,034771 USD anteriores: el gasto adicional sigue dentro del total de 0,15 USD del día y 5 USD del mes. La ejecución programada de las 22:30 detectará el registro y no lo repetirá.

Unidad transitoria de observación de proceso: `foroia-research-evidencefix-20261024.service`. Expediente privado: `/var/lib/foroia/research-audits/evidencefix-20261024/`. Evidencias locales privadas en `.local/deploy/evidencefix-*`.

## Resultado real

Finalizó a las **12:17:26 Europe/Madrid**, sin publicación: estado `skipped`, motivo `insufficient_independent_sources`. El proceso terminó con código 0 y liberó el bloqueo. Esto representa un rechazo editorial registrado, no una aprobación ni una excepción del trabajador.

- Cinco feeds consultados, once documentos candidatos y siete recuperados. Organizaciones disponibles: AI2, Hugging Face, Microsoft y NVIDIA.
- Cuatro descargas de artículos de OpenAI devolvieron 403; no se eludieron las restricciones. El RSS de OpenAI no contenía contenido completo para esa recuperación alternativa.
- Se redactaron dos versiones —propuesta y una corrección—. Todas las citas pasan la comprobación de pertenencia al documento; no se repite `invalid_evidence`.
- Ambas versiones citan solo dos documentos de Microsoft: ThinkingBox-Training (`source_id=89646957686619`, alojado en Hugging Face) y Flint-interactive (`source_id=240795110014883`, en Microsoft Research). Dos dominios no acreditan dos organizaciones independientes. El control las rechaza correctamente.
- No se llegó a la revisión semántica. No se afirma que los controles de utilidad, originalidad o respaldo de cada frase hayan aprobado estas versiones.
- Reserva adicional: **0,043588 USD**. Total del día, incluido el intento anterior: **0,078359 USD / 0,15 USD**. Total del mes: **0,235788 USD / 5 USD**. Son reservas conservadoras; la factura del proveedor no se ha comprobado.
- No hay nueva URL ni nuevas entradas de sitemap. Los cuatro artículos existentes mantienen su contenido y responden 200, con canonical y Open Graph. API privada de investigación devuelve 401 sin sesión.
- Verificado después: usuarios y artículos sin modificaciones, misma cantidad de ejecuciones, expediente anterior íntegro dentro del registro 4, reservas conservadas, configuración idéntica, API saludable y heartbeat activo.

No hubo rollback de producción: los controles de calidad funcionaron y no apareció un fallo crítico de servicio. Durante la verificación final se detectó que una imagen anterior ya no estaba disponible. Se preparó una imagen de recuperación etiquetada con los cuatro módulos previos del respaldo y las mismas dependencias instaladas; build sin red, hashes de los módulos comprobados e importación del trabajador antiguo probada sin red. La configuración de rollback apunta a esa imagen existente, no a la referencia ausente. No se aplicó sobre los contenedores activos.

## Pendiente concreto

El bloqueo por transcripción de citas está corregido y comprobado en una generación real. Sigue pendiente la selección previa de un conjunto temático con dos organizaciones independientes **que se vayan a citar**, en lugar de confiar solo en que el generador seleccione entre las organizaciones disponibles. La corrección repitió el mismo par de Microsoft; se debe enriquecer el diagnóstico y fijar ese conjunto antes de otra generación, con pruebas sin gasto. No eliminar el requisito de independencia ni añadir una fuente ajena al tema para aparentar corroboración.

No se hicieron más reintentos de pago. La ejecución nocturna sigue a las 22:30; hoy no duplicará la fecha ya registrada. El calendario de los siguientes días y el presupuesto permanecen intactos.
