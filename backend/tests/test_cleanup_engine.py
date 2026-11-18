from datetime import datetime, timedelta, timezone
from typing import List
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    CleanupAuditLog,
    EmailMetadata,
    LifecycleTTL,
    SeverityLevel,
    SmartCategory,
)
from app.schemas.api_schemas import CleanupExecuteRequest, CleanupPreviewRequest
from app.services.cleanup_engine import SafeBulkCleanupEngine
from app.services.gmail_client import GmailServiceClient, RateLimitExceededError


@pytest.mark.asyncio
async def test_active_thread_shield_prevents_deleting_old_message_in_active_thread(
    db_session: AsyncSession,
):
    """
    NON-NEGOTIABLE SAFETY SHIELD TEST:
    An old thread started 45 days ago (older than 30-day cutoff T) that received a reply 2 days ago
    (newer than cutoff T) MUST NOT have any of its messages deleted!
    Meanwhile, an inactive thread where all messages are > 45 days old MUST be eligible.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)

    # Thread A (Active): Message 1 is 45 days old, Message 2 (reply) is 2 days old
    msg_a1 = EmailMetadata(
        message_id="active_thd_msg_old",
        thread_id="thd_active_conversation",
        sender_email="colleague@company.com",
        subject="Project Architecture Discussion",
        snippet="Initial proposal from 45 days ago",
        body_text="Initial proposal",
        internal_date=now - timedelta(days=45),
        is_read=True,
        is_starred=False,
        category=SmartCategory.STUDY_TRAINING.value,
        severity=SeverityLevel.P2_NORMAL.value,
        ttl_policy=LifecycleTTL.TTL_30D.value,
        expires_at=now - timedelta(days=15),
    )
    msg_a2 = EmailMetadata(
        message_id="active_thd_msg_new_reply",
        thread_id="thd_active_conversation",
        sender_email="me@company.com",
        subject="Re: Project Architecture Discussion",
        snippet="New reply sent 2 days ago",
        body_text="Following up with latest specs",
        internal_date=now - timedelta(days=2),
        is_read=True,
        is_starred=False,
        category=SmartCategory.STUDY_TRAINING.value,
        severity=SeverityLevel.P2_NORMAL.value,
        ttl_policy=LifecycleTTL.TTL_30D.value,
        expires_at=now + timedelta(days=28),
    )

    # Thread B (Inactive): Only message is 45 days old
    msg_b1 = EmailMetadata(
        message_id="inactive_thd_msg_old",
        thread_id="thd_inactive_promo",
        sender_email="promo@store.com",
        subject="Old Summer Sale",
        snippet="Expired promo",
        body_text="Expired promo",
        internal_date=now - timedelta(days=45),
        is_read=False,
        is_starred=False,
        category=SmartCategory.PROMOTIONS_NOISE.value,
        severity=SeverityLevel.P3_NOISE.value,
        ttl_policy=LifecycleTTL.TTL_30D.value,
        expires_at=now - timedelta(days=15),
    )

    db_session.add_all([msg_a1, msg_a2, msg_b1])
    await db_session.commit()

    engine = SafeBulkCleanupEngine()
    preview = await engine.preview_cleanup(
        db_session,
        CleanupPreviewRequest(
            before_date=cutoff,
            include_expired_ttl=True,
            override_protected=False,
        ),
    )

    assert "inactive_thd_msg_old" in preview.candidate_message_ids
    assert "active_thd_msg_old" not in preview.candidate_message_ids
    assert "active_thd_msg_new_reply" not in preview.candidate_message_ids
    assert preview.shielded_active_threads_count >= 1


@pytest.mark.asyncio
async def test_protected_labels_shield(db_session: AsyncSession):
    """
    Verify STARRED, AI/Financial-Leakage, AI/Security-OAuth-Radar, and P0_CRITICAL
    are never deleted even if older than 90 days, while expired OTPs ARE deleted.
    """
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=90)
    cutoff = now - timedelta(days=30)

    protected_items = [
        EmailMetadata(
            message_id="prot_starred",
            thread_id="thd_prot_1",
            sender_email="newsletter@tech.com",
            subject="Starred Guide",
            internal_date=old_date,
            is_starred=True,
            category=SmartCategory.PROMOTIONS_NOISE.value,
            severity=SeverityLevel.P3_NOISE.value,
            ttl_policy=LifecycleTTL.TTL_30D.value,
        ),
        EmailMetadata(
            message_id="prot_financial",
            thread_id="thd_prot_2",
            sender_email="receipts@stripe.com",
            subject="Invoice #1928",
            internal_date=old_date,
            is_starred=False,
            category=SmartCategory.FINANCIAL_LEAKAGE.value,
            severity=SeverityLevel.P1_HIGH.value,
            ttl_policy=LifecycleTTL.NEVER_DELETE.value,
        ),
        EmailMetadata(
            message_id="prot_oauth",
            thread_id="thd_prot_3",
            sender_email="no-reply@accounts.google.com",
            subject="OAuth grant",
            internal_date=old_date,
            is_starred=False,
            category=SmartCategory.SECURITY_OAUTH.value,
            severity=SeverityLevel.P1_HIGH.value,
            ttl_policy=LifecycleTTL.NEVER_DELETE.value,
        ),
        EmailMetadata(
            message_id="prot_p0",
            thread_id="thd_prot_4",
            sender_email="alerts@aws.amazon.com",
            subject="P0 Production Outage",
            internal_date=old_date,
            is_starred=False,
            category=SmartCategory.INFRA_INCIDENTS.value,
            severity=SeverityLevel.P0_CRITICAL.value,
            ttl_policy=LifecycleTTL.TTL_30D.value,
        ),
        EmailMetadata(
            message_id="deletable_otp",
            thread_id="thd_otp_del",
            sender_email="auth@app.io",
            subject="Your OTP code is 123456",
            internal_date=now - timedelta(days=2),
            is_starred=False,
            category=SmartCategory.EPHEMERAL.value,
            severity=SeverityLevel.P2_NORMAL.value,
            ttl_policy=LifecycleTTL.TTL_24H.value,
            expires_at=now - timedelta(days=1),
        ),
    ]
    db_session.add_all(protected_items)
    await db_session.commit()

    engine = SafeBulkCleanupEngine()
    preview = await engine.preview_cleanup(
        db_session,
        CleanupPreviewRequest(before_date=cutoff, include_expired_ttl=True),
    )

    assert preview.candidate_message_ids == ["deletable_otp"]
    assert preview.shielded_protected_labels_count == 4


@pytest.mark.asyncio
async def test_batch_chunking_rate_limit_retry_and_undo(db_session: AsyncSession):
    """
    Verify:
    1. 2,250 messages are chunked into 3 batchModify calls (1,000 + 1,000 + 250).
    2. RateLimitExceededError (429 simulation) triggers exponential backoff retry and succeeds.
    3. Execution writes full audit log with checkpointing and 1-click Undo restores all messages.
    """
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=60)
    cutoff = now - timedelta(days=30)

    bulk_messages = [
        EmailMetadata(
            message_id=f"bulk_msg_{i}",
            thread_id=f"bulk_thd_{i}",
            sender_email="spam@promo.example.com",
            subject=f"Bulk Promo #{i}",
            internal_date=old_date,
            size_estimate=1024,
            category=SmartCategory.PROMOTIONS_NOISE.value,
            severity=SeverityLevel.P3_NOISE.value,
            ttl_policy=LifecycleTTL.TTL_30D.value,
            expires_at=now - timedelta(days=30),
        )
        for i in range(2250)
    ]
    db_session.add_all(bulk_messages)
    await db_session.commit()

    chunk_sizes: List[int] = []
    call_attempts = {"count": 0}

    def flaky_batch_executor(ids: List[str], add_labels: List[str], remove_labels: List[str]):
        call_attempts["count"] += 1
        # Simulate transient 429 rate-limit on first attempt of the first chunk
        if call_attempts["count"] == 1:
            raise RateLimitExceededError("Simulated 429 Too Many Requests")
        chunk_sizes.append(len(ids))

    gmail_client = GmailServiceClient(raw_batch_executor=flaky_batch_executor)
    engine = SafeBulkCleanupEngine(gmail_client=gmail_client)

    audit = await engine.execute_cleanup(
        db_session,
        CleanupExecuteRequest(before_date=cutoff, include_expired_ttl=True),
    )

    assert audit.status == "COMPLETED"
    assert audit.total_messages == 2250
    assert audit.checkpoint_offset == 2250
    assert chunk_sizes == [1000, 1000, 250]
    assert call_attempts["count"] == 4  # 1 failed + 3 succeeded

    # Verify messages marked as trashed
    sample_trashed = (
        await db_session.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == "bulk_msg_0")
        )
    ).scalar_one()
    assert sample_trashed.is_trashed is True

    # Test 1-click Undo / Restore
    restored_audit = await engine.undo_cleanup_batch(db_session, audit.batch_id)
    assert restored_audit.status == "RESTORED"
    assert restored_audit.restored_at is not None

    sample_restored = (
        await db_session.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == "bulk_msg_0")
        )
    ).scalar_one()
    assert sample_restored.is_trashed is False
