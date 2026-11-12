# Investigación web nocturna — despliegue del 27/10/2026

**Actualización posterior:** el propietario autorizó adelantar la jornada del 27/10. Se ejecutaron investigación, redacción y revisión reales y se publicó un tutorial evergreen verificado; la búsqueda no aportó candidatos de noticias. [Prueba real, costes y correcciones](REAL_EDITORIAL_TEST_2026_10_27.md). Las referencias a la primera búsqueda pendiente en el texto siguiente describen el estado inicial del despliegue.

## Resultado y alcance comprobado

Desplegado en el trabajador editorial existente. La única investigación automática comienza cada día a las **22:30 Europe/Madrid**. El detector de media hora está desactivado, no se inicia su coroutine y no se despachan trabajos extraordinarios. Sus tablas e historial permanecen para conservar los datos y permitir rollback. El panel ya no permite reactivarlo.

La siguiente ejecución es **27/10/2026 a las 22:30, hora de Madrid**. No se ha adelantado una llamada de pago para validar este cambio. El acceso de la cuenta a `gpt-5-mini` se comprobó con un GET de metadatos (HTTP 200), que no genera contenido. **El uso real de `web_search` por esta cuenta y la primera publicación de este nuevo recorrido quedan pendientes de la ejecución nocturna.** Las pruebas descritas más abajo usan un proveedor simulado.

Se conservaron los cinco artículos publicados, sus fechas, textos, URLs y fuentes. El verificador público comprobó los cinco: API, HTML SSR, metadatos/canonical, imagen y sitemap correctos. Dos sitemaps contienen 14 URLs públicas; el monitor no presenta alertas. PostgreSQL y Redis siguen sin puertos públicos; entorno, credenciales, anuncios y GA4 no se modificaron.

## Recorrido reutilizado

1. El `tick` existente crea una única jornada editorial persistente y utiliza el bloqueo Redis habitual. No se añade cron, timer ni servicio editorial.
2. `night_web.py` usa la misma integración HTTPS con **Responses API**, `gpt-5-mini`, herramienta **`web_search`**, acceso externo habilitado y una llamada de herramienta como máximo. `tool_choice=required` exige buscar; una respuesta sin búsqueda acreditada no aporta candidatos válidos.
3. Solicita JSON estructurado con hasta seis oportunidades: título, acontecimiento, fecha, organización, relevancia categórica, URLs y justificación. La ventana principal es de 24 horas y puede ampliarse a 48. El contexto pide cobertura de modelos, robótica, autonomía, chips, herramientas y programación, incluyendo OpenAI, NVIDIA, Tesla, xAI, Google, Anthropic, Microsoft, Meta y DeepSeek. Una consulta acotada no equivale a rastrear toda la web ni garantiza descubrir todos los anuncios.
4. Las propuestas y resúmenes de búsqueda **no son evidencias**. Se descargan como máximo doce páginas de destinos HTTPS permitidos, con DNS público fijado al socket, TLS, redirecciones y tamaño acotados. Se exige fecha original comprobable y contenido suficiente. Un 403 no se elude; las descargas fallidas o incompletas no detienen las demás.
5. El registro de organizaciones y el selector existentes comprueban relación temática, corroboración de dos organizaciones independientes y ausencia de contenido reproducido. Además se exige una fuente original entre los documentos elegidos. Las fuentes permitidas se amplían con destinos oficiales y publicaciones independientes; las URLs propuestas fuera del registro se rechazan.
6. Se reutiliza `discover_news` y `EditorialCandidate`: identidad persistente, selección, descarte de duplicados y prioridad por categoría editorial. Los niveles `major_release`, `practical_update` y `research` ordenan la cola; no son mediciones de demanda, impacto o tráfico. Un borrador sin publicar no se trata como cobertura pública existente.
7. Los documentos pasan al catálogo de evidencias con identificadores estables. `worker.pipeline`, generación, revisión, corrección acotada y validadores siguen siendo los mismos. El artículo debe citar realmente la evidencia suficiente; se mantienen los controles de afirmaciones, originalidad y SEO.
8. Las noticias verificadas pueden publicarse por prioridad dentro de la misma jornada. Se retiran los topes globales anteriores de una publicación diaria y cinco semanales; no se impone una cantidad mínima. Si no se publica ninguna noticia viable, se evalúa la cola evergreen. Se conserva el límite específico de una actualización de contenido existente por semana, para no desplazar artículos nuevos.
9. La comprobación pública y la recuperación/retirada segura existentes se conservan. Una verificación pendiente detiene nuevas publicaciones hasta resolver su visibilidad. Las ejecuciones manuales explícitas y la recuperación siguen disponibles con sus protecciones; no constituyen otra programación automática.

