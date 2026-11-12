// Nombre legible de una fuente. Solo presentación: el dato guardado y el JSON-LD (citation = URLs) no cambian.
// Títulos de fuentes guardados con restos del documento («[1] --- title: X url: …», «# Rate limits > …»).
// Solo se limpia lo que se muestra; el dato y el JSON-LD (citation = URLs) no cambian.
export function sourceLabel(raw: string, url: string): string {
  const number = /^\[(\d+)\]\s*/.exec(raw)?.[1]
  let text = raw.replace(/^\[\d+\]\s*/, '')
  const front = /^-{3}\s*title:\s*(.+?)\s+(?:url|description):/i.exec(text)
  if (front) text = front[1]!
  text = text.replace(/^#+\s*/, '').split(/\s+>\s+|\s+¶/)[0]!.trim()
  // Centros de ayuda: el «título» guardado es la primera frase del documento. Nombre legible desde la URL.
  const help = helpCentreLabel(url, text)
  if (help && (text.length > 70 || /^(This|When|To|You|If|Learn|Use|Upload)\b/.test(text))) text = help
  // Documentación oficial: «Pricing» o restos como «> ## AI Agent Context» no dicen de quién es la fuente.
  const org = DOC_ORGS[new URL(url).hostname]
  if (org) {
    const page = urlPage(url)
    if (!/^[\p{L}\d]/u.test(text) || text.split(/\s+/).length <= 2) text = page ? `${org}: ${page}` : org
  }
  if (text.length < 3) text = new URL(url).hostname
  return number ? `[${number}] ${text}` : text
}
const DOC_ORGS: Record<string, string> = {
  'developers.openai.com': 'Documentación de OpenAI', 'platform.claude.com': 'Documentación de Anthropic',
  'docs.anthropic.com': 'Documentación de Anthropic', 'aistudio.google.com': 'Documentación de Google AI',
  'ai.google.dev': 'Documentación de Google AI'
}
function urlPage(url: string): string {
  const slug = (new URL(url).pathname.split('/').filter(Boolean).pop() || '').replace(/\.md$/, '').replace(/^\d+-?/, '').replace(/-/g, ' ').trim()
  return slug && !/^\d+$/.test(slug) ? slug.charAt(0).toUpperCase() + slug.slice(1) : ''
}
function helpCentreLabel(url: string, text: string): string | undefined {
  const u = new URL(url)
  const page = urlPage(url)
  if (u.hostname === 'support.claude.com') return `Centro de ayuda de Claude${page ? `: ${page}` : ''}`
  if (u.hostname === 'support.google.com') {
    const product = u.pathname.split('/')[1] || ''
    // Las URLs de Google son numéricas: el título real es el texto antes de la primera frase («… You can …»).
    const heading = text.split(/\s(?=You |This |If |To )/)[0]!.trim()
    const name = page || (heading.length >= 5 && heading.length <= 70 ? heading : '')
    return `Ayuda de Google${product ? ` (${product.charAt(0).toUpperCase() + product.slice(1)})` : ''}${name ? `: ${name}` : ''}`
  }
}
