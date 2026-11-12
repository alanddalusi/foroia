# Prueba real de noticias — 29/10/2026, 10:32 Madrid

Resultado: ejecución real completada **sin nueva publicación**. La investigación respondió, pero ninguna de sus cinco propuestas reunió evidencia suficiente. No se declara éxito de extremo a extremo.

Se ejecutó `python -m app.research.worker --retry-news-run 9` en el contenedor del trabajador de producción. Este mecanismo existente conserva la jornada, el historial previo, el presupuesto atómico y el bloqueo Redis. Máximo una publicación y sin sustitución evergreen en esta prueba. No se cambió código, configuración, límites ni horario para ejecutarla.

## Fases

1. Preflight: trabajador libre, sin trabajo manual concurrente ni respuestas inciertas. Presupuesto disponible: 0,099548 USD. Reserva máxima de investigación: 0,054553 USD.
2. OpenAI Responses con `web_search`: respuesta real, una llamada de herramienta registrada y cinco propuestas válidas en su esquema. El resumen escrito por el modelo enumera consultas; no se confunde ese texto con el número de llamadas de herramienta realmente informado.
3. Recuperación y verificación: las cinco propuestas fueron descartadas antes de redactar. Se conservaron estados HTTP, URL y causas por documento.
4. Redacción, revisión y publicación: no se ejecutaron porque no hubo candidata verificada. No existe una URL nueva que comprobar.

| Propuesta del modelo | Resultado real del trabajador |
| --- | --- |
| OpenAI DevDay | El índice oficial devolvió 403. Los documentos alternativos trataban otros acontecimientos. No se eludió el bloqueo. |
| Colaboración Oracle–OpenAI | El comunicado original devolvió 403. Las alternativas consultadas no corroboraban esa colaboración. |
| AMD–Meta | La única URL propuesta estaba en Nasdaq, fuera del registro permitido. Las publicaciones de Meta recuperadas trataban otros acontecimientos. No se atribuyó el comunicado sindicado a una organización independiente. |
| Presentación S-1 de Anthropic | Detectada como acontecimiento ya publicado; no se duplicó. |
| Seguimiento de la salida a bolsa de Anthropic | Yahoo no estaba permitido; Axios devolvió 403 y Tom’s Hardware excedió el límite de descarga. Los dos documentos accesibles procedían de TechCrunch y no equivalen a dos organizaciones. |

El motivo global `news_only_no_verified_publication` indica que la prueba terminó antes de encargar contenido, no que fallase la publicación de un artículo aprobado. Algunos motivos resumidos son `document_unrelated` porque incluyen documentos alternativos rechazados; los diagnósticos detallados conservan también el 403 de la fuente original.

## Diagnóstico adicional gratuito

Una comprobación externa encontró el [comunicado original de AMD](https://ir.amd.com/news-events/press-releases/detail/1302/amd-and-meta-advance-strategic-partnership-to-power-metas-superintelligence-infrastructure) y su [versión en AMD Newsroom](https://newsroom.amd.com/news/amd-meta-advance-strategic-partnership-power-metas-ai-infrastructure/). Esto identifica una carencia de cobertura del recuperador: no convirtió la referencia sindicada en una fuente directa de AMD. No demuestra que exista corroboración independiente suficiente ni se incorporó manualmente un artículo a la cola para aparentar autonomía. Los dominios no se habilitaron automáticamente por aparecer en una respuesta de búsqueda.

## Costes

- Investigación: 9.668 tokens de entrada, 2.388 de salida y una llamada `web_search`.
- Coste calculado con el uso comunicado: **0,017193 USD**, de los que 0,010000 corresponden a búsqueda y 0,007193 a tokens. Factura del proveedor no verificada.
- Redacción, revisión y correcciones de esta prueba: **0 USD**.
- Reserva máxima inicial liquidada contra uso conocido; no se cobró toda la estimación como si fuera consumo real.
- Total conservado para la jornada 29/10, incluidas sus ejecuciones anteriores: **0,067645 USD**.
- Capacidad de reserva restante diaria: **0,082355 USD**. Mensual: **9,404097 USD**.
- Límites intactos: 0,15 USD diarios y 10 USD mensuales.

## Comprobación posterior

El trabajador liberó su bloqueo y permanece activo. API, portada, sitemap, robots y los siete artículos existentes responden HTTP 200. No se insertó contenido de prueba ni se convirtió un descarte en publicación manual.

La jornada de hoy sigue marcada como ejecutada; próxima ejecución ordinaria **30/10/2026 a las 22:30 Europe/Madrid**. El disparador diario no fue modificado.

Pendiente para conseguir una nueva noticia: recuperar una fuente original accesible y corroboración independiente del mismo acontecimiento, dentro del registro permitido. Las respuestas actuales no justifican desactivar controles ni repetir la investigación de pago con la misma consulta.
