'use client';

const TOKEN_KEY = 'leadforge_token';
const ACTIVE_ORG_KEY = 'leadforge_active_org_id';

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
  return localStorage.getItem(ACTIVE_ORG_KEY);
}

export function setActiveOrgId(orgId: string): void {
  localStorage.setItem(ACTIVE_ORG_KEY, orgId);
}
