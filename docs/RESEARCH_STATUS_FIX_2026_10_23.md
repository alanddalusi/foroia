# Estado del proceso automático: corrección del panel

Desplegado el 23/10/2026. La corrección afecta al seguimiento del proceso, no a la decisión de publicar ni a su presupuesto.

## Problema y cambio

El panel usaba «Ejecución en curso» para cualquier motivo desconocido, incluso con estado skipped. Los registros migrated_local_budget del 21 y 22 de octubre representaban reservas históricas importadas del entorno local; ese mensaje no acreditaba que estuvieran ejecutándose.

Ahora se muestran como «Historial importado», con explicación de que no son investigaciones activas del VPS. Solo un registro running sin finished_at recibe el mensaje de ejecución en curso. Los motivos o estados desconocidos tienen un texto neutro y no simulan actividad.

El panel muestra el estado de hoy, usando Europe/Madrid, con estas situaciones: pendiente de la hora programada, franja de inicio, resultado disponible o ausencia de ejecución transcurridos cinco minutos. Si la fecha actual contiene una reserva importada, se advierte expresamente de que no acredita una nueva investigación y no se repetirá el gasto automáticamente.

Mientras el panel está visible, actualiza su consulta de solo lectura cada 30 segundos; el intervalo se elimina al salir. No lanza investigaciones, no llama a OpenAI y no sustituye una alerta externa cuando nadie tiene el panel abierto.

Se explica además que la reserva mensual acumulada no es el gasto del día. Se conservan las reservas históricas y el límite de una ejecución por fecha: no se reabren fechas que ya tengan un registro.

## Fiabilidad y límites

Una prueba de regresión del planificador verifica que registros importados de días anteriores no bloquean el día siguiente: se ejecuta una vez, se conserva el coste histórico y no se vuelve a gastar al repetir tick. La prueba usa SQLite, Redis simulado y un pipeline simulado; no consume API ni publica contenido real.

Esto no garantiza un artículo diario. La publicación sigue dependiendo de fuentes accesibles y suficientes, generación, validación, revisión y límites económicos. No se han eliminado controles, creado artículos de relleno ni reiniciado reservas para forzar una publicación. Para mantener publicaciones durante fallos externos haría falta además una reserva de artículos originales ya revisados y una política de publicación aprobada; esta entrega no crea esa cola ni inventa contenido.

## Pruebas

- research-status.cjs: históricos importados, estados finalizados/desconocidos, trabajo activo, huecos diarios y horario de verano/invierno de Madrid.
- 51 pruebas de investigación correctas, incluida la nueva regresión de reservas históricas y día siguiente.
- 8 pruebas de navegador/SSR correctas: autenticación del panel, historial importado, actualización de consulta con reloj simulado, navegación, consentimiento, SEO y accesibilidad.
- Se corrigió una carrera de la propia prueba de GA4: ahora espera la petición interceptada antes de comprobar su contador. No se cambió ni activó GA4 en producción.
- Nuxt typecheck y build correctos, también dentro de la imagen de producción.

## Despliegue y preservación

Backup nuevo completo y cifrado, copiado fuera del VPS: `/var/backups/foroia/researchui-20261023-final`. Se restauró PostgreSQL en aislamiento y coincidieron las huellas y recuentos de las 12 tablas de aplicación. Redis pasó validación y restauración aislada; código/configuración y certificados se descifraron y leyeron íntegramente. La identidad privada permaneció fuera del servidor.

Se desplegaron solo web/pages/editorial/investigacion.vue y web/utils/research-status.ts; no se cambió backend, base de datos ni Compose. Paquete SHA256 `3da200d772f205e81d4b50928faebd30c74ca286ad765e8a8f52bdc1e70d366a`; imagen `sha256:817b4dded9f473c7cb622cb538f7d292a8272bb688e4b85e9355d7d86de617e9`.

Solo se recreó web. production.env conserva su huella. El trabajador, su contenedor, API, PostgreSQL, Redis y Caddy permanecen intactos y saludables. Investigación a las 22:30 Europe/Madrid, presupuesto mensual de 5 USD, límite diario y reservas conservados. Publicidad y GA4 siguen desactivados.

Verificación autenticada real: dos tarjetas de historial importado, ausencia del mensaje erróneo, aviso del día, reserva mensual intacta, actualización automática observada después de 30 segundos y móvil sin desbordamiento ni errores JavaScript. Las huellas de las tablas ajenas a sesiones y contadores de tráfico coinciden exactamente con el backup: no se modificaron artículos, investigación, auditoría o cuentas.

Rollback preparado con imagen anterior fija, archivos previos y override Compose, con sintaxis y configuración verificadas. La activación y comprobaciones estaban protegidas por rollback; no fue necesario ejecutarlo.

Otros archivos modificados para pruebas: tests/research-status.cjs, tests/test_research.py, tests/test_analytics_local.py y .github/workflows/checks.yml. Evidencia privada: .local/deploy/researchui-* y .local/research-ui-20261023/. No versionar backups, sesiones ni credenciales.

Pendiente: observar la ejecución real nocturna y su resultado; no se ha forzado una generación de pago. No hay notificaciones externas de fallo ni una garantía de publicación diaria.
