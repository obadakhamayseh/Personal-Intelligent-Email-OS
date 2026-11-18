"""Initial schema with pgvector and all 10 core tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-17 18:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "emails_metadata",
        sa.Column("message_id", sa.String(length=128), primary_key=True),
        sa.Column("thread_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("sender_email", sa.String(length=320), nullable=False, index=True),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("internal_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("size_estimate", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_trashed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity", sa.String(length=32), nullable=False, index=True),
        sa.Column("ttl_policy", sa.String(length=32), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("classified_by", sa.String(length=32), nullable=False, server_default="TIER1_RULE"),
        sa.Column("matched_rule_id", sa.Integer(), nullable=True),
        sa.Column("has_unsubscribe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unsubscribe_header", sa.Text(), nullable=True),
        sa.Column("gmail_labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("raw_headers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("ghosted_flagged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("digest_included", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "classification_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100", index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sender_domain", sa.String(length=255), nullable=True),
        sa.Column("sender_email", sa.String(length=320), nullable=True),
        sa.Column("subject_regex", sa.String(length=512), nullable=True),
        sa.Column("snippet_regex", sa.String(length=512), nullable=True),
        sa.Column("header_key", sa.String(length=128), nullable=True),
        sa.Column("header_regex", sa.String(length=512), nullable=True),
        sa.Column("target_category", sa.String(length=64), nullable=False),
        sa.Column("target_severity", sa.String(length=32), nullable=False),
        sa.Column("target_ttl", sa.String(length=32), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cleanup_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("max_severity", sa.String(length=32), nullable=False, server_default="P2_NORMAL"),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="TRASH"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cleanup_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("cutoff_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_bytes_freed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("category_breakdown", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("affected_messages_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("checkpoint_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="COMPLETED"),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id",
            sa.String(length=128),
            sa.ForeignKey("emails_metadata.message_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("thread_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "financial_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id",
            sa.String(length=128),
            sa.ForeignKey("emails_metadata.message_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("vendor", sa.String(length=255), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True, server_default="USD"),
        sa.Column("renewal_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="RECORDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "oauth_services_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_name", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_type", sa.String(length=128), nullable=False),
        sa.Column("last_ip_or_location", sa.String(length=255), nullable=True),
        sa.Column("scopes_summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="NORMAL"),
        sa.Column("source_message_id", sa.String(length=128), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "sender_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sender_email", sa.String(length=320), nullable=False, unique=True, index=True),
        sa.Column("sender_domain", sa.String(length=255), nullable=False, index=True),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("received_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("read_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("noise_score", sa.Float(), nullable=False, server_default="0.0", index=True),
        sa.Column("has_list_unsubscribe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unsubscribe_url", sa.Text(), nullable=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "email_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id",
            sa.String(length=128),
            sa.ForeignKey("emails_metadata.message_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("thread_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("content_chunk", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value_encrypted", sa.Text(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("email_embeddings")
    op.drop_table("sender_stats")
    op.drop_table("oauth_services_registry")
    op.drop_table("financial_events")
    op.drop_table("deadlines")
    op.drop_table("cleanup_audit_logs")
    op.drop_table("cleanup_policies")
    op.drop_table("classification_rules")
    op.drop_table("emails_metadata")
