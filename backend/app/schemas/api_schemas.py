from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.entities import LifecycleTTL, SeverityLevel, SmartCategory


class LLMClassificationResult(BaseModel):
    category: SmartCategory = Field(description="Primary Smart Category")
    severity: SeverityLevel = Field(description="Priority / Severity P0..P3")
    ttl_policy: LifecycleTTL = Field(description="Lifecycle retention policy")
    ai_summary: str = Field(description="Concise 1-sentence summary in the email's original language (Arabic or English)")
    deadline_at: Optional[datetime] = Field(default=None, description="ISO timestamp if a deadline/expiration exists")
    deadline_title: Optional[str] = Field(default=None, description="Short action title if a deadline exists")
    monetary_amount: Optional[float] = Field(default=None, description="Extracted monetary amount for financial emails")
    currency: Optional[str] = Field(default=None, description="ISO currency code e.g. USD, EUR, EGP, SAR")
    renewal_date: Optional[datetime] = Field(default=None, description="Upcoming subscription renewal or trial end timestamp")
    financial_event_type: Optional[str] = Field(
        default=None,
        description="RECEIPT | PAYMENT_FAILED | TRIAL_ENDING | REFUND | AUTO_RENEWAL",
    )
    vendor_name: Optional[str] = Field(default=None, description="Vendor or platform name")
    oauth_app_name: Optional[str] = Field(default=None, description="Third-party OAuth app or service name")
    oauth_event_type: Optional[str] = Field(
        default=None,
        description="OAUTH_GRANT | NEW_SIGN_IN | TWO_FACTOR_CHANGE | SECURITY_ALERT",
    )
    oauth_location_or_ip: Optional[str] = Field(default=None, description="Detected IP or geographic location")
    oauth_risk_level: Optional[str] = Field(default="NORMAL", description="NORMAL | ELEVATED | CRITICAL")


class EmailCreateInput(BaseModel):
    message_id: str
    thread_id: str
    sender_email: str
    sender_name: Optional[str] = None
    recipient_email: Optional[str] = None
    subject: str = ""
    snippet: str = ""
    body_text: str = ""
    internal_date: datetime
    size_estimate: int = 2048
    is_read: bool = False
    is_starred: bool = False
    is_sent: bool = False
    is_trashed: bool = False
    gmail_labels: List[str] = Field(default_factory=list)
    raw_headers: Dict[str, str] = Field(default_factory=dict)


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    thread_id: str
    sender_email: str
    sender_name: Optional[str]
    recipient_email: Optional[str]
    subject: str
    snippet: str
    body_text: str
    internal_date: datetime
    size_estimate: int
    is_read: bool
    is_starred: bool
    is_sent: bool
    is_trashed: bool
    is_archived: bool
    category: str
    severity: str
    ttl_policy: str
    expires_at: Optional[datetime]
    ai_summary: Optional[str]
    classified_by: str
    matched_rule_id: Optional[int]
    has_unsubscribe: bool
    unsubscribe_header: Optional[str]
    gmail_labels: List[str]
    ghosted_flagged: bool
    digest_included: bool
    gmail_link: Optional[str] = None


class EmailListResponse(BaseModel):
    total: int
    unread_count: int
    p0_count: int
    items: List[EmailResponse]


class ClassificationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: int = 100
    is_active: bool = True
    sender_domain: Optional[str] = None
    sender_email: Optional[str] = None
    subject_regex: Optional[str] = None
    snippet_regex: Optional[str] = None
    header_key: Optional[str] = None
    header_regex: Optional[str] = None
    target_category: SmartCategory
    target_severity: SeverityLevel
    target_ttl: LifecycleTTL


class ClassificationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    sender_domain: Optional[str] = None
    sender_email: Optional[str] = None
    subject_regex: Optional[str] = None
    snippet_regex: Optional[str] = None
    header_key: Optional[str] = None
    header_regex: Optional[str] = None
    target_category: Optional[SmartCategory] = None
    target_severity: Optional[SeverityLevel] = None
    target_ttl: Optional[LifecycleTTL] = None


class ClassificationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    priority: int
    is_active: bool
    sender_domain: Optional[str]
    sender_email: Optional[str]
    subject_regex: Optional[str]
    snippet_regex: Optional[str]
    header_key: Optional[str]
    header_regex: Optional[str]
    target_category: str
    target_severity: str
    target_ttl: str
    hit_count: int
    created_at: datetime


class CleanupPreviewRequest(BaseModel):
    before_date: Optional[datetime] = None
    categories: Optional[List[SmartCategory]] = None
    include_expired_ttl: bool = True
    override_protected: bool = False


class CleanupCategoryStat(BaseModel):
    category: str
    count: int
    bytes_freed: int
    sample_subjects: List[str]


class CleanupPreviewResponse(BaseModel):
    cutoff_date: datetime
    total_candidate_messages: int
    estimated_bytes_freed: int
    estimated_mb_freed: float
    shielded_active_threads_count: int
    shielded_protected_labels_count: int
    categories: List[CleanupCategoryStat]
    candidate_message_ids: List[str]


class CleanupExecuteRequest(BaseModel):
    before_date: Optional[datetime] = None
    categories: Optional[List[SmartCategory]] = None
    include_expired_ttl: bool = True
    override_protected: bool = False


class CleanupAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: str
    execution_mode: str
    cutoff_date: datetime
    total_messages: int
    estimated_bytes_freed: int
    category_breakdown: Dict[str, Any]
    status: str
    restored_at: Optional[datetime]
    created_at: datetime


class CustomBulkFilterRequest(BaseModel):
    before_date: Optional[datetime] = None
    after_date: Optional[datetime] = None
    categories: Optional[List[str]] = None
    severities: Optional[List[str]] = None
    sender_query: Optional[str] = None
    keyword_query: Optional[str] = None
    unread_only: Optional[bool] = None
    exclude_starred: bool = False
    limit: int = Field(default=500, ge=1, le=5000)


class CustomBulkMessageItem(BaseModel):
    message_id: str
    thread_id: str
    sender_email: str
    sender_name: Optional[str] = None
    subject: str
    internal_date: datetime
    size_estimate: int
    category: str
    severity: str
    is_read: bool
    is_starred: bool


class CustomBulkPreviewResponse(BaseModel):
    total_matching: int
    estimated_bytes: int
    estimated_mb: float
    category_counts: Dict[str, int]
    severity_counts: Dict[str, int]
    messages: List[CustomBulkMessageItem]


class CustomBulkDeleteExecuteRequest(BaseModel):
    message_ids: Optional[List[str]] = None
    filter_criteria: Optional[CustomBulkFilterRequest] = None


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)
    category_filter: Optional[SmartCategory] = None


class RagCitation(BaseModel):
    message_id: str
    thread_id: str
    subject: str
    sender_email: str
    internal_date: datetime
    category: str
    similarity_score: float
    gmail_thread_url: str
    snippet: str


class RagQueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[RagCitation]


class SenderStatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_email: str
    sender_domain: str
    sender_name: Optional[str]
    received_count: int
    read_count: int
    replied_count: int
    noise_score: float
    unread_rate_percent: float
    is_dead_subscription: bool
    has_list_unsubscribe: bool
    unsubscribe_url: Optional[str]
    is_muted: bool
    last_received_at: Optional[datetime]


class OAuthServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_name: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_event_type: str
    last_ip_or_location: Optional[str]
    scopes_summary: Optional[str]
    risk_level: str
    source_message_id: str
    event_count: int
    gmail_link: Optional[str] = None


class DeadlineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: str
    thread_id: str
    title: str
    deadline_at: datetime
    is_completed: bool
    reminder_sent: bool
    gmail_link: Optional[str] = None


class FinancialEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: str
    vendor: str
    event_type: str
    amount: Optional[float]
    currency: Optional[str]
    renewal_date: Optional[datetime]
    status: str
    created_at: datetime


class DashboardStatusResponse(BaseModel):
    total_emails: int
    unread_emails: int
    active_p0_incidents: int
    upcoming_deadlines_count: int
    ghosted_threads_count: int
    dead_subscriptions_count: int
    oauth_apps_count: int
    financial_events_count: int
    category_counts: Dict[str, int]
    severity_counts: Dict[str, int]
    gmail_connected: bool
    next_scheduled_cleanup: str
