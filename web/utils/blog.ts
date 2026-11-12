export const SECTIONS = [
  { slug: 'actualidad', name: 'Actualidad' },
  { slug: 'herramientas', name: 'Herramientas' },
  { slug: 'programacion', name: 'Programación' },
  { slug: 'tutoriales', name: 'Tutoriales' }
] as const

export const sectionName = (slug: string) => SECTIONS.find(s => s.slug === slug)?.name ?? slug

// SEO: Google muestra ~60 caracteres de título y ~155 de descripción.
const SITE = 'Foro IA al Día'
export function seoTitle(title: string): string {
  const full = `${title} | ${SITE}`
  return full.length <= 60 ? full : title
}
export function seoDescription(text: string, max = 155): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  if (clean.length <= max) return clean
  const cut = clean.slice(0, max - 1)
  return `${cut.slice(0, Math.max(cut.lastIndexOf(' '), 80)).replace(/[\s,;:.-]+$/, '')}…`
}

// Ficha de autoría editorial. Mientras no haya una persona real que firme,
// se presenta como equipo y no como persona (sin identidades inventadas).
export const AUTHOR = {
  slug: 'redaccion',
  name: 'Redacción de Foro IA al Día',
  path: '/autor/redaccion'
}

// Textos de introducción de cada sección (contenido indexable propio).
export const SECTION_INTROS: Record<string, { title: string, paragraphs: string[], start: { label: string, href: string }[] }> = {
  actualidad: {
    title: 'Noticias de inteligencia artificial en español',
    paragraphs: [
      'Aquí reunimos los anuncios relevantes de OpenAI, Google, Anthropic, Microsoft, NVIDIA y otras organizaciones del sector, explicados en español y siempre enlazados a su fuente original.',
      'Cada noticia distingue qué ha comunicado la empresa, qué está confirmado y qué queda pendiente de comprobar. No publicamos rumores ni comparativas sin una fuente independiente.'
    ],
    start: [{ label: 'Cómo seleccionamos y verificamos las noticias', href: '/informacion/criterio-editorial' }]
  },
  herramientas: {
    title: 'Herramientas de IA: ChatGPT, Gemini, Claude y más',
    paragraphs: [
      'Guías para sacar partido a los asistentes y servicios de IA más usados: cómo organizar instrucciones, preparar documentos y revisar lo que responde el modelo.',
      'Nos basamos en la documentación oficial de cada proveedor e indicamos con claridad qué está documentado y qué es una recomendación editorial.'
    ],
    start: [{ label: 'Separar instrucciones, contexto y datos en OpenAI, Gemini y Claude', href: '/articulos/separar-instrucciones-contexto-datos-openai-gemini-claude' }]
  },
  programacion: {
    title: 'Programar con IA en Python',
    paragraphs: [
      'Tutoriales para integrar modelos de IA en tus programas con Python: validar respuestas JSON, crear APIs con FastAPI y Pydantic, exportar datos y procesar documentos.',
      'Los ejemplos de código marcados como reproducibles se han ejecutado en un entorno aislado antes de publicarse, y cada guía enlaza la documentación oficial en la que se apoya.'
    ],
    start: [
      { label: 'Validar un JSON generado por IA en Python', href: '/articulos/validar-json-ia-python' },
      { label: 'Validar peticiones de una API de IA con FastAPI', href: '/articulos/fastapi-validar-peticiones-ia' },
      { label: 'Extraer texto de un PDF con Python', href: '/articulos/extraer-texto-pdf-python' }
    ]
  },
  tutoriales: {
    title: 'Tutoriales de IA paso a paso',
    paragraphs: [
      'Explicaciones prácticas para aprender a trabajar con inteligencia artificial sin conocimientos previos: resumir documentos, comprobar citas, escribir mejores instrucciones y revisar las respuestas de un asistente antes de fiarte de ellas.',
      'Cada tutorial indica qué se ha comprobado, qué límites tiene la herramienta y qué fuentes oficiales consultar si quieres profundizar o adaptarlo a tu caso.'
    ],
    start: [
      { label: 'Cómo resumir un PDF con IA y comprobar sus citas', href: '/articulos/resumir-pdf-ia-comprobar-citas' },
      { label: 'NotebookLM con un PDF: fuentes y citas', href: '/articulos/notebooklm-pdf-fuentes-citas' }
    ]
  }
}

// Editorial brand byline; the editorial policy explains the use of automation.
export function articleAuthor(name: string): string {
  return ['Redacción de Foro IA al Día · con asistencia de IA', 'Redacción automatizada · IA'].includes(name)
    ? 'Redacción de Foro IA al Día' : name
}

// Zona horaria fija para que SSR e hidratación produzcan el mismo texto.
export const formatDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Madrid' }) : ''

// HTML allows at most three fractional second digits. Presentation only; never writes dates.
export function htmlDateTime(iso?: string | null): string | undefined {
  if (!iso) return undefined
  const date = new Date(iso)
  return Number.isFinite(date.getTime()) ? date.toISOString() : undefined
}

// JSON-LD seguro dentro de <script>: impide cerrar la etiqueta con contenido del usuario.
export const jsonLd = (data: unknown) => JSON.stringify(data).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')

export const languageName = (code: string) => ({ en: 'en inglés', es: 'en español', fr: 'en francés', de: 'en alemán' } as Record<string, string>)[code] ?? code

export interface ArticleMedia {
  cover?: { src: string; variants: Record<string, string>; width: number; height: number; alt: string; caption: string; credit: string } | null
  charts?: { title: string; unit: string; points: { label: string; value: number }[]; source_url: string }[]
  videos?: { id: string; title: string; source_url: string; provenance: string }[]
}
export interface ArticleSummary { slug: string, title: string, summary: string, section: string, author_name: string, published_at: string | null, updated_at: string, media?: ArticleMedia }
export interface Source { title: string, url: string, language: string }
export interface Article extends ArticleSummary { body: string, sources: Source[], reviewed_at: string | null, comments_enabled: boolean }
export interface ArticleDetail extends Article { related: ArticleSummary[] }
export interface ArticlePage { items: ArticleSummary[], page: number, has_next: boolean }

export interface EditorialArticle {
  id?: number, slug: string, title: string, summary: string, body: string, section: string,
  author_name: string, sources: Source[], status?: string, published_at?: string | null, updated_at?: string, reviewed_by?: string | null, comments_enabled?: boolean
}
export const STATUS_LABELS: Record<string, string> = { draft: 'Borrador', review: 'En revisión', published: 'Publicado', archived: 'Archivado' }
