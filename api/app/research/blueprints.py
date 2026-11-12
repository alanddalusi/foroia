"""Initial intent hypotheses, not claimed search volumes or fabricated demand."""
from dataclasses import dataclass
from app.research.examples import EXAMPLES


@dataclass(frozen=True)
class Blueprint:
    key: str
    topic: str
    keyword: str
    intent: str
    kind: str
    section: str
    docs: tuple[str,...]
    example: str | None = None


BLUEPRINTS = (
    Blueprint('json-validation','Validar un JSON generado por IA antes de usarlo en Python','validar json ia python','Detectar JSON mal formado, tipos incorrectos y tamaños excesivos antes de procesar una respuesta.','tutorial','programacion',tuple(EXAMPLES['json_validation']['docs']),'json_validation'),
    Blueprint('json-to-csv','Convertir una respuesta JSON en CSV con Python sin romper columnas','convertir json a csv python ia','Exportar datos estructurados, tratar comas y rechazar celdas peligrosas para hojas de cálculo.','tutorial','programacion',tuple(EXAMPLES['json_csv']['docs']),'json_csv'),
    Blueprint('save-summaries','Cómo guardar respuestas de un asistente de IA en SQLite sin duplicados','guardar respuestas ia sqlite python','Guardar resúmenes de un asistente como datos no confiables, usar consultas parametrizadas y actualizar un registro sin duplicarlo.','tutorial','programacion',tuple(EXAMPLES['sqlite_results']['docs']),'sqlite_results'),
    Blueprint('normalize-text','Cómo comparar respuestas de IA sin errores por espacios y Unicode','comparar respuestas ia unicode python','Comparar variantes textuales de respuestas de un asistente sin confundir normalización con equivalencia de significado ni borrar diferencias relevantes.','tutorial','programacion',tuple(EXAMPLES['text_normalization']['docs']),'text_normalization'),
    Blueprint('pydantic-responses','Validar respuestas estructuradas de IA con Pydantic','validar respuestas ia pydantic','Rechazar campos adicionales y tipos incorrectos mediante un esquema explícito.','tutorial','programacion',tuple(EXAMPLES['pydantic_response']['docs']),'pydantic_response'),
    Blueprint('fastapi-prompts','Cómo validar entradas para una API de IA con FastAPI','fastapi validar peticiones ia','Validar las entradas que recibirá una aplicación de IA: limitar tamaños, detectar campos desconocidos y probar errores HTTP sin llamar al modelo.','tutorial','programacion',tuple(EXAMPLES['fastapi_body']['docs']),'fastapi_body'),
    Blueprint('prompt-context','Separar instrucciones, contexto y datos en un prompt','como estructurar prompt con contexto','Organizar instrucciones y datos de consulta, con criterios para comprobar la respuesta.','guide','tutoriales',('https://developers.openai.com/api/docs/guides/prompt-engineering.md',)),
    Blueprint('gemini-prompts','Diseñar prompts de Gemini con ejemplos y criterios de evaluación','prompts gemini con ejemplos','Usar documentación oficial para diseñar una tarea y evaluar su resultado sin inventar pruebas de la interfaz.','guide','herramientas',('https://ai.google.dev/gemini-api/docs/prompting-strategies',)),
    Blueprint('claude-prompts','Organizar documentos y tareas en instrucciones para Claude','organizar instrucciones claude documentos','Separar documentos, petición y formato de salida según documentación oficial, con limitaciones explícitas.','guide','herramientas',('https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview',)),
    Blueprint('structured-output','Cómo revisar una respuesta JSON de IA: formato, esquema y fuentes','json valido respuesta ia correcta','Revisar una respuesta estructurada de IA separando sintaxis, esquema y apoyo factual; no confundir validación de formato con veracidad.','guide','tutoriales',('https://docs.python.org/3.12/library/json.html','https://developers.openai.com/api/docs/guides/structured-outputs.md')),
    Blueprint('prompt-comparison','Prompts en OpenAI, Gemini y Claude: cómo separar instrucciones y documentos','prompts openai gemini claude diferencias','Aplicar a una misma tarea las pautas documentadas de instrucciones y contexto de cada proveedor, sin comparar rendimientos ni inventar pruebas de producto.','comparison','herramientas',('https://developers.openai.com/api/docs/guides/prompt-engineering.md','https://ai.google.dev/gemini-api/docs/prompting-strategies','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview')),
    # Clúster SEO "integrar APIs de IA en Python" (04/11/2026). Temas ya cubiertos
    # (JSON, Pydantic, FastAPI, prompts, PDF, CSV) no se duplican; URLs comprobadas.
    Blueprint('openai-python-start','Cómo usar la API de OpenAI con Python desde cero','api openai python','Instalar el SDK, configurar la clave y hacer una primera petición siguiendo la guía oficial.','guide','programacion',('https://developers.openai.com/api/docs/quickstart.md',)),
    Blueprint('gemini-python-start','Primera llamada a la API de Gemini con Python','api gemini python','Obtener una clave, instalar el SDK oficial y hacer una primera petición según la guía de inicio.','guide','programacion',('https://aistudio.google.com/docs/get-started',)),
    Blueprint('claude-python-start','Primera llamada a la API de Claude con Python','api claude python','Configurar la clave, instalar el SDK y enviar un primer mensaje según la guía oficial de Anthropic.','guide','programacion',('https://platform.claude.com/docs/en/get-started.md',)),
    Blueprint('api-pricing','Cómo estimar el coste de usar las APIs de OpenAI, Gemini y Claude','precio api openai gemini claude','Leer las tablas oficiales de precios por tokens y estimar un presupuesto, sin rankings inventados y con fecha de consulta.','comparison','herramientas',('https://developers.openai.com/api/docs/pricing.md','https://aistudio.google.com/docs/pricing','https://platform.claude.com/docs/en/about-claude/pricing.md')),
    Blueprint('api-rate-limits','Límites de uso en APIs de IA: qué hacer cuando rechazan peticiones','error 429 api openai','Entender los límites de peticiones y tokens documentados y aplicar reintentos con espera exponencial.','comparison','programacion',('https://developers.openai.com/api/docs/guides/rate-limits.md','https://platform.claude.com/docs/en/api/rate-limits.md')),
    Blueprint('api-errors','Errores comunes de las APIs de IA y cómo interpretarlos','errores api openai claude','Interpretar los códigos de error documentados y decidir cuándo reintentar y cuándo corregir la petición.','comparison','programacion',('https://developers.openai.com/api/docs/guides/error-codes.md','https://platform.claude.com/docs/en/api/errors.md')),
    Blueprint('count-tokens','Contar tokens antes de llamar a un modelo de IA','contar tokens api ia','Estimar tokens de entrada con las herramientas documentadas para controlar coste y límites de contexto.','comparison','programacion',('https://platform.claude.com/docs/en/build-with-claude/token-counting.md','https://aistudio.google.com/docs/tokens')),
    Blueprint('streaming-responses','Recibir respuestas de IA en streaming con Python','streaming api openai python','Mostrar la respuesta mientras se genera usando los eventos documentados y tratar cortes de conexión.','comparison','programacion',('https://developers.openai.com/api/docs/guides/streaming-responses.md','https://platform.claude.com/docs/en/build-with-claude/streaming.md')),
    Blueprint('embeddings-intro','Qué son los embeddings y cómo usarlos para buscar texto','que son embeddings ia','Explicar embeddings y búsqueda por similitud con la documentación oficial, sin prometer precisión.','guide','tutoriales',('https://developers.openai.com/api/docs/guides/embeddings.md','https://aistudio.google.com/docs/embeddings')),
    Blueprint('rag-basics','RAG explicado: responder con tus propios documentos','que es rag ia','Explicar recuperación más generación con la guía oficial, sus límites y cómo citar fuentes.','guide','tutoriales',('https://developers.openai.com/api/docs/guides/retrieval.md',)),
    Blueprint('function-calling','Function calling: cómo conectar un modelo de IA con tus funciones','function calling openai python','Declarar herramientas, validar argumentos y ejecutar solo funciones permitidas según la documentación oficial.','comparison','programacion',('https://developers.openai.com/api/docs/guides/function-calling.md','https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md')),
    Blueprint('prompt-evals','Cómo probar prompts de forma sistemática con evaluaciones','evaluar prompts ia','Definir casos de prueba y criterios de éxito antes de cambiar un prompt, según las guías oficiales.','comparison','tutoriales',('https://developers.openai.com/api/docs/guides/evals.md','https://platform.claude.com/docs/en/test-and-evaluate/develop-tests.md')),
    # Equilibrio de secciones (09/11/2026): temas para quien usa la IA, no solo para programadores.
    # URLs oficiales comprobadas el 09/11/2026.
    Blueprint('reduce-hallucinations','Cómo reducir las alucinaciones de la IA en tus respuestas','como evitar alucinaciones ia','Aplicar las técnicas documentadas (permitir «no lo sé», citas literales, verificación) para obtener respuestas más fiables, sin prometer que desaparecen los errores.','guide','tutoriales',('https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations.md',)),
    Blueprint('image-analysis','Analizar imágenes con IA: formatos, nivel de detalle y coste','analizar imagenes con ia','Saber qué imágenes admite un modelo de visión, cómo elegir el nivel de detalle y cómo se calcula su coste, según la guía oficial.','guide','herramientas',('https://developers.openai.com/api/docs/guides/images-vision.md',)),
    # Herramientas para usuarios (11/11/2026): demanda en España de Gemini y Claude (Ahrefs, nov. 2026).
    # Centros de ayuda oficiales comprobados con el descargador de producción.
    Blueprint('gemini-apps-start','Cómo usar Gemini: primeros pasos con la app de Google','como usar gemini','Explicar qué se puede hacer con la app de Gemini y cómo empezar según el centro de ayuda oficial de Google, sin prometer funciones no documentadas ni disponibilidad por país.','guide','herramientas',('https://support.google.com/gemini/answer/13275745','https://support.google.com/gemini/answer/14903178')),
    Blueprint('claude-start','Cómo empezar a usar Claude: cuenta, conversaciones y archivos','como usar claude','Explicar qué es Claude y cómo empezar a usarlo según el centro de ayuda oficial de Anthropic, sin inventar funciones ni comparar con otros asistentes.','guide','herramientas',('https://support.claude.com/en/articles/8114491-get-started-with-claude','https://support.claude.com/en/articles/9797557-usage-limit-best-practices')),
    Blueprint('claude-pro-plan','Claude Pro: qué incluye el plan de pago de Anthropic','claude pro precio','Explicar qué incluye el plan Pro de Claude según el centro de ayuda oficial, sin inventar precios, límites ni disponibilidad que la página no indique.','guide','herramientas',('https://support.claude.com/en/articles/8325606-what-is-the-pro-plan','https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work')),
    Blueprint('pdf-models','Enviar PDFs a un modelo de IA: qué admite y qué límites tiene','enviar pdf api claude','Conocer formatos, tamaños y límites documentados antes de procesar PDFs largos con un modelo.','guide','herramientas',('https://platform.claude.com/docs/en/build-with-claude/pdf-support.md',)),
)
BY_KEY={b.key:b for b in BLUEPRINTS}

