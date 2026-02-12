export interface LeadListItem {
  id: string;
  created_at: string;
  name: string | null;
  phone: string | null;
  service: string | null;
  language: string;
  score: number | null;
}

export interface LeadDetail {
  id: string;
  org_id: string;
  funnel_id: string;
  language: string;
  answers_json: Record<string, string>;
  source_json: {
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    referrer?: string;
    landing_url?: string;
  };
  score: number | null;
  is_spam: boolean;
  created_at: string;
}

export interface LeadsResponse {
  leads: LeadListItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface FunnelListItem {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
  created_at: string;
}
