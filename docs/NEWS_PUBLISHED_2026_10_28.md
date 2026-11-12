# Noticia real publicada mediante investigación web — 28/10/2026

## Resultado público

**Anthropic presenta su S-1 y anuncia su intención de salir a bolsa como «ANT»**

https://foroiaaldia.com/articulos/anthropic-s1-ipo-ant-2026-10

Publicado el **28/10/2026 a las 12:21:23 Europe/Madrid** por el trabajador editorial. Candidato 20, artículo 7, ejecución de recuperación 6. Procedencia persistida: `nightly_web_search`. No se insertó un artículo manualmente.

La investigación comenzó el 27/10 y el anuncio original es del 26/10. No se afirma que el anuncio ocurriera el día de publicación. La revisión final reutilizó el texto y las evidencias conservadas, sin repetir investigación ni redacción.

## Fuentes reales verificadas

- Comunicado original: https://www.anthropic.com/news/s1-sec
- Cobertura independiente: https://techcrunch.com/2026/10/26/anthropic-officially-files-for-its-public-debut/

Se descargaron ambos documentos y se comprobaron sus fechas originales. Las afirmaciones se vinculan a fragmentos versionados. Una respuesta del buscador nunca constituye evidencia por sí sola.

## Búsqueda y descartes

Una acción completada de Responses `web_search`, cinco propuestas y una noticia publicada. Se conservaron respuesta, consultas, fuentes y uso. Las continuaciones reutilizaron esa misma búsqueda pagada.

| Propuesta del buscador | Resultado comprobado |
| --- | --- |
| Documentación pública y posible salida a bolsa de Anthropic | AP y Axios devolvieron 403. Se recuperaron TechCrunch y el comunicado oficial. Seleccionada, revisada y publicada. |
| Supuesta disponibilidad de OpenAI en Google Cloud | Fuente propuesta bloqueada; no se logró verificar. No se afirma que el anuncio sea cierto. |
| NVIDIA: DSX y centros de datos | La entrada DSX era antigua. Otros artículos recuperados no aportaron corroboración independiente suficiente sobre el mismo acontecimiento. |
| Índice de novedades de Claude | Una entrada reciente verificada, sin dos organizaciones independientes sobre el mismo acontecimiento. |
| Recopilaciones sobre Anthropic | Sin fuentes independientes actuales suficientes sobre una misma noticia. |

No se eludieron bloqueos ni se publicó otro evergreen para ocultar un fallo de actualidad.

## Correcciones desplegadas

1. Contrato de búsqueda con candidatos individuales y diagnóstico de resultados vacíos. Una propuesta incorrecta no descarta las válidas.
2. Normalización estricta de URLs Markdown y extracción acotada de artículos desde índices permitidos. Se conservan HTTPS, dominios autorizados, DNS público, límites de descarga y protección SSRF.
3. Fecha original explícita y recuperación mediante RSS e índices oficiales. No se usa `dateModified`, copyright o una barra lateral para fechar la noticia.
4. La deduplicación conserva titulares descriptivos frente a etiquetas derivadas de rutas. Se excluyen referencias laterales.
5. Los metadatos pueden seleccionar otro fragmento verificado de un documento citado en el artículo. La revisión semántica de título, resumen y afirmaciones sigue siendo obligatoria.
6. Comparación de tokens numéricos completos con separadores españoles/ingleses: `11.900` y `11,900`. No se acepta `119` por aparecer dentro de `11900`, ni se cambia la magnitud.
7. Se elimina una frase final incompleta de la metadescripción cuando existe una frase completa suficiente. No se inventa una continuación. Revisión y presupuesto utilizan el texto resultante.
8. Liquidación idempotente de reservas del trabajador diario solo para respuestas completadas con uso persistido y coincidente. Ante incertidumbre se conserva la reserva íntegra. La liquidación y las reservas comparten el bloqueo PostgreSQL. Las cuotas manuales conservan su contabilidad conservadora; no se redujeron las reservas históricas de esta prueba.
9. Reconciliación del historial cuando una investigación se publica mediante una revisión pagada al día siguiente. No se mueven costes ni se alteran fechas. Se conserva el borrador previo y se enlaza la ejecución de recuperación.

Archivos principales: `api/app/research/{night_web,sources,selection,writing,quality,checkpoints,editorial,executions,worker}.py`. También se actualizaron cola, blueprints, monitor y panel en los cambios precedentes. Regresiones en `test_nightly_web.py`, `test_evidence_first.py`, `test_editorial_executions.py`, `test_editorial_engines.py` y `settlement_postgres_check.py`.

## Costes y reservas

| Fase real | USD calculados |
| --- | ---: |
| Investigación, incluida búsqueda | 0,017624 |
| Redacción original | 0,004588 |
| Primera revisión | 0,005571 |
| Corrección | 0,004915 |
| Revisión final del 28/10 | 0,005930 |
| **Total de esta noticia** | **0,038628** |

Importes calculados con tokens y acciones informados; **no son una factura verificada**. No incluyen el ensayo evergreen anterior. La búsqueda tiene un componente de 0,01 USD por acción; no se cobra otra búsqueda por releer su respuesta guardada.

Reserva del 28/10: **0,016310 USD**. Disponible diario: **0,133690 USD**. Reserva mensual: **0,510803 USD**. Disponible mensual: **4,489197 USD**. Límites intactos: **0,15 USD/día y 5 USD/mes**.

## Pruebas y seguridad

- **234 pruebas correctas**, 11 omitidas por requerir integraciones específicas. Registro: `.local/news-final-tests.log`.
- **12 pruebas HTTP correctas** con Nuxt SSR y API reales, base aislada y proveedor simulado. No son llamadas reales de producción.
- PostgreSQL restaurado y aislado sin red: límites diarios/mensuales concurrentes, búsqueda idempotente, deduplicación y liquidación concurrente. Una liquidación; una reserva permitida y otra bloqueada. Cero llamadas externas.
- Prueba real: revisión pagada, aprobación y publicación por el proceso existente.
- Verificación externa: HTTP 200, SSR, canonical, metadescripción completa, fuentes, JSON-LD, enlaces desde portada/categoría y una aparición en sitemap. HTTP redirige a HTTPS con 308.
- Siete servicios funcionando, PostgreSQL/Redis sin puertos públicos, credenciales y configuración de producción intactas. GA4 y publicidad siguen desactivados.
- Huellas de los seis artículos anteriores, usuarios, comentarios, categorías y temas intactas. Los siete artículos permanecen iguales tras el ajuste final del historial.
- Backups completos cifrados y copias fuera del VPS antes de cada despliegue. Restauración de las 19 tablas, Redis, archivos y Caddy verificada. Último punto: `/var/backups/foroia/historyfix-20261028-final/`, con imágenes previas y `rollback.py`. El rollback de aplicación no elimina publicaciones ni restaura una base antigua sobre producción.

## Próxima ejecución y límites pendientes

Se mantiene el único turno de las **22:30 Europe/Madrid**. La recuperación consume la jornada editorial del 28/10; el panel indica la próxima investigación para el **29/10/2026 a las 22:30**. No se activa un segundo planificador ni monitorización de media hora.

Persisten 403 en algunas fuentes y se buscan alternativas permitidas. Puede no haber publicación si faltan evidencias o presupuesto: no se garantiza una noticia diaria. Esta publicación demuestra el recorrido real desde web_search hasta la web pública, sin asegurar que toda propuesta futura vaya a aprobarse. No se ha medido ni se afirma indexación en Google.
