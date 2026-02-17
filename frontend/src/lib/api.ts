import { getActiveOrgId, clearActiveOrgId, markOrgWasReset, isValidUuid } from '@/lib/auth';
import type { OrgListItem } from '@/types/admin';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

/** Build auth headers, injecting X-ORG-ID only when a valid UUID is set. */
function authHeaders(token: string): Record<string, string> {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` };
  const orgId = getActiveOrgId();
  if (orgId && isValidUuid(orgId)) h['X-ORG-ID'] = orgId;
  return h;
}

/** Fetch with 403 auto-recovery: if a 403 occurs and X-ORG-ID was sent,
 *  clear the stale org, mark it for the UI, and retry once without it. */
async function authFetch(url: string, init: RequestInit & { headers: Record<string, string> }): Promise<Response> {
  const hadOrgHeader = 'X-ORG-ID' in init.headers;
  const res = await fetch(url, init);
  if (res.status === 403 && hadOrgHeader) {
    clearActiveOrgId();
    markOrgWasReset();
    const retryHeaders = { ...init.headers };
    delete retryHeaders['X-ORG-ID'];
    return fetch(url, { ...init, headers: retryHeaders });
  }
  return res;
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

  const res = await authFetch(`${API_BASE}/admin/leads?${searchParams}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch leads');
  return res.json();
}

export async function fetchLeadDetail(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch lead');
  return res.json();
}

export async function fetchAdminFunnels(token: string) {
  const res = await authFetch(`${API_BASE}/admin/funnels`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch funnels');
  return res.json();
}

export async function fetchFunnelDetail(token: string, funnelId: string) {
  const res = await authFetch(`${API_BASE}/admin/funnels/${funnelId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch funnel');
  return res.json();
}

export async function updateFunnelSettings(token: string, funnelId: string, data: Record<string, unknown>) {
  const res = await authFetch(`${API_BASE}/admin/funnels/${funnelId}`, {
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

export async function fetchLeadIntelligence(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/intelligence`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch intelligence');
  return res.json();
}

export async function fetchDashboardInsights(token: string) {
  const res = await authFetch(`${API_BASE}/admin/dashboard/insights`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch insights');
  return res.json();
}

export async function updateLeadStage(token: string, leadId: string, data: {
  stage: string; deal_amount?: number;
  next_action_at?: string; next_action_note?: string; reason?: string;
  outcome_reason?: string; outcome_note?: string;
}) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/stage`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Failed to update lead stage');
  }
  return res.json();
}

export async function fetchStageHistory(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/stage-history`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch stage history');
  return res.json();
}

export async function generateLeadAssist(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/assist`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to generate assist');
  return res.json();
}

export async function fetchLeadSequences(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/sequences`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch sequences');
  return res.json();
}

export async function fetchLeadEvents(token: string, leadId: string) {
  const res = await authFetch(`${API_BASE}/admin/leads/${leadId}/events`, {
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
  const res = await authFetch(`${API_BASE}/admin/dashboard`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchPipelineMetrics(token: string) {
  const res = await authFetch(`${API_BASE}/admin/dashboard/metrics`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch pipeline metrics');
  return res.json();
}

export async function updateOrgSettings(token: string, data: {
  avg_deal_value?: number; close_rate_percent?: number;
}) {
  const res = await authFetch(`${API_BASE}/admin/org/settings`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update org settings');
  return res.json();
}

export async function fetchIndustries(token: string) {
  const res = await authFetch(`${API_BASE}/admin/industries`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch industries');
  return res.json();
}

export async function fetchIndustryTemplate(token: string, slug: string) {
  const res = await authFetch(`${API_BASE}/admin/industries/${encodeURIComponent(slug)}/template`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch industry template');
  return res.json();
}

export async function fetchCampaigns(token: string) {
  const res = await authFetch(`${API_BASE}/admin/campaigns`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch campaigns');
  return res.json();
}

export async function createCampaign(token: string, data: {
  campaign_name: string; source: string; utm_campaign: string; ad_spend?: number;
}) {
  const res = await authFetch(`${API_BASE}/admin/campaigns`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Failed to create campaign');
  }
  return res.json();
}

export async function updateCampaignSpend(token: string, campaignId: string, ad_spend: number) {
  const res = await authFetch(`${API_BASE}/admin/campaigns/${campaignId}`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ ad_spend }),
  });
  if (!res.ok) throw new Error('Failed to update campaign');
  return res.json();
}

export async function generateAdStrategy(token: string, data: {
  goal: string; monthly_budget: number; notes?: string;
}) {
  const res = await authFetch(`${API_BASE}/admin/ai/ad-strategy`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to generate strategy');
  return res.json();
}

export async function createAgencyOrg(token: string, data: {
  name: string; slug: string; display_name?: string;
  logo_url?: string; primary_color?: string; support_email?: string;
  industry_slug?: string;
}) {
  const res = await authFetch(`${API_BASE}/admin/agency/orgs`, {
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
  const res = await authFetch(`${API_BASE}/admin/agency/orgs/${orgId}/funnels`, {
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
