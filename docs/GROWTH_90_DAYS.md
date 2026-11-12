# Auditoría de crecimiento y plan de 90 días

Foro IA al Día · 23/10/2026 · Solo auditoría y planificación. No se modificaron producción, configuración, horarios, contenidos ni presupuesto; no se ejecutó investigación ni se crearon publicaciones de prueba. Se consultaron páginas públicas, código y el estado de investigación mediante lecturas. Evidencia pública local: `.local/deploy/growth-public-audit.json`; estado de investigación: `.local/deploy/growth-research-current.json`.

## 1. Diagnóstico y objetivo medible

El cuello de botella actual es el catálogo y su diferenciación, no un problema general de acceso o SSR. Hay **un artículo publicado**, en Actualidad, y **cero temas públicos del foro**. Herramientas, Tutoriales y Programación no tienen artículos publicados. El sitio ya tiene rutas individuales, SSR, canonical, metadatos, sitemaps divididos, redirecciones y privacidad básica; rehacerlos no es la primera inversión.

Propuesta de definición del objetivo: **100.000 sesiones mensuales de Organic Search en GA4**, contando por mes natural y mostrando por separado el tráfico total. Debe confirmarse esta definición al iniciar la medición; sesiones, usuarios, páginas vistas, cargas HTML del dashboard y clics de Search Console son magnitudes diferentes. GA4 en modo de consentimiento básico solo observará una parte del tráfico. No extrapolar visitantes que rechazan como si estuvieran medidos.

100.000 sesiones/30 días son unas 3.333 diarias. Como simple aritmética de escala, 100 artículos con 1.000 sesiones mensuales de media darían 100.000; no es una previsión, una recomendación de producir 100 artículos ni un promedio que podamos esperar. Una distribución real puede concentrarse en unas pocas páginas. **No hay evidencia para prometer llegar en 90 días**. Este trimestre debe validar temas, producción y medición antes de proyectar una fecha o gastar más.

No tengo acceso a la propiedad privada de Search Console ni a informes GA4. La verificación y aceptación del sitemap fueron comunicadas por el propietario. No conozco clics, impresiones, consultas, posiciones, enlaces entrantes ni volúmenes de búsqueda reales del dominio. No se han comprado bases de palabras clave ni inventado volúmenes/KD. La muestra de resultados web no es un ranking Google España estable ni una medición de demanda.

## 2. Inventario y evaluación del artículo real

URL: https://foroiaaldia.com/articulos/agentic-commerce-anuncios-agentes-servicio-asia

Título: **Agentes de IA: distinguir el interés comercial de la fiabilidad técnica**. Publicado el 22/10/2026. Autor visible: «Redacción automatizada · IA». Aproximadamente 321 palabras en el cuerpo, incluidos títulos y aviso de automatización.

| Comprobación | Resultado observado | Acción recomendada |
| --- | --- | --- |
| URL y estado | Individual, 200, sin fragmento; slug estable | Mantenerla. No cambiar por estética sin 301 y comprobación posterior |
| Title/description/canonical | Presentes y coherentes con el artículo | Con un solo artículo no se demuestra unicidad a escala; comprobar todos al crecer |
| SSR y estructura | Texto entregado en HTML, encabezados, Article/BlogPosting y BreadcrumbList | Conservar y validar al ampliar el editor |
| Utilidad | Diferencia preferencias comerciales de una prueba técnica; no presenta ambos estudios como validación mutua | Añadir checklist de evaluación, ejemplo reproducible y explicación de términos si aportan valor; no alargar para alcanzar una cifra SEO |
| Intención | Análisis especializado, no tutorial de agentes ni respuesta amplia a «qué es IA» | Asignar una intención concreta: cómo evaluar fiabilidad de agentes. No intentar cubrir todas las búsquedas con esta página |
| Fuentes | Dos enlaces, ambos respondieron 200 al comprobarlos | Disponibilidad no acredita cada afirmación ni revisión por pares |
| Enlaces internos | Navegación a secciones, pero cero enlaces a otros artículos; related vacío | Es normal con un único artículo. Crear piezas complementarias y enlazarlas con contexto real |
| Imagen | Ilustración genérica por sección y OG local | No sustituye capturas, ejemplos o resultados originales de un tutorial |
| Autoría | Automatización declarada; no hay identidad experta humana acreditada | Añadir quién responde editorialmente cuando haya datos reales autorizados; no fabricar expertos |

