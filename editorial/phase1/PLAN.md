# Primera fase editorial: diez temas y tres borradores

Estado: pendiente de revisión del propietario. Nada publicado, importado en la base de producción o enviado al trabajador nocturno. El gasto y el horario existentes no se modifican. No se atribuyen volúmenes de búsqueda ni dificultad SEO calculada: las palabras clave representan intenciones propuestas.

## Primera entrega completa

| ID | Título SEO | Palabra clave principal | Categoría | URL pública propuesta |
| --- | --- | --- | --- | --- |
| T01 | Cómo resumir un PDF con IA y comprobar sus citas | resumir PDF con IA | tutoriales | /articulos/resumir-pdf-ia-comprobar-citas |
| T02 | NotebookLM con un PDF: prepara las fuentes y revisa las citas | NotebookLM PDF fuentes citas | herramientas | /articulos/notebooklm-pdf-fuentes-citas |
| T03 | Extraer texto de un PDF con Python antes de usar IA | extraer texto PDF Python | programacion | /articulos/extraer-texto-pdf-python |

Metadescripciones propuestas:

- T01: «Aprende a resumir un PDF con IA y revisar fechas, cifras y citas con un documento de ejemplo y una referencia que puedes comprobar.»
- T02: «Prepara un PDF como fuente en NotebookLM y aprende a revisar sus citas. Guía basada en documentación oficial, con un ejercicio de comprobación.»
- T03: «Extrae texto de un PDF con Python y pypdf, conserva las páginas y detecta casos sin texto antes de enviar el documento a una IA.»

Contenido íntegro: [T01](01-resumir-pdf.md), [T02](02-notebooklm-fuentes.md), [T03](03-extraer-pdf-python.md). Los tres tienen ejemplo común original; no son tres resúmenes del mismo tema. T01 responde a un procedimiento de revisión independiente del producto, T02 a una interfaz documental concreta y T03 a extracción mediante código. El artículo ya publicado sobre agentes analiza fiabilidad frente a interés comercial: ninguna nueva pieza lo duplica.

## Briefs: intención, estructura, fuentes y diferencia

### T01 — Resumir un PDF con IA y comprobar sus citas

