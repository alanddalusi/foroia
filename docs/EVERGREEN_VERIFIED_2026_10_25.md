# Correcciones verificadas y desplegadas — 25/10/2026

El estado inicial era correcto: once candidatas (seis tutoriales, cuatro guías y una comparativa), una preparada por el preview sin gasto, todas con cero intentos. El trabajador seguía activo; a mediodía todavía no correspondía ejecutar la jornada del 25. Se conserva el historial de días anteriores, sin forzar otra ejecución.

Se ha comprobado el fallback de noticias a evergreen, incluido el inicio natural del planificador a las 22:30 Europe/Madrid y la ausencia de repetición tras reiniciar. Las guías y tutoriales aceptan una organización oficial pertinente; las noticias y comparativas conservan sus requisitos de independencia. Los once planes pasan el flujo de control completo con proveedor simulado y base aislada. No se interpreta esa simulación como verificación semántica de respuestas futuras del modelo.

## Cambios

- `api/app/research/editorial.py`: coste calculado sobre tokens informados, distinguiendo entrada en caché; registro acotado de razonamiento (ya incluido en salida, sin duplicar coste) y llamadas sin uso conocido. Recuperación verificable después de reiniciar.
- `api/app/research/writing.py`: registra la ausencia de uso también cuando la petición falla o su resultado es incierto, conservando siempre las reservas.
- `api/app/research/routes.py`: respuestas con uso registrado, tokens en caché, inicio de cobertura y facturación explícitamente desconocida (`billed_usd=null`). No se reconstruyen tokens históricos inventados.
- `api/app/research/worker.py`: eventos JSON de inicio y resultado, identificador de ejecución, fecha, motivo y reserva, sin credenciales ni datos personales.
- `api/app/research/publication.py`: ausencia inicial en sitemap con hasta tres comprobaciones públicas sin generación; retirada si persiste. Las demás validaciones se mantienen.
- `web/pages/editorial/investigacion.vue`: explica «preparado, cero intentos» y diferencia reservas, uso comunicado, estimación y factura. Muestra consumo desconocido cuando falta telemetría.

La tarifa de caché se aplica únicamente al modelo/tarifa actualmente documentados, GPT-5 mini con 0,25 USD/M de entrada y 0,025 USD/M en caché. En otras configuraciones se mantiene una estimación conservadora a tarifa completa. Las reservas siguen cobrando internamente toda la entrada a tarifa completa para proteger el límite. [Modelo y tarifas oficiales](https://developers.openai.com/api/docs/models/gpt-5-mini). Los tokens de razonamiento ya forman parte de `output_tokens`; no se suman de nuevo. [Documentación oficial](https://developers.openai.com/api/docs/guides/reasoning).

## Pruebas

- Suite general: **195 correctas, 66 omitidas** por depender de entornos optativos.
- **19 pruebas optativas correctas**: las once candidatas llegan a Nuxt SSR, API, metadatos, imágenes y sitemap, más ocho pruebas de navegación, accesibilidad y consentimiento. Se probaron las recuperaciones gratuitas ante fallos transitorios; un fallo persistente sigue retirando el contenido.
- **11 comprobaciones optativas correctas con documentación oficial recién recuperada**: fuentes accesibles y preflight válido; la primera generación cabe en el límite diario. El callback de reserva detiene la prueba antes del proveedor.
- TypeScript y build correctos. Ninguna llamada de generación de pago ni publicación de prueba en producción.

Las pruebas HTTP usan SQLite en un archivo temporal y conexiones separadas para que las lecturas concurrentes SSR no compartan la transacción del escritor. El proveedor y su revisión se simulan explícitamente: la ejecución real posterior debe confirmar qué calidad consigue el modelo con fuentes actuales. No se garantiza que cada candidata sea aprobada.

## Despliegue y recuperación

Backup cifrado completo en `/var/backups/foroia/evergreen-20261025-final`, cuatro archivos descargados con hashes comprobados. Restauración verificada de las quince tablas PostgreSQL, Redis, código/configuración y certificados. Sin cambios de esquema.

API, web y trabajador se reconstruyen y recrean con rollback disponible. La cola conserva once candidatas y una preparada después del reinicio. HTTPS y redirecciones, URLs públicas, artículos, sitemap y servicios se verifican tras activar. PostgreSQL y Redis siguen sin puertos públicos.

Rollback: `sudo python3 /var/backups/foroia/evergreen-20261025-final/rollback.py`. Recupera archivos e imágenes anteriores, conservando datos y reservas recientes. No restaura una base antigua sobre las escrituras actuales.

Límites conservados: **0,15 USD diarios / 5 USD mensuales**; reserva mensual anterior y posterior **0,235788 USD**. Publicación automática activa. La próxima jornada elegible es **25/10/2026 a las 22:30 Europe/Madrid (UTC+01:00)**. Investigará noticias; si no son viables, evaluará evergreen y publicará únicamente si pasa todos los controles.

Seguimiento: `/editorial/investigacion` y `docker logs foroia-production-research-worker-1`. Falta observar la primera respuesta real del proveedor con esta corrección durante la ejecución programada. No se han modificado credenciales, DNS, programación, anuncios ni límites.
