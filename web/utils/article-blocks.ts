export type ArticleBlock = { type: 'h2' | 'h3' | 'p' | 'code' | 'ul' | 'table', text?: string, items?: string[], lang?: string, id?: string, headers?: string[], rows?: string[][] }
export function articleBlocks(body: string): ArticleBlock[] {
  const out: ArticleBlock[] = [], lines = body.replace(/\r\n?/g, '\n').split('\n')
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(s => s.trim()).slice(0, 20)
  let i = 0, heading = 0
  while (i < lines.length) {
    const line = lines[i]!
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim().slice(0, 20), code: string[] = []; i++
      while (i < lines.length && !lines[i]!.startsWith('```')) code.push(lines[i++]!)
      i++; out.push({ type: 'code', text: code.join('\n'), lang })
    } else if (/^###? /.test(line)) {
      out.push({ type: line.startsWith('### ') ? 'h3' : 'h2', text: line.replace(/^###? /, ''), id: `apartado-${++heading}` }); i++
    } else if (line.startsWith('- ')) {
      const items: string[] = []; while (i < lines.length && lines[i]!.startsWith('- ')) items.push(lines[i++]!.slice(2))
      out.push({ type: 'ul', items })
    } else if (line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1] || '') && cells(lines[i + 1]!).every(s => /^:?-{3,}:?$/.test(s))) {
      const headers = cells(line), rows: string[][] = []; i += 2
      while (i < lines.length && lines[i]!.trim() && lines[i]!.includes('|') && rows.length < 100) rows.push(cells(lines[i++]!))
      out.push({ type: 'table', headers, rows })
    } else if (!line.trim()) i++
    else {
      const para: string[] = []
      while (i < lines.length && lines[i]!.trim() && !/^(```|## |### |- )/.test(lines[i]!)) {
        if (para.length && lines[i]!.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1] || '')) break
        para.push(lines[i++]!)
      }
      out.push({ type: 'p', text: para.join(' ') })
    }
  }
  return out
}
// Notas finales que añade el servidor (transparencia). Se muestran en un recuadro aparte.
const NOTE = /^(Redacción y revisión automatizadas con IA|No se ha probado la interfaz|La documentación se ha contrastado|El contenido se ha contrastado|El ejemplo de código se ha ejecutado)/
export function splitTransparencyNotes(blocks: ArticleBlock[]): { blocks: ArticleBlock[], notes: string[] } {
  let end = blocks.length
  while (end > 0 && blocks[end - 1]!.type === 'p' && NOTE.test(blocks[end - 1]!.text || '')) end--
  const hasCode = blocks.some(b => b.type === 'code')
  const notes = blocks.slice(end).map((b) => {
    const text = b.text || ''
    // Frase antigua que citaba un «ejemplo aislado» aunque no lo hubiera: se muestra con exactitud.
    if (text.startsWith('No se ha probado la interfaz ni un servicio externo; solo el ejemplo aislado')) {
      return hasCode ? 'El ejemplo de código se ha ejecutado en un entorno aislado; no se ha probado la interfaz ni ningún servicio externo.'
        : 'No se ha probado la interfaz ni ningún servicio externo.'
    }
    if (text.startsWith('Redacción y revisión automatizadas con IA')) return 'Redactado y revisado de forma automatizada con IA a partir de las fuentes citadas, sin revisión humana previa.'
    return text
  })
  return { blocks: blocks.slice(0, end), notes }
}
export function articleSpeech(body: string): string {
  return articleBlocks(body).filter(b => !['code', 'table'].includes(b.type)).map(b => b.text || b.items?.join('. ') || '').join('. ').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\[[\d, ]+\]/g, '').replace(/[`*#]/g, '')
}
