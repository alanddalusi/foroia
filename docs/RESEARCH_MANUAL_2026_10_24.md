# Ejecución adelantada del 24/10/2026

El propietario autorizó ejecutar ahora la investigación, sustituyendo para esta prueba la petición anterior de esperar a las 22:30. Se utilizó el comando existente `python -m app.research.worker --once` dentro del trabajador de producción, mediante una unidad transitoria systemd. No se modificó código de aplicación, configuración, horario ni presupuesto.

## Resultado comprobado

- Inicio: 11:56:34 Europe/Madrid; fin: 11:57:11 del 24/10/2026.
- Proceso finalizado con código 0, trabajador persistente activo.
- Resultado editorial: `skipped`, motivo `invalid_evidence`, sin artículo asociado ni publicación nueva.
- Tres fuentes RSS configuradas, siete documentos candidatos, tres documentos recuperados. Organizaciones reconocidas: AI2, Hugging Face y Microsoft.
- Cuatro descargas de artículos de OpenAI devolvieron HTTP 403. No se intentó eludir las restricciones.
- Se redactó una propuesta y se aplicó una corrección automática. Ambas versiones fallaron `invalid_evidence`: el control exige que cada referencia identifique una fuente y que su cita esté contenida en el texto recuperado. No se completó la revisión generativa posterior; no afirmar que sus controles se aprobaron.
- Reserva conservadora del día: 0,034771 USD de 0,15 USD; del mes: 0,192200 USD de 5 USD. No representa una factura verificada del proveedor.
- No hay URL nueva ni comprobaciones de publicación/sitemap aplicables.

La restricción de una ejecución por fecha editorial sigue vigente: hoy a las 22:30 el trabajador detectará este registro y no repetirá la generación. El horario diario permanece intacto para los días siguientes. No se borraron registros ni se reintentaron llamadas adicionales.

## Evidencia y seguimiento

Expediente privado del VPS: `/var/lib/foroia/research-audits/manual-20261024/`, con report.md, report.json y snapshot.json. Copia privada local de los JSON en `.local/research-audit-20261024/`. El informe Markdown manual aclara que la ejecución fue adelantada por autorización; el observador no genera contenido.

Pendiente: analizar por qué las citas propuestas y corregidas no coinciden con la evidencia recuperada, mejorar la selección de citas y comprobarlo sin llamadas de pago antes de otro despliegue. Mantener la validación; no aprobar citas inválidas ni prometer publicaciones diarias. Ampliar alternativas públicas verificables para reducir la dependencia de las páginas con 403.
