# Dos publicaciones diarias: diagnóstico y plan de implementación

Fecha: 4 de noviembre de 2026. Estado: **plan y simulación local; no implementado ni desplegado**.

## Decisión propuesta

Una única jornada a las **22:30 Europe/Madrid**, con dos objetivos: una noticia y un artículo práctico. Se reutilizan `ResearchRun`, `EditorialCandidate`, el bloqueo Redis, el reservador PostgreSQL, los checkpoints, los validadores, la revisión y la publicación verificada actuales. No se crea otro planificador.

Los límites activos, comprobados mediante lectura del trabajador, son **0,20 USD/día y 10 USD/mes**. Los **0,40 USD/día y 12 USD/mes** son una propuesta pendiente de validación y activación autorizada posterior. No se han cambiado variables ni realizado llamadas a OpenAI.

El objetivo es condicionado a evidencia, calidad y presupuesto. Dos artículos publicados no equivalen a cumplir ambas líneas si los dos son prácticos: el panel debe mostrar la ausencia de noticia y su sustitución explícita.

## Diagnóstico comprobado

| Hallazgo | Evidencia | Consecuencia y corrección propuesta |
|---|---|---|
| Las líneas actuales no son independientes | `editorial.execute`: `if engine=='evergreen' and publications:break`; límite predeterminado `max_publications=1`; retorno tras publicar evergreen | Una noticia impide el práctico. Sustituir esos cortes por cuotas por línea, manteniendo una jornada y un presupuesto. |
| Algunos errores de investigación bloquean expresamente evergreen | `research_failed_no_evergreen_substitution`; retornos globales por `provider_unavailable`, `incomplete_generation`, presupuesto o verificación pendiente | Registrar el fallo en la línea afectada y continuar la otra si tiene material válido y presupuesto reservado. Pausa, pérdida del bloqueo y corrupción contable siguen deteniendo toda la jornada. |
| Seis ejemplos rechazados antes de generar | Recibo montado `/app/receipts/verified-examples.json`: coincide código y runtime, **no coincide `dependency_sha256`**. Runtime de ambos: Python 3.12.15, FastAPI 0.149.0, Pydantic 2.14.1 | `example_not_verified` es un rechazo de seguridad correcto ante un artefacto desalineado. Regenerar recibo en runner local/CI con la imagen/dependencias del despliegue; verificarlo antes de activar el release. No desactivar esta comprobación. |
| El validador nocturno de ejemplos no los vuelve a ejecutar | `scripts/verify_editorial_examples.py --check-receipt`; servicio existente a las 22:20 solo verifica recibos | No puede reparar un recibo inválido. La reparación debe formar parte del build/release, fuera de producción; conservar ese control gratuito. |
| Cola práctica agotada | 31 candidatos: 4 evergreen publicados, 3 aplazados, 21 rechazados; noticias: 2 publicadas y 1 rechazada. Solo son elegibles tres prácticos, los tres bloqueados por ejemplos | No hay reserva de artículos completos. Renovar intenciones concretas y recuperar únicamente candidatos cuyo motivo haya sido resuelto, con auditoría; no reabrir todos los rechazados. |
| Catálogo corto y concentrado | `blueprints.py`: 11 hipótesis, seis de programación y varias de prompts/JSON | No sostiene 30 prácticos distintos. Ampliar catálogo, rotación y renovación verificable. Un candidato no es un artículo listo. |
| Fallo de estilo con causa identificable | Jornada 2/11, candidato 10: primera versión seis apartados/384 palabras; corrección seis/336, rechazada por `oversegmented` | La corrección no resolvió la estructura. Instrucciones y feedback deben pedir agrupación concreta, sin alargar por rellenar. Probar guías con pasos legítimos y noticias breves; no eliminar controles indiscriminadamente. |
| Ventana de actualidad limitada a 48 horas en varias capas | `night_web.payload`, `news_recovery.document`, `queue.prepare_candidate`; feeds y colectores también filtran fechas | Cambiar solo el prompt a siete días no funcionaría. Propagar una política explícita de ventana por todas las capas afectadas y conservar la fecha original del acontecimiento. |
| Hay infraestructura reutilizable | Checkpoints de peticiones/respuestas, recuperación de revisión, claves únicas, transacción final y verificación pública | Extenderla por línea y candidato. No volver a generar un texto ya aprobado ni duplicar sistemas. |
| Los topes propuestos todavía no son aceptados por configuración | `ResearchSettings` limita `daily_usd <= 0.20`, `monthly_usd <= 10`; Compose fija los valores actuales | La subida requiere código, tests y configuración explícitos posteriores. No basta cambiar `.env`. |

