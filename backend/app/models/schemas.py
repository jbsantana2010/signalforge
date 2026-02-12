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
