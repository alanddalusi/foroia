export interface Account { id: number; display_name: string; role: string; verified: boolean }
export function useAccount() {
  const user = useState<Account | null>('account', () => null)
  async function refreshAccount() {
    try { user.value = await $fetch<Account>('/api/community/auth/me') } catch { user.value = null }
  }
  return { user, refreshAccount }
}
