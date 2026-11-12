# Recuperación y tres slots: despliegue y ejecución real

6 de noviembre de 2026. Despliegue, activación de presupuesto y prueba real autorizados expresamente por el propietario tras recibir el informe local.

**Resultado: tres espacios editoriales completados y verificados; dos artículos nuevos y uno recuperado.** No se ha demostrado todavía que se repita ese resultado todos los días.

## Desplegado realmente

- 23 archivos de backend, migración, panel, recibos y Compose. No se trasladaron los otros cambios locales del frontend.
- Migración aditiva `0011_recoverable_editorial`, estados recuperables y dos slots prácticos bajo el trabajador existente.
- `RESEARCH_TWO_LANES=true`, `RESEARCH_PRACTICAL_PUBLICATIONS=2`, **0,50 USD diarios y 15 USD mensuales**. Horario único **22:30 Europe/Madrid**.
- Corregidos el recorte de metadescripciones y la aceptación de `NewsArticle`; correcciones dirigidas y conservación de material pagado.
- Rehechos API, frontend y trabajador. PostgreSQL, Redis y Caddy conservaron sus contenedores. Sin cambios de DNS, firewall, SSH, credenciales, correo, GA4 o publicidad. Se verificó que las únicas líneas modificadas del entorno son las cuatro opciones editoriales autorizadas.

API local probada y transportada: `sha256:0fcc9e5738c432adbe6c3edb0d77d412e22aa4737627da3fb472619c6c6a5419`. El importador del VPS cambió su identificador a `sha256:665328a55a5d9b64c30f77d1a0bd663b31a117aca843d92165b138fa8f0f71b4`; se verificaron capas raíz y configuración idénticas. Se comprobaron seis ejemplos **fuera de producción**, con red desactivada y sin secretos, y se validó el recibo dentro de la imagen del VPS. Entorno: Python 3.12.15, FastAPI 0.149.0, Pydantic 2.14.1.

Frontend construido desde la fuente existente del servidor más los dos archivos de panel autorizados. TypeScript y build correctos; comprobación de ausencia de `node-forge` en el runtime superada.

## Backups, migración y rollback

Antes del cambio: `/var/backups/foroia/recoveryprod-20261106-final`. PostgreSQL, Redis, código/configuración y certificados cifrados y copiados fuera del VPS, con SHA256 contrastados. Restauración aislada: **21 tablas coincidentes**, Redis y archivos correctos.

Se aplicó además la migración nueva en otra restauración aislada antes de tocar producción: las 20 tablas ajenas a los slots conservaron sus huellas exactas y los slots conservaron todas sus filas.

Después de publicar: `/var/backups/foroia/recoverypost-20261106-final`, con otros cuatro archivos cifrados copiados fuera del VPS. Restauración aislada correcta de las **21 tablas**, Redis, configuración y certificados, incluyendo las publicaciones y reservas nuevas.

Rollback concreto guardado en `rollback.py` y `rollback.yml` del primer checkpoint. Restaura imágenes, archivos previos y entorno; conserva esquema aditivo, artículos, intentos y reservas. La API anterior arranca Uvicorn sin un Alembic antiguo que desconozca `0011`. No se ejecutó rollback porque las comprobaciones críticas fueron satisfactorias.

## Ejecución real #17

Ejecutada mediante `python -u -m app.research.worker --once` en producción, usando el mismo bloqueo y presupuesto de la jornada del **6/11**, sin simulaciones ni inserción manual de artículos. Comenzó aproximadamente a las 00:48 y terminó a las 00:51 Madrid.

