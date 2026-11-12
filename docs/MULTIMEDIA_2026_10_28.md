# Multimedia editorial y presupuesto — 28/10/2026

## Desplegado

- Nueva presentación de artículos: portada, entradilla, tiempo de lectura, índice, tipografía y columnas adaptadas al móvil, fuentes y artículos relacionados.
- Portadas específicas compuestas por código en nuestro servidor: WebP de 480, 800 y 1200 px, más PNG de 1200 × 630 para Open Graph. Alt, crédito y aviso de ilustración conceptual; nunca se presentan como fotografías del acontecimiento.
- Los siete artículos existentes tienen sus propias portadas: 28 archivos, máximo observado 36.821 bytes por archivo. No se cambian títulos, textos, fuentes, fechas o URLs.
- Anthropic incluye un gráfico de ingresos del primer semestre: 1,2 en 2025 y 16,3 en 2026, en miles de millones de USD. Solo se acepta una comparación explícita, con unidad y periodo comunes, valores presentes en el artículo y fragmento verificado. Escala desde cero, tabla accesible y enlace a la fuente. No se calculan previsiones ni se inventan cifras.
- Código con etiqueta y botón de copiar; tablas Markdown escapadas y desplazables con teclado. No se ejecuta HTML del artículo.
- Lectura bajo demanda con voces locales en español disponibles en el navegador. Sin autoplay, sin generación de audio mediante API; el código no se lee. Si no existe una voz local, se indica y el control queda deshabilitado.
- Soporte para vídeos incrustados por una fuente oficial recuperada. Solo IDs válidos de YouTube, sin descargar el vídeo ni la miniatura. El lector decide cuándo cargar el reproductor de `youtube-nocookie.com`, sin autoplay. La procedencia significa que esa página oficial contiene el embed; no se inventa una identidad del canal. No se han añadido vídeos inexistentes a los artículos de muestra.
- El índice mantiene la página montada al cambiar el fragmento de URL. Las consultas y rutas distintas siguen actualizando sus datos.

Ejemplos públicos:

- https://foroiaaldia.com/articulos/anthropic-s1-ipo-ant-2026-10
- https://foroiaaldia.com/articulos/validar-json-ia-python

## Arquitectura implementada

Se reutiliza el mismo trabajador editorial y su transacción de publicación. `ensure_media` compone los recursos originales después de la aprobación editorial y antes de publicar. No hace llamadas a modelos ni descarga fotografías externas. Al cambiar el contenido cambia la versión de recursos; una publicación no necesita generar imágenes durante una petición de lectura.

La migración aditiva `0009_article_media` añade `articles.media` y `article_assets`. Los archivos optimizados viven en PostgreSQL, separados del JSON que se entrega al listar artículos. Así participan en los backups existentes y no requieren un servicio de almacenamiento ni un volumen adicional. Para el tamaño actual resulta sencillo; si el archivo multimedia crece mucho, convendrá evaluar almacenamiento de objetos y su respaldo antes de migrar.

El endpoint de imágenes valida claves y solo sirve recursos de artículos publicados. Borradores y archivados devuelven 404, incluso con un ETag anterior. No se habilitan subidas arbitrarias ni URLs externas de imágenes suministradas por modelos. Actualmente no hay una biblioteca de fotografías de terceros con licencias aprobadas: se usa la alternativa de composición propia en lugar de asumir permisos por encontrar una `og:image`.

Se añade Pillow 13.0.0 para generar y optimizar imágenes y la fuente DejaVu de la distribución para renderizar texto. No hay servicios de imágenes/audio de pago. Nuxt 4, FastAPI, PostgreSQL, Redis y Caddy se mantienen.

Archivos principales: `api/app/modules/articles/media.py`, modelos, esquemas y lectura/publicación de artículos; `research/worker.py`, `night_web.py`, `publication.py`, `config.py`; migración, requisitos e imagen API; `ArticleBody`, `ArticleCode`, `ArticleAudio`, `ArticleVisuals`, `ArticleCard`, página de artículo, parser de bloques, tipos, proxy público, estilos y `app.vue`. Configuración: Compose y política de frames de Caddy.

## Presupuesto autorizado

El propietario confirmó **10 USD/mes**, manteniendo **0,15 USD/día**. Aplicado en producción y comprobado en API y trabajador. El límite mensual de configuración permite como máximo 10 USD; no se han modificado tarifas, credenciales ni el horario.

Con el límite diario conservado, el máximo teórico de un mes de 31 días sigue siendo 4,65 USD. Cambiar solo el techo mensual no aumenta ese máximo diario acumulado.

## Prueba real adicional

El mismo trabajador se lanzó mediante el mecanismo operatorio existente, con bloqueo global, deduplicación, máximo de una publicación y sin evergreen. Se permite este ensayo explícito después de una recuperación manual ya completada, conservando el mismo registro diario y sus reservas; no es un segundo planificador.

