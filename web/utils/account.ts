export function accountHeaders(): Record<string, string> {
  const raw = import.meta.client ? document.cookie.split('; ').find(c => c.startsWith('foroia_csrf='))?.split('=')[1] : undefined
  return raw ? { 'X-CSRF-Token': decodeURIComponent(raw) } : {}
}
export function accountError(error: any): string {
  const detail = error?.data?.detail
  if (Array.isArray(detail)) return 'Revisa los campos: correo válido, contraseña de 12 a 128 caracteres y tamaños permitidos.'
  return typeof detail === 'string' ? detail : 'No se pudo completar la operación. Inténtalo de nuevo.'
}