Las jornadas 1, 2 y 3 de noviembre acabaron sin publicaciones; sus motivos finales fueron `no_viable_candidate`, `editorial_style_rejected` y `example_not_verified`. El 31 de octubre sí consta una publicación automática. Los motivos finales no sustituyen el historial de cada candidato.

## Costes y simulación reproducible

Modelo auditado: `gpt-5-mini`. La [ficha oficial](https://developers.openai.com/api/docs/models/gpt-5-mini) indica 0,25 USD/millón de tokens de entrada, 0,025 de entrada cacheada y 2 de salida. [Web search](https://developers.openai.com/api/docs/pricing) añade 0,01 USD por llamada más tokens de contenido. Los tokens de razonamiento forman parte de la salida comunicada; no se suman otra vez. No se presupone descuento de caché futuro.

La ficha consultada marca el modelo como deprecated: comprobar disponibilidad y calendario de retirada antes de implementar. No se ha cambiado de modelo; una migración exigiría sus propios contratos y nueva simulación de tarifas. Esta marca no demuestra que sea la causa de los rechazos observados.

Muestra: **46 registros reales `GenerationUsage`**, anonimizados en `tests/fixtures/editorial_capacity_20261104.json`. Son costes calculados con uso comunicado por la API y tarifa configurada; **no facturas verificadas**. Incluyen ejecuciones fallidas y reintentos históricos; no constituyen una muestra de 46 artículos válidos.

| Fase | Llamadas observadas | Mediana USD | Máximo observado USD |
|---|---:|---:|---:|
| Investigación | 11 | 0,017220 | 0,026333 |
| Recuperación alternativa | 5 | 0,015098 | 0,023215 |
| Redacción/corrección | 17 | 0,005317 | 0,007594 |
| Revisión | 13 | 0,007573 | 0,010707 |

Se calcularon también reservas con los constructores reales de peticiones, sin enviarlas: investigación 0,054427 USD; noticia borrador/revisión/corrección 0,014978/0,013540/0,011892; práctico 0,015261/0,014099/0,012226. Son **fixtures representativas** de anuncio oficial y tutorial, no máximos universales: documentos y artículos mayores aumentarán la reserva. La recuperación se modela conservadoramente con la misma reserva de búsqueda de la fixture, no como una medición exacta de todas sus peticiones.

| Escenario de 30 días | Consumo modelado USD | Límite 0,20/día, 10/mes | Límite propuesto 0,40/día, 12/mes |
|---|---:|---:|---:|
| Una búsqueda y dos pares redacción/revisión diarios, a medianas observadas | 1,290000 | 60 artículos hipotéticos | 60 hipotéticos |
| Búsqueda, recuperación y una corrección con nueva revisión **por cada artículo**, todos a máximos observados | 3,682560 | 60 hipotéticos | 60 hipotéticos |
| Sensibilidad: duplicar costes y reservas del escenario anterior | 5,169000 / 7,365120 | 30 hipotéticos; se bloquea la segunda línea por reserva diaria | 60 hipotéticos; pico de reserva diaria 0,252288 |

En sensibilidad, el gasto menor con 0,20 es consecuencia de llamadas bloqueadas, no de mayor eficiencia. El pico del escenario exigente observado es 0,126144 USD/día. El cálculo no demuestra que los modelos aprueben contenido ni que existan noticias suficientes; **no es un test de extremo a extremo del futuro coordinador**.

El depósito inicial añade trabajo, no artículos gratuitos: nueve pares redacción/revisión suponen **0,116010 USD** a las medianas observadas o **0,164709 USD** a los máximos; con una corrección y nueva revisión por artículo serían **0,329418 USD**. Si se producen 60 artículos y además se termina el mes con nueve aprobados sin publicar, el escenario exigente suma **4,011978 USD**; con sensibilidad duplicada, **8,023956 USD**. Estos importes adicionales son aritmética del inventario, no una prueba de que quepan todas sus reservas en una noche: repartir el relleno entre jornadas con margen. Fuentes no recuperables, ejemplos nuevos y aprobación editorial pueden impedir completarlo. Durante el arranque todavía no habrá nueve artículos disponibles para cubrir fallos.

Una búsqueda con resultado incierto conserva los 0,054427 de reserva representativa: el modelo comprueba que aún cabe reservar el práctico, sin inventar consumo cero. Producción deberá aplicar además bloqueo de filas y pruebas de concurrencia reales en PostgreSQL.

**Conclusión:** 0,20/10 parece económicamente suficiente para cargas similares a esta pequeña muestra, pero la arquitectura y los bloqueos actuales impiden aprovecharlo. 0,40/12 añade margen ante contextos/correcciones mayores; no garantiza 60 publicaciones ni justifica gastar más sin resultados.

0,20 × 30 = 6 USD: subir solo el límite mensual actual no cambia la capacidad diaria. 0,40 × 30 = 12 USD deja cero margen si se agotara cada día. En meses de 31 días, 12 USD permiten una media máxima aproximada de 0,387096 diarios desde saldo íntegro; reservas anteriores reducen esa cantidad.

Reproducción local, sin claves ni red:

```powershell
.local/venv/Scripts/python.exe scripts/simulate_editorial_capacity.py
$env:PYTHONPATH='api'
.local/venv/Scripts/python.exe -m pytest tests/test_editorial_capacity_simulation.py -q
```

## Arquitectura propuesta

1. **Una jornada y dos líneas persistentes.** Mantener `ResearchRun` como cuenta económica diaria. Añadir mediante Alembic una tabla hija de resultados por línea/slot, con unicidad `(run_id, slot)`, estado, candidato, artículo, motivo y checkpoints propios. Slots `news`, `practical` y, únicamente al sustituir una noticia ausente, `practical_replacement`. Las reservas globales no se duplican en tablas hijas.
2. **Cuotas:** máximo dos publicaciones nuevas por jornada, objetivo una por línea. Las actualizaciones de artículos existentes no cuentan como una publicación nueva. Si falta noticia, el segundo práctico es una sustitución identificada. La rotación principal Herramientas → Programación → Tutoriales se decide según publicaciones reales, no intentos; una sustitución elige otra sección si hay material válido y no adelanta dos veces el cursor principal.
3. **Aislamiento de errores:** checkpoints, artículo activo y errores por slot. Un HTTP 403, un rechazo editorial, una revisión pendiente o un timeout de una línea no cancela la otra. Presupuesto global insuficiente, pausa, pérdida de propiedad del bloqueo o inconsistencia contable sí impiden nuevas llamadas. Mantener un plazo por fase y reservar tiempo al práctico dentro del timeout total de la jornada.
4. **Presupuesto protegido antes de investigar.** Calcular reservas exactas de las peticiones disponibles, proteger al menos un par práctico redacción/revisión o usar el artículo de reserva. La búsqueda debe dejar también margen para convertir una noticia en publicación. La recuperación alternativa solo se permite si conserva ese margen. Reutilizar el bloqueo de `ResearchControl` y el libro de uso; no gastar dos veces una reserva ni liberar cargos inciertos.
5. **Límites por candidato:** preflight gratuito primero, una corrección como máximo según el contrato actual y continuación con otro candidato únicamente si cabe su recorrido. No repetir un rechazo determinista con la misma petición. Guardar respuestas y reanudar desde la última etapa válida; corregir/revisar solo lo pendiente. Cambiar de candidato no debe perder una reserva ni reasignar un cargo de búsqueda a un artículo equivocado.
6. **Actualidad:** 24–48 horas primero; si no hay candidato verificable, ampliar hasta siete días con una única política temporal coherente en búsqueda, recuperación, cola y validación. Reutilizar resultados y recuperación HTTP/RSS antes de otra búsqueda pagada. Fecha del acontecimiento, fecha de fuente y fecha de recuperación separadas. Fechas ambiguas/futuras, fuentes no relacionadas y duplicados siguen rechazándose. Presentar el anuncio con su fecha real, sin decir «hoy» cuando no corresponde.
7. **Reserva editorial:** objetivo inicial **9 artículos completos aprobados**, tres por sección; alerta por debajo de tres. No cuentan candidatos preparados solo con fuentes. Reutilizar `Article` en borrador, snapshots, evidencias, recibos y checkpoint aprobado. Guardar el digest del texto/evidencias/política/versiones de validadores; antes de publicar comprobar que sigue válido, no es duplicado y sus fuentes no han quedado obsoletas. Si cambia algo relevante, invalidar aprobación y volver solo a la etapa necesaria.
8. **Preparación de reserva dentro de la jornada:** rellenar el depósito después de cumplir las dos publicaciones y solo con saldo suficiente. Sin otra programación de OpenAI. El coste de preparar una reserva se registra cuando ocurre, aunque el artículo se publique otro día. Nunca contabilizarlo como gratuito ni cobrar otra generación al utilizarlo. El arranque del depósito requiere varios días o una preparación autorizada; no existe ya.
9. **Ejemplos:** CI/local ejecuta únicamente programas del catálogo revisado, en contenedores sin red, secretos ni escritura en raíz, con límites. El recibo acompaña a la imagen verificada; el release comprueba hashes y runtime dentro del trabajador real antes de activarlo. No ejecutar código arbitrario devuelto por modelos. Un ejemplo que depende de API externa no se presenta como probado por un test local.
10. **Estilo:** mantener revisión factual y semántica. Dar al redactor una estructura apropiada al tipo de contenido y feedback con sección/defecto concreto; detectar la corrección que reproduce el mismo fallo. Evaluar `oversegmented` con fixtures de noticias breves, guías procedimentales y bloques de código: corregir falsos positivos demostrados, conservar rechazos por fragmentación/repetición reales. No añadir texto para cruzar 350 palabras ni aprobar al agotar reintentos.

El actual `ready` significa **fuentes preparadas**, no texto aprobado. Añadir una distinción explícita de preparación en detalles/panel y comprobar el checkpoint; no publicarlo directamente por estar `ready`.

## Catálogo renovable de oportunidades prácticas

Preparar al menos 30 fichas activas, deduplicadas por tarea/resultado y contra los artículos existentes, más el depósito de nueve completos. Semillas a contrastar con documentación oficial antes de habilitarlas, no afirmaciones de demanda medida ni de interfaces probadas:

| Sección | Diez tareas iniciales a investigar y diferenciar |
|---|---|
| Herramientas | ChatGPT: localizar conversaciones propias; controles de datos y conservación; edición de textos con Canvas; Gemini: organizar un proyecto de estudio; AI Studio: revisar límites y permisos de claves; Claude: organizar proyectos/documentos; NotebookLM: audio y límites de las fuentes; Ollama: elegir modelo según memoria; LM Studio: privacidad de ejecución local; comparar tres herramientas por requisitos documentados de una misma tarea, sin rankings de rendimiento inventados. |
| Programación | Ejecutar una inferencia local y tratar timeouts; cliente HTTP con cancelación para un modelo local; endpoint FastAPI que transmite una respuesta local; ocultar claves y separar configuración de código; pruebas sin coste de errores 429 de un cliente; cargar documentos con límites y protección de rutas; búsqueda de texto para preparar contexto; medir latencia local sin llamarla benchmark comercial; pruebas de inyección de instrucciones con casos locales; cola SQLite de tareas para una aplicación de IA con reanudación segura. |
| Tutoriales | Preparar un corpus de apuntes para NotebookLM sin repetir las guías PDF ya publicadas; verificar una transcripción antes de resumirla; convertir una reunión en una lista de tareas sin inventar responsables; revisar respuestas con una rúbrica explícita; anonimizar un documento antes de usar IA; transcribir audio local con un modelo compatible; organizar permisos de una automatización; OCR local previo a una consulta; evaluar traducciones con un corpus propio; elaborar material de repaso y comprobarlo contra el documento original. |

Cada ficha necesita intención, diferencia frente al inventario, fuentes permitidas y accesibles, secciones, ejemplo/resultado esperado verificable cuando corresponda y limitaciones. Las fichas pueden descartarse si la funcionalidad no está disponible o no se puede verificar sin gasto/prueba externa. No se cargarán las 30 ciegamente.

Renovar al consumir fichas o cambiar documentación: detectar huecos del catálogo, proponer tareas concretas con documentos oficiales recuperables, deduplicar antes de generar, registrar origen y verificar. Los encabezados de documentación no vuelven a convertirse automáticamente en temas. Las señales de Search Console, si se configuran, complementan la selección; su ausencia no se sustituye por volúmenes inventados.

## Fases, archivos y criterios de paso

| Fase | Trabajo / archivos previstos | Esfuerzo estimado | Criterio de aceptación |
|---|---|---|---|
| 1. Reparar preparación y diagnóstico | `research/examples.py`, `scripts/verify_editorial_examples.py`, `.github/workflows/checks.yml`, despliegue de recibos; `quality.py`, `style.py`, `writing.py`; fixtures anónimas de los fallos reales | 0,5–1 día | Seis ejemplos válidos para la imagen candidata; dependencia/código/runtime incorrectos siguen bloqueando; feedback corrige el caso de seis apartados; cero API pagada. |
| 2. Independencia y presupuesto | `models.py`, nueva migración `0010_editorial_lanes.py`, `editorial.py`, `worker.py`, `checkpoints.py`, `executions.py`, `publication.py` | 1,5–2 días | Dos slots completos en simulación, fallo de una línea no bloquea la otra; timeout, reinicio y concurrencia PostgreSQL sin doble gasto/publicación. Compatibilidad con jornadas anteriores y ejecución manual. |
| 3. Noticias y variedad | `night_web.py`, `news_recovery.py`, `sources.py`, `queue.py`, `blueprints.py`, `opportunities.py`, política temporal compartida | 1–2 días | Un anuncio de cinco días puede validarse con su fecha real; uno de ocho/futuro/duplicado no. Rotación y tareas distintas; ampliar sin bucles pagados. |
| 4. Reserva reutilizable | `quality.py`, `queue.py`, `checkpoints.py`, `executions.py`, catálogo y recibos | 1–2 días | Texto aprobado persistente tras reiniciar; publicación sin nueva generación; aprobación invalidada si cambia texto/fuente/ejemplo/validador; recuento y coste de relleno correctos. |
| 5. Panel y despliegue gradual | `research/routes.py`, `web/pages/editorial/investigacion.vue`, `web/utils/research-status.ts`, proxies/tipos necesarios; `config.py`, `compose.production.yml`, ejemplos de entorno y documentación | 0,5–1 día | Panel separa objetivo/resultado/coste por línea y sustituciones. Backup restaurado, migración aditiva y rollback sin borrar datos. Límites propuestos activados solo después de superar criterios y contar con aprobación. |

Estimación total: aproximadamente **5–8 jornadas de ingeniería**, según los fallos de integración y la verificación de nuevas fuentes/ejemplos. No incluye esperar resultados orgánicos ni garantiza noticias disponibles todos los días.

## Panel y medición

- Jornada: previstos dos; publicados/verificados; noticia ausente y motivo; sustitución práctica; pendiente de verificación pública no cuenta como éxito completo.
- Por línea: candidato y fecha del acontecimiento, fase, rechazos concretos, corrección utilizada, fuentes, URL, tokens/uso comunicado y reservas inciertas.
- Investigación compartida: coste separado; no sumarlo de nuevo a ambas líneas. Facturación real solo cuando se reconcilie con el proveedor.
- Depósito: completos aprobados por sección, fuentes preparadas aparte, invalidaciones y coste de reponerlo.
- Indicadores: publicaciones verificadas/previstas; proporción de noticias; coste por artículo y por intento fallido; rechazos evitados antes de API; días cubiertos por reserva; duplicados; fallos de verificación; diversidad por tarea/sección. Medir resultados antes de conceder más reintentos.

## Pruebas necesarias antes de producción

1. Noticia válida + práctico válido; noticia 403/ausente/rechazada + práctico válido; noticia válida + fallo de ejemplo práctico; ambas inválidas: ninguna publicación inventada.
2. Ventanas 24/48/168 horas coherentes en todas las capas; fechas de calendario sin zona; futuro; fuente actualizada sobre anuncio antiguo; duplicado entre jornadas.
3. Recibos correctos y desalineados; runtime/dependencias/código alterados; ejecución local aislada sin red. Pruebas de programación no deben consumir OpenAI.
4. Prosa natural aprobable, repetición real, seis pasos útiles frente a seis apartados de relleno; corrección acotada y fallida; descripciones completas. Sin aprobación automática por agotar intentos.
5. Dos conexiones PostgreSQL reservando a la vez, respuesta incierta, liquidación duplicada, reinicio tras cada commit y después de publicar antes de verificar. Las pruebas SQLite no acreditan concurrencia de producción.
6. Reserva aprobada ayer: publicar sin regenerar, validar vigencia y deduplicación; consumo simultáneo del mismo borrador imposible; no doble facturación contable al usarlo.
7. 30 y 31 días, saldo mensual consumido y día caro; nunca exceder ninguno de los dos límites. Incluir coste de preparar los nueve artículos, correcciones y fallos, además de búsquedas.
8. Prueba real aislada FastAPI/PostgreSQL/Redis/Nuxt con modelos simulados: dos URLs públicas de prueba **solo locales**, SSR, canonical, sitemap, metadatos, categorías y rollback. TypeScript/build y tests de permisos/CSRF del panel.
9. Único turno a las 22:30 Madrid, cambio de mes/horario, reinicios y jornadas antiguas. No reactivar detección cada 30 minutos.

Después: habilitación gradual por bandera, backup cifrado completo con restauración comprobada y verificación de servicios/URLs. Rollback de código/bandera conservando artículos, presupuestos y tabla aditiva; no rebobinar reservas ni borrar publicaciones legítimas. Cualquier prueba OpenAI real requiere autorización posterior y un máximo calculado con el saldo entonces disponible.

## Realizado en esta revisión

- Lectura del código y consulta **solo lectura** de configuración, cola, informes y uso del trabajador real.
- Confirmados los recibos incompatibles y el caso de estilo; no se reactivaron candidatos ni se modificaron artículos.
- Simulación offline: seis escenarios de 30 días y caso de búsqueda incierta. Cuatro tests del modelo económico correctos.
- Baseline existente: **97 tests correctos** de motores, matriz de 11 planes, estilo, recuperación, presupuesto y búsqueda nocturna. Sus respuestas de OpenAI son simuladas; no demuestran el futuro flujo de dos artículos ni sustituyen la validación real posterior.
- Archivos añadidos: este plan, `scripts/simulate_editorial_capacity.py`, `tests/test_editorial_capacity_simulation.py`, `tests/fixtures/editorial_capacity_20261104.json`. Ningún módulo productivo, variable, planificador o límite fue modificado para esta propuesta.

No se ha implementado todavía la estrategia de dos artículos ni se ha generado/publicado un artículo durante esta revisión. No se necesita build de Nuxt para estos cambios de documentación/simulador; será obligatorio al modificar el panel.
