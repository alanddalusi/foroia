# Detección periódica y publicación editorial — resultado del 27/10/2026

## Estado final

Desplegado y activado en producción. Se comprobaron **21 barridos reales consecutivos**, en ventanas separadas por 1.800 segundos, desde el 26/10 a las 23:00 hasta el 27/10 a las 09:00, Europe/Madrid. El primero se ejecutó al activar la función dentro de la ventana de las 23:00. La detección no ha llamado a OpenAI ni añadido reservas de gasto.

Los cinco artículos públicos siguen accesibles y coinciden con el backup en texto, fechas y metadatos. El trabajador nocturno permanece habilitado a las **22:30 Europe/Madrid**. Sus límites siguen en **0,15 USD diarios y 5 USD mensuales**. También se mantienen los límites editoriales existentes: como máximo una publicación automática al día y cinco a la semana. La publicación extraordinaria adelanta un acontecimiento elegible; no elimina esos límites.

## Componentes reutilizados

- El mismo proceso `research-worker`, sin otro servicio editorial. Su bucle sigue atendiendo recuperación, trabajos duraderos y ejecución nocturna.
- Un coroutine de detección gratuito observa ventanas UTC de media hora. Tiene un bloqueo Redis propio y una clave de ventana única en PostgreSQL; no mantiene el bloqueo editorial durante las descargas ni impide iniciar la ejecución nocturna.
- Los acontecimientos usan `EditorialCandidate`; la activación diurna prepara `EditorialExecution` de modo `rapid`. El mismo `execute_job`, las mismas reservas y `worker.pipeline` realizan generación, revisión, validación, publicación y verificación pública.
- La ejecución diurna y la nocturna comparten `ResearchRun` como cuenta diaria de reservas. Un intento diurno sin publicación no consume la ejecución nocturna: a las 22:30 se puede reutilizar esa cuenta, conservando las reservas anteriores y registrando un único inicio nocturno.
- No se ha sustituido el contrato de evidencias, la revisión de afirmaciones, los controles de originalidad ni los requisitos SEO. Se congelan las fuentes y los títulos de contexto al preparar una petición para recuperar una etapa sin pagar de nuevo por datos reconstruidos de forma diferente.

## Detección y decisiones

Se utilizan 12 fuentes permitidas, preferentemente RSS y algunos índices HTML oficiales. Se amplió el registro con Tesla, Tesla Investor Relations, Waymo y NVIDIA Newsroom. Waymo y Google cuentan como la misma organización; lo mismo ocurre con los distintos dominios de NVIDIA o Tesla. Las verificaciones de autoría en plataformas de alojamiento y la detección de comunicados reproducidos siguen aplicándose.

El clasificador local identifica entidad, producto/versiones, tipo de acontecimiento y fecha de publicación original. Tiene reglas explícitas para modelos, robótica, autonomía y hardware, incluyendo variantes de modelos que no deben agruparse entre sí. No es un sistema general de comprensión semántica ni garantiza detectar cualquier producto nuevo. Los nombres no reconocidos no obtienen un permiso de generación por contener palabras genéricas sobre IA.

Los documentos del mismo acontecimiento se agrupan antes de generar. La identidad se conserva en la cola y las URLs observadas tienen claves persistentes: modificar el título o la fecha del RSS no vuelve a activar la misma URL. Si la página acredita una publicación original antigua, se descarta aunque el RSS parezca reciente. La fecha utilizada procede de la publicación de la fuente; no se inventa una fecha de anuncio cuando no está documentada.

La selección prioriza anuncios identificables y recientes frente a enlaces HTML genéricos sin fecha, y acontecimientos corroborados frente a hipótesis. La cola conserva su prioridad categórica de noticias; no se presenta un número inventado como impacto, popularidad o demanda SEO medida. El catálogo es equilibrado: un emisor prolífico no puede desplazar la evidencia de otra organización por llenar el límite de documentos.

Hay tres estados distintos:

1. **Anuncio nominado por RSS**: candidato pendiente de documentos verificados, sin texto de evidencia ni autorización para llamar al generador.
2. **Documento recuperado**: puede faltar una segunda organización independiente; el candidato espera corroboración.
3. **Noticia lista**: tiene documentos pertinentes y verificados de al menos dos organizaciones independientes y puede preparar un trabajo, sujeto a presupuesto y límites editoriales. El artículo final debe citar realmente la evidencia suficiente.

Un dato de RSS no reemplaza un documento ya verificado. Un candidato sin presupuesto se conserva mientras siga vigente. La rutina de detección no llama al modelo para decidir si un título es importante.

## Seguridad, costes y recuperación

- Se conservan los destinos HTTPS permitidos, DNS público fijado a la conexión TLS, validación de redirecciones, tamaño máximo de descarga y rechazo de XML con entidades/DOCTYPE.
- Descargas limitadas, timeout por petición y máximo de cinco minutos por barrido. Los errores de una fuente se registran y no cancelan el resto.
- Backoff persistente: los 403 no se eluden, los 429 respetan `Retry-After` dentro del límite de seguridad y los fallos transitorios se espacian. Los intentos de recuperación de un documento son acotados.
- Las reservas se realizan antes de llamar al proveedor, bajo bloqueo de la fila de control en PostgreSQL. Se recarga el importe diario después de adquirir el bloqueo para evitar que dos sesiones usen un saldo antiguo.
- Los trabajos diurnos usan el mismo bloqueo editorial y las mismas comprobaciones finales de límites de publicación. Las claves de acontecimiento, URL, ventana y solicitud evitan duplicados después de reinicios.
- Se conservan respuestas y checkpoints; no se reenvía un cobro incierto ni se repiten llamadas ante un error determinista. El borrador y el contexto de generación se recuperan desde la etapa válida.
- URL, API, HTML SSR, canonical, metadatos, imagen y sitemap se comprueban mediante el verificador existente. Una verificación fallida conserva su diagnóstico y utiliza la recuperación o retirada segura ya implementada.

