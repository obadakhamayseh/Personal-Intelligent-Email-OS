from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SmartCategory(str, Enum):
    EPHEMERAL = "AI/Ephemeral-SelfDestruct"
    SECURITY_OAUTH = "AI/Security-OAuth-Radar"
    INFRA_INCIDENTS = "AI/Infra-Incidents"
    FINANCIAL_LEAKAGE = "AI/Financial-Leakage"
    ACTION_SLA = "AI/Action-SLA"
    WAITING_GHOSTED = "AI/Waiting-On-Ghosted"
    STUDY_TRAINING = "AI/Study-Training"
    KNOWLEDGE_DIGEST = "AI/Knowledge-Digest"
    PROMOTIONS_NOISE = "AI/Promotions-Noise"


class SeverityLevel(str, Enum):
    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_NORMAL = "P2_NORMAL"
    P3_NOISE = "P3_NOISE"


class LifecycleTTL(str, Enum):
    NEVER_DELETE = "NEVER_DELETE"
    TTL_24H = "TTL_24H"
    TTL_7D = "TTL_7D"
    TTL_14D = "TTL_14D"
    TTL_30D = "TTL_30D"
    TTL_60D = "TTL_60D"
    ARCHIVE_ONLY = "ARCHIVE_ONLY"


TTL_DURATION_MAP: Dict[LifecycleTTL, Optional[timedelta]] = {
    LifecycleTTL.NEVER_DELETE: None,
    LifecycleTTL.ARCHIVE_ONLY: None,
    LifecycleTTL.TTL_24H: timedelta(hours=24),
    LifecycleTTL.TTL_7D: timedelta(days=7),
    LifecycleTTL.TTL_14D: timedelta(days=14),
    LifecycleTTL.TTL_30D: timedelta(days=30),
    LifecycleTTL.TTL_60D: timedelta(days=60),
}

PROTECTED_CATEGORIES = {
    SmartCategory.FINANCIAL_LEAKAGE.value,
    SmartCategory.SECURITY_OAUTH.value,
}


def compute_expires_at(base_time: datetime, ttl: LifecycleTTL | str) -> Optional[datetime]:
    ttl_enum = LifecycleTTL(ttl) if isinstance(ttl, str) else ttl
    delta = TTL_DURATION_MAP.get(ttl_enum)
    if delta is None:
        return None
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    return base_time + delta


class EmailMetadata(Base):
    __tablename__ = "emails_metadata"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    sender_email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(Text, default="", nullable=False)
    snippet: Mapped[str] = mapped_column(Text, default="", nullable=False)
    body_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    internal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    size_estimate: Mapped[int] = mapped_column(Integer, default=2048, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    ttl_policy: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classified_by: Mapped[str] = mapped_column(String(32), default="TIER1_RULE", nullable=False)
    matched_rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    has_unsubscribe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unsubscribe_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmail_labels: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    raw_headers: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    ghosted_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    digest_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class ClassificationRule(Base):
    __tablename__ = "classification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sender_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    subject_regex: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    snippet_regex: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    header_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    header_regex: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    target_category: Mapped[str] = mapped_column(String(64), nullable=False)
    target_severity: Mapped[str] = mapped_column(String(32), nullable=False)
    target_ttl: Mapped[str] = mapped_column(String(32), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class CleanupPolicy(Base):
    __tablename__ = "cleanup_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    max_severity: Mapped[str] = mapped_column(String(32), default=SeverityLevel.P2_NORMAL.value, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="TRASH", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class CleanupAuditLog(Base):
    __tablename__ = "cleanup_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    cutoff_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_bytes_freed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    category_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    affected_messages_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    checkpoint_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    restored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class DeadlineItem(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("emails_metadata.message_id", ondelete="CASCADE"), index=True, nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class FinancialEvent(Base):
    __tablename__ = "financial_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("emails_metadata.message_id", ondelete="CASCADE"), index=True, nullable=False
    )
    vendor: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(16), default="USD", nullable=True)
    renewal_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="RECORDED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class OAuthServiceRegistry(Base):
    __tablename__ = "oauth_services_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    last_ip_or_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scopes_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    source_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SenderStat(Base):
    __tablename__ = "sender_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    sender_domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    received_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    read_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    noise_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    has_list_unsubscribe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unsubscribe_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailEmbedding(Base):
    __tablename__ = "email_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("emails_metadata.message_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    content_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(
        Vector(768).with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
