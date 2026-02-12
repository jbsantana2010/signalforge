export interface LeadListItem {
  id: string;
  created_at: string;
  name: string | null;
  phone: string | null;
  service: string | null;
  language: string;
  score: number | null;
  tags?: string[];
  priority?: string;
  ai_score?: number;
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
  tags?: string[];
  priority?: string;
  ai_summary?: string;
  ai_score?: number;
  email_status?: string;
  sms_status?: string;
  call_status?: string;
  call_attempts?: number;
  contact_status?: string;
  last_contacted_at?: string;
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

export interface RoutingRule {
  when: { field: string; equals: string };
  then: { tag: string; priority: string };
}

export interface RoutingRules {
  rules: RoutingRule[];
}

export interface FunnelDetail extends FunnelListItem {
  routing_rules: RoutingRules | null;
  auto_email_enabled: boolean;
  auto_sms_enabled: boolean;
  auto_call_enabled: boolean;
  notification_emails: string[] | null;
  webhook_url: string | null;
  rep_phone_number: string | null;
  twilio_from_number: string | null;
  working_hours_start: number;
  working_hours_end: number;
  sequence_enabled: boolean;
  sequence_config: SequenceConfig | null;
}

export interface FunnelUpdateRequest {
  auto_email_enabled?: boolean;
  auto_sms_enabled?: boolean;
  auto_call_enabled?: boolean;
  notification_emails?: string[];
  webhook_url?: string;
  rep_phone_number?: string;
  twilio_from_number?: string;
  working_hours_start?: number;
  working_hours_end?: number;
  routing_rules?: RoutingRules;
  sequence_enabled?: boolean;
  sequence_config?: SequenceConfig;
}

export interface LeadSequenceItem {
  id: string;
  step: number;
  scheduled_at: string;
  sent_at: string | null;
  status: string;
  message: string | null;
}

export interface SequenceStep {
  delay_minutes: number;
  message: string;
}

export interface SequenceConfig {
  steps: SequenceStep[];
}
