import { getActiveOrgId } from '@/lib/auth';
import type { OrgListItem } from '@/types/admin';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

/** Build auth headers, injecting X-ORG-ID when an active org is set. */
function authHeaders(token: string): Record<string, string> {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` };
  const orgId = getActiveOrgId();
  if (orgId) h['X-ORG-ID'] = orgId;
  return h;
}

export async function fetchFunnel(slug: string) {
  const res = await fetch(`${API_BASE}/public/funnels/${slug}`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error('Funnel not found');
  return res.json();
}

export async function submitLead(data: {
  funnel_slug: string;
  answers: Record<string, string>;
  language: string;
  source: {
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    referrer?: string;
    landing_url?: string;
  };
  honeypot?: string;
}) {
  const res = await fetch(`${API_BASE}/public/leads/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function loginAdmin(email: string, password: string) {
  const res = await fetch(`${API_BASE}/admin/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error('Login failed');
  return res.json();
}

export async function fetchLeads(token: string, params?: {
  page?: number;
  per_page?: number;
  funnel_id?: string;
  language?: string;
  search?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.per_page) searchParams.set('per_page', String(params.per_page));
  if (params?.funnel_id) searchParams.set('funnel_id', params.funnel_id);
  if (params?.language) searchParams.set('language', params.language);
  if (params?.search) searchParams.set('search', params.search);

  const res = await fetch(`${API_BASE}/admin/leads?${searchParams}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch leads');
  return res.json();
}

export async function fetchLeadDetail(token: string, leadId: string) {
  const res = await fetch(`${API_BASE}/admin/leads/${leadId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch lead');
  return res.json();
}

export async function fetchAdminFunnels(token: string) {
  const res = await fetch(`${API_BASE}/admin/funnels`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch funnels');
  return res.json();
}

export async function fetchFunnelDetail(token: string, funnelId: string) {
  const res = await fetch(`${API_BASE}/admin/funnels/${funnelId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch funnel');
  return res.json();
}

export async function updateFunnelSettings(token: string, funnelId: string, data: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/admin/funnels/${funnelId}`, {
    method: 'PATCH',
    headers: {
      ...authHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update funnel');
  return res.json();
}

export async function fetchLeadSequences(token: string, leadId: string) {
  const res = await fetch(`${API_BASE}/admin/leads/${leadId}/sequences`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch sequences');
  return res.json();
}

export async function fetchLeadEvents(token: string, leadId: string) {
  const res = await fetch(`${API_BASE}/admin/leads/${leadId}/events`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function fetchAgencyOrgs(token: string): Promise<{ orgs: OrgListItem[] }> {
  const res = await fetch(`${API_BASE}/admin/agency/orgs`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch orgs');
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchDashboard(token: string) {
  const res = await fetch(`${API_BASE}/admin/dashboard`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function updateOrgSettings(token: string, data: {
  avg_deal_value?: number; close_rate_percent?: number;
}) {
  const res = await fetch(`${API_BASE}/admin/org/settings`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update org settings');
  return res.json();
}

export async function createAgencyOrg(token: string, data: {
  name: string; slug: string; display_name?: string;
  logo_url?: string; primary_color?: string; support_email?: string;
}) {
  const res = await fetch(`${API_BASE}/admin/agency/orgs`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Failed to create org');
  }
  return res.json();
}

export async function createOrgFunnel(token: string, orgId: string, data: {
  name: string; slug: string; enable_sequences?: boolean;
  enable_email?: boolean; enable_sms?: boolean; enable_call?: boolean;
}) {
  const res = await fetch(`${API_BASE}/admin/agency/orgs/${orgId}/funnels`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Failed to create funnel');
  }
  return res.json();
}