- Disponible antes: 0,133690 USD. Reserva máxima de búsqueda: 0,054553 USD.
- Responses `web_search` realizó una búsqueda real y devolvió seis propuestas.
- Se recuperaron tres documentos; ninguna propuesta obtuvo dos organizaciones independientes actuales y verificables sobre el mismo acontecimiento.
- AP/OpenAI devolvieron 403; hubo destinos fuera de la lista autorizada y documentos antiguos o demasiado grandes. No se eludieron bloqueos ni se ampliaron límites para forzar resultados.
- **No se llamó al modelo para redactar/revisar y no se publicó un octavo artículo.** No se considera una publicación completa satisfactoria.
- Coste calculado con el uso informado de esta prueba: **0,017455 USD**; facturación del proveedor sin verificar.
- Reservado el 28/10: 0,033765 USD; disponible diario: **0,116235 USD**. Reserva mensual: 0,528258 USD; disponible mensual: **9,471742 USD**.
- Próximo turno: **29/10/2026 a las 22:30 Europe/Madrid**. Trabajador activado, sin monitorización de media hora.

Esta prueba demuestra la búsqueda real y el rechazo antes de gastar en generación cuando faltan evidencias. La nueva integración multimedia del trabajador completó publicación en las pruebas aisladas; no se afirma haber publicado una nueva noticia multimedia mediante esa prueba real. Los siete artículos públicos sí tienen sus nuevos recursos generados y servidos desde producción.

## Comprobaciones

- 240 pruebas correctas de investigación, validación, recuperación, publicación y medios; 11 omitidas por requerir entornos específicos. Regresiones específicas posteriores de medios y contratos: 55 correctas.
- Parser de bloques, aislamiento del código, celdas de tabla literales y filtrado de lectura: pruebas Node añadidas a CI. Las comprobaciones existentes de enlaces, SEO, analítica y estados editoriales también pasan.
- 12 pruebas HTTP con Nuxt SSR y FastAPI reales, base aislada y modelos simulados: correctas.
- TypeScript y build: correctos. No se introducen dependencias de frontend para imágenes, gráficos o voz.
- PostgreSQL restaurado y aislado: migración sin modificar los 19 conjuntos de datos anteriores, generación de 28 recursos para los siete artículos, huellas de contenido/fechas intactas, presupuesto concurrente y deduplicación correctos. Sin llamadas de pago.
- Chromium público a 1440 y 390 px: imágenes WebP responsivas, alt, sin desbordamiento, índice por teclado y copia de código. Sin errores JavaScript ni peticiones de terceros durante la carga inicial. CLS observado 0 en estas mediciones de laboratorio, que no sustituyen datos de campo ni garantizan Core Web Vitals.
- Fixtures aislados de componentes: tabla, voz local y detener/pausar; cero reproducción o peticiones de vídeo antes del clic. El iframe se solicita tras el clic y con `autoplay=0`. Son simulaciones explícitas, no vídeos reales publicados.
- HTTP 200, SSR, canonical, metadatos, fuentes, JSON-LD y sitemap comprobados en la web pública. Anthropic aparece una sola vez; HTTP redirige a HTTPS con 308. No se afirma indexación en Google.
- Siete servicios funcionando. PostgreSQL/Redis sin puertos públicos. Usuarios, comentarios, foro, artículos anteriores y credenciales intactos. GA4 y publicidad no se activan.

## Backups y rollback

Backup completo cifrado antes del despliegue en `/var/backups/foroia/multimedia-20261028-final/`, copiado fuera del VPS, con restauración verificada. Después de generar las imágenes se verificó otra restauración de las **20 tablas**, incluidos todos los binarios, en `/var/backups/foroia/multimediaassets-20261028-final/`. Se conservan código, configuración, Redis, Caddy e imágenes anteriores.

El ajuste del índice tiene rollback separado en el segundo directorio. Para revertir toda la entrega se revierte primero ese ajuste y después la aplicación multimedia. No se ejecuta un downgrade que borre `article_assets` ni se restaura una base antigua sobre producción.

Último endurecimiento del parser multimedia: una comparación requiere un conector explícito y el mismo periodo, para no mezclar ingresos con otras cantidades del texto; un iframe opcional mal formado no invalida una fuente de noticias. Regresiones correctas y backup/restauración de las 20 tablas en `/var/backups/foroia/multimediafinal-20261028-final/`, posterior a la prueba real y conservando sus registros económicos.

El override del rollback arranca la API antigua directamente con Uvicorn: evita que su Alembic anterior intente resolver una revisión posterior desconocida. Esa API antigua se arrancó y leyó correctamente los siete artículos sobre una restauración del esquema aditivo, sin exposición de red ni llamadas externas. Los datos y los recursos permanecen guardados.

## Límites pendientes

No se garantiza una noticia diaria: los controles de evidencia siguen siendo obligatorios. Persisten avisos `news_verification_exhausted` y `source_http_403` para la prueba real. No se han presentado como fallos del despliegue multimedia ni se han ocultado.

La voz depende de las voces locales instaladas. Los vídeos dependen de los embeds presentes en las fuentes oficiales; no se añaden por rellenar la página. El extractor de gráficos es deliberadamente conservador y solo representa comparaciones inequívocas admitidas. Otras comparativas pueden mostrarse como tablas del texto validado.
