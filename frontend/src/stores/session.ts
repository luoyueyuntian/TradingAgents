import { computed, reactive } from 'vue';

const TENANT_STORAGE_KEY = 'tradingagents.tenantId';
const API_TOKEN_STORAGE_KEY = 'tradingagents.apiToken';
const CURRENT_MEMBER_STORAGE_KEY = 'tradingagents.currentMemberId';

type SessionState = {
  tenantId: string;
  apiToken: string;
  currentMemberId: string;
};

function readStorage(key: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.localStorage.getItem(key) || '';
}

function writeStorage(key: string, value: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  if (value) {
    window.localStorage.setItem(key, value);
  } else {
    window.localStorage.removeItem(key);
  }
}

const state = reactive<SessionState>({
  tenantId: readStorage(TENANT_STORAGE_KEY),
  apiToken: readStorage(API_TOKEN_STORAGE_KEY),
  currentMemberId: readStorage(CURRENT_MEMBER_STORAGE_KEY),
});

export function useSession() {
  function setTenantId(value: string) {
    state.tenantId = value.trim();
    writeStorage(TENANT_STORAGE_KEY, state.tenantId);
  }

  function setApiToken(value: string) {
    state.apiToken = value.trim();
    writeStorage(API_TOKEN_STORAGE_KEY, state.apiToken);
  }

  function setCurrentMemberId(value: string) {
    state.currentMemberId = value;
    writeStorage(CURRENT_MEMBER_STORAGE_KEY, state.currentMemberId);
  }

  return {
    state,
    apiContext: computed(() => ({
      tenantId: state.tenantId,
      apiToken: state.apiToken,
    })),
    setTenantId,
    setApiToken,
    setCurrentMemberId,
  };
}