Fuentes del artículo: [IBM Research en Hugging Face](https://huggingface.co/blog/ibm-research/altk-evolve-bc) y [Google e-Conomy SEA](https://blog.google/company-news/inside-google/around-the-globe/google-asia/e-conomy-sea-report-2026/). Son trabajos sobre cuestiones diferentes. Dos organizaciones en un texto no equivalen a dos verificaciones independientes de cada afirmación. La lectura conjunta resulta defendible precisamente porque explicita esa distinción. El artículo no acredita por sí solo un ciclo autónomo completo: su publicación inicial requirió intervención editorial del operador.

## 3. Qué cubre realmente la investigación nocturna

Lectura actual de producción: habilitada, clave configurada sin exponerla, señal activa; 22:30 Europe/Madrid, publicación automática condicionada, 5 USD/mes. A las 12:15 del 23/10 solo había registros importados de los días 21 y 22; aún no se había observado un ciclo nocturno nuevo completo. No se forzó ninguno.

Fortalezas existentes:

- Tres fuentes registradas: OpenAI News, Hugging Face Blog y Google AI; predominantemente inglés. TLS, límites de descarga y destinos permitidos.
- Ventana reciente de 48 horas, máximo ocho documentos candidatos descargados y extracción de texto.
- Evidencias literales contrastadas con los documentos, controles de números, coincidencias/copias, dos organizaciones y revisión automática.
- Detección aproximada de duplicados por similitud de título/texto frente a los últimos 300 artículos, una corrección acotada, reservas económicas persistidas y fecha editorial única.
- Publica solo tras superar los controles. La publicación llega al terminar el proceso, no necesariamente a las 22:30 exactas. No hay publicación diaria garantizada ni generación de temas del foro.

Limitaciones que afectan al crecimiento:

- Ordena candidatos por palabras y novedad; **no mide demanda de búsqueda**, interés de lectores, SERP ni dificultad competitiva.
- Tres feeds de novedades no son una biblioteca de documentación duradera. Faltan fuentes de otros proveedores y recursos para tutoriales; no rastrea LinkedIn o todos los foros.
- Redactar y revisar con IA puede compartir errores. Un extracto coincidente demuestra trazabilidad, no que la afirmación sea verdadera ni que el texto aporte conocimiento nuevo. La originalidad semántica no está certificada por los umbrales de similitud.
- La organización se asigna por feed: un artículo de IBM en Hugging Face queda bajo ese registro. Haría falta distinguir autor/editor, plataforma y dependencia entre fuentes para hablar con precisión de independencia.
- La regla de dos organizaciones encaja en ciertas noticias; puede excluir tutoriales sólidos de una sola herramienta. La propuesta futura es diferenciar políticas por tipo de pieza: documentación oficial + prueba reproducible para tutoriales, corroboración adecuada para afirmaciones periodísticas. No se cambia ahora ni se relajan controles para cumplir cuota.
- No hay ejecución real de pasos, captura de interfaz, comparación sobre el mismo conjunto de tareas o validación de resultados de herramientas. No debe afirmar «lo probamos» sin esa evidencia.
- No existe una cola editorial de 90 días ni un selector que distribuya automáticamente tutoriales/comparativas/noticias. El nuevo plan **no está implementado por existir este documento**.

Mejora propuesta: asignar a cada oportunidad una intención, audiencia, formato, utilidad demostrable, fuentes necesarias y coste antes de redactar. Reutilizar investigación/documentación y actualizar una URL existente cuando responda a la misma intención. Cualquier llamada futura debe pasar por el mismo contador de 5 USD/mes y su límite diario; no crear un segundo trabajador o presupuesto para guías. Priorizar, no ampliar el gasto. Google advierte sobre contenido masivo sin valor y recomienda verificar el material generado; las comprobaciones automáticas no garantizan cumplimiento ni posiciones [1,2].

## 4. Categorías y oportunidades: hipótesis, no volúmenes

**Foco inicial recomendado: IA práctica en español para estudiar y trabajar con documentos.** Es una audiencia concreta que permite ejemplos repetibles y piezas conectadas. No competir de entrada por «inteligencia artificial» o «mejores IA» sin especialización.

| Prioridad | Grupo dentro de categorías existentes | Búsquedas/ideas candidatas | Potencial relativo y dificultad estimados |
| --- | --- | --- | --- |
| A | Tutoriales: documentos y estudio | resumir PDF con citas; NotebookLM con apuntes; comprobar un resumen; crear tarjetas; PDF escaneado | Mejor encaje inicial. Tareas concretas y actualización repetible; competencia ya visible. Demanda cuantitativa desconocida |
| A | Herramientas: comparativas por tarea | NotebookLM vs chatbot para el mismo PDF; comparar herramientas gratuitas para documentos en español | Intención de elección clara. Requiere pruebas y límites fechados, no rankings de opiniones |
| B | Programación y automatización | extracción de PDF; comprobar fuentes; agentes vs flujo automático; permisos y confirmación | Público más especializado y mayor coste de prueba. Elegir según consultas reales, no por moda |
| B | Actualidad útil | cambios que afectan a subir documentos, citar o exportar resultados | Puede captar interés puntual, vida útil incierta y competencia editorial alta. Explicar impacto y enlazar a una guía |
| C | IA local | instalación y verificación de un flujo local en un equipo documentado | Hipótesis secundaria; requiere hardware disponible y pruebas. No lanzar un grupo amplio aún |
| C | Listas generales, prompts genéricos, «qué es IA» | conceptos y listas globales | Material de apoyo, no principal apuesta de adquisición al comenzar |

Muestra consultada: Xataka Basics ya publica guías de NotebookLM para estudiar [3]; bibliotecas universitarias tratan errores y verificación [4]; Hipertextual tiene comparativas con tareas concretas [5]. Aparecen además directorios/listas y tutoriales en vídeo para búsquedas amplias. **La oportunidad inferida es aportar documentos propios de prueba, procedimientos y limitaciones verificables, no asumir que la competencia es débil.** No se han validado ni copiado las afirmaciones comerciales de otras listas.

Validación de cada idea: revisar 5–10 resultados actuales de la consulta en español, intención y formatos; anotar qué pregunta queda sin responder, qué evidencia podemos producir y cómo se diferencia de una URL propia. Usar primero consultas de Search Console; Google Trends puede ayudar a comparar interés relativo, no dar visitas absolutas. Si no podemos aportar algo verificable, no crear la pieza.

## 5. Arquitectura editorial y enlaces

Conservar las cuatro categorías existentes. No crear decenas de etiquetas o categorías vacías. Una guía principal de documentos/estudio puede agrupar piezas complementarias; esto sería contenido real en una URL individual, no un listado vacío nuevo.

Cada nueva pieza: una intención principal, título claro sin fechas/promesas falsas, respuesta breve inicial, requisitos/plan/versión/fecha, pasos o metodología, ejemplo propio y resultado esperado, fallos/limitaciones, fuentes identificadas y siguiente lectura pertinente. Sin longitud mínima artificial. Las comparativas deben usar el mismo documento o tareas, indicar planes y fecha y separar observación de recomendación.

Enlazar guía → tutorial específico → guía y comparativa relacionada cuando existan. Revisar que cada artículo sea alcanzable desde una sección y otro contenido relevante al crecer, sin forzar enlaces irrelevantes ni inventar páginas. No añadir UTM a enlaces internos. Actualizar en la misma URL si cambia la herramienta sin cambiar la intención; decidir una nueva URL solo para una necesidad diferente.

Limitación técnica comprobada: ArticleBody solo renderiza texto escapado, títulos, listas y código; **no soporta enlaces contextuales, tablas ni capturas por bloque**. Los related automáticos actuales son hasta tres de la misma sección. Propuesta P1: bloques seguros o relaciones editoriales a IDs publicados y medios locales controlados, manteniendo escape/validación y ocultando referencias retiradas. No activar HTML arbitrario o v-html para resolverlo.

## 6. Calendario de 90 días y capacidad

Ventana orientativa: 23/10/2026–20/01/2027. Las semanas son bloques de trabajo de siete días, no fechas de publicación obligatorias. Cadencia base propuesta: **10 piezas nuevas de fondo + 2 actualizaciones en 12 semanas**, más hasta una noticia seleccionada por semana si hay evidencia y recursos. Son entregables propuestos, no publicaciones autorizadas o un nuevo límite técnico aplicado. La configuración actual puede publicar hasta una pieza diaria; armonizarla con el calendario requiere la tarea de cola/selección, aún pendiente.

| Semana | Entregable principal | Sección/formato | Esfuerzo editorial orientativo |
| --- | --- | --- | --- |
| 1 | Línea base de medición y actualizar el artículo de agentes con checklist útil, sin cambiar URL | Actualidad/actualización | 2–3 h de contenido + preparación de métricas |
| 2 | Resumir un PDF conservando citas: procedimiento y ejemplo propio | Tutorial | 3–4 h |
| 3 | NotebookLM con apuntes: de documento a preguntas verificables | Tutorial | 3–5 h |
| 4 | Un PDF escaneado no se procesa: diagnóstico y alternativas verificadas | Resolución de problema | 3–4 h |
| 5 | NotebookLM y un chatbot con el mismo documento: resultados y límites | Comparativa | 5–7 h |
| 6 | Tarjetas de repaso: generarlas y comprobar que no inventan datos | Tutorial | 3–4 h |
| 7 | Cómo evaluar un resumen de IA: checklist descargable con ejemplo | Guía práctica | 3–4 h |
| 8 | Herramientas gratuitas para documentos: comparación por tareas y restricciones actuales | Comparativa | 5–7 h |
| 9 | Agente frente a automatización: ejemplo con permisos y confirmación | Explicación con demostración | 3–5 h |
| 10 | Extraer texto de un PDF con Python y detectar errores antes de usar IA | Programación/tutorial | 4–6 h |
| 11 | Experimento elegido con Search Console: ampliar el grupo ganador; IA local solo si hay demanda y equipo disponible | Tutorial o comparativa | 4–6 h |
| 12 | Actualizar piezas con impresiones/clics y decidir el siguiente trimestre | Actualización, sin duplicar URL | 2–4 h |

Actualidad: solo cambios relacionados con los grupos elegidos, con enlace a una guía que resuelva una tarea. No cubrir cada lanzamiento. La noche sigue con su configuración actual hasta autorizar mejoras; su salida no se cuenta como tutorial probado. La mezcla de contenidos deseada no se consigue solo cambiando el prompt.

Capacidad: aproximadamente **40–60 horas editoriales en el trimestre**, más 30–45 minutos semanales de evaluación y las tareas técnicas estimadas aparte. Son horas de trabajo de operador/redactor/pruebas, no tiempo garantizado que la IA actual elimina. El propietario estudia y tiene poco tiempo: puede delegar ejecución y reservar una revisión semanal, pero hoy no existe el agente que haga todas esas pruebas. Si solo hay una hora total semanal y nadie ejecuta pruebas, reducir a unas seis piezas principales en 90 días y aplazar programación/IA local; no fingir pruebas ni aumentar publicaciones para compensar. No se recomiendan suscripciones o ensayos de pago adicionales.

## 7. Medición necesaria

### Search Console: línea base sin esperar GA4

Guardar exportación semanal de consultas, páginas, clics, impresiones, CTR, posición media, país y dispositivo; separar marca/no marca, tipo de contenido y cohortes por fecha de publicación. Comparar 28 días completos con los 28 anteriores, sin usar días preliminares ni exigir una posición fija a todas las búsquedas. Conservar contexto de cambios y anotaciones de publicaciones. La posición es una media, no un puesto universal [6].

Revisar sitemaps, indexación de páginas y muestra de inspección de URLs nuevas; distinguir «sitemap aceptado», «rastreada» e «indexada». Si falta indexación, investigar una muestra antes de pedirla manualmente para todas. No hay exportaciones privadas disponibles durante esta auditoría.

### GA4: no activarlo todavía sin corregir atribución y completar privacidad

Hallazgo real P0: AnalyticsConsent envía **page_referrer vacío** en config y page_view. Ese campo interviene en el cálculo del origen [7]; la preparación actual puede perder atribución orgánica/referida. Además page_location elimina toda query, por lo que las campañas UTM no se conservarían explícitamente. No se ha medido el efecto con tráfico real porque GA4 sigue desactivado. Es un problema de medición, no una penalización de ranking.

Corregir en desarrollo la conservación del origen externo seguro y parámetros de campaña expresamente permitidos, evitando URLs con datos personales; validar primera entrada, aceptación tardía, navegación SPA y retirada. No conservar indiscriminadamente queries ni referentes completos por medir más. La implementación anterior priorizó minimizar datos, pero necesita este ajuste para medir adquisición.

| Métrica/evento | Uso | Criterio de validación propuesto |
| --- | --- | --- |
| Sesiones por Session default channel group y source/medium | Separar Organic Search, Direct y Referral | Entradas de prueba controladas bien clasificadas tras consentimiento; no inferir orgánico si figura Direct |
| page_view | Páginas y navegación SPA | Un evento por navegación pública; ninguno en panel/cuenta, sin duplicación de medición automática |
| Landing page + article_id/section/content_type | Qué páginas captan tráfico y qué formatos funcionan | IDs públicos estables, sin correos, cuentas ni texto de documentos |
| Sesiones con interacción, tasa y tiempo de interacción | Utilidad aproximada | Comprobar informes y denominadores; tiempo de pantalla activa, no prueba de aprendizaje [8] |
| article_read (p. ej. 60 s visibles y 75% de contenido) | Lectura útil aproximada | Una vez por artículo/sesión, definición documentada; no fingir que el scroll es satisfacción |
| related_article_click | Continuidad de lectura | Parámetros solo IDs públicos origen/destino; enlaces siguen funcionando sin analítica |
| source_link_click / resource_download | Consulta de fuentes o uso de un recurso propio | Un evento por acción, destinos sin datos personales; no marcar todo como conversión |
| Registro verificado/newsletter | Retención futura | No implementarlos como KPI mientras altas/correo/newsletter no funcionen |

Organic Search debe medirse con la dimensión de sesión, no con el origen del primer usuario ni el canal de evento [9]. Enlazar GA4 y Search Console cuando proceda facilita informes, pero sus clics y sesiones no tienen por qué coincidir. Consentimiento, bloqueadores, sesión, zona horaria y definiciones explican parte de la diferencia; nunca dividir o extrapolar ciegamente para fabricar visitantes.

Configurar zona Europe/Madrid en GA4, exclusión de tráfico interno/desarrollo con comprobación previa, medición mejorada compatible sin duplicar page_view/formularios y conservación mínima apropiada. Aceptar/rechazar/retirar se prueba antes de habilitar. La tasa de aceptación no debe medirse enviando eventos a Google antes de consentimiento. El contador propio de cargas HTML continúa siendo auxiliar: no mide sesiones, omite navegación interna SPA y filtra bots de manera aproximada.

## 8. Backlog priorizado con esfuerzo y aceptación

Estimaciones de trabajo activo, no plazos garantizados ni compromisos de tráfico. No se suman automáticamente las tareas opcionales al plan base.

| ID | Prioridad / momento | Tarea concreta | Responsable / esfuerzo | Cómo comprobar resultado |
| --- | --- | --- | --- | --- |
| G01 | P0 / días 1–7 | Exportar línea base Search Console y fijar definición de 100k | Titular + analista, 1–2 h | Exportación fechada; clics y sesiones separados; tablero semanal sin datos inventados |
| G02 | P0 / antes de GA4 | Corregir referrer/campañas, consentimiento y SPA en desarrollo | Ingeniería, 4–8 h | Pruebas de origen y eventos, cero peticiones previas al permiso, cero PII; no se activa producción todavía |
| G03 | P0 / días 1–14 | Elegir 10 intenciones sin solapamiento y definir evidencia de cada una | Editor, 3–5 h | Backlog con consulta, audiencia, evidencia propia, fuentes y URL propuesta; revisión de resultados actuales |
| G04 | P0 / primer ciclo nocturno | Observar registros reales y clasificar cada no-publicación sin forzar generación | Operador, 1–2 h inicial y 10 min/semana | Estado, motivo, coste reservado, artículo y fuentes; prueba real diferenciada de reservas migradas |
| G05 | P1 / días 8–30 | Publicar primeras tres piezas útiles y mejorar la existente | Editor/pruebas, 11–16 h | Pasos reproducidos, fuentes y plan/fecha; HTML y sitemap correctos; sin relleno |
| G06 | P1 / días 8–30 | Enlaces contextuales/relaciones editoriales seguras y medios por artículo | Ingeniería, 8–16 h | Permisos, enlaces solo a contenido público, escape, dimensiones de medios y retirada comprobados |
| G07 | P1 / días 15–45 | Cola por intención/formato y actualización frente a nueva URL | Ingeniería + editor, 10–18 h | Selección trazable; evita duplicar la misma intención; no añade llamadas fuera del contador existente |
| G08 | P1 / días 15–45 | Separar políticas de evidencia para noticia, tutorial y comparativa; mejorar identidad de fuente | Ingeniería + editor, 8–16 h | Fixtures de fuentes dependientes, tutorial no ejecutado y comparativa sin prueba rechazados o etiquetados; ningún bypass por cuota |
| G09 | P1 / semanal | Capturas/datos/resultados de cada tutorial y comparar sobre misma tarea | Editor o agente con ejecución verificada, incluido en horas editoriales | Evidencia fechada, sin datos privados; no se atribuye prueba inexistente |
| G10 | P1 / días 30, 60, 90 | Revisar grupos y actualizar las mejores oportunidades | Analista/editor, 1–2 h por revisión + edición | Decisión por consultas/páginas/cohortes; muestra pequeña se declara insuficiente |
| G11 | P1 / continuo | Corregir incidencias reales de indexación/CWV si aparecen | Ingeniería, 2–6 h de diagnóstico por incidencia | URL afectada y antes/después medidos; sin cambiar canonical/rutas por intuición |
| G12 | P1 de confianza / antes de activar terceros | Completar responsable y políticas reales, revisar autoría/contacto | Titular y asesor si procede; ingeniería 1–3 h tras recibir datos | Datos autorizados, contacto y textos consistentes; no inventar identidad |
| G13 | P2 / con catálogo | Recursos originales y difusión pertinente, sin compra/spam | Editor, 1–2 h/semana opcional | Recurso reutilizable y referencias reales; ningún enlace garantizado ni mensajes sin autorización |
| G14 | P2 / después de demanda real | Búsqueda interna, RSS o newsletter | Ingeniería, estimar por función | Se justifica por uso; búsqueda noindex; newsletter solo con SMTP/consentimiento |
| G15 | Operativo / continuo | Revisar avisos de dependencias, backup y alertas externas | Operador, 1 h/semana; alertas a estimar | Sin regresiones y con restauración/avisos comprobados; no afirmar que añadir Redis/CDN mejora rankings |

G07 y G08 son desarrollos propuestos, no exigencias para empezar a escribir tres guías contrastadas manualmente. Si el tiempo es limitado, primero G01/G03/G04/G05 y G02 antes de GA4; después G06. No gastar el primer mes rehaciendo infraestructura, instalando un buscador con un artículo o abriendo un foro vacío. AdSense no es palanca de adquisición: sigue pendiente de datos legales, aprobación y consentimiento adecuado, y su incorporación debe medir CLS/retención.

## 9. Puertas de decisión a 30, 60 y 90 días

Estos son criterios de trabajo, no pronósticos ni umbrales oficiales de Google:

- **Día 30:** línea base guardada, tres piezas de fondo nuevas + actualización, cada publicada con intención/evidencia/fuentes/URL única y enlaces pertinentes existentes. Cero fallos críticos de acceso, sitemap o canonical. Inspeccionar muestra de URLs; si no hay indexación, resolver causas antes de escalar.
- **Día 60:** siete piezas de fondo nuevas acumuladas si hay capacidad; al menos un grupo empieza a mostrar impresiones no de marca en varias URLs. Si no hay muestra suficiente, continuar diagnóstico de demanda/calidad/distribución; no dar por hecho que falta volumen. Revisar posibles canibalizaciones cuando dos URLs compitan por la misma intención.
- **Día 90:** diez piezas nuevas + dos actualizaciones, si se ha asignado el esfuerzo. Comparar ventanas completas de 28 días y cohortes; describir qué grupos reciben consultas y clics, coste/horas y errores. Elegir mantener, profundizar o cambiar foco. No crear una previsión a 100k con solo unas decenas de clics.

Reglas concretas: una página con ≥200 impresiones completas, posición media aproximada 5–20 y CTR inferior a páginas propias comparables puede entrar en prueba de title/description; es un criterio de selección, no un CTR universal. Una URL sin impresiones tras 4–6 semanas exige separar indexación, intención y competencia; no se borra ni se reescribe automáticamente. Si hay impresiones pero escasos clics en todo el sitio, revisar intención y resultados reales antes de producir más. Con pocos datos, no hacer A/B tests ni porcentajes de crecimiento espectaculares desde cero.

El resultado esperado del trimestre es un catálogo inicial verificable, medición fiable y evidencia para priorizar, no 100.000 visitas garantizadas. Se puede mantener la meta a largo plazo y ajustar ritmo cuando existan datos y capacidad.

## Fuentes y alcance

Fuentes primarias para criterios técnicos/medición; ejemplos de competidores únicamente para observar formatos y cobertura, no para validar prestaciones de herramientas. Consultadas el 23/10/2026:

1. https://developers.google.com/search/docs/fundamentals/using-gen-ai-content/
2. https://developers.google.com/search/docs/fundamentals/creating-helpful-content
3. https://www.xataka.com/basics/como-usar-notebooklm-para-ayudarte-a-estudiar-repasar-nuevo-curso-escolar
4. https://bibliotecas.duoc.cl/ia-investigadores/NotebookLM
5. https://hipertextual.com/tecnologia/chatgpt-vs-gemini-analisis-comparativa/
6. https://support.google.com/webmasters/answer/7576553
7. https://developers.google.com/analytics/devguides/collection/ga4/reference/config
8. https://support.google.com/analytics/answer/12195621
9. https://support.google.com/analytics/answer/9756891

Solo se añade documentación local y evidencia de auditoría. No hay cambios de aplicación que compilar ni pruebas de escritura/publicación que ejecutar para este encargo.
