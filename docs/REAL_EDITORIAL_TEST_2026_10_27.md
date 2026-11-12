# Prueba editorial real del 27/10/2026

## Resultado comprobado

Se publicó y verificó un artículo real mediante el trabajador y la recuperación editorial existentes:

**[Convertir una respuesta JSON en CSV con Python sin romper columnas](https://foroiaaldia.com/articulos/convertir-json-csv-python-seguro)**

Publicación: **27/10/2026 a las 14:36:18, Europe/Madrid**. Artículo 6, candidato evergreen 2, jornada editorial 7. El artículo fue redactado y revisado con llamadas reales a OpenAI; la publicación quedó auditada como `auto_publish`, actor `automation`. No se insertó ni aprobó un artículo manualmente.

**La búsqueda de actualidad devolvió cero candidatos.** Por tanto, esta prueba demuestra una publicación real por el recorrido evergreen después de investigar, pero **no valida todavía el recorrido completo de una noticia actual encontrada y corroborada mediante web_search**. No significa que no hubiera noticias en Internet.

## Ejecución real y fuentes

La autorización del propietario permitió consumir la jornada y el saldo de hoy, conservando 0,15 USD diarios y 5 USD mensuales. No se exigió reservar también otra investigación para esta noche.

Se inició el mismo módulo editorial de producción:

```sh
python -u -m app.research.worker --once --max-publications 1
```

El límite de una publicación es puntual para esta prueba. El comando habitual del contenedor y su horario siguen iguales; no se añadió otro planificador.

| Fase | Evidencia y resultado real |
| --- | --- |
| Investigación | Responses API con `gpt-5-mini` y `web_search`, iniciada a las 14:17:59. La respuesta comunicó dos acciones `search`; JSON recibido: `{"candidates": []}`. |
| Noticias y fuentes encontradas | Ningún candidato y ninguna URL de fuente en los metadatos conservados. No se inventa una lista de noticias ni una explicación de ausencia de noticias global. |
| Cola de noticias previa | El candidato preexistente 14 no tenía documentos verificados suficientes; se rechazó con `insufficient_independent_topic_sources`. No fue un hallazgo de esta búsqueda. |
| Selección alternativa | Candidato evergreen 2: convertir JSON en CSV con Python. Documentación oficial y ejemplo con recibo de comprobación aislada. |
| Redacción | Una llamada real; borrador conservado como artículo 6, sin visibilidad pública hasta superar los controles. |
| Revisión | Una llamada real; aprobación con 27 comprobaciones de título, resumen, encabezados y afirmaciones. |
| Recuperación | Correcciones deterministas de contabilidad y enumeraciones; reutilización de la respuesta de revisión ya guardada, sin otra llamada facturable. |
| Publicación | Ejecución duradera 5 completada con gasto nuevo máximo autorizado de cero; publicación por `worker.pipeline` y comprobación pública existentes. |
| Verificación pública | HTTP 200, texto en HTML SSR inicial, canonical exacto, metadatos/datos estructurados, imagen, sitemap y enlaces desde portada y Programación. |

Fuentes del artículo:

- [Documentación oficial de csv — Python 3.12](https://docs.python.org/3.12/library/csv.html).
- [Documentación oficial de json — Python 3.12](https://docs.python.org/3.12/library/json.html).

El ejemplo es `json_csv`, verificado previamente en un entorno aislado. En esta prueba no se ejecutó código generado en el VPS ni se afirmó haber probado un servicio comercial.

## Incidencias reales corregidas

### Reserva de búsqueda retenida pese a disponer de uso comunicado

La petición llevaba `max_tool_calls=1`, pero la respuesta comunicó dos acciones `search`. La contabilidad anterior exigía exactamente ese límite esperado para liquidar el uso; por la discrepancia retuvo la reserva completa de **117.249 microUSD**. Tras reservar otros 23.055 microUSD para redactar, solo quedaban 9.696 microUSD reservables y se bloqueó la revisión.

La respuesta ya estaba guardada: 6.904 tokens de entrada, 416 de salida y dos acciones de búsqueda. Se corrigió la liquidación para aceptar uso completo observado **únicamente si su coste total cabe dentro de la reserva original**. Se contabilizaron ambas acciones, sin fingir que hubo una sola: **22.558 microUSD**. Se liberaron **94.691 microUSD de exceso confirmado**, preservando la reserva de redacción y todas las reservas históricas. La operación quedó auditada y no volvió a consultar OpenAI.

La discrepancia permanece registrada como `observed_tool_limit_exceeded`. Para futuras solicitudes se deshabilitó el paralelismo y se amplió el registro de identificadores de respuesta/herramienta, consultas y citas. **No se ha hecho otra búsqueda pagada para comprobar si el proveedor respeta el límite con esa configuración.** La primera versión no guardó los identificadores ni las consultas, de modo que no puede reconstruirse el detalle exacto de las búsquedas iniciales a partir de esos registros.

### Enumeraciones confundidas con cantidades sin evidencia

La revisión real aprobó el texto, pero el validador numérico trató los marcadores `1)`, `2)`, `3)` y `4)` como cantidades que debían aparecer en las citas. El fallo concreto afectó a los párrafos «Reglas básicas que aplicaremos (y por qué)» y «Resumen rápido de pasos».

Se añadió una excepción estrictamente tipográfica para enumeraciones consecutivas que empiezan por `1)` al inicio del párrafo. **Las cifras de precios, capacidades, versiones y cantidades siguen necesitando respaldo**. Los errores numéricos ahora identifican párrafo y cifra. Las pruebas incluyen los textos reales que fallaron y casos con cantidades sin apoyo que deben seguir rechazándose.

El intento de corrección posterior a aquella aprobación se detuvo antes de llamar a OpenAI, por el máximo de la ejecución de recuperación. No hubo una segunda redacción ni una segunda revisión de pago.

### Recuperación de la revisión aprobada y estado de la jornada

Se habilitó recuperar una revisión aprobada guardada aunque el fallo determinista hubiese dejado `pending_review=false`. La recuperación exige checkpoint de respuesta conocido, ausencia de llamadas inciertas, fuentes vigentes, texto sin modificaciones, revisión exhaustiva y nueva validación completa. No fabrica una aprobación ni modifica las afirmaciones para publicar.

La ejecución 4 pagó la revisión. Tras corregir el falso positivo, la ejecución 5 obtuvo presupuesto nuevo de **0 microUSD**, reutilizó ese checkpoint y publicó con los controles habituales. El ledger impidió contar o pagar dos veces la revisión. La jornada original quedó en `published`, con vínculo a la recuperación y sin reiniciar sus reservas.

## Consumo y reservas

Tres respuestas reales de OpenAI: investigación, redacción y revisión. Los importes son **costes calculados con uso real comunicado y tarifas registradas; no constituyen una factura verificada del proveedor**.

| Fase | Entrada | Salida | Coste calculado USD |
| --- | ---: | ---: | ---: |
| Investigación, incluidas dos acciones web | 6.904 | 416 | 0,022558 |
| Redacción | 11.797 | 1.941 | 0,006832 |
| Revisión | 18.922 | 2.988 | 0,010707 |
| **Total** | **37.623** | **5.345** | **0,040097** |
| Recuperación final del checkpoint | Sin nueva llamada | Sin nueva llamada | **0** |

- Reserva inicial máxima de búsqueda: **0,117249 USD**, liquidada a 0,022558 USD con el uso comunicado.
- Reservas conservadoras de redacción y revisión: **0,023055 + 0,025145 USD**. No se devolvieron sus márgenes.
- **Total reservado de la jornada: 0,070758 USD**.
- **Disponible para nuevas reservas hoy: 0,079242 USD**.
- Reservado este mes, incluida la historia anterior: **0,428980 USD**.
- **Disponible mensual: 4,571020 USD**.

Se mantienen los límites de 0,15 USD diarios y 5 USD mensuales. No se compraron servicios ni se alteraron credenciales.

## Estado de producción y programación

La jornada del **27/10 ya está realizada**. A las 22:30 el trabajador encontrará esa jornada y no iniciará otra investigación de pago para la misma fecha. La próxima ejecución automática indicada por el panel es:

**28/10/2026 a las 22:30 Europe/Madrid**.

Continúan habilitados trabajador y publicación automática. La detección de media hora sigue retirada. Siete servicios saludables, PostgreSQL/Redis sin exposición pública, configuración y secretos conservados. Se comprobaron los seis artículos públicos; los cinco anteriores conservan sus hashes. Historial económico anterior, usuarios, comentarios, categorías y temas no se alteraron.

El nuevo artículo aparece una vez en el sitemap, que ahora contiene 15 URLs públicas en dos archivos. Está enlazado desde portada y Programación. Esto demuestra accesibilidad e inclusión en sitemap, **no indexación confirmada por Google**.

## Cambios, pruebas y recuperación

Archivos de aplicación modificados en esta tarea:

- `api/app/research/worker.py`: límite puntual de publicaciones y auditoría del adelanto autorizado.
- `api/app/research/editorial.py`: límite por ejecución y reconocimiento seguro de revisiones aprobadas recuperables.
- `api/app/research/night_web.py`: liquidación del uso observado dentro de la reserva y desactivación del paralelismo.
- `api/app/research/writing.py`: diagnóstico de herramientas y distinción entre listas y cifras factuales.
- `api/app/research/executions.py`: recuperación de revisión guardada y actualización de la jornada tras verificación pública.

Pruebas locales separadas de esta ejecución real: **291 correctas, 67 opcionales omitidas**; regresiones con uso y párrafos reales anonimizados, presupuesto, texto modificado, revisión incierta y cifras genuinamente no respaldadas. Builds Docker correctos. Los fixtures y proveedores simulados se usaron exclusivamente en esas pruebas aisladas; no en las llamadas que redactaron y revisaron el artículo publicado.

Backups cifrados completos, copiados fuera del VPS y restaurados con hashes coincidentes de 19 tablas, Redis, configuración y Caddy:

- `/var/backups/foroia/realtest-20261027-final/`
- `/var/backups/foroia/settle-20261027-final/`
- `/var/backups/foroia/lists-20261027-final/`

Cada directorio conserva originales e imágenes anteriores y `rollback.py`. El último rollback revierte solo código/contenedores, sin restaurar una base antigua ni borrar la publicación, el historial o las reservas. No fue necesario aplicarlo: los fallos se corrigieron y se recuperó la etapa válida.

Evidencias privadas: `.local/deploy/realtest-live-20261027.json`, `realtest-review-feedback.json`, `realtest-number-diagnostic.json`, `realtest-usage-reconciled.json`, `realtest-replay-result.json`, `realtest-public-verified.json`, `realtest-integrity-verified.json` y `realtest-final-accounting.json`.

## Pendiente

La publicación del tutorial está demostrada. Sigue pendiente obtener una oportunidad actual con URLs verificables mediante búsqueda web y completar una publicación de noticia sobre ella. La nueva instrumentación permitirá diagnosticar consultas/resultados y la discrepancia de herramientas sin repetir búsquedas innecesarias ni superar el presupuesto. No se atribuye el resultado vacío a una causa que los registros iniciales no permiten conocer.
