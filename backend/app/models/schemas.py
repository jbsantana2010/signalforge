from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Funnel Schema (describes the schema_json structure) ---


class FunnelFieldOption(BaseModel):
    value: str
    label: dict[str, str]


class FunnelField(BaseModel):
    key: str
    type: str
    required: bool = False
    label: dict[str, str]
    options: list[FunnelFieldOption] | None = None


class FunnelStep(BaseModel):
    id: str
    title: dict[str, str]
    fields: list[FunnelField]


class FunnelSchema(BaseModel):
    slug: str
    languages: list[str] = ["en"]
    steps: list[FunnelStep]


# --- Public Responses ---


class FunnelPublicResponse(BaseModel):
    slug: str
    name: str
    schema_json: FunnelSchema
    branding: dict
    languages: list[str]


# --- Lead Submission ---


class LeadSubmitRequest(BaseModel):
    funnel_slug: str
    answers: dict
    language: str = "en"
    source: dict = Field(default_factory=dict)
    honeypot: Optional[str] = None


class LeadSubmitResponse(BaseModel):
    success: bool
    message: str


# --- Admin: Leads ---


class LeadListItem(BaseModel):
    id: UUID
    created_at: datetime
    name: Optional[str] = None
    phone: Optional[str] = None
    service: Optional[str] = None
    language: str
    score: Optional[float] = None
    tags: list[str] | None = None
    priority: str | None = None
    ai_score: int | None = None


class LeadDetail(BaseModel):
    id: UUID
    org_id: UUID
    funnel_id: UUID
    language: str
    answers_json: dict
    source_json: dict
    score: Optional[float] = None
    is_spam: bool
    created_at: datetime
    tags: list[str] | None = None
    priority: str | None = None
    ai_summary: str | None = None
    ai_score: int | None = None
    email_status: str | None = None
    sms_status: str | None = None
    call_status: str | None = None
    call_attempts: int = 0
    contact_status: str | None = None
    last_contacted_at: datetime | None = None
    stage: str = "new"
    deal_amount: Optional[float] = None
    stage_updated_at: datetime | None = None
    next_action_at: datetime | None = None
    next_action_note: str | None = None
    outcome_reason: str | None = None
    outcome_note: str | None = None
    closed_at: datetime | None = None
    close_probability: int | None = None
    days_in_stage: float | None = None
    is_stale: bool | None = None
    stage_leak_warning: bool | None = None
    stage_leak_message: str | None = None


class LeadStageUpdateRequest(BaseModel):
    stage: str
    deal_amount: Optional[float] = None
    next_action_at: datetime | None = None
    next_action_note: str | None = None
    reason: str | None = None
    outcome_reason: str | None = None
    outcome_note: str | None = None


class StageHistoryItem(BaseModel):
    id: UUID
    from_stage: str | None = None
    to_stage: str
    changed_by_user_id: UUID | None = None
    reason: str | None = None
    note: str | None = None
    created_at: datetime


class LeadStageUpdateResponse(BaseModel):
    lead: LeadDetail
    history_event_id: UUID | None = None


# --- Admin: Auth ---


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Admin: Funnels ---


class FunnelListItem(BaseModel):
    id: UUID
    slug: str
    name: str
    languages: list[str]
    is_active: bool
    created_at: datetime


# --- Routing Rules ---


class RoutingRuleCondition(BaseModel):
    field: str
    equals: str


class RoutingRuleAction(BaseModel):
    tag: str | None = None
    priority: str | None = None


class RoutingRule(BaseModel):
    when: RoutingRuleCondition
    then: RoutingRuleAction


class RoutingRulesConfig(BaseModel):
    rules: list[RoutingRule] = []


# --- Admin: Funnel Detail & Update ---


class FunnelDetail(BaseModel):
    id: UUID
    org_id: UUID
    slug: str
    name: str
    schema_json: dict
    languages: list[str]
    is_active: bool
    created_at: datetime
    routing_rules: dict | None = None
    auto_email_enabled: bool = False
    auto_sms_enabled: bool = False
    auto_call_enabled: bool = False
    notification_emails: list[str] | None = None
    webhook_url: str | None = None
    rep_phone_number: str | None = None
    twilio_from_number: str | None = None
    working_hours_start: int = 9
    working_hours_end: int = 19
    sequence_enabled: bool = False
    sequence_config: dict | None = None


