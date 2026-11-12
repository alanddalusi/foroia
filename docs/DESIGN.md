# Identidad editorial de ForoIA

Dirección aplicada el 21 de octubre de 2026. La marca sigue siendo provisional; este trabajo no confirma disponibilidad legal del nombre.

## Decisión

Una publicación de lectura, con cabecera tipográfica, tinta oscura, fondo claro y un único acento rojo. La personalidad depende de la composición, la tipografía y la voz; no de añadir decoración a una plantilla de producto tecnológico. No hay imágenes, autores, testimonios ni cifras de actividad inventados para llenar la portada.

La crítica a la repetición de morados, sombras y tarjetas aparece en [esta conversación de diseñadores](https://www.reddit.com/r/webdesign/comments/1m2om61/why_is_every_ai_website_designed_the_same/). Es una opinión de comunidad, no una prueba de autoría ni una conclusión científica sobre el uso de IA. Se tomó como punto de partida estético, no como requisito de accesibilidad.

## Sistema visual

- Fondo `#f8f7f3`, texto `#242420`, secundario `#64635c`, acento `#a33425`, líneas `#d6d3ca`. Variables centrales en `web/assets/css/main.css`.
- Georgia para cabecera, titulares y lectura; tipografía de sistema para navegación, datos y controles. Sin descargar fuentes ni añadir dependencias o peticiones a terceros.
- Portada con un artículo principal real y columna de guías; el destacado no se repite en esa columna. Si no hay contenido publicado, se explica con claridad, sin fingir noticias.
- Directorio de secciones numerado como índice, enlaces del foro y listados separados por líneas. Sin sombras, degradados, brillos, iconos decorativos o contenedores redondeados repetidos.
- Artículos centrados con columna máxima de 720 px y prosa de hasta 66ch; texto a 20 px en escritorio y 19 px en móvil, con interlineado 1,8. Autoría, fechas y fuentes siguen visibles. El código conserva monoespaciado y desplazamiento dentro del bloque.
- Cuenta, formularios, panel editorial y moderación comparten los mismos colores, controles y estados. Errores, aprobaciones y estados se expresan también con texto.
- Navegación en texto, visible y adaptable sin menú oculto ni JavaScript adicional. La cuenta queda separada del menú editorial. Salto al contenido, foco visible y controles de al menos 44 px de alto para las acciones principales.

## Fundamento y fuentes

1. [Baymard: longitud de línea](https://baymard.com/research-articles/line-length-readability). Recomienda mantener contenida la medida del texto; su intervalo orientativo es de 50–75 caracteres. `ch` es una medida tipográfica aproximada, no garantiza un número exacto de caracteres en cada línea.
2. [NN/G: legibilidad y comprensión](https://www.nngroup.com/articles/legibility-readability-comprehension/). Tipos legibles, tamaños cómodos, contraste y fondo sencillo; distingue entre facilidad de reconocer letras y comprensión del contenido. La elección de serif no demuestra por sí sola una mejora de comprensión.
3. [W3C: contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Referencia de 4,5:1 para texto ordinario. El texto secundario sobre el fondo da 5,63:1 y el texto blanco del botón sobre el acento, 6,83:1. Los bordes de controles contra su superficie dan 3,66:1.
4. [W3C: reflujo](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html). Se comprueba la portada a 320 CSS px sin desplazamiento horizontal de la página; los bloques de código y tablas conservan desplazamiento interno cuando lo necesitan.

## Mantener la identidad

- Antes de crear un componente, elegir su función editorial: titular, lectura, índice, dato, fuente o acción. Reutilizar los estilos existentes.
- Reservar los fondos y bordes de controles para delimitar acciones o estados; no convertir cada párrafo o artículo en una tarjeta.
- No añadir retratos, sellos de confianza, logotipos de empresas o estadísticas que no correspondan a información real. La autoría y experiencia deben ser reales.
- Las imágenes futuras deben explicar el contenido: capturas propias, gráficos o fotografías con derechos y contexto. El diseño no depende de imágenes de relleno.
- No introducir animaciones ni nuevos paquetes para conseguir esta estética. Mantener SSR, enlaces rastreables y los estados vacíos honestos.

## Archivos del cambio

`web/app.vue`, `web/pages/index.vue`, `web/pages/blog/[seccion].vue`, `web/pages/articulos/[slug].vue`, `web/components/ArticleCard.vue`, `web/components/ArticleComments.vue`, `web/assets/css/main.css`, `web/nuxt.config.ts` y ampliación de las comprobaciones visuales en `tests/test_browser.py`. No se cambia el esquema de datos ni la autorización.

Capturas y logs locales en `.local/design/`, `.local/design-build-final.log` y `.local/design-final-tests.log`. Las publicaciones de las capturas son artículos temporales identificados como pruebas y se archivan al terminar.

Esta es una revisión visual y funcional en Chromium, no una auditoría WCAG completa ni una prueba con lectores reales. La percepción de autenticidad es subjetiva: hace falta también contenido y autoría propios, no solo un estilo distinto.

## Verificación del 21 de octubre de 2026

- Comprobación de TypeScript y compilación Nuxt correctas en `.local/design-build-final.log`.
- Suite HTTP y navegador: **33 pruebas correctas**, 25,78 segundos, en `.local/design-final-tests.log`. Incluye acceso, creación, revisión, publicación, archivo, registro, verificación y moderación de comentarios.
- Chromium en escritorio (1280 px) y móvil (390 px); comprobación adicional de reflujo a 320 px, navegación por teclado, salto al contenido y ausencia de desplazamiento horizontal. Capturas finales en `.local/design/home-published-*.png` y `.local/browser/`.
- Un intento anterior quedó en 32 correctas y un rechazo 429 por acumulación de accesos de pruebas. Se esperó la caducidad del límite sin modificar Redis. Se corrigió además una aserción cuyo diagnóstico podía revelar la contraseña local; se renovó esa credencial en `.env` y en la cuenta, se revocaron sus sesiones y se censuró el log anterior.
- Una repetición posterior del arranque encontró una restricción local de Windows al instalar el ejecutable de Compose (`Move-Item: Access denied`). Los servicios existentes siguen funcionando y sirven la compilación final verificada; queda pendiente resolver esa restricción del equipo para repetir el arranque con el script. No se ha desactivado ninguna protección de Windows.
