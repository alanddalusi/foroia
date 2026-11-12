# Estrategia de enlaces externos y difusión — Foro IA al Día (2026-11-05)

Estado: **solo informe**. No se ha registrado ninguna cuenta, no se ha publicado nada y no se ha tocado producción.

## 1. Comprobación técnica (Bing / sitemap)

Comprobado desde fuera contra `https://foroiaaldia.com`:

| Punto | Resultado |
|---|---|
| `robots.txt` | 200, `Allow: /`, declara `Sitemap: https://foroiaaldia.com/sitemap.xml` ✅ |
| `sitemap.xml` | 200, índice con `sitemap-pages.xml` + `sitemaps/articles/1` (11 artículos) ✅ |
| `llms.txt` | 200 ✅ |
| Meta `msvalidate.01` (Bing) | **No existe** |
| `/BingSiteAuth.xml` | **404** |
| Meta `google-site-verification` | No existe (GSC puede estar verificado por DNS; no se puede ver desde fuera) |
| IndexNow | No implementado |

**Conclusión:** no hay rastro de verificación de Bing por meta ni por archivo. Puede estar verificado por DNS (CNAME) o importado desde Search Console, pero eso solo se confirma entrando en la cuenta. Bing sí puede descubrir el sitemap vía `robots.txt`, pero sin propiedad verificada no hay informes ni envío confirmado.

**Pasos recomendados (requieren tu autorización/acción):**
1. Entrar en https://www.bing.com/webmasters → *Importar desde Google Search Console* (lo más rápido; trae propiedad y sitemaps).
2. Si no, verificar por DNS (registro CNAME) — no requiere tocar el código.
3. En *Sitemaps*, enviar `https://foroiaaldia.com/sitemap.xml` y comprobar estado "Correcto".
4. Opcional (cambio en producción): añadir IndexNow (archivo clave + ping al publicar) para indexación casi inmediata en Bing/Yandex.
5. En GSC: confirmar que el sitemap figura como "Correcto" con 11+ URLs descubiertas.

## 2. Artículos publicados disponibles para compartir

| Slug | Uso ideal |
|---|---|
| `extraer-texto-pdf-python` | Comunidades Python |
| `validar-json-ia-python` | Python / desarrollo con LLM |
| `convertir-json-csv-python-seguro` | Python / datos |
| `fastapi-validar-peticiones-ia` | Backend / FastAPI |
| `separar-instrucciones-contexto-datos-openai-gemini-claude` | IA general, prompts (pieza "pilar") |
| `resumir-pdf-ia-comprobar-citas` | Público general / estudiantes |
| `notebooklm-pdf-fuentes-citas` | Público general / educación |
| `agentic-commerce-anuncios-agentes-servicio-asia` | Medios / análisis |
| `anthropic-s1-ipo-ant-2026-10`, `microsoft-presenta-copilot-harness-foundry` | Actualidad (agregadores) |

## 3. Sitios y comunidades (17)

> La actividad y las normas se basan en conocimiento general; **antes de publicar hay que leer las reglas actuales de cada sitio** (muchos limitan la autopromoción). Regla práctica: aportar en la comunidad antes de compartir y no más de 1 enlace propio por cada ~10 aportaciones.

| # | Sitio | Tipo | ¿Permite compartir? | Coste | Beneficio | Artículo |
|---|---|---|---|---|---|---|
| 1 | Bing Webmaster Tools — bing.com/webmasters | Herramienta | Envío de sitemap | Gratis | Indexación Bing/Copilot/DuckDuckGo | Sitemap completo |
| 2 | Stack Overflow en español — es.stackoverflow.com | Foro Q&A | Solo como fuente dentro de una respuesta útil | Gratis | Tráfico cualificado, enlace nofollow | `validar-json-ia-python`, `extraer-texto-pdf-python` |
| 3 | r/programacion — reddit.com/r/programacion | Comunidad | Sí, con moderación | Gratis | Tráfico | `convertir-json-csv-python-seguro` |
| 4 | r/devsarg — reddit.com/r/devsarg | Comunidad | Limitado (leer reglas) | Gratis | Tráfico, marca en LatAm | `fastapi-validar-peticiones-ia` |
| 5 | r/Python_es / r/programacionES (verificar actividad) | Comunidad | Sí | Gratis | Tráfico de nicho | `extraer-texto-pdf-python` |
| 6 | Python España — es.python.org (Telegram/Slack) | Comunidad | En canales de recursos | Gratis | Marca entre pythonistas | `validar-json-ia-python` |
| 7 | Python Argentina (PyAr) — python.org.ar (lista/Telegram) | Comunidad | Sí, si es útil | Gratis | Marca, LatAm | `convertir-json-csv-python-seguro` |
| 8 | Comunidad Discord de midudev — midu.dev | Comunidad | Canal de recursos/compartir | Gratis | Visibilidad (gran audiencia hispana) | `separar-instrucciones-contexto-datos-…` |
| 9 | Comunidad Discord de MoureDev — mouredev.com | Comunidad | Canal de recursos | Gratis | Visibilidad | `fastapi-validar-peticiones-ia` |
| 10 | DEV Community — dev.to (etiqueta `spanish`) | Blog/plataforma | Sí, republicar con `canonical_url` | Gratis | Enlace + tráfico | `validar-json-ia-python` (versión resumida) |
| 11 | Medium en español | Blog/plataforma | Sí, importar con canonical | Gratis | Visibilidad, enlace | `separar-instrucciones-…` |
| 12 | Menéame — meneame.net | Agregador social | Sí (penaliza autopromoción repetida) | Gratis | Picos de tráfico | `anthropic-s1-ipo-ant-2026-10` |
| 13 | Genbeta — genbeta.com (contacto/tips) | Medio | Sugerencia de tema a redacción | Gratis | Posible enlace editorial fuerte | `notebooklm-pdf-fuentes-citas` |
| 14 | Xataka — xataka.com (contacto) | Medio | Sugerencia a redacción | Gratis | Posible enlace editorial | `agentic-commerce-…` |
| 15 | Hipertextual — hipertextual.com (contacto) | Medio | Sugerencia a redacción | Gratis | Posible enlace editorial | `separar-instrucciones-…` |
| 16 | GitHub — listas "awesome" de IA/Python en español | Directorio | Pull request añadiendo recurso | Gratis | Enlace editorial duradero | `separar-instrucciones-…`, guías Python |
| 17 | LinkedIn (página de Foro IA al Día) | Red social | Sí | Gratis | Marca, señales de entidad | Todos, 2–3/semana |
| 18 | X / Bluesky (perfil del blog) | Red social | Sí | Gratis | Marca, descubrimiento rápido | Noticias |

