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


# --- Paginated response ---


class LeadListResponse(BaseModel):
    leads: list[LeadListItem]
    total: int
    page: int
    per_page: int
