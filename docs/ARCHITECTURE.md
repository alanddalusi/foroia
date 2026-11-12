# Arquitectura

08/11/2026: [contrato de citas numéricas y recuperación documental desplegados](PUBLICATION_BLOCKERS_FIXED_2026_11_08.md). La revisión añade referencias numéricas restringidas por esquema y verificadas por servidor; recuperación de borradores antiguos solo a revisión, conservando correcciones e historial. Google usa cinco representaciones Markdown oficiales curadas; gzip con límites y alternativa a propuestas fallidas desde los RSS ya descargados, dentro del trabajador existente. Sin nuevas dependencias, migraciones, programación o límites.

06/11/2026, producción: [recuperación y tres slots](EDITORIAL_RECOVERY_DEPLOY_REAL_2026_11_06.md), migración `0011`, flags y presupuesto 0,50/15 activados. Jornada real #17 completa noticia #18, recuperación gratuita #16 y práctico #19. Se mantienen bloqueo, cuotas y planificador únicos. El detalle distingue búsqueda sin candidatos, recuperación de cola y borradores aún bloqueados.

05/11/2026, solo local: [recuperación y tres slots](EDITORIAL_RECOVERY_THREE_ARTICLES_2026_11_05.md). `0011_recoverable_editorial` añade estados y slot práctico persistido; el mismo trabajador comparte bloqueo, cuotas finales y presupuesto atómico. Correcciones dirigidas reutilizan borradores; recuperación de publicación aprobada sin modelo y con protección frente a ediciones. Configuración nueva desactivada por defecto; sin despliegue ni cambios de gasto en producción.

04/11/2026, desplegado: `0010_editorial_lanes` y `RESEARCH_TWO_LANES=true`, sin cambiar presupuesto ni planificador. Recibos verificados contra la imagen transportada. Pasada diaria #15 sin publicación; ejecución controlada #7 completa el artículo FastAPI #15 con validación pública. [Despliegue, costes, rollback y límites reales](EDITORIAL_PHASES_1_2_DEPLOY_2026_11_04.md).

04/11/2026, solo local: `0010_editorial_lanes` añade dos espacios persistentes bajo el mismo `ResearchRun`. `LaneRun` reutiliza selección, revisión y publicación, reserva en la cuenta diaria y separa los fallos. La bandera `RESEARCH_TWO_LANES` permanece desactivada; no se añade planificador. Recibos ligados a imagen/dependencias, recuperación selectiva de ejemplos y feedback de estructura. [Implementación, pruebas y pasos de activación](EDITORIAL_PHASES_1_2_2026_11_04.md).

31/10/2026: `discover_document_opportunities` deja de fabricar temas de encabezados y agrupa el legado con el catálogo de necesidades existente. `opportunity` aporta evaluación editorial y títulos/resúmenes relacionados al escritor/revisor, sin demanda inventada. El panel distingue recuentos de artículos actuales, trabajos manuales, eventos históricos e identificadores. [Auditoría, cambios de cola y verificaciones](EDITORIAL_SEO_SELECTION_2026_10_31.md).

31/10/2026: `research.style` añade comprobaciones locales de repetición y estructura; el `Review` existente exige naturalidad, ausencia de redundancias, estructura proporcionada y atribución clara. `quality.prepare` aplica la misma corrección acotada sin llamadas adicionales de revisión. La atribución oficial se comprueba en el contexto inicial y por el revisor para afirmaciones comerciales, sin exigirla en cada párrafo. [Despliegue y pruebas](NATURAL_EDITORIAL_STYLE_2026_10_31.md).

29/10/2026, desplegado: `editorial_policy` deriva el modo de verificación de los documentos recuperados. Una fuente oficial propia admite `official_announcement`; el resto conserva `independently_corroborated`. Selección, cola, generación y validación final comparten esa política. Recuperación de borrador sin nueva investigación/redacción y publicación real verificadas. [Pruebas, costes y resultado](OFFICIAL_NEWS_DEPLOY_REAL_2026_10_29.md).

