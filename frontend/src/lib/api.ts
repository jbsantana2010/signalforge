const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

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
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch leads');
  return res.json();
}

export async function fetchLeadDetail(token: string, leadId: string) {
  const res = await fetch(`${API_BASE}/admin/leads/${leadId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch lead');
  return res.json();
}

export async function fetchAdminFunnels(token: string) {
  const res = await fetch(`${API_BASE}/admin/funnels`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch funnels');
  return res.json();
}

export async function fetchFunnelDetail(token: string, funnelId: string) {
  const res = await fetch(`${API_BASE}/admin/funnels/${funnelId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch funnel');
  return res.json();
}

export async function updateFunnelSettings(token: string, funnelId: string, data: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/admin/funnels/${funnelId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update funnel');
  return res.json();
}

export async function fetchLeadSequences(token: string, leadId: string) {
  const res = await fetch(`${API_BASE}/admin/leads/${leadId}/sequences`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch sequences');
  return res.json();
}
