# Bloqueos de publicación corregidos — 8 de noviembre de 2026

## Resultado real

Desplegadas diez modificaciones del backend en API y trabajador, sin migraciones, nuevas dependencias, cambios del frontend ni llamadas pagadas. Los artículos, cuentas, historial de ejecuciones y registros de consumo existentes se han conservado. La publicación automática continúa activa, con **0,50 USD/día, 15 USD/mes y las 22:30 Europe/Madrid**.

La reparación **no ha publicado artículos nuevos ni demuestra todavía tres publicaciones diarias**. La ejecución del día 8 ya estaba terminada; el panel confirma la siguiente jornada el **9/11/2026 a las 22:30**. No se ha reabierto la jornada para gastar otra vez.

## Causas comprobadas y correcciones

1. **Clasificación de números.** La expresión anterior interpretaba `4xx` como el número `4` y `(1)… (2)…` como cifras factuales. Ahora conserva las familias HTTP como identificadores completos y excluye únicamente enumeraciones consecutivas. No infiere `4xx` por encontrar `400`, ni acepta subcadenas como `11` a partir de `119`. Se mantienen las comprobaciones de cifras y unidades por el revisor y el validador.
2. **Citas numéricas incompletas.** Los borradores reales #38 y #39 tenían una revisión favorable, pero las referencias elegidas para varias frases omitían `429`, `402`, `503`, etc., presentes en otros fragmentos verificados. No era correcto desactivar la validación: se añadió un contrato versionado de revisión con comprobaciones numéricas adicionales. El esquema JSON restringe cada referencia a fragmentos ofrecidos que contienen el token exacto. El backend vuelve a comprobarlo; la revisión semántica exhaustiva sigue siendo obligatoria. Si un número no aparece entre las evidencias ofrecidas, se rechaza antes de pagar una revisión.
3. **Reescrituras innecesarias.** Una recuperación acotada prepara una nueva revisión de los dos borradores antiguos, sin redactarlos otra vez ni reiniciar sus dos correcciones o su gasto histórico. Exige catálogo íntegro, revisión previa completa, ausencia de llamadas inciertas y coincidencia exacta del borrador privado almacenado. Una edición posterior bloquea la recuperación. No convierte la aprobación histórica en permiso de publicación.
4. **Documentación de Google.** Las páginas HTML registradas devolvían una aplicación vacía para el extractor (por ejemplo, 59 caracteres en la página de tokens). Se verificaron representaciones oficiales públicas `.md`, con contenido sustancial. El recuperador normaliza exclusivamente cinco rutas conocidas de Google; conserva la lista de dominios permitidos, límites, caché y verificación de redirecciones. No se usan proxies ni acceso autenticado.
5. **Agotamiento de descargas.** `document_fetch_budget` deja de acumular fallos que terminaban rechazando permanentemente candidatos sin haber podido evaluar sus documentos. Se aplazan sin modificar sus intentos. El recorrido deja de marcar a todos los candidatos restantes con el mismo límite ya agotado.
6. **Noticias de otra fuente.** Cuando falla la propuesta del modelo, se pueden seleccionar hasta tres acontecimientos concretos de los RSS oficiales que ya se habían descargado. Se reutilizan detección de entidad/producto/acontecimiento, fechas, fuentes, deduplicación y publicación existentes. No es otro investigador ni otra programación; estos candidatos se identifican expresamente como `official_feed`, no como resultados de `web_search`. No se inventan acontecimientos cuando no hay evidencias.
7. **Feeds gzip.** El recuperador admite gzip válido, limitando tanto bytes comprimidos como descomprimidos. Rechaza datos truncados, cadenas adicionales y bombas de compresión. El máximo de respuesta no aumenta.
8. **Diagnóstico y gasto de búsqueda.** La línea que descubre propuestas pero no verifica ninguna termina como `news_verification_exhausted`, en lugar de resumirse como éxito de búsqueda. Si el proveedor devuelve más llamadas de herramienta de las solicitadas, se contabilizan y no se inicia otra búsqueda alternativa pagada. La documentación oficial describe `max_tool_calls` como límite de herramientas, pero las respuestas guardadas muestran una discrepancia del proveedor; no se afirma haber reparado internamente ese comportamiento externo. Se mantiene el cálculo conservador de reservas. Referencia: [herramienta web oficial de OpenAI](https://developers.openai.com/api/docs/guides/tools-web-search).

## Verificación sin coste en producción

- Borradores/candidatos **#38 y #39**: recuperados a `deferred / numeric_review_pending`, **1 intento y 2 correcciones conservados**. Solo requieren revisión con el nuevo contrato; no hay autorización de publicación fabricada.
- Candidato **#37, precios de APIs**: `ready`, con documentación completa de OpenAI, Google y Anthropic.
- Candidato **#40, contar tokens**: `ready`, documentación de Google y Anthropic.
- Candidato **#42, embeddings**: `ready`, documentación de OpenAI y Google.
- Las tres preparaciones usan el componente existente `prepare_candidate`, sin invocar generación. Sus documentos contienen 18.000 caracteres de texto almacenado por fuente, dentro del límite del catálogo.
- **Cero nuevas llamadas pagadas**: los 93 registros de consumo anteriores mantienen exactamente su huella; también coinciden los 22 artículos, las 19 jornadas y la cuenta existente con el backup previo. El preflight modificó únicamente la cola, caché y auditoría previstas.
- El gasto de hoy sigue siendo el de la ejecución anterior: **0,072468 USD**; disponible diario **0,427532 USD**, mensual **14,423882 USD**. No se modificó `production.env`.

## Pruebas

- Suite final local: **527 correctas, 107 omitidas** por requisitos de servicios/entornos específicos.
- Selección relevante bajo **Python 3.12**, sin red ni claves: **171 correctas**.
- PostgreSQL 17 y Redis 7 aislados: **10 correctas**; presupuesto concurrente diario/mensual, cuotas, duplicados, slots y liquidación idempotente. Se inicializó la base dedicada de pruebas con Alembic; no se usó la base de producción. Persisten dos avisos antiguos de configuración `path_separator` de Alembic.
- **21 regresiones nuevas** con borradores/respuestas reales guardados, cobertura numérica restringida, edición posterior, caché de documentos, presupuesto de descargas, recuperación RSS y gzip seguro.
- Dos simulaciones completan el trabajador, revisión y publicación en una base de pruebas, con comprobación de HTML, canonical y sitemap mediante transporte simulado. **No son publicaciones reales.** Los cambios de referencias del revisor son simulados y no se han presentado como una nueva respuesta real de OpenAI.
- La imagen de destino importa los diez módulos correctamente y valida los seis recibos de ejemplos existentes, sin ejecutar código generado ni llamar a servicios en el VPS.
- No fue necesario reconstruir Nuxt ni ejecutar TypeScript: el frontend no cambió. Portada, categorías, API, artículos previos, robots y sitemaps siguen respondiendo HTTP 200 con HTTPS válido.

## Despliegue y rollback

Backup completo cifrado en `/var/backups/foroia/blockersprod-20261108-final`: PostgreSQL, Redis, código/configuración y volúmenes/certificados Caddy. Cuatro copias descargadas fuera del VPS y verificadas mediante SHA-256. Restauración aislada correcta: **21 tablas con idénticas huellas**, Redis correcto e integridad de configuración y certificados comprobada.

Se construyó una imagen sobre la imagen previa exacta, sin instalar dependencias. Se comprobaron los permisos del usuario de ejecución y los hashes de los diez archivos antes de activarla. Imagen API/trabajador: `sha256:e80790686f16b4b65255ad471ff9e536968260cec847cbd5319b1f56adda04e9`.

Solo se recrearon API y trabajador. Web, PostgreSQL, Redis y Caddy conservan sus contenedores; PostgreSQL y Redis siguen sin puertos públicos. Todos los servicios están activos y API/web/DB/Redis saludables.

Rollback preparado en el mismo checkpoint: `rollback.py`, `rollback.yml`, `before-files.tgz` y `release.json`. Restaura fuentes e imágenes anteriores, sin restaurar una base antigua sobre los datos actuales ni borrar artículos, reservas o historial. No fue necesario ejecutarlo.

## Archivos

Backend: `research/numbers.py` (nuevo), `writing.py`, `evidence.py`, `quality.py`, `recovery.py`, `documents.py`, `queue.py`, `editorial.py`, `news_recovery.py`, `sources.py`.

Pruebas: `tests/test_publication_blockers.py`, `tests/fixtures/numeric_review_failures_20261108.json`. Este informe y enlaces de estado en documentación. Herramientas operativas y resultados privados bajo `.local/deploy/blockersprod-*`.

## Límites que permanecen

Una fuente que devuelve 403 sigue sin estar verificada. La recuperación RSS necesita un anuncio pertinente y un documento accesible con fecha válida; no garantiza encontrar noticia todos los días. La revisión nueva de los dos borradores debe ejecutarse realmente y puede rechazarlos si descubre otros problemas. No se promete una publicación ni indexación de Google por haber pasado pruebas simuladas.
