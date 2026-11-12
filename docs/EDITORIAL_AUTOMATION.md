# Investigación y publicación autónomas

Configuración vigente desde el 27/10/2026: [investigación con búsqueda web a las 22:30](NIGHTLY_WEB_2026_10_27.md), una sola jornada automática y publicación de noticias verificadas por prioridad dentro de 0,15 USD diarios y 5 USD mensuales. La detección de media hora está retirada; el máximo anterior de un artículo diario queda sustituido por el presupuesto y los controles editoriales. Se conservan evergreen, cola y validación. Las decisiones anteriores siguientes son históricas.

Decisión del propietario, 21/10/2026: automatizar también la publicación porque no dispone de tiempo para revisar diariamente. Sustituye la propuesta anterior de aprobación humana obligatoria. Máximo **un artículo diario**, OpenAI y **5 USD al mes**. No cambia la moderación de contenido de usuarios nuevos ni autoriza publicidad o despliegue público.

## Funcionamiento

Servicio Compose `research-worker`, sin puertos públicos, después de las migraciones. Ejecuta a las 22:30 en `Europe/Madrid`, con cambios de hora de `tzdata`. Debe permanecer encendido: no funciona con el ordenador apagado. Si arranca más tarde esa misma noche, recupera el día; no rellena días anteriores.

Registro inicial: RSS de OpenAI, Hugging Face y Google AI, principalmente en inglés. Ventana de 48 horas y máximo ocho documentos. No accede a LinkedIn, cuentas privadas, todos los idiomas ni búsquedas generales en Internet. La prioridad por palabras del título y fecha es una heurística, no una medición de tendencias globales. Omite fuentes inaccesibles sin eludir restricciones.

Normaliza enlaces, descarta fechas inválidas y URLs ya utilizadas. Compara título y cuerpo con los últimos 300 artículos. La primera llamada genera un borrador original en español, con citas literales por párrafo. Exige fuentes de dos organizaciones distintas, citas que existan, cifras apoyadas en el párrafo y ausencia de copias extensas. La segunda llamada comprueba afirmaciones, corroboración del mismo tema, utilidad, originalidad, idioma, experiencias inventadas y temas sensibles. Si todos los controles pasan, publica. Ante dudas, errores o presupuesto insuficiente, no publica; conserva los borradores ya guardados.

Las citas del expediente se mantienen literalmente en el idioma original, aunque el artículo se redacte en español. Las propuestas recibidas se conservan en el expediente privado incluso cuando no pasan la validación; no se convierten por ello en artículos ni aparecen públicamente. Esto permite diagnosticar fallos sin volver a pagar por el mismo texto. Se aplica la retención del resto del expediente.

Cuando detecta un fallo corregible, hace **una corrección automática como máximo por ejecución** y vuelve a revisar la versión corregida. Entrega al corrector el texto, los errores concretos y fragmentos originales alrededor de las citas. Corrige cifras/unidades y alcance, o retira afirmaciones sin apoyo; no inventa evidencias ni fuerza una aprobación. El título y resumen se verifican contra las evidencias de los párrafos: no se exigen citas visibles dentro de esos campos. Los errores técnicos, pausa, pérdida de bloqueo, contenido sensible y presupuesto agotado no disparan esta corrección.

Se conserva el mismo artículo, sin crear otra publicación. Cada versión y revisión queda en el expediente privado; se audita la corrección y se persiste su contador antes de llamar a la IA. Una edición manual concurrente bloquea tanto la sustitución como la publicación. Si el segundo control falla, el artículo sigue sin publicar; no hay un bucle ilimitado ni una cuota obligatoria de publicaciones.

Publicación, resultado y auditoría en una transacción. Autor visible «Redacción automatizada · IA» y aviso de que no hubo revisión humana. No inventa autores ni aprobaciones. Mantiene SSR, fuentes, canonical y sitemap existentes. Si un editor modifica o retira el borrador durante la revisión, no publica ni sobrescribe esa versión.

## Panel y activación

`/editorial/investigacion`, para editores y administradores verificados: señal del trabajador, configuración sin secretos, últimas 14 ejecuciones, candidatos, fallos, motivos, borradores y reservas. Pausa/reanudación con sesión, CSRF y auditoría. El resumen diario está en ese panel; no se envía por correo.

Configurar en `.env` local (la clave nunca se comparte por chat ni se commitea):

```dotenv
OPENAI_API_KEY=
RESEARCH_MODEL=gpt-5-mini
RESEARCH_AT=22:30
RESEARCH_AUTO_PUBLISH=true
RESEARCH_MONTHLY_USD=5
RESEARCH_DAILY_USD=0.15
RESEARCH_INPUT_USD_PER_MILLION=0.25
RESEARCH_OUTPUT_USD_PER_MILLION=2
```

Aplicar con `./scripts/local.ps1 Start -Toolbox`, sin `-Toolbox` en Docker Desktop. Sin clave, permanece en espera y no hace llamadas de pago. No se ha configurado una clave automáticamente. `RESEARCH_AUTO_PUBLISH=false` conserva artículos aprobados en revisión. Pausar no cancela una petición ya enviada, pero evita nuevas llamadas y publicación final.