## Resultado real, sin confundirlo con simulaciones

El primer barrido consultó 12 fuentes, recuperó correctamente nueve feeds/índices y examinó 149 entradas. Registró 403 de Tesla y de una página de OpenAI, codificación no admitida en DeepMind y una página de Meta demasiado grande. Las demás fuentes continuaron procesándose. Los barridos posteriores mantuvieron el backoff y completaron sus ventanas.

Existe un candidato real en la cola, ID 14, derivado del RSS de OpenAI para `https://openai.com/index/introducing-gpt-6-1-terra`. Está **en cola / `waiting_verified_sources`**, con cero intentos de generación. La página devolvió 403: el anuncio no se convirtió en hechos verificados ni en un artículo publicable.

Se hizo una adaptación única de las observaciones creadas por la primera versión: se pasaron sus metadatos vigentes a la misma función de incorporación de candidatos, sin investigación pagada, sin texto de evidencia y con auditoría `research_rss_nominate_backfill`. Las observaciones nuevas recorren automáticamente esta etapa en cada barrido. No se insertaron artículos manualmente.

**No hubo una publicación extraordinaria real durante esta validación.** No había un candidato con documentos suficientes para superar los controles. No se han inventado noticias ni presentado los casos históricos como novedades. La publicación real anterior de JSON permanece comprobada; no demuestra por sí sola una publicación diurna de noticias.

Las reservas totales se mantienen en **358.222 microUSD**, con seis registros históricos de uso comunicado. No se añadieron llamadas de pago en esta tarea; una noticia real elegible podrá utilizar el presupuesto existente de forma automática.

## Pruebas

- **261 pruebas generales correctas**; 67 opcionales omitidas en esa ejecución.
- **29 casos específicos de detección**: hechos históricos de Tesla, NVIDIA y OpenAI; rechazo de noticias antiguas y fechas RSS modificadas; nombres/versiones; fuentes repetidas; evidencia equilibrada; nominación sin evidencia; prioridad frente a índices genéricos; backoff; reinicio; concurrencia; presupuesto y preservación de las 22:30.
- **12 escenarios de extremo a extremo con Nuxt SSR real**, API y base de datos aislada. Incluyen RSS simulado, cola, despacho fuera del horario nocturno, proveedor simulado, publicación y comprobación de URL, contenido, canonical, metadatos e inclusión en sitemap. No publicaron nada en producción.
- Pruebas sobre PostgreSQL real restaurado y sin red externa: dos sesiones competidoras solo consiguieron una reserva cuando la siguiente excedía el límite diario o mensual; la creación concurrente produjo un solo acontecimiento y una sola ventana.
- Los datos históricos de prueba están identificados como tales y citan fuentes primarias. La adaptación de título y los documentos complementarios sintéticos no se presentan como capturas reales ni pruebas de productos.
- TypeScript, build Nuxt y builds Docker correctos. Activación y pausa desde el panel autenticado comprobadas en móvil y mediante teclado.
- Verificación final: siete servicios saludables; PostgreSQL y Redis sin puertos públicos; entorno y secretos conservados; cinco artículos públicos correctos; monitor sin alertas.

## Despliegue y rollback

Migración aditiva `0008_rapid_news`: bandera `ResearchControl.rapid_enabled`, `NewsScan`, `NewsFeedState` y `NewsObservation`. Primero se desplegó desactivada y se comprobó la compatibilidad del esquema. Después se habilitó desde el panel editorial.

Backups cifrados completos y copias fuera del VPS:

- `/var/backups/foroia/rapid-20261026-final/`: restauración de las 16 tablas anteriores comprobada antes de la migración; migración aislada conservó sus hashes.
- `/var/backups/foroia/rapidq-20261027-final/`: restauración comprobada de las 19 tablas actuales antes del último ajuste.

Cada checkpoint conserva imágenes anteriores, archivos originales y `rollback.py`. No se revierten ni eliminan artículos, reservas, observaciones o columnas aditivas. Para el primer rollback, la API anterior arranca con Uvicorn sin ejecutar una migración descendente ni intentar reconocer una revisión que su imagen no incluía. La detección rápida se puede desactivar mediante su bandera sin pausar la programación nocturna. Los trabajos ya enviados al proveedor pueden terminar.

La actualización solo copió los archivos previstos; no sobrescribió la portada desplegada, que difiere de la copia local. No se modificaron DNS, SSH, firewall, credenciales, anuncios, GA4 ni servicios contratados. No hay dependencias nuevas.

Archivos principales: `api/app/research/{rapid,events,queue,sources,selection,worker,executions,quality,routes,monitor}.py`, modelos y migración indicados, `web/pages/editorial/investigacion.vue`, `web/utils/research-status.ts`, pruebas y fixtures asociados. Los comprobadores privados y sus resultados están en `.local/deploy/rapid*-*.json`.

## Límites que permanecen

Los 403 y los sitios que no ofrecen evidencia accesible siguen limitando la cobertura. El detector utiliza un catálogo explícito y no rastrea toda la web, redes privadas ni todos los modelos posibles. Si faltan fuentes independientes, no publica; una frecuencia de barrido no garantiza frecuencia de artículos. No hay motivo para aumentar el gasto ni reducir controles para ocultar estas limitaciones.