Evitar: directorios de pago, "granjas" de enlaces, intercambio masivo de enlaces y posts patrocinados sin `rel="sponsored"` (riesgo de penalización).

## 4. Mensajes de presentación (no publicitarios)

**Stack Overflow ES (dentro de una respuesta):**
> […respuesta completa con código…] Si quieres ver el proceso completo con validación de esquema, lo dejé explicado paso a paso aquí: <enlace>.

**Reddit r/programacion / r/Python_es:**
> Me encontré varias veces con CSV rotos al convertir respuestas JSON de modelos de IA (comas, saltos de línea, campos que faltan). Escribí una guía corta de cómo hacerlo con `csv` y validación previa. ¿Cómo lo resolvéis vosotros? <enlace>

**r/devsarg:**
> Pregunta + recurso: ¿validáis con Pydantic lo que mandáis a un LLM desde FastAPI? Dejo lo que usamos nosotros (límites de longitud, campos obligatorios, errores claros). Feedback bienvenido. <enlace>

**Python España / PyAr (Telegram):**
> Hola, comparto una guía en español sobre validar el JSON que devuelve un modelo de IA antes de procesarlo en Python. Si a alguien le sirve o ve algo mejorable, encantado de corregirlo. <enlace>

**Discord midudev / MoureDev (canal de recursos):**
> Recurso en español: cómo separar instrucciones, contexto y datos en los prompts según las guías oficiales de OpenAI, Gemini y Claude. Con enlaces a la documentación original. <enlace>

**DEV.to / Medium (introducción del artículo republicado):**
> Publicado originalmente en Foro IA al Día. Versión resumida; el original incluye ejemplos completos y referencias oficiales.

**Menéame:**
> Título: "Anthropic presenta su S‑1 y prepara su salida a bolsa como «ANT»". Entradilla neutral de 2 frases con el dato principal y la fuente oficial.

**Medios (correo a redacción):**
> Asunto: Idea de tema — cómo comprobar las citas al resumir PDFs con IA
> Hola, escribo desde Foro IA al Día, un blog en español sobre IA práctica. Hemos documentado un método sencillo para verificar las citas que generan NotebookLM y otros asistentes al resumir PDFs. Por si os encaja como tema o fuente: <enlace>. Gracias por vuestro tiempo.

**GitHub awesome (descripción del PR):**
> Añade una guía en español sobre separar instrucciones, contexto y datos en prompts, basada en la documentación oficial de OpenAI, Gemini y Claude.

**LinkedIn:**
> Tres errores frecuentes al extraer texto de PDFs antes de pasarlos a un modelo de IA, y cómo evitarlos con Python. <enlace>

## 5. Plan sugerido (4 semanas)

- **Semana 1:** Bing Webmaster (importar GSC) + comprobar sitemaps; crear perfiles LinkedIn/X; unirse a comunidades y leer reglas (sin publicar enlaces).
- **Semana 2:** 3–5 respuestas útiles en Stack Overflow ES (enlace solo cuando aporte); 1 post en Reddit.
- **Semana 3:** Republicar 1–2 guías en DEV.to/Medium con canonical; 1 PR a una lista awesome.
- **Semana 4:** 2–3 correos a medios con la pieza más original; medir en GSC/Bing las URLs referidas.

KPI: dominios de referencia nuevos, sesiones por referencia (analítica propia), impresiones en GSC/Bing.

## 6. Pendiente de tu autorización

- Registro/verificación en Bing Webmaster Tools (o darme acceso al resultado).
- Implementar IndexNow (cambio en producción).
- Crear cuentas y publicar en cualquiera de los sitios listados.
