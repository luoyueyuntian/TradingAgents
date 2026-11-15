import { computed, ref } from 'vue';
import { apiGet, type ApiContext } from '../services/api';

export const unreadCount = ref<number | null>(null);
export const unreadBadge = computed(() => unreadCount.value && unreadCount.value > 0 ? unreadCount.value > 99 ? '99+' : String(unreadCount.value) : '');
let scope = '';
let generation = 0;
export function clearUnread() { scope = ''; generation++; unreadCount.value = null; }
export function activateNotificationScope(tenant: string) {
  if (tenant !== scope) { scope = tenant; generation++; unreadCount.value = null; }
}
export async function refreshUnread(context: ApiContext) {
  const tenant = context.tenantId || '';
  if (!tenant || tenant !== scope) return;
  const requestId = ++generation;
  try {
    const result = await apiGet<{ unread_count: number }>('/api/notifications?unread_only=true&limit=1', context);
    if (requestId !== generation || tenant !== scope) return;
    const count = Number(result.unread_count);
    if (Number.isFinite(count)) unreadCount.value = Math.max(0, Math.floor(count));
  } catch {
    // Preserve the last known value on transient failures; never show a fake zero.
  }
}
