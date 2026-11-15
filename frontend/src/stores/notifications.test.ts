import { beforeEach, describe, expect, it, vi } from 'vitest';
const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock('../services/api', () => ({ apiGet }));
import { activateNotificationScope, clearUnread, refreshUnread, unreadCount, unreadBadge } from './notifications';
describe('notification unread count', () => {
  beforeEach(() => { clearUnread(); apiGet.mockReset(); });
  it.each([[0, ''], [1, '1'], [99, '99'], [100, '99+'], [1234, '99+']])('formats %s as %s', async (count, expected) => {
    activateNotificationScope('a'); apiGet.mockResolvedValue({ unread_count: count });
    await refreshUnread({ tenantId: 'a' }); expect(unreadBadge.value).toBe(expected);
  });
  it('ignores a late response from the previous tenant', async () => {
    let finish!: (value: unknown) => void;
    activateNotificationScope('a'); apiGet.mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
    const old = refreshUnread({ tenantId: 'a' });
    activateNotificationScope('b'); apiGet.mockResolvedValueOnce({ unread_count: 2 });
    await refreshUnread({ tenantId: 'b' }); finish({ unread_count: 999 }); await old;
    expect(unreadCount.value).toBe(2);
  });
  it('preserves the last known count on transient errors', async () => {
    activateNotificationScope('a'); apiGet.mockResolvedValueOnce({ unread_count: 4 }); await refreshUnread({ tenantId: 'a' });
    apiGet.mockRejectedValueOnce(new Error('network')); await refreshUnread({ tenantId: 'a' }); expect(unreadCount.value).toBe(4);
  });
});