Ejecución a demanda: `docker compose exec research-worker python -m app.research.worker --once`. Respeta pausa, presupuesto y fecha única; no repite fechas registradas. En Toolbox requiere los mismos ajustes TLS/túnel del script local.

## Presupuesto y recuperación

- `0004_research`: ejecución única por fecha de Madrid, reservas en microdólares y pausa persistentes. Redis coordina un bloqueo de 30 minutos; el trabajo tiene un máximo de 15 minutos. Heartbeat separado de la generación.
- Antes de cada llamada reserva su máximo conservador: bytes UTF-8 del payload más margen como cota de tokens de entrada. Hasta cuatro llamadas: redacción, revisión, corrección y nueva revisión; máximos de salida de 6.000, 4.000, 4.000 y 4.000 tokens respectivamente. La corrección/revisión usan fragmentos originales relevantes para contener coste; el validador determinista conserva los documentos consultados completos. Bloqueo de fila PostgreSQL serializa reservas con los mismos límites diario y mensual. Si no cabe la siguiente llamada, se detiene sin aumentar esos límites.
- No devuelve reservas, incluso ante fallos. No reintenta inmediatamente llamadas de resultado incierto ni compra búsquedas. Una revisión que quede pendiente por un fallo técnico o presupuesto puede ocupar la ejecución del día siguiente una sola vez, sin volver a redactar y sin crear otro artículo. Mantiene las reservas del día anterior y aplica las nuevas al presupuesto del nuevo día. Vuelve a consultar las mismas fuentes (antigüedad máxima de 72 horas para esta continuación), revalida el texto y respeta cambios manuales. Si falla otra vez, se detiene; no hay una cadena indefinida de continuaciones. La factura real se consulta en OpenAI. El tope cubre esta automatización bajo las tarifas configuradas; excluye impuestos, otras aplicaciones, uso externo de la clave y cambios de precio. Configurar también controles de gasto del proyecto en el proveedor.
- Modelos admitidos: `gpt-5-mini`, `gpt-5.4-mini`, `gpt-5.4-nano`. Al cambiar, ajustar ambas tarifas. Mínimos documentados al implementar: 0,25/2; 0,75/4,5; 0,2/1,25 USD por millón de tokens. Actualizarlos si el proveedor cambia precios. Se rechazan presupuestos mensuales superiores a 5 USD y tarifas inferiores a estos mínimos.
- Reiniciar no repite la fecha ni el gasto. Una ejecución inconclusa se marca interrumpida cuando vuelve a procesarse, tras 30 minutos; no se reintenta. Historial económico persistente; expedientes privados vaciados tras 30 días durante el mantenimiento de ejecuciones. Artículos y fuentes se conservan.

En una continuación se recuperan todas las fuentes citadas en la propuesta conservando sus identificadores. Una fuente recopilada pero descartada al redactar no bloquea la revisión si deja de estar accesible. Si falta una fuente citada, no se publica sin verificarla ni se sustituye por un texto inventado.

## Seguridad y limitaciones

Solo HTTPS/443 a hosts exactos. DNS público validado y fijado al socket real, con SNI y TLS para el hostname original. Redirecciones revalidadas, sin IP privadas ni credenciales en URL. Máximo 2 MB por descarga, tres redirecciones, formatos acotados y sin compresión. XML sin DTD, entidades ni bytes nulos; HTML reducido a texto. Selección alternada entre organizaciones para que una fuente no desplace al resto. Los documentos son datos no confiables: el modelo no tiene herramientas, secretos ni ejecución de código, solo devuelve JSON validado. El servidor decide publicar. No se registran respuestas del proveedor en logs; la web escapa el texto.

Dos llamadas al mismo modelo pueden compartir errores. Las citas coincidentes no demuestran apoyo semántico por sí solas. No se promete veracidad absoluta, cobertura amplia, publicaciones todos los días ni ingresos. Con tres fuentes y corroboración estricta es normal no publicar algunos días. No ejecuta tutoriales ni prueba herramientas; no debe afirmar haberlo hecho. Correcciones y retirada disponibles desde el panel.

## Referencias y archivos

[OpenAI: JSON estructurado en Responses](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini), [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini), [GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano). Verificar disponibilidad y tarifas antes de activar facturación.

Cambios: `api/app/research/`, modelos, migración `0004`, integración API, proxy y página Nuxt, Compose, configuración y scripts locales. Pruebas en `tests/test_research.py` y navegador. Resultados en `docs/VALIDATION.md`.
# Corrección de fuentes — 24/10/2026

La atribución de organizaciones, los diagnósticos de descarga y los límites de selección se han revisado y desplegado. Véase [diagnóstico, pruebas y resultado](RESEARCH_SOURCES_FIX_2026_10_24.md). Se mantienen presupuesto, horario y controles de publicación. Los 403 de OpenAI no se eluden; las próximas ejecuciones conservan sus errores detallados en el expediente.

