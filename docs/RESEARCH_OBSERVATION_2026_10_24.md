# Observación programada de la investigación del 24/10/2026

Estado: observador instalado y timer activo, pendiente de la ejecución futura. No es un informe de una investigación ya realizada.

## Horarios y alcance

- Investigación existente: 24/10/2026 a las 22:30 Europe/Madrid. No se modifica su servicio, horario ni presupuesto.
- Observador independiente: comienza a las 22:29 Europe/Madrid, confirmado por systemd como 20:29 UTC.
- Consulta cada 30 segundos hasta que el registro del día esté finalizado. Límite de observación: 23:05 de Madrid; si no hay resultado, deja constancia del hueco o de la ejecución sin terminar. No reinicia ni fuerza el trabajador.
- El timer es de una sola fecha, persistente ante reinicio del servidor; no añade otra tarea diaria de generación. Timeout del servicio: 40 minutos.

El observador solo ejecuta lecturas de PostgreSQL bajo transacción REPEATABLE READ READ ONLY, consulta el heartbeat y el estado del contenedor, y comprueba páginas públicas si se publica un artículo. No importa ni llama al pipeline, no modifica artículos, no hace reservas ni llama a OpenAI.

## Informe automático privado

Directorio en el VPS: `/var/lib/foroia/research-audits/2026-10-24/`.

- report.md: resumen, descargas fallidas, versiones y controles registrados, presupuesto reservado, comprobaciones públicas y seguimiento necesario.
- report.json: resultados estructurados y cronología de observación.
- snapshot.json: expediente del día y artículo asociado, si existe. Puede contener borradores privados; nunca servir este directorio por la web.

Directorio con permisos privados y archivos 600 mediante umask 0077. Se escribe el JSON de forma atómica. No se incluyen claves, cookies ni variables privadas del proveedor.

El informe distingue candidatos documentales de artículos: el sistema redacta como máximo una propuesta al día, con una corrección acotada. No se afirmará que cada noticia detectada haya recibido una revisión generativa independiente. Una validación determinista fallida guarda el primer motivo; el resto de controles que no consten se indicarán como no registrados/evaluados, sin inventar aprobaciones.

El presupuesto se contrasta con las reservas conservadoras del día y del mes, no con una factura del proveedor a la que el observador no tiene acceso. Los límites configurados se leen, nunca se aumentan.

Si hay publicación, comprueba URL 200, H1, título, descripción, canonical, Open Graph, igualdad del cuerpo/fuentes con la API pública, enlaces de fuentes, tipos JSON-LD e inclusión en el sitemap de artículos. También consulta Schema.org Validator; si ese servicio externo no responde, deja la comprobación como no completada.

## Instalación y pruebas realizadas

- Script: scripts/research_audit.py; instalado como `/usr/local/lib/foroia/research-audit-20261024.py`.
- Unidades nuevas: `foroia-research-audit-20261024.timer` y `.service`; verificadas con systemd-analyze verify. Timer habilitado y activo, con el próximo disparo correcto.
- Cuatro pruebas locales correctas: separación de documentos/borradores, controles de versiones, límites económicos y extracción de metadatos SSR. Compilación Python correcta.
- Preflight de lectura en VPS con --check-once: trabajador activo, reservas mensuales dentro del límite, sin ejecución del día 24 todavía. Resultado separado en `/var/lib/foroia/research-audits/preflight-20261024/`, sin confundirlo con el informe nocturno.
- Prueba del comprobador público sobre la guía Python ya existente: todos los checks correctos, sitemap presente y Schema.org sin errores ni advertencias. No se publicó contenido de prueba.
- Huella de production.env idéntica antes/después de la instalación. No se cambió ni recreó ningún servicio de la aplicación. No hubo llamadas de generación, cambios de datos o reservas.

Evidencia local privada: .local/research-audit-20261024/installation.json y public-check-preflight.json. El JSON de instalación confirma el hash del script remoto y su timer. No versionar datos privados de observación.

## Consultar después de la ejecución

```sh
sudo systemctl status foroia-research-audit-20261024.service --no-pager
sudo cat /var/lib/foroia/research-audits/2026-10-24/report.md
sudo journalctl -u foroia-research-audit-20261024.service --no-pager
```

La cuenta SSH actual sigue intacta. Para detener únicamente este observador, sin tocar la investigación:

```sh
sudo systemctl disable --now foroia-research-audit-20261024.timer
sudo systemctl stop foroia-research-audit-20261024.service
```

No hay integración de notificaciones externas. Este chat no dispone de una herramienta para iniciar un mensaje futuro por sí solo. El informe se generará en el VPS y se podrá consultar al regresar a la conversación o por SSH; no se promete entrega automática en el chat.
