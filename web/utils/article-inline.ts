export type InlinePart = { text: string; href?: string; style?: 'code' | 'strong' | 'cite' }

const SECTION_LABELS: Record<string, string> = { actualidad: 'actualidad', herramientas: 'herramientas', programacion: 'programación', tutoriales: 'tutoriales' }

// Small grammar, no HTML interpretation and no automatic linkification.
export function safeArticleHref(value: string): string | undefined {
  if (/[\s\\\u0000-\u001f\u007f]/.test(value) || /%0[ad]/i.test(value)) return
  if (/^\/(?!\/)[a-zA-Z0-9/_\-.]*$/.test(value) && !value.split('/').includes('..')) return value
  try {
    const url = new URL(value)
    if (url.protocol === 'https:' && !url.username && !url.password) return url.href
  } catch { /* invalid destinations stay plain text */ }
}

export function articleInline(text: string): InlinePart[] {
  const result: InlinePart[] = []
  // Referencias «[1]» / «[2, 1]» del servidor: mismo texto visible, enlazado a «Fuentes originales».
  const pattern = /`([^`\n]+)`|\*\*([^*\n]+)\*\*|\[(\d{1,2}(?:,\s*\d{1,2})*)\](?!\()|\[([^\]\n]+)\]\(([^)\s]+)\)/g
  let offset = 0
  for (const match of text.matchAll(pattern)) {
    const start = match.index!
    if (start > offset) result.push({ text: text.slice(offset, start) })
    if (match[1] !== undefined) result.push({ text: match[1], style: 'code' })
    else if (match[2] !== undefined) result.push({ text: match[2], style: 'strong' })
    else if (match[3] !== undefined) result.push({ text: match[0], href: '#fuentes', style: 'cite' })
    else {
      const href = safeArticleHref(match[5]!)
      // Enlaces de sección generados con el slug («Más guías de programacion»): nombre legible.
      const section = href && /^\/(actualidad|herramientas|programacion|tutoriales)$/.exec(href)?.[1]
      const label = section && match[4]!.startsWith('Más guías de ') ? `Más guías de ${SECTION_LABELS[section]}` : match[4]!
      result.push(href ? { text: label, href } : { text: match[0] })
    }
    offset = start + match[0].length
  }
  if (offset < text.length) result.push({ text: text.slice(offset) })
  return result
}