class FunnelUpdateRequest(BaseModel):
    routing_rules: dict | None = None
    auto_email_enabled: bool | None = None
    auto_sms_enabled: bool | None = None
    auto_call_enabled: bool | None = None
    notification_emails: list[str] | None = None
    webhook_url: str | None = None
    rep_phone_number: str | None = None
    twilio_from_number: str | None = None
    working_hours_start: int | None = None
    working_hours_end: int | None = None
    sequence_enabled: bool | None = None
    sequence_config: dict | None = None


# --- Paginated response ---


class LeadListResponse(BaseModel):
    leads: list[LeadListItem]
    total: int
    page: int
    per_page: int


# --- Admin: Agency ---


class AgencyOrgListItem(BaseModel):
    id: UUID
    name: str
    slug: str
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    support_email: str | None = None
    created_at: datetime | None = None


class AgencyOrgsResponse(BaseModel):
    orgs: list[AgencyOrgListItem]


class LeadSequenceItem(BaseModel):
    id: UUID
    step: int
    scheduled_at: datetime
    sent_at: datetime | None = None
    status: str
    message: str | None = None


# --- Admin: Agency Onboarding (Sprint 4C) ---


class CreateOrgRequest(BaseModel):
    name: str
    slug: str
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    support_email: str | None = None
    industry_slug: str | None = None


class CreateOrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    support_email: str | None = None


class CreateFunnelRequest(BaseModel):
    name: str
    slug: str
    schema_json: dict | None = None
    language_default: str = "en"
    enable_sequences: bool = True
    enable_email: bool = False
    enable_sms: bool = False
    enable_call: bool = False


class CreateFunnelResponse(BaseModel):
    id: UUID
    slug: str
    org_id: UUID


class OrgMetricsUpdateRequest(BaseModel):
    avg_deal_value: float | None = None
    close_rate_percent: float | None = None


# --- Admin: Industries ---


class IndustryListItem(BaseModel):
    slug: str
    name: str
    description: str | None = None


class IndustryTemplateDetail(BaseModel):
    slug: str
    name: str
    description: str | None = None
    default_funnel_json: dict
    default_sequence_json: dict
    default_scoring_json: dict
    default_avg_deal_value: float
    default_close_rate_percent: float


# --- Admin: Pipeline Metrics (Sprint 7) ---


class PipelineTotals(BaseModel):
    leads: int = 0
    won: int = 0
    lost: int = 0
    conversion_rate: float = 0.0


class PipelineStages(BaseModel):
    new: int = 0
    contacted: int = 0
    qualified: int = 0
    proposal: int = 0
    won: int = 0
    lost: int = 0


class PipelineValues(BaseModel):
    total_value: float = 0.0
    won_value: float = 0.0
    avg_deal_value: float = 0.0


class PipelineAvgDaysInStage(BaseModel):
    new: float | None = None
    contacted: float | None = None
    qualified: float | None = None
    proposal: float | None = None


class PipelineVelocity(BaseModel):
    avg_days_to_close: float | None = None
    avg_days_in_stage: PipelineAvgDaysInStage = PipelineAvgDaysInStage()


class PipelineActionability(BaseModel):
    overdue_next_actions: int = 0
    stale_leads: int = 0


class PipelineMetricsResponse(BaseModel):
    totals: PipelineTotals = PipelineTotals()
    stages: PipelineStages = PipelineStages()
    pipeline: PipelineValues = PipelineValues()
    velocity: PipelineVelocity = PipelineVelocity()
    actionability: PipelineActionability = PipelineActionability()


# --- Admin: Campaigns ---


class CreateCampaignRequest(BaseModel):
    campaign_name: str
    source: str
    utm_campaign: str
    ad_spend: float = 0


class UpdateCampaignRequest(BaseModel):
    ad_spend: float


class CampaignListItem(BaseModel):
    id: UUID
    campaign_name: str
    source: str
    utm_campaign: str
    ad_spend: float
    created_at: datetime


# --- Lead Intelligence (Sprint 8) ---


class LeadIntelligenceResponse(BaseModel):
    close_probability: int
    days_in_stage: float | None = None
    is_stale: bool = False
    stage_leak_warning: bool = False
    stage_leak_message: str | None = None


class OrgInsightsResponse(BaseModel):
    summary: str
    highlights: list[str]
    mode: str = "stub"
