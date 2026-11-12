// Small, explicit allowlists: URLs and arbitrary campaign values never enter GA.
const campaigns = new Set(['editorial-90dias', 'guia-pdf'])
const campaignSources: Record<string, string> = { newsletter: 'email', linkedin: 'social', github: 'referral', youtube: 'social' }

export function publicAnalyticsPage(path: string): boolean {
  return !/^\/(editorial|cuenta|moderacion|api)(\/|$)/.test(path)
}

export function analyticsLocation(raw: string): string {
  const url = new URL(raw)
  const page = url.searchParams.get('pagina') || ''
  const pagination = /^[1-9][0-9]{0,2}$/.test(page) && Number(page) > 1 ? `?pagina=${page}` : ''
  return url.origin + url.pathname + pagination
}

export function analyticsEntry(referrer: string, landing: string): Record<string, string> {
  const page = new URL(landing)
  const result: Record<string, string> = { page_referrer: '' }
  try {
    const source = new URL(referrer)
    if (['http:', 'https:'].includes(source.protocol) && !source.username && !source.password && source.origin !== page.origin) {
      result.page_referrer = source.origin + '/' // search terms, paths and fragments discarded
    }
  } catch { /* a missing referrer is a valid direct entry */ }
  const source = page.searchParams.get('utm_source') || ''
  const medium = page.searchParams.get('utm_medium') || ''
  const campaign = page.searchParams.get('utm_campaign') || ''
  if (Object.hasOwn(campaignSources, source) && campaignSources[source] === medium && campaigns.has(campaign)) {
    result.campaign_source = source; result.campaign_medium = medium; result.campaign_name = campaign
  }
  return result
}
