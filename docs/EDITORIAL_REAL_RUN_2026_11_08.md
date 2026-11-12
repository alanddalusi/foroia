# Ejecución real adelantada — 8 de noviembre de 2026

Ejecutado el trabajador existente con `--once`, a petición del propietario. Sin mocks, cambios de configuración ni inserciones manuales. Preflight: jornada pendiente, bloqueo libre, cero trabajos manuales activos y límites de 0,50 USD/día y 15 USD/mes.

## Resultado

Jornada #19, aproximadamente 02:56–02:59 Europe/Madrid: **0 de 3 publicaciones**, `skipped / no_verified_publication`. No se ha conseguido una publicación real con esta ejecución.

| Línea/candidato | Resultado |
| --- | --- |
| Actualidad | Una propuesta con esquema válido; cero documentos verificados. Fuentes OpenAI bloqueadas con HTTP 403 y cobertura alternativa no relacionada con el acontecimiento. No se redactó una noticia sin evidencia. |
| #38 Límites de APIs | Borrador #20 reanudado con segunda corrección y revisión reales. Revisor favorable, pero validador determinista rechaza `429` en el párrafo 1: `unsupported_number`. Estado final rechazado, 2/2 correcciones, borrador conservado. |
| #39 Errores de APIs | Borrador #21 reanudado con segunda corrección y revisión reales. Revisor favorable, pero validador rechaza `4` en el párrafo 1: `unsupported_number`. Estado final rechazado, 2/2 correcciones, borrador conservado. |
| #37 Costes, #40 Tokens, #42 Embeddings | `deferred / short_document`: documentación insuficiente; sin generación de esos candidatos. |
| #43 RAG, #44 Function calling, #45 Evaluaciones, #46 PDFs | `deferred / document_fetch_budget`: agotado el límite de recuperación de documentos de la pasada, no el presupuesto monetario. Candidatos conservados. |

La noticia termina con motivo `web_candidates_found`, un resumen impreciso: hubo descubrimiento pero no verificación ni publicación. Los informes detallados contienen los fallos. Los conflictos entre revisión y validación numérica necesitan reproducción sin coste y comparación con fragmentos/citas antes de calificarlos como falsos positivos. No se desactivaron controles.

La respuesta de investigación registra dos acciones `web_search`, aunque el máximo anunciado era una (`observed_tool_limit_exceeded=true`); la recuperación alternativa registra otra. Las tres acciones están contabilizadas dentro del presupuesto. Es necesario revisar este control de herramientas. No se hicieron búsquedas adicionales fuera del trabajador.

## Consumo y continuidad

Consumo total calculado con tokens y herramientas informados por la API: **0,072468 USD**, no conciliado con factura del proveedor. Reservas de la jornada liquidadas al mismo importe.

- Disponible hoy: **0,427532 USD**.
- Acumulado mensual reservado/contabilizado: **0,576118 USD**.
- Disponible mensual: **14,423882 USD**.
- Los límites económicos no causaron la ausencia de publicaciones.
- Próxima jornada confirmada en el panel autenticado: **9/11/2026, 22:30 Europe/Madrid**. La del día 8 queda adelantada y no se repite esta noche.

Bloqueo libre al terminar; los seis servicios activos y API/web/PostgreSQL/Redis saludables. PostgreSQL y Redis sin exposición pública. Portada, artículo previo de streaming, API correspondiente y ambos sitemaps responden HTTP 200. No hubo artículos nuevos que verificar ni afirmaciones de indexación.

Antes de más reintentos pagados conviene reparar y probar sin coste los conflictos numéricos y la recuperación de documentos: relanzar el mismo flujo puede repetir estos bloqueos.

Artefactos privados: `.local/deploy/manualdaily-20261108-full.json`, `manualdaily-20261108-final-overview.json`; registro del servidor `/var/log/foroia/manual-daily-20261108.log`. Solo se añadió este informe y un observador local; no se desplegó código ni se modificaron credenciales, DNS, firewall o programación.