- Intención: realizar una tarea y contrastar el resultado; lector que necesita un resumen comprobable.
- Estructura: archivo y derechos → legibilidad → petición acotada → referencia manual de datos → comprobación de cifras/condiciones → corrección o vuelta al original → alcance real de las pruebas.
- Fuentes: [pypdf, extracción y OCR](https://pypdf.readthedocs.io/en/stable/user/extract-text.html); [Google, conversación y citas](https://support.google.com/gemininotebook/answer/16179559?hl=es).
- Diferencia: PDF propio de dos páginas y lista de hechos verificables, incluido un dato ausente para detectar inferencias. No se publica una respuesta de IA ficticia.

### T02 — NotebookLM con un PDF: prepara las fuentes y revisa las citas

- Intención: aprender un flujo específico de herramienta, no elegir un «mejor chatbot».
- Estructura: alcance documental/no sesión probada → archivo pequeño → cuaderno → fuente seleccionada → pregunta → cita y contexto → datos ausentes → notas y actualización.
- Fuentes: ayuda oficial de [creación](https://support.google.com/gemininotebook/answer/16206563?hl=es), [fuentes](https://support.google.com/gemininotebook/answer/16215270?hl=es) y [chat/citas](https://support.google.com/gemininotebook/answer/16179559?hl=es).
- Diferencia: preguntas con referencia de control, advertencia sobre nombres actuales del producto y separación explícita entre documentación y prueba de una cuenta. No hay promesas sobre cuotas o funciones verificadas en una sesión.

### T03 — Extraer texto de un PDF con Python antes de usar IA

- Intención: ejecutar un programa local de preprocesado; lector con nociones básicas de terminal.
- Estructura: requisitos/límites → venv → instalación fijada → núcleo del programa → ejecución digital → caso solo imagen → revisión antes de IA → evidencia y límites.
- Fuentes: [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) y [Python venv](https://docs.python.org/3/library/venv.html).
- Diferencia: script, generador, PDF digital e imagen sintéticos incluidos; ejecución local registrada; no usa API de modelos ni claves. No se disfraza la extracción como OCR.

### T04 — NotebookLM no lee bien un PDF: cómo localizar el problema

- Keyword: NotebookLM no lee PDF. Categoría: herramientas. Intención: resolver un fallo, no repetir la guía de creación.
- Estructura: síntoma → prueba de legibilidad → páginas problemáticas → formato/requisitos → fuente actualizada → cuándo separar el archivo u obtener OCR → qué aportar a soporte.
- Fuentes: [importación oficial de fuentes](https://support.google.com/gemininotebook/answer/16215270?hl=es) y [límites de extracción](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
- Diferencia: árbol de diagnóstico con ejemplos. No atribuir un problema al modelo o al plan sin evidencia. Pendiente de pruebas reales de carga antes de presentarse como tutorial probado.

### T05 — Crear tarjetas de repaso con IA sin cambiar tus apuntes

- Keyword: crear tarjetas de estudio con IA. Categoría: tutoriales. Intención: generar y revisar un formato de aprendizaje.
- Estructura: apuntes con permiso → unidades de pregunta/respuesta → petición → revisión contra fuente → casos ambiguos → formato de exportación → rutina de corrección.
- Fuentes: [notebooks y artefactos](https://support.google.com/gemininotebook/answer/16206563?hl=es) y [citas](https://support.google.com/gemininotebook/answer/16179559?hl=es).
- Diferencia: pequeño conjunto original de tarjetas y errores identificables, no una lista de prompts genéricos. No afirmar mejora del aprendizaje sin estudio.

### T06 — NotebookLM vs Gemini: compara las citas con el mismo PDF

- Keyword: NotebookLM vs Gemini PDF. Categoría: herramientas. Intención: elegir por la tarea de lectura documental.
- Estructura: herramienta y plan/versiones → mismas preguntas → registro de respuestas y citas → errores por tipo → tiempos si se miden → límites/coste documentado → recomendación acotada.
- Fuentes: documentación de cada herramienta efectivamente elegida y las [fuentes/citas de Google](https://support.google.com/gemininotebook/answer/16179559?hl=es). La documentación oficial de la segunda herramienta debe añadirse tras seleccionarla; no sustituirla por rankings de terceros.
- Diferencia: comparación sobre el mismo documento y una referencia independiente. **No redactada ni probada**; no se elige ganador por intuición ni se contrata un plan.

### T07 — Preparar un CSV para Anki con Python sin romper los campos

- Keyword: CSV Anki Python. Categoría: programacion. Intención: convertir datos revisados a un formato reutilizable.
- Estructura: esquema de dos campos → codificación → comillas/comas/saltos → DictWriter → lectura de vuelta → validación → límites del importador elegido.
- Fuentes: [Python csv](https://docs.python.org/3/library/csv.html); documentación oficial del importador que se elija, pendiente de selección y verificación.
- Diferencia: prueba de ida y vuelta con caracteres españoles y campos problemáticos. No duplica T05: parte de tarjetas ya revisadas y resuelve su transporte.

### T08 — Probar un chatbot con preguntas cuya respuesta ya conoces

- Keyword: evaluar respuestas chatbot. Categoría: programacion. Intención: preparar una evaluación pequeña, no una clasificación universal de modelos.
- Estructura: conjunto de referencia → hechos y ausencias → criterios → casos JSON → comprobaciones deterministas → revisión semántica → límites de una muestra pequeña.
- Fuentes: [Python unittest](https://docs.python.org/3/library/unittest.html) y documentación de la herramienta evaluada, pendiente de elección. El programa puede validar respuestas guardadas, sin invocar APIs.
- Diferencia: prueba reproducible y fallos explícitos; no confundir coincidencia literal con exactitud semántica ni prometer un benchmark representativo.

### T09 — Agente de IA o flujo automático: elige según la tarea

- Keyword: agente IA vs automatización. Categoría: tutoriales. Intención: decidir una arquitectura con un ejemplo acotado.
- Estructura: tarea → pasos fijos frente a decisiones → ejemplo con herramientas simuladas → aprobación de acciones → fallo y recuperación → checklist de elección.
- Fuentes: documentación de la implementación finalmente elegida; como antecedente, [IBM ALTK-Evolve](https://huggingface.co/blog/ibm-research/altk-evolve-bc) y el artículo público existente sobre distinguir demanda y fiabilidad.
- Diferencia: demostración con permisos y consecuencias explícitas. No repite el análisis comercial ya publicado. Requiere escoger y ejecutar una implementación antes de afirmar resultados.

### T10 — Ollama en Windows: instalación y primera respuesta local

- Keyword: instalar Ollama Windows. Categoría: programacion. Intención: instalar y ejecutar un ejemplo local.
- Estructura: equipo/versiones → requisitos oficiales → instalación → modelo elegido y tamaño → primera petición → comprobación de qué usa red → errores y limpieza.
- Fuentes: [Ollama para Windows](https://docs.ollama.com/windows) y documentación oficial del modelo elegido, pendiente de selección.
- Diferencia: hardware y modelo identificados y captura del procedimiento real. No prometer privacidad absoluta, ausencia de red o velocidad antes de probarlo; baja prioridad si no hay equipo/capacidad.

## Enlaces internos preparados

| Origen | Destino propuesto | Contexto del enlace |
| --- | --- | --- |
| T01 | T02 | Cuando el lector quiere trabajar con fuentes y citas en una herramienta concreta |
| T01 | T03 | Cuando la extracción del PDF resulta dudosa |
| T02 | T01 | Criterios para comprobar lo resumido |
| T02 | T03 | Diagnóstico local de texto extraíble |
| T03 | T01 | Paso posterior a una extracción revisada |
| T03 | T02 | Alternativa para consultar documentos desde un cuaderno |

Las categorías /tutoriales, /herramientas y /programacion ya existen. Los enlaces entre borradores apuntan a archivos locales, con equivalencias de URL en la tabla inicial. Tras aprobar, publicar juntos o activar solo enlaces a destinos ya publicados; nunca enlazar a un borrador privado.

La adaptación local del renderer ya admite enlaces con nodos Vue escapados y destinos validados, sin HTML arbitrario. publication.json contiene los cuerpos con rutas públicas y fuentes estructuradas. Los Markdown conservan enlaces locales para facilitar la revisión. Procedimiento de publicación y reversión en PUBLICACION_Y_ROLLBACK.md; nada desplegado.

## Reglas de calidad y aprobación

- Títulos, resúmenes y ejemplos cumplen intenciones diferentes; revisar futuras consultas de Search Console para confirmar demanda, sin inventar volúmenes.
- No buscar una extensión fija ni rellenar categorías. La utilidad y la trazabilidad importan más que una supuesta densidad de palabras clave.
- Los tres primeros borradores distinguen datos del documento, respuesta de control, salida ejecutada y funciones solo documentadas. NotebookLM no se presenta como una prueba de cuenta.
- No publicar con fechas o autores humanos inventados. Fecha real de publicación al aprobar; autoría asistida por IA y responsable editorial solo cuando se haya confirmado.
- No hay cambios de publicación nocturna, modelo, pausa, reserva ni presupuesto. No se ha llamado a OpenAI para preparar estos textos.
- Estado final de cada texto y comprobaciones: ver COMPROBACIONES.md. Aprobación de publicación y despliegue todavía pendientes.

Referencia editorial: [Google Search Central, contenido útil y fiable](https://developers.google.com/search/docs/fundamentals/creating-helpful-content).
