export interface ResearchRunState { status: string; reason: string; finished_at?: string | null }

const labels: Record<string, string> = { running: 'Investigando', published: 'Publicado', review: 'Listo para revisión', draft: 'Borrador sin publicar', skipped: 'Sin publicación', interrupted: 'Interrumpido' }

const reasons: Record<string, string> = {
  partial_publication: 'Se publicaron algunos de los artículos previstos; consulta el resultado independiente de cada línea.',
  no_verified_publication: 'Ningún candidato terminó como publicación verificada. Consulta los fallos de cada línea.',
  checkpoint_sources_stale: 'La evidencia guardada necesita una comprobación de vigencia antes de reutilizarse.',
  evidence_source_changed: 'La documentación ha cambiado: se conserva el borrador, pero no se reutiliza la aprobación antigua.',
  publication_not_indexable: 'La comprobación de metadescripción o robots no coincide con lo esperado.',
  publication_schema_mismatch: 'Los datos estructurados no coinciden con el artículo publicado.',
  publication_missing_sitemap: 'La URL todavía no aparece en el sitemap comprobado.',
  uncertain_provider_result: 'No se conoce el resultado de una llamada: se conserva su reserva y no se repite automáticamente.',
  documentation_topic_merged: 'Apartado de documentación agrupado con una tarea editorial existente; se conservan las fuentes y el historial.',
  documentation_topic_not_actionable: 'La etiqueta de documentación no define un problema útil para el lector. No se encarga una redacción.',
  editorial_style_rejected: 'El texto necesita una reescritura: estructura repetitiva, atribuciones mecánicas o párrafos redundantes.',
  editorial_review_rejected: 'La revisión de naturalidad, estructura o atribución ha rechazado el artículo; se intenta corregir dentro del presupuesto.',
  invalid_editorial_review: 'La respuesta del revisor no incluye todas las comprobaciones editoriales obligatorias; no se publica.',
  verified_official_announcement: 'Anuncio oficial verificado: basta la fuente original para informar de lo anunciado por esa organización.',
  official_attribution_missing: 'El borrador debe atribuir las afirmaciones a la organización que hace el anuncio.',
  invalid_official_announcement: 'La evidencia no permite aplicar la excepción de anuncio oficial.',
  official_scope_requires_corroboration: 'El texto excede el anuncio oficial: requiere corroboración adicional o retirar esas afirmaciones.',
  news_research_empty: 'La búsqueda terminó sin noticias candidatas. Consulta su explicación; no acredita que no existan noticias.',
  news_research_failed: 'Falló la investigación de noticias. No se sustituye silenciosamente por un tutorial.',
  news_verification_exhausted: 'Se encontraron oportunidades, pero ninguna reunió evidencias verificadas suficientes.',
  news_retry_no_publication: 'La prueba adicional de noticias terminó sin publicar; se conserva el artículo anterior de la jornada.',
  no_candidates_reported: 'El proveedor no propuso candidatas; revisa el diagnóstico de búsqueda.',
  all_candidates_invalid: 'Todas las propuestas incumplieron el contrato; consulta los errores individuales.',
  research_failed_no_evergreen_substitution: 'La investigación falló o no explicó su resultado vacío; no se publicó un tutorial para ocultarlo.',
  evergreen_topic_cooldown: 'Se han publicado dos guías de esta familia técnica en siete días. Se priorizan otras aplicaciones de IA.',
  evergreen_missing_ai_application: 'La propuesta no tiene una aplicación de IA concreta y documentada.',
  verified_queued: 'Fuentes originales y corroboración comprobadas; noticia incorporada a la cola.',
  already_published: 'El acontecimiento ya está cubierto por una publicación existente.',
  stale_event: 'El acontecimiento propuesto queda fuera de la ventana de actualidad.',
  missing_original_source: 'Falta una fuente original accesible entre las evidencias seleccionadas.',
  invalid_web_research: 'La búsqueda no devolvió candidatos válidos o no acreditó una consulta web real.',
  uncertain_search_result: 'La búsqueda quedó con resultado incierto; se conserva la reserva y no se repite el cobro.',
  web_model_tariff_unverified: 'La búsqueda necesita un modelo con capacidad y tarifas verificadas.',
  rapid_heartbeat_missing: 'Falta la señal del detector gratuito de noticias.',
  rapid_scan_failed: 'La última detección de noticias se interrumpió; la ejecución nocturna sigue siendo independiente.',
  rapid_scan_stalled: 'No hay una detección reciente de noticias; revisa el trabajador.',
  rapid_disabled: 'La detección rápida está desactivada.',
  waiting_independent_sources: 'Acontecimiento detectado; esperando evidencias de otra organización independiente.',
  waiting_verified_sources: 'Anuncio detectado en RSS; todavía no tiene documentos verificados suficientes para redactar.',
  corroborated_named_event: 'Acontecimiento identificado y corroborado por fuentes independientes.',
  manual_budget_bucket: 'Reserva compartida de una ejecución manual. Consulta su resultado en Ejecución manual y recuperación.',
  execution_budget_exhausted: 'Se alcanzó el máximo autorizado para esta ejecución.',
  execution_call_limit: 'Se alcanzó el número de llamadas autorizado; el borrador se conserva.',
  quote_changed: 'La petición ha cambiado respecto al presupuesto; prepara una nueva autorización.',
  quote_expired: 'El presupuesto ha caducado; preparar otro no realiza llamadas de pago.',
  worker_heartbeat_missing: 'Falta la señal del trabajador.', scheduled_run_missing: 'No consta la ejecución prevista y ha pasado el margen de veinte minutos.',
  run_stalled: 'La ejecución supera el tiempo previsto; necesita comprobación.', editorial_run_failed: 'La investigación terminó con una incidencia técnica.',
  no_publication_today: 'La ejecución de hoy terminó sin publicar. Consulta su motivo; no se repite el gasto automáticamente.',
  publication_verification_stalled: 'Hay una publicación pendiente de comprobación desde hace más de diez minutos.',
  monthly_budget_exhausted: 'No queda presupuesto mensual para nuevas reservas.', source_http_403: 'Una fuente ha devuelto 403. Se conserva el bloqueo y se utilizan otras fuentes.',
  public_seo_check_failed: 'No se pudo completar la comprobación pública de SEO.', robots_invalid: 'robots.txt no coincide con la configuración prevista.',
  published_article_missing_sitemap: 'Un artículo publicado no aparece en el sitemap comprobado.', article_seo_mismatch: 'Una URL de artículo no coincide con sus metadatos previstos.',
  maintenance_weekly_cap: 'Se reserva capacidad para artículos nuevos: máximo una actualización automática por semana.',
  maintenance_budget_exhausted: 'La actualización alcanzó su límite de reserva de 0,06 USD. Se evalúa otro candidato.',
  migrated_local_budget: 'Reserva histórica importada del entorno local. No corresponde a una investigación activa en este servidor.',
  domain_not_allowed: 'Dominio no incluido en el registro de fuentes permitidas.',
  recovery_timeout: 'Se agotó el tiempo reservado para recuperar fuentes alternativas.',
  recovery_not_configured: 'Búsqueda alternativa sin proveedor configurado; no se ha realizado gasto.',
  recovery_budget_headroom: 'No se encargó otra búsqueda: el presupuesto disponible debe cubrir también redacción y revisión.',
  unexpected_search_count: 'La herramienta comunicó más búsquedas de las permitidas; se conserva su coste y se descarta la respuesta.',
  unrequested_event: 'La respuesta alternativa cambió el acontecimiento solicitado y se descartó.',
  news_only_no_verified_publication: 'La prueba de noticias terminó sin evidencias suficientes para encargar una redacción.',
  official_path_not_allowed: 'Ruta fuera del ámbito oficial autorizado.',
  unsafe_url: 'URL rechazada por los controles de seguridad.',
  document_inaccessible: 'Documento inaccesible; consulta el estado HTTP y la URL.',
  index_without_article: 'La URL es un índice y no se encontró un artículo individual relacionado y accesible.',
  document_unrelated: 'El documento no corresponde al acontecimiento investigado.',
  date_unverifiable: 'No se pudo verificar la fecha original de publicación.',
  document_stale: 'La fuente queda fuera de la ventana de actualidad.',
  unverified_organization: 'No se pudo verificar la organización autora.',
  independent_corroboration_missing: 'Hay documentación válida, pero falta corroboración del mismo acontecimiento por otra organización independiente.',
  recovery_limit_reached: 'Se alcanzó el límite de descargas de esta ejecución.',
  insufficient_document_content: 'El documento no tiene contenido suficiente para servir de evidencia.',
  quality_checks_passed: 'Controles superados', insufficient_sources: 'Faltan fuentes accesibles de distintas organizaciones',
  insufficient_independent_sources: 'El borrador no reúne corroboración suficiente', budget_exhausted: 'Presupuesto reservado agotado',
  insufficient_independent_topic_sources: 'No hay un tema con evidencias relacionadas de dos organizaciones independientes. No se ha encargado una nueva redacción.',
  weekly_target_reached: 'Se ha alcanzado el máximo de cinco publicaciones automáticas de esta semana. La investigación continúa sin generar más artículos.',
  no_viable_candidate: 'No hay candidatos viables ahora; se volverá a investigar en la próxima ejecución.',
  example_not_verified: 'El ejemplo de código no tiene una comprobación aislada reciente. Se probará otro candidato.',
  publication_verification_pending: 'Artículo generado; se están comprobando URL, contenido, metadatos y sitemap.',
  publication_check_failed: 'La comprobación pública falló. El contenido afectado se ha retirado o se ha restaurado su versión anterior.',
  candidate_internal_error: 'Incidencia en un candidato; se continúa con otro dentro de los límites.',
  insufficient_official_documentation: 'Falta documentación oficial suficiente para este contenido.',
  stale_sources: 'Las fuentes de la noticia han caducado; se busca otro tema.',
  candidate_attempt_limit: 'Este candidato ha agotado sus intentos permitidos.',
  verified_publication: 'Publicación comprobada: URL, contenido, metadatos y sitemap correctos.',
  preflight_interrupted: 'Se recuperó una preparación interrumpida sin repetir una llamada de pago.',
  interrupted_uncertain_generation: 'La generación se interrumpió con resultado incierto; no se repetirá automáticamente.',
  document_unavailable: 'Documentación temporalmente no disponible. Se continúa con otro candidato.',
  http_status: 'Una fuente ha rechazado la descarga. Se prueba otra fuente o candidato sin eludir el bloqueo.',
  short_document: 'La fuente no contiene documentación suficiente para redactar con respaldo.',
  invalid_example: 'El borrador no seleccionó el ejemplo verificado permitido.',
  document_fetch_budget: 'Se ha alcanzado el límite de recuperación de documentación de esta ejecución.',
  review_rejected: 'El revisor ha detectado dudas o falta de calidad', paused: 'Investigación pausada', invalid_evidence: 'Las citas no coinciden con las fuentes',
  duplicate_topic: 'Tema parecido a uno ya tratado', provider_unavailable: 'Proveedor no disponible', incomplete_generation: 'Generación incompleta',
  worker_interrupted: 'Trabajador interrumpido; no se repetirá el gasto de ese día', timeout: 'Tiempo de ejecución agotado', internal_error: 'Error interno',
  unsupported_number: 'Cifras sin apoyo suficiente', copied_text: 'Texto demasiado parecido a una fuente', invalid_generation: 'Respuesta no válida',
  insufficient_content: 'Contenido insuficiente', invalid_article: 'Metadatos no válidos', unsafe_format: 'Formato no permitido',
  provider_refusal: 'El proveedor ha rechazado generar el contenido', lock_lost: 'Se perdió la coordinación del trabajo', usage_outside_budget_bound: 'Uso fuera del límite estimado',
  article_changed: 'Un editor modificó el borrador durante la revisión automática', correction_limit_reached: 'Ya se utilizó la corrección automática permitida'
}

