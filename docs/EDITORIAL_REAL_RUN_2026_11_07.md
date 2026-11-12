# Ejecuci?n real adelantada ? 7 de noviembre de 2026

Autorizaci?n: el propietario solicit? lanzar los procesos para publicar nuevos art?culos. Se ejecut? una sola vez el trabajador existente con `--once`, sin modificar c?digo de producci?n, configuraci?n, cuotas, modelos ni programaci?n. No se utilizaron mocks ni inserciones editoriales manuales.

## Resultado comprobado

- Jornada #18, 7/11/2026, iniciada aproximadamente a las 03:16 de Madrid y terminada aproximadamente a las 03:21.
- Estado final `published / partial_publication`: **1 publicaci?n de 3 previstas**. El bloqueo Redis qued? libre; los seis servicios contin?an funcionando y API/web saludables. PostgreSQL y Redis sin puertos p?blicos.
- Art?culo #22, categor?a Programaci?n: [streaming api openai python: comparar opciones y prÃ¡cticas](https://foroiaaldia.com/articulos/streaming-api-openai-python-comparar-opciones-practicas). Publicado a las 03:21:31 de Madrid.
- Generaci?n y revisi?n reales mediante OpenAI. Documentaci?n oficial de OpenAI y Anthropic como fuentes. El art?culo no demuestra una prueba pagada contra las APIs descritas.
- Verificaci?n del trabajador e independiente desde Windows: HTTP 200, contenido SSR, API coincidente, H1/title/canonical, metadescripci?n/OG, datos estructurados/fechas/fuentes, imagen accesible y presencia en sitemap. Sin afirmar indexaci?n por Google.

## Cupos no completados

- Actualidad: b?squeda real con `web_search`, tres propuestas con esquema v?lido; ninguna verificada. Fuentes inaccesibles/403, l?mites de tama?o y un ?ndice sin art?culo espec?fico impidieron validar las propuestas. Recuperaci?n alternativa real acotada tampoco permiti? verificarlas. Se evit? redactar los tres candidatos sin evidencia.
- La cola de noticias aport? adem?s candidato #33 (NVIDIA), cuyo borrador no se reanud? por `checkpoint_sources_stale`. El motivo final de la l?nea refleja este ?ltimo intento, no todos los descartes de la b?squeda.
- Pr?ctico #38 (l?mites de APIs): borrador #20, correcci?n y revisi?n; `unsupported_number`, c?digo HTTP 429 se?alado por el validador. Queda `correction_pending`, se conserva el borrador. Hay que investigar el contexto de evidencia antes de determinar si es falso positivo.
- Pr?ctico #39 (errores APIs): borrador #21, correcci?n y revisi?n; `unsupported_number`, n?mero 4 se?alado. Queda `correction_pending`, con borrador. El revisor aprob? el respaldo pero fall? el control determinista; requiere analizar ambos criterios, sin eludir el validador.
- Pr?ctico #40 (tokens): `deferred / short_document`, sin generaci?n pagada para ese candidato.
- Pr?ctico #41 (streaming): redacci?n y revisi?n aprobadas, publicaci?n y comprobaciones completas. No se reabrieron cuotas ni se generaron duplicados.

## Consumo y reservas

Coste calculado con tokens y acciones de herramienta informados por la API; **no es una conciliaci?n de la factura del proveedor**.

| Fase | Consumo calculado |
| --- | ---: |
| NewsResearch | 0.016884 USD |
| SourceRecovery | 0.015261 USD |
| Draft | 0.035835 USD |
| Review | 0.045996 USD |
| **Total** | **0.113976 USD** |

- Las reservas de llamadas concluidas quedaron liquidadas al consumo calculado: 0.113976 USD en la jornada.
- L?mite diario 0,50 USD; disponible 0.386024 USD.
- L?mite mensual 15 USD; acumulado reservado/contabilizado 0.503650 USD; disponible 14.496350 USD.
- Dos acciones de b?squeda en total: investigaci?n y recuperaci?n alternativa. Se respetaron los topes existentes; no se relanz? la jornada ni se gast? el saldo para forzar una publicaci?n.

## Pr?ximo turno

El panel autenticado confirma **8/11/2026, 22:30 Europe/Madrid**. El 7/11 a las 22:30 no repetir? la jornada ya adelantada. Publicaci?n autom?tica activa. La salud cacheada del panel a?n mostraba la pasada en curso a las 03:20; la consulta directa posterior confirm? terminaci?n y bloqueo libre.

## Artefactos privados

`.local/deploy/manualdaily-20261107-full.json`, `manualdaily-20261107-published-snapshot.json`, `manualdaily-20261107-public-verified.json`, `manualdaily-20261107-final-overview.json`. Registro del servidor: `/var/log/foroia/manual-daily-20261107.log`.

Esta intervenci?n fue operativa: sin despliegue, cambios de credenciales, DNS, firewall, presupuesto ni horario. Los borradores fallidos permanecen privados y conservados. El objetivo de tres publicaciones diarias no se ha demostrado con esta ejecuci?n.