## Presupuesto y costes

Se mantienen **0,15 USD diarios y 5 USD mensuales**, compartidos entre búsqueda, redacción, revisión y corrección. La configuración ahora rechaza también valores diarios superiores a 0,15 USD.

Fuentes oficiales consultadas el 27/10/2026:

- [Herramienta web de Responses API](https://developers.openai.com/api/docs/guides/tools-web-search).
- [Tarifas de herramientas](https://developers.openai.com/api/docs/pricing): búsqueda web a 10 USD por mil llamadas, es decir **0,01 USD por llamada**, más tokens.
- [Tarifas y contexto de GPT-5 Mini](https://developers.openai.com/api/docs/models/gpt-5-mini): **0,25 USD por millón de tokens de entrada y 2 USD por millón de salida**; contexto de 400.000 tokens. Se conserva el modelo accesible actual; la documentación lo identifica como una versión antigua/deprecada y debe vigilarse su disponibilidad. No se ha migrado a otro modelo ni modificado sus tarifas sin comprobarlas.
- [Contrato de Responses](https://developers.openai.com/api/reference/resources/responses/methods/create): `max_tool_calls` limita el total de llamadas a herramientas incorporadas.

Antes de buscar se reserva de forma atómica el contexto máximo posible del modelo, el primer prompt conocido —la herramienta puede producir un segundo turno—, hasta 3.000 tokens de salida y la llamada web. Con los cinco títulos actuales, la reserva máxima calculada sin enviar la petición es **0,117249 USD**. **Es una cota preventiva, no el coste esperado.** Si no cabe en el saldo diario o mensual no se llama al proveedor y puede utilizarse el saldo restante para evergreen.

Cuando hay una respuesta con uso completo comunicado, se registra una fila `GenerationUsage` de etapa `NewsResearch`, incluyendo tokens y coste de herramienta. Se libera únicamente el exceso confirmado de esa reserva de búsqueda bajo el mismo bloqueo transaccional. El resultado se guarda antes de interpretarlo. No se liberan reservas históricas ni las de otras fases; con consumo desconocido se conserva la reserva completa y no se repite la petición incierta.

Las fases de redacción/revisión mantienen sus reservas conservadoras existentes. El panel distingue esas reservas, el coste calculado según uso comunicado y la factura del proveedor, que **no está verificada**. No se presenta una simulación como gasto real.

Ejemplo aritmético, no factura ni medición de esta integración nueva:

| Fase | Tokens ilustrativos entrada/salida | Coste calculado |
| --- | --- | --- |
| Investigación con una búsqueda | 8.000 / 800 | 0,0136 USD |
| Redacción | 20.000 / 3.000 | 0,0110 USD |
| Revisión | 20.000 / 2.000 | 0,0090 USD |
| Total para un artículo sin corrección | | **0,0336 USD** |

El coste varía con el contexto y las correcciones. El límite operativo de toda la jornada permanece en 0,15 USD; un saldo insuficiente conserva los candidatos/borradores pertinentes y nunca autoriza gastar por encima del presupuesto para completar una pieza.

## Persistencia, concurrencia y supervisión

La reserva y la intención de búsqueda se guardan en una sola transacción bajo bloqueo de `ResearchControl`. Al adquirirlo se recarga el informe: otra sesión que ya haya iniciado la investigación impide una segunda llamada. La respuesta y la liquidación tienen clave de ledger estable por jornada, evitando dobles registros y devoluciones tras reinicios. Las peticiones inciertas se conservan sin reenvío automático.

El panel privado muestra oportunidades, motivos de selección/descarte, URLs propuestas, candidatos incorporados, publicaciones verificadas y costes calculados por fase. Los informes económicos y controles existentes siguen siendo la fuente persistente; no hay una segunda cola.

Las reservas históricas totales permanecen en **0,358222 USD**, con seis respuestas de uso históricas. No hubo llamadas de generación, búsqueda o revisión de pago adicionales en este despliegue. Los 21 barridos de media hora previos permanecen en el historial; no son ejecuciones del nuevo proceso nocturno.

## Pruebas y verificación

- **285 pruebas generales correctas**, 67 opcionales omitidas; **83 comprobaciones específicas correctas** en la última revisión (se solapan con la suite general, no se suman). Resultados exactos en `.local/nightly-suite-verified.log` y `.local/nightly-target-final.log`.
- 25 casos de investigación web: contrato, fechas, fuentes originales, corroboración, URLs no permitidas, duplicados, 403, descargas incompletas, respuestas inválidas, costes, reserva incierta, recuperación y límite diario.
- Simulación del recorrido completo: investigación estructurada → páginas verificadas → cola → generación → revisión → publicación aislada. Otro caso publica dos noticias distintas en una jornada dentro de presupuesto. Un caso sin noticias utiliza evergreen.
- **12 escenarios HTTP con Nuxt SSR real**: once planes evergreen y una noticia histórica aislada mediante el nuevo flujo de búsqueda. Se comprueban URL, contenido, metadatos, imagen y sitemap. Las respuestas OpenAI y páginas históricas son fixtures identificados, no pruebas comerciales ni noticias actuales.
- PostgreSQL real restaurado y sin red externa: reservas diarias/mensuales concurrentes, una sola llamada simulada para la misma jornada, liquidación y ledger idempotentes, identidad de candidatos y ventanas. No se escribieron artículos de prueba en producción.
- TypeScript, build Nuxt y builds Docker correctos. Panel de producción comprobado en móvil y con teclado, sin errores JavaScript ni desbordamiento horizontal. La activación de detección rápida ya no está disponible.
- Producción: siete servicios saludables, bases privadas, hashes de artículos/usuarios/comentarios/categorías/temas/historial económico conservados, cinco artículos públicos verificados y monitor sin alertas.

## Despliegue y rollback

Backup completo cifrado antes de cambiar producción:

`/var/backups/foroia/nightweb-20261027-final/`

Se restauraron las **19 tablas**, comparando sus hashes, además de Redis. Se verificó integridad de código/configuración y Caddy, y cuatro copias cifradas se copiaron fuera del VPS con SHA256 coincidente. No se introducen migraciones ni dependencias.

El directorio conserva imágenes anteriores, originales de los archivos cambiados, lista de archivos nuevos, `rollback.yml` y `rollback.py`. Recuperación:

```sh
sudo python3 /var/backups/foroia/nightweb-20261027-final/rollback.py
```

El rollback recupera API, web y trabajador anteriores sin restaurar una base antigua, eliminar artículos ni reiniciar reservas. La bandera rápida queda desactivada para que tampoco se reactive al volver a la imagen anterior. Antes de ejecutarlo comprobar que no haya una llamada facturable en curso y dejar que termine o conservar su estado incierto según el procedimiento de recuperación existente.

Archivos de aplicación desplegados:

- `api/app/research/night_web.py`
- `api/app/research/{config,writing,sources,selection,queue,editorial,worker,routes,monitor}.py`
- `web/pages/editorial/investigacion.vue`
- `web/utils/research-status.ts`

Pruebas añadidas/adaptadas: `tests/test_nightly_web.py`, `tests/nightly_postgres_check.py`, `tests/test_editorial_http.py` y `tests/test_editorial_recovery.py`. No se sobrescribió la portada desplegada, que difiere de la copia local.

## Verificación de la primera noche

Consultar la jornada del 27/10 en `/editorial/investigacion`: herramienta realmente ejecutada, uso comunicado, oportunidades y documentos recuperados, rechazos por URL/fecha/corroboración, publicación o uso de evergreen. Si publica, el verificador existente comprueba el artículo público y sitemap. Si falla la búsqueda, conservar el código HTTP/etapa y la reserva incierta; no repetir automáticamente una petición posiblemente facturada.

La consulta de metadatos del modelo y las simulaciones no demuestran que el proveedor acepte la primera búsqueda de esta cuenta. Tampoco se garantiza una publicación diaria: faltas de evidencia, bloqueos, revisión o presupuesto pueden impedirla legítimamente.