export function researchRunLabel(run: ResearchRunState): string {
  if (run.reason === 'migrated_local_budget') return 'Historial importado'
  if (run.status === 'running' && run.finished_at) return 'Finalizada'
  return labels[run.status] || 'Estado no reconocido'
}

export function researchRunReason(run: ResearchRunState): string {
  if (reasons[run.reason]) return reasons[run.reason]!
  if (run.status === 'running' && !run.finished_at) return 'Ejecución en curso'
  return 'No consta una ejecución activa. Consulta el expediente y los registros del servicio para conocer el resultado.'
}

export function researchDayNotice(runs: (ResearchRunState & { date: string })[], now: Date, at: string): string {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(now)
  const value = (type: string) => parts.find(p => p.type === type)?.value || ''
  const day = `${value('year')}-${value('month')}-${value('day')}`
  const run = runs.find(r => r.date === day)
  if (run?.reason === 'migrated_local_budget') return 'Hoy figura una reserva histórica importada. No acredita una investigación nueva y no se repetirá el gasto de esa fecha automáticamente.'
  if (run) return `Resultado de hoy: ${researchRunLabel(run)}. ${researchRunReason(run)}`
  const [hour, minute] = at.split(':').map(Number)
  if (hour === undefined || minute === undefined || !Number.isFinite(hour + minute)) return 'Consulta la programación de investigación.'
  const current = Number(value('hour')) * 60 + Number(value('minute'))
  const scheduled = hour * 60 + minute
  if (current < scheduled) return `La investigación de hoy está prevista a las ${at}, hora de Madrid. Todavía no consta una ejecución.`
  if (current < scheduled + 5) return 'Ya ha llegado la hora de inicio. El trabajador comprueba la programación cada 30 segundos; actualiza para ver el resultado.'
  return 'No consta una ejecución de hoy y han pasado más de cinco minutos desde la hora programada. Revisa el estado del trabajador y sus registros.'
}
