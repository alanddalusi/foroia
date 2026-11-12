# Despliegue y ejecución real — 29/10/2026

## Despliegue comprobado

Política de anuncios oficiales desplegada mediante 11 archivos seleccionados: nueve módulos del backend y dos archivos del panel. No se copió el frontend local completo ni se modificaron configuración privada, migraciones, DNS, firewall o SSH.

Checkpoint: `/var/backups/foroia/officialnews-20261029-final`. Cuatro backups cifrados, copias fuera del VPS y hashes comprobados; restauración aislada de PostgreSQL con las 20 tablas coincidentes, Redis, código/configuración y certificados. `rollback.py`, `rollback.yml` e imágenes anteriores conservados. El rollback no borra artículos ni consumo registrado.

Pruebas: **400 correctas, 24 omitidas** en la suite general; pruebas previas de TypeScript, build y publicación HTTP/SSR satisfactorias. Además se probaron en PostgreSQL aislado la concurrencia diaria/mensual, deduplicación, reserva de recuperación y liquidación única del ledger, sin llamadas de pago.

Tras activar: siete servicios ejecutándose, 20 tablas sin cambios, siete artículos públicos comprobados mediante HTTP 200, SSR, canonical y sitemap. PostgreSQL y Redis siguen sin puertos públicos. Configuración privada sin cambios. Límite **0,20 USD/día y 10 USD/mes**, horario **22:30 Europe/Madrid**. Próximo turno ordinario confirmado: 30/10/2026 a las 22:30.

## Prueba real autorizada

Las búsquedas guardadas correspondían a acontecimientos demasiado antiguos. Se habilitó una única nueva tentativa explícita de operador mediante `--new-news-attempt 9`, reutilizando `retry_news` y el coordinador existentes. No es un planificador ni una automatización paralela.

La operación exige una tentativa previa terminada sin nueva publicación, resultados previos liquidados, ausencia de borradores pendientes o llamadas inciertas, bloqueo global y presupuesto para la búsqueda más margen de redacción/revisión. Conserva íntegro el informe anterior dentro de `prior_attempts` y el gasto acumulado. Una marca durable impide repetir esta nueva tentativa. La publicación queda limitada a una noticia y sin alternativa evergreen en esta prueba.

Preflight a las 23:17 Madrid: 0,083281 USD contabilizados/reservados hoy, 0,116719 USD disponibles. Reserva máxima de búsqueda 0,054553 USD y margen de redacción/revisión 0,040000 USD. Llamada real iniciada a las 22:17:23 UTC (23:17:23 Madrid), con reserva atómica y el mismo día editorial. No se reinició el presupuesto ni se aumentaron los límites.

## Resultado real comprobado

**Publicado automáticamente el artículo 9:** [Microsoft presenta el Copilot harness: disponible a través de Microsoft Foundry](https://foroiaaldia.com/articulos/microsoft-presenta-copilot-harness-foundry).

La búsqueda real devolvió cinco candidatos: Oracle/OpenAI, ServiceNow/OpenAI, Microsoft Copilot harness, OpenAI DevDay y Meta/universidades. Los tres candidatos de OpenAI no se pudieron verificar por HTTP 403; el de Meta apuntaba a un índice sin artículo individual recuperable. Microsoft se aceptó como anuncio oficial de su propia organización, con una fuente original accesible y fecha 28/10/2026 a las 16:51:35 UTC.

Fuente publicada: `https://blogs.microsoft.com/blog/2026/10/28/introducing-the-microsoft-copilot-harness-unlocking-the-potential-of-truly-multi-model-agentic-work/`.

La redacción inicial y su corrección encontraron un fallo determinista del filtro: interpretaba **VS Code** como **versus**. Se reprodujo con el borrador real guardado, se corrigió la excepción del nombre del producto y se añadieron pruebas que conservan el rechazo de comparaciones auténticas. También se evitaron falsos positivos en «compartir» y «demanda empresarial».

Segundo checkpoint: `/var/backups/foroia/vscoderecovery-20261029-final`, también restaurado y verificado con 20 tablas. Se desplegaron solamente `editorial_policy.py` y `worker.py`; sin nuevo build de frontend ni cambios de configuración privada. Suite general: **406 correctas, 24 omitidas**; prueba final dirigida: **34 correctas**, incluida recuperación sin repetir investigación/redacción, revisión rechazada, presupuesto insuficiente, resultado incierto y evidencia modificada.

Se recuperó el borrador mediante `--resume-proposal-run 9`. El trabajador reutilizó el texto y catálogo originales, conservó la corrección ya consumida y realizó **únicamente la revisión pendiente**. La creación del artículo, validación, revisión y publicación se hicieron mediante el pipeline existente: no se insertó contenido manualmente ni se anuló ningún rechazo del revisor. La revisión real marcó `approved=true` y `supported=true` y confirmó que las afirmaciones se atribuían a Microsoft y estaban respaldadas por los fragmentos del comunicado.

Comprobación pública independiente tras publicar: HTTP 200, contenido SSR, H1 y canonical correctos, sin noindex, datos estructurados Article/BlogPosting y BreadcrumbList, Open Graph con imagen accesible, enlace desde `/actualidad` y presencia en sitemap. Los ocho artículos públicos responden correctamente, el borrador anterior 8 se conserva y los siete servicios están ejecutándose. PostgreSQL y Redis continúan sin puertos públicos.

## Coste y programación

| Fase real | Coste calculado con uso comunicado |
| --- | ---: |
| Investigación, una llamada `web_search` y tokens | 0,017220 USD |
| Primera redacción | 0,004052 USD |
| Corrección de redacción anterior al arreglo de VS Code | 0,004858 USD |
| Revisión recuperada, sin volver a redactar | 0,006017 USD |
| **Total de esta prueba** | **0,032147 USD** |

La búsqueda incluye 0,010000 USD por herramienta. Reservas liquidadas según el uso comunicado; **la factura del proveedor no se ha verificado**. Total contabilizado/reservado hoy: **0,115428 USD**; disponible diario **0,084572 USD**, mensual **9,356314 USD**. Los límites siguen en 0,20 USD/día y 10 USD/mes.

Jornada de hoy realizada; siguiente ejecución ordinaria confirmada: **30/10/2026 a las 22:30 Europe/Madrid**. Bloqueo liberado, trabajador habilitado. No se han contratado servicios ni cambiado publicidad, credenciales, DNS, firewall o SSH. Los dos rollbacks conservados son de código/imágenes; no restaurar una copia anterior sobre la base de datos activa, porque ya existe un artículo nuevo que debe conservarse.

Evidencias locales: `.local/deploy/officialnews-final-public-checks.json`, `.local/deploy/real-news-20261029-progress.json`, `.local/deploy/vscode-review-preflight.json`, `.local/vscode-all-tests.log`, `.local/vscode-targeted-final.log`.
