# Recuperación editorial — 26/10/2026

Prueba real autorizada y **completada en producción**. El trabajador recuperó el borrador y publicó [Validar un JSON generado por IA antes de procesarlo en Python](https://foroiaaldia.com/articulos/validar-json-ia-python) el 26/10/2026 a las 19:02:04 Europe/Madrid. Investigación reanudada por autorización expresa. Horario y límites intactos: 22:30 Europe/Madrid, 0,15 USD/día, 5 USD/mes.

La ejecución manual 3 terminó `completed / quality_checks_passed`: una llamada de revisión, 14.585 tokens de entrada y 1.963 de salida, coste calculado **0,007573 USD**. Reserva conservadora **0,021575 USD**; no se devuelve ni se confunde con facturación. No se repitieron investigación ni redacción. La revisión aprobó 18 objetivos; el cuerpo, los metadatos y sus citas se validaron antes de publicar. No se insertó un artículo manualmente ni se publicó contenido de prueba. La factura de OpenAI no se ha conciliado.

## Problemas reproducidos

- Las revisiones históricas devolvían referencias alternativas, referencias inventadas y un identificador vacío. El contrato antiguo no impedía estos valores al generar la respuesta. Una referencia alternativa válida tampoco podía corregir la selección inicial del redactor.
- El contrato nuevo enumera únicamente los fragmentos ofrecidos. Las comprobaciones son un objeto con todas las claves de afirmación obligatorias. El servidor rechaza claves JSON duplicadas, cobertura incompleta y referencias ajenas al catálogo.
- Una revisión plenamente aprobada puede corregir referencias usando el catálogo verificado. El servidor resuelve las citas exactas y vuelve a aplicar las validaciones finales antes de publicar. Las dos organizaciones deben citarse realmente en el cuerpo de las noticias: no basta incluirlas entre los documentos o los metadatos. Las referencias iniciales del borrador privado son provisionales.

## Recuperación y panel

Migración aditiva `0007_editorial_executions`: historial manual persistente separado del historial diario y clave idempotente del consumo de cada llamada. El presupuesto se comparte mediante las reservas diarias existentes; no se borran ejecuciones ni importes anteriores.

El panel `/editorial/investigacion` permite preparar gratuitamente, consultar la estimación y confirmar explícitamente un máximo. Las peticiones llevan autenticación editorial y CSRF; preparación limitada, clave idempotente, caducidad de treinta minutos y máximo de una solicitud activa. La confirmación comprueba pausa, importe, día, tarifas y presupuesto disponible. El trabajador usa el mismo bloqueo Redis de la ejecución diaria. No se inicia el proveedor dentro de la petición HTTP del navegador.

Se conserva el catálogo original y la respuesta bruta antes de validar. Una respuesta guardada se puede reprocesar sin reservar ni cobrar de nuevo. Una petición de resultado incierto no se reenvía automáticamente. La revisión aprobada guarda un hash del borrador, catálogo y referencias; se recupera sin otra revisión, comprobando que ningún editor haya cambiado el texto. La programación diaria también recupera el catálogo guardado, sin reemplazarlo silenciosamente por documentación distinta.

La primera solicitud caducó antes de la autorización. La segunda se detuvo sin gasto: PostgreSQL JSONB reordenaba las claves del JSON incluido como texto en la petición y cambiaba su huella. Se confirmó que ambos contenidos decodificados eran iguales y se normalizó su serialización. La tercera solicitud, con el mismo máximo autorizado, completó el flujo. La regresión reproduce el orden de claves de JSONB, incluido el contenido anidado.

Las respuestas incompletas recibidas y registradas permiten como máximo un reintento en un día editorial posterior, dentro de las reservas ordinarias. No se reintenta un resultado incierto ni un fallo de transporte. Los fallos históricos se mantienen en sus expedientes; no se muestran como fallo actual de un trabajo completado.

La representación de citas agrupa una sola vez cada número de fuente aunque varias evidencias del párrafo procedan del mismo documento. Se regeneró ese formato desde la propuesta aprobada con guardas de igualdad: solo se eliminaron números repetidos, sin cambiar el texto editorial, fuentes ni aprobación, y sin llamadas al modelo. Cambio auditado como `research_render_normalize`.

## Comprobaciones

- Suite general: **230 correctas y 66 opcionales omitidas**. Después se añadieron dos regresiones del monitor y pasaron sus **17 pruebas específicas**.
- Pruebas de ejecución/recuperación: permisos e idempotencia, caché de respuestas, incertidumbre, revisión con objeto de claves obligatorias, respuesta incompleta, claves duplicadas, referencias inválidas, reserva diaria/mensual y por trabajo, recuperación sin redactar, recuperación de revisión aprobada, claves JSONB y protección de cambios humanos.
- Reproducción privada de dos borradores y revisiones reales guardadas: sin proveedor ni escrituras en producción. Los rechazos históricos no se convierten en aprobaciones sintéticas.
- 11 escenarios de publicación aislada con Nuxt SSR, API y sitemap: correctos, sin proveedor real ni contenido de prueba en producción.
- TypeScript y builds Nuxt/Docker correctos.
- Backup cifrado completo fuera del VPS: PostgreSQL, Redis, código/configuración y Caddy. Restauraciones y verificaciones de integridad correctas. La migración se probó sobre una restauración aislada y conservó los hashes de las 15 tablas anteriores.
- Tras publicar: cinco artículos públicos comprobados con API, HTML, SEO, imagen y sitemap. Rastreo de las 14 URLs de los dos sitemaps sin enlaces internos rotos ni artículos huérfanos. Navegador móvil sobre portada y artículo nuevo: sin desbordamiento, errores JavaScript ni incidencias axe WCAG A/AA; foco por teclado comprobado. Sin peticiones GA4 ni publicidad. Son comprobaciones de laboratorio, no métricas de campo.
- El monitor reconoce una publicación manual verificada aunque su reserva diaria tenga estado `manual_budget_bucket`; evita una falsa alerta de ausencia de publicación. Los casos con publicación y sin ella tienen pruebas independientes.

## Operación y rollback

Backups y recuperación en `/var/backups/foroia/manualjobs-20261026-final/`, `/var/backups/foroia/quotehash-20261026-final/` y `/var/backups/foroia/publication-20261026-final/`, con copias cifradas fuera del VPS. El último incluye la publicación real; restauración de sus 16 tablas verificada. `rollback.py` restaura archivos e imágenes anteriores sin eliminar las columnas ni el historial aditivos. Antes de retirar un trabajador con llamadas en curso hay que conservar su estado y comprobar el bloqueo: nunca repetir una petición incierta. Mantener la pausa durante una recuperación técnica hasta comprobar el estado del proveedor.

La siguiente ejecución diaria corresponde al **27/10/2026 a las 22:30 Europe/Madrid**: el presupuesto compartido y el máximo de una publicación diaria evitan duplicar la publicación del día 26. La publicación futura depende de que haya fuentes, presupuesto y contenido que supere los controles; esta prueba acredita un caso real, no una frecuencia garantizada. No se hicieron más llamadas de pago para probar las correcciones posteriores.