# Concrete applications, never a claim that an external model/API was tested.
AI_APPLICATIONS={
    'json-validation':'Comprobar la estructura de una respuesta de un asistente antes de consumirla en otra aplicación.',
    'json-to-csv':'Exportar respuestas estructuradas de un asistente a una hoja de cálculo sin convertir sus celdas en instrucciones.',
    'save-summaries':'Guardar resúmenes recibidos de un asistente como datos no confiables, sin concatenarlos con SQL.',
    'normalize-text':'Comparar variantes textuales de respuestas de un asistente; distinguir normalización de equivalencia semántica o calidad.',
    'pydantic-responses':'Aplicar un contrato a la respuesta estructurada de un modelo y explicar qué errores factuales no detecta el esquema.',
    'fastapi-prompts':'Validar el texto que recibe una aplicación de IA antes de enviarlo a un modelo; el ejemplo no llama a una API externa.',
    'prompt-context':'Separar la tarea del asistente de los documentos no confiables y definir cómo evaluar la respuesta.',
    'gemini-prompts':'Diseñar una tarea concreta de Gemini con ejemplos y criterios verificables, sin inventar resultados de pruebas.',
    'claude-prompts':'Organizar documentos y una solicitud concreta de Claude con límites explícitos del contexto.',
    'structured-output':'Distinguir formato y veracidad al consumir respuestas estructuradas de un modelo de IA.',
    'prompt-comparison':'Comparar únicamente pautas documentadas de OpenAI, Gemini y Claude para una misma tarea, sin rankings inventados.',
    'openai-python-start':'Hacer la primera petición a la API de OpenAI desde Python con la clave fuera del código.',
    'gemini-python-start':'Hacer la primera petición a Gemini desde Python siguiendo la guía oficial.',
    'claude-python-start':'Enviar el primer mensaje a Claude desde Python siguiendo la guía oficial.',
    'api-pricing':'Estimar el gasto de una aplicación de IA a partir de los precios publicados, citando la fecha de consulta.',
    'api-rate-limits':'Mantener estable una aplicación de IA cuando el proveedor limita peticiones o tokens.',
    'api-errors':'Distinguir errores transitorios de errores de la petición al integrar un modelo de IA.',
    'count-tokens':'Controlar coste y tamaño de contexto antes de enviar texto a un modelo.',
    'streaming-responses':'Mostrar al usuario la respuesta de un modelo mientras se genera.',
    'embeddings-intro':'Buscar textos parecidos con embeddings como base de un buscador o asistente.',
    'rag-basics':'Hacer que un asistente responda con documentos propios y cite de dónde sale cada dato.',
    'function-calling':'Permitir que un modelo solicite funciones de tu programa sin ejecutar nada no autorizado.',
    'prompt-evals':'Comprobar con casos de prueba que un cambio de prompt mejora y no rompe resultados.',
    'pdf-models':'Decidir cómo enviar un PDF a un modelo según los límites documentados.',
    'reduce-hallucinations':'Pedir a un asistente de IA respuestas apoyadas en el texto proporcionado y que admita cuándo no sabe algo.',
    'gemini-apps-start':'Empezar a usar la app de Gemini para escribir, resumir o planificar tareas con la ayuda de la IA de Google.',
    'claude-start':'Abrir una cuenta de Claude y mantener las primeras conversaciones con el asistente, incluido el trabajo con archivos.',
    'claude-pro-plan':'Decidir si el plan de pago de Claude encaja con el uso que se hace del asistente, con lo que documenta Anthropic.',
    'image-analysis':'Enviar una foto o captura a un modelo de visión eligiendo formato y nivel de detalle con el coste previsto.',
}
