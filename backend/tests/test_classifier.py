from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    DeadlineItem,
    FinancialEvent,
    LifecycleTTL,
    OAuthServiceRegistry,
    SeverityLevel,
    SmartCategory,
)
from app.schemas.api_schemas import EmailCreateInput, LLMClassificationResult
from app.services.classifier import HybridClassificationEngine
from app.services.llm_provider import LLMProviderService


@pytest.mark.asyncio
async def test_tier1_deterministic_rules_zero_llm_cost(db_session: AsyncSession):
    """Verify Tier 1 rules classify OTPs, Cloud P0 vs P2, and Promotions without calling Tier 2 LLM."""
    mock_llm = LLMProviderService()
    mock_llm.classify_email = AsyncMock()
    engine = HybridClassificationEngine(llm_service=mock_llm)
    now = datetime.now(timezone.utc)

    # 1. OTP Email -> AI/Ephemeral-SelfDestruct, TTL_24H
    otp_in = EmailCreateInput(
        message_id="test_otp_1",
        thread_id="thd_otp_1",
        sender_email="security@service.io",
        subject="Your verification code is 991827",
        snippet="Enter OTP 991827 to sign in.",
        body_text="Your verification code is 991827.",
        internal_date=now,
    )
    otp_meta, created = await engine.ingest_and_classify(db_session, otp_in)
    assert created is True
    assert otp_meta.classified_by == "TIER1_RULE"
    assert otp_meta.category == SmartCategory.EPHEMERAL.value
    assert otp_meta.ttl_policy == LifecycleTTL.TTL_24H.value
    mock_llm.classify_email.assert_not_called()

    # 2. Cloud Infra P0 Critical (Vercel deploy failed) vs P2 Routine (Vercel deployment ready)
    p0_in = EmailCreateInput(
        message_id="test_vercel_p0",
        thread_id="thd_vercel_p0",
        sender_email="builds@vercel.com",
        subject="Production Deployment Failed on main",
        snippet="Build exited with code 1",
        body_text="Error during build.",
        internal_date=now,
    )
    p0_meta, _ = await engine.ingest_and_classify(db_session, p0_in)
    assert p0_meta.classified_by == "TIER1_RULE"
    assert p0_meta.category == SmartCategory.INFRA_INCIDENTS.value
    assert p0_meta.severity == SeverityLevel.P0_CRITICAL.value
    assert p0_meta.ttl_policy == LifecycleTTL.NEVER_DELETE.value

    p2_in = EmailCreateInput(
        message_id="test_vercel_p2",
        thread_id="thd_vercel_p2",
        sender_email="builds@vercel.com",
        subject="Deployment ready for staging branch",
        snippet="Build succeeded in 32s",
        body_text="Preview ready.",
        internal_date=now,
    )
    p2_meta, _ = await engine.ingest_and_classify(db_session, p2_in)
    assert p2_meta.classified_by == "TIER1_RULE"
    assert p2_meta.category == SmartCategory.INFRA_INCIDENTS.value
    assert p2_meta.severity == SeverityLevel.P2_NORMAL.value
    assert p2_meta.ttl_policy == LifecycleTTL.TTL_14D.value


@pytest.mark.asyncio
async def test_tier2_mocked_llm_bilingual_and_derived_entities(db_session: AsyncSession):
    """Verify unmatched ambiguous emails invoke Tier 2 LLM and populate Deadlines, Financial, and OAuth tables."""
    now = datetime.now(timezone.utc)
    deadline_target = now + timedelta(days=2)

    mock_llm = LLMProviderService()
    mock_llm.classify_email = AsyncMock(
        return_value=LLMClassificationResult(
            category=SmartCategory.ACTION_SLA,
            severity=SeverityLevel.P1_HIGH,
            ttl_policy=LifecycleTTL.TTL_14D,
            ai_summary="يرجى تأكيد حضور الجلسة المباشرة قبل يوم الخميس.",
            deadline_at=deadline_target,
            deadline_title="تأكيد حضور الجلسة المباشرة",
        )
    )

    engine = HybridClassificationEngine(llm_service=mock_llm)
    arabic_email = EmailCreateInput(
        message_id="test_arabic_llm_1",
        thread_id="thd_arabic_llm_1",
        sender_email="coordinator@academy-mena.org",
        subject="دعوة لحضور اللقاء التحضيري للمنحة",
        snippet="نرجو منك ملء النموذج المرفق في أقرب وقت.",
        body_text="تفاصيل اللقاء المباشر للمنحة الدراسية.",
        internal_date=now,
    )

    meta, created = await engine.ingest_and_classify(db_session, arabic_email)
    assert created is True
    assert meta.classified_by == "TIER2_LLM"
    assert meta.category == SmartCategory.ACTION_SLA.value
    assert meta.severity == SeverityLevel.P1_HIGH.value
    assert "يرجى تأكيد" in (meta.ai_summary or "")
    mock_llm.classify_email.assert_awaited_once()

    deadlines = (
        await db_session.execute(
            select(DeadlineItem).where(DeadlineItem.message_id == "test_arabic_llm_1")
        )
    ).scalars().all()
    assert len(deadlines) == 1
    assert deadlines[0].title == "تأكيد حضور الجلسة المباشرة"


@pytest.mark.asyncio
async def test_oauth_and_financial_extraction(db_session: AsyncSession):
    """Verify OAuth Radar and Financial Leakage records are automatically created."""
    engine = HybridClassificationEngine()
    now = datetime.now(timezone.utc)

    oauth_in = EmailCreateInput(
        message_id="test_oauth_figma",
        thread_id="thd_oauth_figma",
        sender_email="no-reply@accounts.google.com",
        subject="Security alert: You shared Google data with Figma",
        snippet="Figma now has access to your Google profile.",
        body_text="OAuth grant detected for Figma from Amsterdam.",
        internal_date=now,
    )
    await engine.ingest_and_classify(db_session, oauth_in)

    oauth_rows = (
        await db_session.execute(
            select(OAuthServiceRegistry).where(OAuthServiceRegistry.source_message_id == "test_oauth_figma")
        )
    ).scalars().all()
    assert len(oauth_rows) == 1
    assert "Figma" in oauth_rows[0].service_name

    fin_in = EmailCreateInput(
        message_id="test_fin_paypal",
        thread_id="thd_fin_paypal",
        sender_email="service@paypal.com",
        subject="Your receipt from PayPal for $49.00 USD",
        snippet="Payment confirmation of $49.00 USD.",
        body_text="You paid $49.00 USD to JetBrains.",
        internal_date=now,
    )
    fin_meta, _ = await engine.ingest_and_classify(db_session, fin_in)
    assert fin_meta.ttl_policy == LifecycleTTL.NEVER_DELETE.value

    fin_rows = (
        await db_session.execute(
            select(FinancialEvent).where(FinancialEvent.message_id == "test_fin_paypal")
        )
    ).scalars().all()
    assert len(fin_rows) == 1