29/10/2026: `event_sources` define entradas oficiales y consultas por acontecimiento. `news_recovery` agota la recuperación gratuita y puede usar un único checkpoint `SourceRecovery` a través del mismo reservador atómico de `night_web.research`. Sin otro trabajador ni planificador. [Contratos, límites, reproducción y despliegue](EVENT_SOURCE_RECOVERY_2026_10_29.md).

29/10/2026: `night_web.discover` delega la recuperación acotada en `news_recovery`, dentro del coordinador nocturno existente. `news_gate` comprueba correspondencia entre acontecimientos y documentos antes de la selección y generación. No hay un segundo trabajador ni nuevo planificador. [Implementación, casos reales, pruebas y despliegue](NEWS_RECOVERY_2026_10_29.md).

Multimedia del 28/10/2026: `articles.media` conserva metadatos y `article_assets` los WebP/PNG originales; el trabajador genera ambos antes de publicar, sin llamadas adicionales a IA. [Arquitectura, límites, pruebas y rollback](MULTIMEDIA_2026_10_28.md). Presupuesto de producción: 10 USD/mes y 0,15 USD/día.

28/10/2026: [investigación web y publicación real completadas](NEWS_PUBLISHED_2026_10_28.md). Recuperación entre jornadas, cifras con separadores locales y liquidación idempotente de reservas comprobadas; se conserva el único planificador diario.

Configuración vigente del 27/10/2026: [investigación web única a las 22:30](NIGHTLY_WEB_2026_10_27.md). `night_web` propone candidatos con Responses `web_search`; los documentos originales y su corroboración se verifican antes de incorporarlos a `EditorialCandidate`. El mismo coordinador genera, revisa y publica por prioridad bajo el presupuesto compartido. La tarea periódica rápida descrita a continuación es histórica y ya no se inicia; sus datos se conservan.

Detección de noticias de media hora: [arquitectura implementada, pruebas y operación](RAPID_NEWS_2026_10_27.md). Se ejecuta en el trabajador existente como tarea de observación gratuita, persiste acontecimientos en la cola editorial actual y entrega los trabajos al mismo proceso de validación/publicación. La bandera rápida es independiente de la ejecución nocturna de las 22:30; las reservas son compartidas y atómicas.

```text
Internet → reverse proxy TLS/CDN → Nuxt SSR → FastAPI → PostgreSQL
                                      ↘ Redis (caché / límites / colas)
```

- `web/`: presentación pública SSR; no exponer secretos al navegador.
- `api/`: API pública y escrituras autorizadas por sesión, rol y recurso.
- `api/alembic/`: migraciones versionadas. `db/schema.sql` es una referencia histórica; no se ejecuta en el arranque.
- `docs/`: decisiones técnicas, SEO y seguridad.
- `tests/`: verificaciones automatizadas.

## Límites del MVP
Hay blog, panel editorial, cuentas y comentarios moderados. El foro sigue siendo de lectura. El entorno Compose incluye correo local de pruebas; faltan seguridad operativa, configuración de correo real y cumplimiento antes de abrirlo al público.

## Decisiones futuras
- Sesiones seguras con cookies HttpOnly/Secure/SameSite y CSRF para escrituras; política de sesiones documentada.
- RBAC: visitante, miembro, moderador, administrador. Autorización por recurso en backend.
- Auditoría de moderación y cola de revisión.
- Tareas asíncronas para email, notificaciones e indexación.
- Índices compuestos y paginación keyset al crecer.

## Cuentas y comentarios del blog — requisito acordado

Implementado mediante `0003_accounts_comments`. Operación y límites en `docs/ACCOUNTS.md`.

