// Normalize only generated <link> tags in the document head. Keep every URL and hint.
export function normalizePrefetchHead(head: string): string {
  return head.replace(/<link\b(?:"[^"]*"|'[^']*'|[^'">])*>/gi, (tag) => {
    const rel = tag.match(/\srel\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i)
    const tokens = (rel?.[1] ?? rel?.[2] ?? rel?.[3] ?? '').toLowerCase().split(/\s+/)
    if (!tokens.includes('prefetch') || tokens.includes('preload') || tokens.includes('modulepreload')) return tag
    return tag.replace(/\s+as\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  })
}