| Línea | Resultado | Artículo |
|---|---|---|
| Actualidad | Corrección del borrador de Google Cloud de la cola y revisión aprobadas; publicado y verificado | [Qué anunció Google Cloud en IA este mes](https://foroiaaldia.com/articulos/que-anuncio-google-cloud-en-ia-este-mes), #18 |
| Práctico 1 | Recuperación de la publicación aprobada de Pydantic, sin nuevas llamadas al modelo | [Validar respuestas IA con Pydantic: esquema y límites](https://foroiaaldia.com/articulos/validar-respuestas-ia-pydantic-esquema-limites), #16 |
| Práctico 2 | Generación y revisión reales de una guía de Claude con Python; publicada y verificada | [api claude python: primera petición con Python](https://foroiaaldia.com/articulos/api-claude-python-primera-peticion), #19 |

Google Cloud se publicó a las **00:49 Madrid del 6/11**. Claude, a las **00:50**. Pydantic conserva su fecha original, **5/11 a las 16:42 Madrid**, además de URL y contenido. Es una recuperación, no un tercer artículo recién redactado.

El trabajador y una comprobación externa independiente verificaron las tres páginas: **HTTP 200, API pública, HTML SSR, canonical absoluto, descripción y etiquetas sociales, datos estructurados y fechas, imagen local y sitemap**. Se comprobó ausencia de `noindex` en `X-Robots-Tag`. Se revisaron también portada, categorías, robots, sitemap, API, protección del panel y redirección HTTP→HTTPS (308).

### Investigación actual y fuentes

La investigación Responses/web_search fue auténtica: **una acción de búsqueda**, 14.414 tokens de entrada y 2.164 de salida comunicados. Devolvió **cero candidatos nuevos**. No se declara que haya descubierto la noticia publicada en esta búsqueda.

La noticia se obtuvo de la cola anterior, aprovechando el borrador y las evidencias ya recuperadas. Fuente oficial: [recopilación de Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/what-google-cloud-announced-in-ai-this-month), registrada con fecha de origen **3/11/2026**. La recuperación evita presentarla como un anuncio recién sucedido hoy. La búsqueda reciente sin candidatos sigue siendo una limitación a seguir, no un éxito oculto bajo el resultado de la cola.

Fuentes de Pydantic: [modelos](https://pydantic.dev/docs/validation/latest/concepts/models/) y [strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/). Las fuentes concretas de Claude están enlazadas en la publicación; no se llamó a Anthropic ni se inventó una prueba de su API.

## Coste y saldo

| Concepto | USD calculados |
|---|---:|
| Investigación compartida, incluida búsqueda | 0,017932 |
| Corrección y revisión de Google Cloud | 0,012344 |
| Recuperación de Pydantic | **0,000000** |
| Corrección/revisión de OpenAI rechazada | 0,014468 |
| Redacción/revisión de Claude | 0,011415 |
| **Total de la ejecución** | **0,056159** |

Siete llamadas con uso registrado. Reserva final de hoy: **0,056159 USD**; saldo diario según reservas: **0,443841 USD**. Reserva mensual acumulada: **0,389674 USD**; saldo mensual: **14,610326 USD**. Se liquidaron solo reservas con respuesta y consumo conocidos. No se borró historial ni se aumentaron límites para completar candidatos.

Los importes se calculan con tokens/herramientas comunicados y tarifas configuradas; no son una factura del proveedor comprobada.

El panel confirmó las tres líneas `published / quality_checks_passed`, con costes separados y la investigación compartida aparte. El bloqueo quedó libre y el trabajador conserva su señal de vida.

## Datos y pendientes

Se conservaron los 17 slugs anteriores. Quince artículos/borradores mantienen exactamente su contenido, estado, autor y fuentes. Las excepciones autorizadas son Pydantic #16, recuperado, y el borrador OpenAI #17, corregido por el trabajador y conservado sin publicar tras no aprobar la revisión. Se añadieron los artículos #18 y #19. No se eliminó contenido.

Pendientes comprobados en la ejecución:

- SQLite #3, Unicode #4 y JSON #10 se detuvieron con `article_changed`. No se sobreescribieron sus filas. Hay que comparar el material histórico y el borrador persistido antes de permitir otra recuperación; no afirmar sin más que los editó una persona ni retirar esta protección.
- Gemini #8 y la primera petición Gemini #35 devolvieron `short_document`; quedaron pospuestos sin gastar en generación durante esta prueba.
- OpenAI con Python #34 agotó sus dos correcciones y recibió `review_rejected`. El borrador se conserva y no se publica para completar una cuota.
- NVIDIA #33 permanece `correction_pending`; Google Cloud ocupó el único slot de noticias de hoy.
- El duplicado #7 y el candidato #14 sin evidencia suficiente siguen rechazados.
- La búsqueda nueva no aportó candidatos. La continuidad de la cola no demuestra que la detección diaria de noticias esté resuelta de forma fiable.

La ejecución de hoy quedó consumida. Próximo turno confirmado en el panel: **7 de noviembre de 2026 a las 22:30 Europe/Madrid**. No se repetirá una investigación pagada a las 22:30 del día 6. No se ha afirmado indexación en Google ni una garantía de tres artículos nuevos diarios.
