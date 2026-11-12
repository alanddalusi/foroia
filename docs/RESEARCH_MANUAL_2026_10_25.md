# Ejecución real adelantada — 25/10/2026

Solicitada expresamente por el propietario y ejecutada mediante `app.research.worker --once`, conservando lock, fecha editorial única y límites. Expediente **5**, fecha 25/10. No se crea otro turno para las 22:30 ni se modifica la programación.

## Resultado observado

**Sin publicación nueva.** Se consultaron nueve fuentes iniciales y se detectaron veinticinco entradas candidatas, pero no hubo noticia viable. El flujo pasó a evergreen y generó un borrador privado de validación de JSON con Python.

- Candidata 1: dos versiones y dos revisiones; rechazada por el contrato de referencias. El revisor utilizó fragmentos existentes en el catálogo, pero distintos de los citados en los párrafos. No faltaban todos los targets: el fallo concreto era la correspondencia de sus fragmentos permitidos.
- Candidata 2: la generación devolvió un identificador no ofrecido; se bloqueó con `invalid_evidence`. La versión anterior solo guardaba `fragment_not_offered`, por lo que no se inventa qué identificador exacto era.
- Cinco llamadas reales, 51.334 tokens de entrada y 10.429 de salida informados. Coste calculado: **0,033693 USD**; reserva conservadora de la jornada: **0,100859 USD**. La facturación del proveedor no se ha verificado.
- Reserva mensual acumulada: **0,336647 USD**. Se conservan 0,15 USD/día y 5 USD/mes.

Los documentos de noticias devueltos sin fecha válida, demasiado grandes o con codificación no admitida no se utilizaron como evidencia. No se eludieron restricciones. Permanecen cuatro artículos públicos; el borrador 5 sigue en estado `draft`, su URL pública devuelve 404 y no se incorpora al sitemap.

## Corrección aplicada y desplegada, sin más llamadas de pago

`api/app/research/writing.py` limita el esquema de generación mediante un `enum` de identificadores realmente ofrecidos. El revisor recibe `allowed_fragment_ids` por target; su esquema usa ramas `anyOf` que vinculan cada target a sus referencias permitidas. Se mantienen la revisión semántica, cobertura completa, ausencia de duplicados, validación de citas y controles de independencia. El servidor sigue rechazando respuestas inválidas aunque un proveedor ignore el esquema.

Se registran los targets cuyas referencias no coinciden y los identificadores desconocidos en fallos futuros. Para errores HTTP del proveedor se conservan estado y códigos acotados, sin guardar mensajes arbitrarios, claves ni cuerpos de error. [Tipos soportados por Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Pruebas: **213 correctas y 66 omitidas** en la suite general; **11 recorridos SSR completos correctos** con proveedor simulado y base aislada. Dos esquemas validados con JSON Schema y cuatro casos positivos/negativos comprobados, sin llamadas al proveedor. Regresiones en `tests/test_decoder_evidence_contract.py`.

Antes de activar API y trabajador se crea y restaura el checkpoint cifrado `/var/backups/foroia/contract-20261025-final`: quince tablas, Redis, código/configuración y certificados. Rollback: `sudo python3 /var/backups/foroia/contract-20261025-final/rollback.py`. La configuración de producción permanece intacta.

## Recuperación preparada

El expediente 5 y sus reservas no se modifican. Tras comprobar que nadie había editado el borrador, se conserva para repetir únicamente su revisión con el nuevo contrato. La segunda candidata vuelve a quedar pospuesta para su último intento permitido; no se reinician sus contadores. La preparación queda auditada y no aprueba ni publica contenido.

Próxima ejecución natural: **26/10/2026 a las 22:30 Europe/Madrid**. No se realiza otra generación de pago para comprobar el parche. Falta confirmar su comportamiento con una respuesta real del modelo; las pruebas no se presentan como una publicación en producción.
