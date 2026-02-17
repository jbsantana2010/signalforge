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
  stage?: string;
  deal_amount?: number;
  stage_updated_at?: string;
  next_action_at?: string;
  next_action_note?: string;
  outcome_reason?: string;
  outcome_note?: string;
  closed_at?: string;
  close_probability?: number;
  days_in_stage?: number;
  is_stale?: boolean;
  stage_leak_warning?: boolean;
  stage_leak_message?: string;
}

export interface LeadIntelligence {
  close_probability: number;
  days_in_stage: number | null;
  is_stale: boolean;
  stage_leak_warning: boolean;
  stage_leak_message: string | null;
}

export interface OrgInsights {
  summary: string;
  highlights: string[];
  mode: string;
}

export interface StageHistoryItem {
  id: string;
  from_stage: string | null;
  to_stage: string;
  changed_by_user_id: string | null;
  reason: string | null;
  note: string | null;
  created_at: string;
}

export interface LeadStageUpdateResponse {
  lead: LeadDetail;
  history_event_id: string | null;
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

export interface DashboardMetrics {
  total_leads: number;
  leads_last_7_days: number;
  avg_response_seconds: number | null;
  contacted_percent: number;
  ai_hot_count: number;
  ai_warm_count: number;
  ai_cold_count: number;
  call_connect_rate: number;
  estimated_revenue: number;
  avg_deal_value: number;
  close_rate_percent: number;
  actual_revenue: number;
  actual_close_rate: number;
  won_deals: number;
  lost_deals: number;
  pipeline_value: number;
}

export interface PipelineMetrics {
  totals: {
    leads: number;
    won: number;
    lost: number;
    conversion_rate: number;
  };
  stages: {
    new: number;
    contacted: number;
    qualified: number;
    proposal: number;
    won: number;
    lost: number;
  };
  pipeline: {
    total_value: number;
    won_value: number;
    avg_deal_value: number;
  };
  velocity: {
    avg_days_to_close: number | null;
    avg_days_in_stage: {
      new: number | null;
      contacted: number | null;
      qualified: number | null;
      proposal: number | null;
    };
  };
  actionability: {
    overdue_next_actions: number;
    stale_leads: number;
  };
}

export interface OrgListItem {
  id: string;
  name: string;
  slug: string;
  display_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  support_email: string | null;
  created_at: string | null;
}
