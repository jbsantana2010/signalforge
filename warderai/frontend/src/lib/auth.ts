'use client';

const TOKEN_KEY = 'leadforge_token';
const ACTIVE_ORG_KEY = 'leadforge_active_org_id';
const ORG_RESET_KEY = 'leadforge_org_was_reset';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidUuid(value: string): boolean {
  return UUID_RE.test(value);
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ACTIVE_ORG_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function getActiveOrgId(): string | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(ACTIVE_ORG_KEY);
  if (!raw || raw === 'null' || raw === 'undefined' || !isValidUuid(raw)) {
    return null;
  }
  return raw;
}

export function setActiveOrgId(orgId: string): void {
  localStorage.setItem(ACTIVE_ORG_KEY, orgId);
}

export function clearActiveOrgId(): void {
  localStorage.removeItem(ACTIVE_ORG_KEY);
}

export function markOrgWasReset(): void {
  localStorage.setItem(ORG_RESET_KEY, '1');
}

export function consumeOrgWasReset(): boolean {
  if (typeof window === 'undefined') return false;
  const val = localStorage.getItem(ORG_RESET_KEY);
  if (val) {
    localStorage.removeItem(ORG_RESET_KEY);
    return true;
  }
  return false;
}
