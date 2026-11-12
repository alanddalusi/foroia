# Seguimiento privado

Panel `/editorial/estadisticas`: requiere cuenta verificada con rol editor o admin, en Nuxt y API. API privada sin caché; no hay endpoint público para enviar eventos. La ruta interna exige el token entre servidores y no está incluida en el proxy público.

Tras desplegar el bloque SEO, las secciones canónicas pasan a /actualidad, /herramientas, /programacion y /tutoriales; las antiguas /blog/... redirigen 301. Los contadores históricos de /blog/... se conservan.

Se cuentan respuestas HTML 200 de portada, secciones y artículos publicados. Se excluyen cuentas con cookie de sesión y agentes reconocibles como bots. Solo se guarda día Europe/Madrid, ruta canónica y contador agregado; no IP, agente, referente, cookie, identificador de persona ni parámetros URL. Incremento atómico PostgreSQL; migración `0005_analytics`. Un error de medición no bloquea la lectura ni se reintenta para evitar duplicados.

Son cargas de documentos, no visitantes únicos. Recargas cuentan y navegación Vue sin cargar un documento nuevo no cuenta. El filtro de bots es aproximado; bots que imitan un navegador pueden contarse. Los contadores no prueban audiencia humana, SEO ni ingresos. No hay reconstrucción de datos anteriores ni integración de Search Console. El primer día con datos no equivale al momento exacto de activación. Los agregados diarios se conservan para comparaciones históricas y se incluyen en los backups de PostgreSQL.

Periodos 7, 30 o 90 días, incluido hoy; comparación con periodo anterior de igual longitud. Estados son recuentos actuales. Publicaciones diarias usan la primera fecha de publicación, incluso si después se archiva. El ranking solo muestra artículos actualmente publicados. Sin cookie de analítica, scripts externos ni nuevas dependencias.

## Verificación

Backend: `PYTHONPATH=api python -m pytest tests/test_analytics.py tests/test_accounts_api.py tests/test_articles_api.py tests/test_research.py tests/test_contract.py -q` (95 correctas). El Dockerfile web ejecuta typecheck y build. Filtro de medición: `docker build --target build -t foroia-analytics-web-check ./web` y `docker run --rm -i --network none foroia-analytics-web-check node < tests/analytics-plugin.cjs` desde la raíz (redirección en shell compatible). El test usa eventos simulados, no altera contadores reales.
