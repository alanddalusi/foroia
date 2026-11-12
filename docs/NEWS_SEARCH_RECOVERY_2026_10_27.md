# Investigación de actualidad: recuperación del 27/10/2026

La prueba real encontró cinco propuestas con Responses `web_search`. Las primeras verificaciones fallaron porque las URLs estaban envueltas en Markdown o apuntaban a índices, y porque no se reconocían algunas fechas originales.

Se corrigieron la normalización de enlaces, extracción de artículos, fechas, conservación de titulares y recuperación desde fuentes permitidas. No se eludieron 403 ni se repitió la búsqueda de pago. Se conservaron los controles de independencia y veracidad.

El candidato seleccionado utilizó un comunicado original de Anthropic y cobertura independiente de TechCrunch. Su borrador y respuestas quedaron conservados al fallar controles de atribución de metadatos y separadores numéricos. Se corrigieron esos falsos rechazos manteniendo la revisión editorial completa.

**Resultado final: noticia real publicada y verificada el 28/10/2026.** Véase [publicación, correcciones, pruebas, costes y próxima ejecución](NEWS_PUBLISHED_2026_10_28.md).

`python -m app.research.worker --resume-news-run ID` permite al operador retomar una búsqueda ya respondida y contabilizada del mismo día. Conserva clave, historial, reservas y bloqueo de concurrencia; utiliza el coordinador existente, sin evergreen ni una nueva búsqueda. No constituye un segundo planificador.