- Los visitantes pueden leer artículos y comentarios aprobados. Para comentar se exige registro, email verificado y sesión válida; el servidor obtiene el autor de la sesión, nunca de un identificador enviado por el cliente.
- Incluir registro, login, logout, verificación de email y recuperación de contraseña. Contraseñas con Argon2id; sesiones revocables en cookies HttpOnly, Secure en producción y SameSite, protección CSRF y límites para autenticación y escrituras. No exponer correos en perfiles ni respuestas públicas.
- Guardar en PostgreSQL usuarios, sesiones, artículos y comentarios mediante migraciones Alembic. Cada comentario referencia artículo y autor e incluye texto, estado, fecha de creación y actualización. Registrar decisiones de moderación en auditoría. No modificar manualmente el esquema inicial para introducir estas entidades.
- Comentarios en texto plano, entre 1 y 5.000 caracteres tras eliminar espacios exteriores; escape en la presentación, sin ejecutar HTML. Inicialmente comentarios planos, sin hilos anidados.
- Los comentarios de usuarios nuevos quedan pendientes hasta aprobación. Solo se permite comentar en artículos publicados con comentarios habilitados; impedir escrituras de cuentas bloqueadas. Mantener rate limiting y controles antispam también para cuentas verificadas.
- El autor puede editar o retirar sus comentarios; una edición vuelve a revisión y deja de mostrarse públicamente hasta aprobarse. Moderadores pueden aprobar, rechazar o retirar con auditoría. Verificar permisos en servidor para cada operación.
- Las lecturas públicas solo devuelven comentarios aprobados de artículos publicados. Los pendientes, rechazados y retirados no aparecen en HTML público, API pública, contadores ni caché compartida. El autor puede consultar el estado de sus comentarios mediante una ruta privada.
- Listados de 20 comentarios por defecto y máximo de 50, con cursor estable por fecha e identificador. Índice compuesto por artículo, estado, fecha e identificador, e índice por autor para su historial. Consultas acotadas y sin N+1; medir con EXPLAIN y pruebas representativas antes de afirmar objetivos de rendimiento.
- Redis se usará para límites y, si es necesario, caché de lecturas públicas; PostgreSQL será la fuente persistente de los comentarios. Invalidar caché cuando cambie su visibilidad o la del artículo.

Antes de habilitar comentarios, verificar con pruebas autenticación, CSRF, permisos entre usuarios, moderación de nuevos usuarios, edición, artículos no publicados, bloqueo de cuentas, paginación, límites, inyección SQL/XSS y ausencia de contenido privado en respuestas y cachés públicas. Implementar después de estabilizar el arranque y las migraciones, respetando el orden de AGENTS.md.

## Blog y panel editorial — implementado (v0.2)

- Migraciones Alembic en `api/alembic/` (`0001` adopta el esquema de `db/schema.sql`, `0002` crea `articles` y `audit_logs`). La API ejecuta `alembic upgrade head` al arrancar (válido con una réplica).
- API modular: `app/core/` (settings, DB), `app/modules/forum.py`, `app/modules/articles/` (`public.py` lectura pública solo `published`; `editorial.py` escritura).
- Flujo: `draft → review → published → archived`. Publicar exige revisión, ≥1 fuente y ≥300 caracteres; cada cambio se registra en `audit_logs`. El slug no cambia una vez publicado (faltan redirecciones 301).
- Cuerpo en texto con formato mínimo (`##`, `###`, `- `, bloques ```), renderizado escapado por `ArticleBody.vue`; nunca `v-html`. JSON-LD se serializa escapando `<`, `>` y `&`.
- Rutas públicas: `/`, `/blog/<seccion>` (`?pagina=N`, noindex si vacía), `/articulos/<slug>`. Sitemap con artículos publicados y secciones con contenido.
- Panel `/editorial` (SPA, `noindex`, `no-store`): sesión opaca HttpOnly validada por servidor y rol `editor` o `admin`. Sin Basic Auth en la web. JSON, comprobación de Origin y token CSRF en mutaciones. El token interno solo autentica el origen de la IP transmitida por Nuxt; no concede permisos editoriales con la configuración normal.
- Portada, artículos, secciones, sitemap y APIs sin caché compartida: prioridad a la retirada inmediata de contenido. Mantener esta garantía al introducir caché futura. El foro histórico aún usa SWR de 60 s.
- Pendiente: redirecciones 301, búsqueda y automatización editorial. El sitemap sigue limitado a 50.000 artículos en un archivo; hay que dividirlo antes de superar ese volumen.
