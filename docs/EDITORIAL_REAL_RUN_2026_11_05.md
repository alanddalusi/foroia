# Ejecución real adelantada — 5 de noviembre de 2026

Autorizada por el propietario. Se ejecutó el trabajador de producción existente con `python -u -m app.research.worker --once`, sin modificar código desplegado, horario, credenciales ni límites. Inicio: **16:40 Madrid**; final: **16:43 Madrid**. Jornada **#16**, dos líneas editoriales, bloqueo Redis compartido y reservas PostgreSQL normales.

**Resultado: ninguna publicación nueva verificada.** No se considera satisfactoria una publicación que no haya superado la comprobación pública.

## Noticias

Responses/web_search devolvió cuatro propuestas. Son propuestas del modelo, **no hechos confirmados**: recopilación de OpenAI DevDay, lanzamiento de DeepSeek, robótica Meta/Fourier y un modelo de Google/DeepMind.

La recuperación no verificó documentos suficientes correspondientes a estos acontecimientos. Registró HTTP 403, páginas de índice sin artículo individual, dominios no permitidos, documentos de otro acontecimiento y fechas fuera de ventana. La búsqueda alternativa permitida tampoco resolvió la verificación. Se evitó redactar los cuatro candidatos. El código de salida de la línea sigue siendo el poco informativo `web_candidates_found`, pero su diagnóstico interno registra `verification_status=no_verified_candidates` y cero documentos aceptados.

No debe usarse el resumen de búsqueda del modelo como prueba de esos anuncios.

## Artículos prácticos

1. Candidato **5**, Pydantic: generación y revisión editorial aprobadas. Se creó el artículo **16**, pero el verificador devolvió `publication_not_indexable` y la recuperación automática lo archivó. La entradilla tiene **183 caracteres**; la web aplica `seoDescription`, que normaliza y recorta las metadescripciones a un máximo de 155. `verify_html` exige igualdad literal con la entradilla completa. Es una incompatibilidad demostrable entre frontend y verificador; ese código no permite concluir por sí solo que exista un `noindex`. **Pendiente corregir y probar esta validación, sin relajar indexabilidad ni modificar contenido para sortearla.**
2. Candidato **34**, primera petición OpenAI con clave fuera del código: borrador y corrección procesados, pero revisión final rechazada por afirmaciones no suficientemente respaldadas. Artículo **17** conservado como borrador; no se publicó.

No se repitieron llamadas después del cierre de la jornada ni se forzó la publicación de los artículos rechazados.

## Costes y operación

Uso calculado a partir de tokens/herramientas comunicados: **0,083999 USD**. Reserva final de la jornada: **0,083999 USD**. Saldo diario por reservas: **0,116001 USD**. Reserva mensual acumulada: **0,333515 USD**; saldo mensual: **9,666485 USD**. No se ha comprobado la factura del proveedor.

Topes efectivos: **0,20 USD/día y 10 USD/mes**. La jornada de hoy quedó consumida; no se repetirá automáticamente esta noche. El panel confirma siguiente ejecución **6 de noviembre de 2026, 22:30 Europe/Madrid**, investigación habilitada y trabajador vivo.

Al cerrar: bloqueo libre; API, frontend, PostgreSQL y Redis saludables; Caddy y trabajador en marcha. PostgreSQL y Redis siguen sin puertos públicos. No se desplegaron cambios ni se alteraron artículos anteriores, DNS, SSH, firewall, publicidad o analítica.

Diagnósticos privados guardados localmente: `daily-20261105-full.json`, `daily-20261105-diagnostics.json`, `daily-20261105-overview.json`. Registro del trabajador: `/var/log/foroia/manual-daily-20261105.log`. Las comprobaciones fueron reales; no se utilizaron mocks ni artículos de prueba.
