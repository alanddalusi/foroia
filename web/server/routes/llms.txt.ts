// Resumen para asistentes de IA (propuesta llms.txt). Solo contenido público.
export default defineEventHandler(async (event) => {
  setHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=3600')
  const site = useRuntimeConfig(event).public.siteUrl
  const base = useRuntimeConfig(event).apiBase
  let articles: { slug: string; title?: string }[] = []
  try {
    const page = await $fetch<{ items: { slug: string; title: string; summary: string }[] }>(`${base}/articles`, { query: { limit: 50 } })
    articles = page.items
  } catch { articles = [] }
  const lines = [
    '# Foro IA al Día',
    '',
    '> Inteligencia artificial explicada en español: noticias contrastadas con su fuente original, guías prácticas y tutoriales de programación con Python.',
    '',
    `Criterio editorial: ${site}/informacion/criterio-editorial`,
    `Autoría y método: ${site}/autor/redaccion`,
    '',
    '## Secciones',
    `- [Actualidad](${site}/actualidad): noticias de IA con fuente original`,
    `- [Programación](${site}/programacion): integrar IA en Python`,
    `- [Herramientas](${site}/herramientas): ChatGPT, Gemini, Claude`,
    `- [Tutoriales](${site}/tutoriales): guías paso a paso`,
    '',
    '## Artículos',
    ...articles.map(a => `- [${(a.title || a.slug).replace(/[[\]]/g, '')}](${site}/articulos/${a.slug})`)
  ]
  return lines.join('\n') + '\n'
})
