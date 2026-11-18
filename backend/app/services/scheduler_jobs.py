from datetime import datetime, timedelta, timezone
from typing import Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import (
    ClassificationRule,
    CleanupPolicy,
    EmailMetadata,
    LifecycleTTL,
    SeverityLevel,
    SmartCategory,
)
from app.schemas.api_schemas import CleanupExecuteRequest, EmailCreateInput
from app.services.classifier import HybridClassificationEngine
from app.services.cleanup_engine import SafeBulkCleanupEngine
from app.services.gmail_client import GmailServiceClient
from app.services.intelligence import IntelligenceModulesService

logger = get_logger("scheduler_jobs")


DEFAULT_TIER1_RULES: List[Dict] = [
    {
        "name": "Ephemeral OTP & 2FA Verification Codes",
        "description": "Matches OTPs, 2FA codes, magic login links, and verification codes in English & Arabic",
        "priority": 10,
        "subject_regex": r"(verification code|security code|login code|one-time password|\botp\b|magic link|رمز التحقق|كود التفعيل)",
        "target_category": SmartCategory.EPHEMERAL.value,
        "target_severity": SeverityLevel.P2_NORMAL.value,
        "target_ttl": LifecycleTTL.TTL_24H.value,
    },
    {
        "name": "Security & OAuth Radar Alerts",
        "description": "Detects OAuth app authorizations, new sign-ins, and 2FA modifications",
        "priority": 15,
        "subject_regex": r"(security alert|new sign-in|shared google data with|third-party access|oauth|2-step verification|تنبيه أمني|تسجيل دخول جديد)",
        "target_category": SmartCategory.SECURITY_OAUTH.value,
        "target_severity": SeverityLevel.P1_HIGH.value,
        "target_ttl": LifecycleTTL.NEVER_DELETE.value,
    },
    {
        "name": "Cloud & DevOps Infra Incidents - P0 CRITICAL",
        "description": "Critical deploy failures, domain expiration, DB deletion/suspension across Vercel, Render, Neon, Supabase, Cloudflare, Namecheap, DigitalOcean, AWS, Oracle",
        "priority": 20,
        "sender_domain": "vercel.com,render.com,neon.tech,supabase.io,supabase.com,cloudflare.com,namecheap.com,digitalocean.com,amazon.com,oracle.com",
        "subject_regex": r"(deploy.*failed|build failed|domain.*expir|database.*delet|suspended|critical|outage|action required|payment overdue)",
        "target_category": SmartCategory.INFRA_INCIDENTS.value,
        "target_severity": SeverityLevel.P0_CRITICAL.value,
        "target_ttl": LifecycleTTL.NEVER_DELETE.value,
    },
    {
        "name": "Cloud & DevOps Infra - Routine Builds & Recaps (P2/P3)",
        "description": "Separates routine cloud usage summaries and successful builds from critical incidents",
        "priority": 25,
        "sender_domain": "vercel.com,render.com,neon.tech,supabase.io,supabase.com,cloudflare.com,namecheap.com,digitalocean.com,amazon.com,oracle.com",
        "subject_regex": r"(deployment ready|build succeeded|usage summary|weekly report|monthly recap)",
        "target_category": SmartCategory.INFRA_INCIDENTS.value,
        "target_severity": SeverityLevel.P2_NORMAL.value,
        "target_ttl": LifecycleTTL.TTL_14D.value,
    },
    {
        "name": "Financial Payment Failures & Trial Ending Alerts",
        "description": "Failed subscription charges (Netflix, Spotify, Cloud) & trial ending alerts",
        "priority": 30,
        "subject_regex": r"(payment failed|unable to process payment|trial.*ending|auto-renewal|billing problem|فشل الدفع|انتهاء الفترة التجريبية)",
        "target_category": SmartCategory.FINANCIAL_LEAKAGE.value,
        "target_severity": SeverityLevel.P0_CRITICAL.value,
        "target_ttl": LifecycleTTL.NEVER_DELETE.value,
    },
    {
        "name": "Financial Receipts & Invoices (Protected NEVER_DELETE)",
        "description": "Google Play, PayPal, Stripe, and merchant receipts/refunds",
        "priority": 35,
        "subject_regex": r"(your receipt|invoice from|payment confirmation|refund processed|google play order|إيصال الدفع|فاتورة)",
        "target_category": SmartCategory.FINANCIAL_LEAKAGE.value,
        "target_severity": SeverityLevel.P1_HIGH.value,
        "target_ttl": LifecycleTTL.NEVER_DELETE.value,
    },
    {
        "name": "Action SLA & Countdown Deadlines",
        "description": "Quizzes, live sessions, support replies needed, and domain restoration deadlines",
        "priority": 40,
        "subject_regex": r"(deadline|due in|action required by|live session starts|quiz closing|موعد نهائي|مطلوب الرد قبل)",
        "target_category": SmartCategory.ACTION_SLA.value,
        "target_severity": SeverityLevel.P1_HIGH.value,
        "target_ttl": LifecycleTTL.TTL_30D.value,
    },
    {
        "name": "Academic, LMS & Study Training",
        "description": "Google Classroom, Coursera, hackathons, scholarships, and training programs",
        "priority": 50,
        "sender_domain": "classroom.google.com,coursera.org,edx.org,devpost.com,kaggle.com",
        "target_category": SmartCategory.STUDY_TRAINING.value,
        "target_severity": SeverityLevel.P2_NORMAL.value,
        "target_ttl": LifecycleTTL.TTL_60D.value,
    },
    {
        "name": "Knowledge Digest & Tech Changelogs",
        "description": "High-signal engineering changelogs and weekly digests",
        "priority": 60,
        "subject_regex": r"(changelog|release notes|engineering digest|weekly roundup|tldr|bytebytego)",
        "target_category": SmartCategory.KNOWLEDGE_DIGEST.value,
        "target_severity": SeverityLevel.P2_NORMAL.value,
        "target_ttl": LifecycleTTL.ARCHIVE_ONLY.value,
    },
    {
        "name": "Promotions & Bulk Marketing Noise",
        "description": "Auto-classifies marketing blasts with List-Unsubscribe and promotional keywords",
        "priority": 90,
        "header_key": "List-Unsubscribe",
        "subject_regex": r"(% off|flash sale|limited time offer|promo code|black friday|خصم حصري|عرض لفترة محدودة)",
        "target_category": SmartCategory.PROMOTIONS_NOISE.value,
        "target_severity": SeverityLevel.P3_NOISE.value,
        "target_ttl": LifecycleTTL.TTL_30D.value,
    },
]


DEFAULT_CLEANUP_POLICIES: List[Dict] = [
    {
        "name": "Ephemeral 24h Self-Destruct Policy",
        "category": SmartCategory.EPHEMERAL.value,
        "max_severity": SeverityLevel.P2_NORMAL.value,
        "retention_days": 1,
        "action": "TRASH",
    },
    {
        "name": "Promotions 30-Day Retention Policy",
        "category": SmartCategory.PROMOTIONS_NOISE.value,
        "max_severity": SeverityLevel.P3_NOISE.value,
        "retention_days": 30,
        "action": "TRASH",
    },
    {
        "name": "Routine Infra Notifications 14-Day Policy",
        "category": SmartCategory.INFRA_INCIDENTS.value,
        "max_severity": SeverityLevel.P2_NORMAL.value,
        "retention_days": 14,
        "action": "TRASH",
    },
]


async def seed_default_rules_and_policies(db: AsyncSession) -> None:
    existing_rules_count = (await db.execute(select(func.count(ClassificationRule.id)))).scalar() or 0
    if existing_rules_count == 0:
        for rule_data in DEFAULT_TIER1_RULES:
            db.add(ClassificationRule(**rule_data))
        await db.commit()
        logger.info("seeded_default_tier1_rules", count=len(DEFAULT_TIER1_RULES))

    existing_policies_count = (await db.execute(select(func.count(CleanupPolicy.id)))).scalar() or 0
    if existing_policies_count == 0:
        for pol_data in DEFAULT_CLEANUP_POLICIES:
            db.add(CleanupPolicy(**pol_data))
        await db.commit()
        logger.info("seeded_default_cleanup_policies", count=len(DEFAULT_CLEANUP_POLICIES))


async def seed_initial_demo_inbox(db: AsyncSession) -> None:
    """
    Populates a realistic initial bilingual (English + Arabic) inbox across all 9 Smart Categories
    when the database is empty so the Gmail UI, RAG, Cleanup Simulator, and OAuth Radar work immediately.
    """
    existing_emails = (await db.execute(select(func.count(EmailMetadata.message_id)))).scalar() or 0
    if existing_emails > 0:
        return

    now = datetime.now(timezone.utc)
    classifier = HybridClassificationEngine()

    sample_emails = [
        EmailCreateInput(
            message_id="msg_infra_p0_vercel",
            thread_id="thd_infra_p0_vercel",
            sender_email="notifications@vercel.com",
            sender_name="Vercel Deployment Bot",
            recipient_email="me@gmail.com",
            subject="[P0] Production Deployment Failed: personal-email-os (exit code 1)",
            snippet="Build failed on branch main due to missing environment variable DATABASE_URL.",
            body_text="Your production deployment for project personal-email-os on branch main failed at step build. Please inspect logs immediately.",
            internal_date=now - timedelta(hours=2),
            size_estimate=18400,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD", "IMPORTANT"],
        ),
        EmailCreateInput(
            message_id="msg_infra_p0_neon",
            thread_id="thd_infra_p0_neon",
            sender_email="alerts@neon.tech",
            sender_name="Neon Cloud Postgres",
            recipient_email="me@gmail.com",
            subject="CRITICAL: Database deletion warning for inactive project 'staging- cluster'",
            snippet="Your Neon PostgreSQL database will be suspended and scheduled for deletion in 48 hours.",
            body_text="Action required: Neon Postgres project 'staging-cluster' has exceeded compute quota and faces deletion unless upgraded before Friday.",
            internal_date=now - timedelta(hours=5),
            size_estimate=22100,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_fin_netflix_fail",
            thread_id="thd_fin_netflix_fail",
            sender_email="info@account.netflix.com",
            sender_name="Netflix Billing",
            recipient_email="me@gmail.com",
            subject="Payment Failed: Please update your payment method ($19.99 USD)",
            snippet="We were unable to process your monthly subscription payment of $19.99 USD.",
            body_text="Hi there, your Netflix Premium renewal of $19.99 USD failed today. Retry payment within 7 days to avoid interruption.",
            internal_date=now - timedelta(hours=9),
            size_estimate=31200,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_fin_gplay_ar",
            thread_id="thd_fin_gplay_ar",
            sender_email="googleplay-noreply@google.com",
            sender_name="Google Play",
            recipient_email="me@gmail.com",
            subject="إيصال الدفع من Google Play لاشتراك Gemini Advanced (20.00 USD)",
            snippet="شكراً على شرائك من Google Play. تم تحصيل مبلغ 20.00 USD وتاريخ التجديد القادم الشهر المقبل.",
            body_text="تفاصيل الفاتورة وإيصال الدفع من Google Play: اشتراك شهري بقيمة 20.00 USD. تاريخ التجديد التلقائي القادم بعد 30 يوماً.",
            internal_date=now - timedelta(days=3),
            size_estimate=28500,
            is_read=True,
            is_starred=True,
            gmail_labels=["INBOX", "STARRED"],
        ),
        EmailCreateInput(
            message_id="msg_oauth_notion",
            thread_id="thd_oauth_notion",
            sender_email="no-reply@accounts.google.com",
            sender_name="Google Security",
            recipient_email="me@gmail.com",
            subject="Security alert: You shared Google data with Notion Calendar",
            snippet="Notion Calendar now has access to your Google Account calendar and contacts from IP 197.55.12.84 (Cairo, EG).",
            body_text="You granted OAuth access to Notion Calendar. If you did not authorize this third-party application, revoke access immediately in your Google Account.",
            internal_date=now - timedelta(days=1, hours=4),
            size_estimate=16400,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_oauth_linear",
            thread_id="thd_oauth_linear",
            sender_email="no-reply@accounts.google.com",
            sender_name="Google Security",
            recipient_email="me@gmail.com",
            subject="New sign-in to Linear using your Google Account",
            snippet="You signed in to Linear from Frankfurt, Germany (IP 185.199.108.153).",
            body_text="Google Security detected a new OAuth login to Linear workspace.",
            internal_date=now - timedelta(days=6),
            size_estimate=14800,
            is_read=True,
            gmail_labels=["INBOX"],
        ),
        EmailCreateInput(
            message_id="msg_sla_quiz_ar",
            thread_id="thd_sla_quiz_ar",
            sender_email="classroom-noreply@classroom.google.com",
            sender_name="Google Classroom - AI Engineering",
            recipient_email="me@gmail.com",
            subject="موعد نهائي: تسليم مشروع هندسة النظم الذكية قبل غد الساعة 11:59 مساءً",
            snippet="مطلوب إجراء: يرجى رفع الكود المصدري والاختبارات قبل انتهاء الموعد النهائي للمشروع.",
            body_text="تذكير هام من Google Classroom: الموعد النهائي لتسليم مشروع هندسة النظم الذكية والاختبارات هو غداً.",
            internal_date=now - timedelta(hours=12),
            size_estimate=19200,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_sla_namecheap",
            thread_id="thd_sla_namecheap",
            sender_email="support@namecheap.com",
            sender_name="Namecheap Domain SLA",
            recipient_email="me@gmail.com",
            subject="Action Required by Friday: Renew domain intelligent-email-os.ai before expiration",
            snippet="Your primary domain intelligent-email-os.ai expires in 48 hours. Renew now to prevent DNS disruption.",
            body_text="Deadline alert: Domain intelligent-email-os.ai will expire in 48 hours. Cost to renew is $68.00 USD.",
            internal_date=now - timedelta(hours=15),
            size_estimate=21000,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_otp_expired",
            thread_id="thd_otp_expired",
            sender_email="noreply@github.com",
            sender_name="GitHub Authentication",
            recipient_email="me@gmail.com",
            subject="[GitHub] Your verification code is 849201",
            snippet="Use OTP verification code 849201 to complete your two-factor sign-in. Expires in 15 minutes.",
            body_text="Your GitHub OTP verification code is 849201.",
            internal_date=now - timedelta(days=3),
            size_estimate=8192,
            is_read=True,
            gmail_labels=["INBOX"],
        ),
        EmailCreateInput(
            message_id="msg_study_hackathon",
            thread_id="thd_study_hackathon",
            sender_email="hackathons@devpost.com",
            sender_name="Devpost Global AI Hackathon",
            recipient_email="me@gmail.com",
            subject="Welcome to the Global Gemini & Agentic Systems Hackathon 2026",
            snippet="Access workshop schedules, cloud credits, and submission guidelines for your team.",
            body_text="Congratulations on registering for the Global AI Hackathon on Devpost. Office hours start Tuesday.",
            internal_date=now - timedelta(days=4),
            size_estimate=34000,
            is_read=True,
            gmail_labels=["INBOX"],
        ),
        EmailCreateInput(
            message_id="msg_digest_bytebytego",
            thread_id="thd_digest_bytebytego",
            sender_email="newsletter@bytebytego.com",
            sender_name="ByteByteGo System Design",
            recipient_email="me@gmail.com",
            subject="Weekly Engineering Digest: How PostgreSQL pgvector Scales to 100M Embeddings",
            snippet="Deep dive into HNSW indexes, IVFFlat quantization, and hybrid lexical-vector retrieval.",
            body_text="In this week's engineering changelog and digest: PostgreSQL 16 pgvector HNSW tuning, FastAPI async connection pooling, and zero-downtime migrations.",
            internal_date=now - timedelta(days=2),
            size_estimate=54000,
            is_read=False,
            gmail_labels=["INBOX", "UNREAD"],
        ),
        EmailCreateInput(
            message_id="msg_ghosted_outbound",
            thread_id="thd_ghosted_outbound",
            sender_email="me@gmail.com",
            sender_name="Engineering Lead",
            recipient_email="enterprise-licensing@vendor-cloud.io",
            subject="Proposal & SLA Contract Review for Q4 Enterprise Tier",
            snippet="Hi team, following up on the enterprise contract terms we sent over earlier this week.",
            body_text="Please let us know if your legal team has approved the Q4 SLA addendum.",
            internal_date=now - timedelta(days=5),
            size_estimate=15600,
            is_read=True,
            is_sent=True,
            gmail_labels=["SENT"],
        ),
    ]

    # Add 6 unread promotional emails from a noisy sender (older than 35 days) to trigger
    # both the Dead Subscription Detector (>= 5 emails, >90% unread) and the Cleanup Simulator
    for i in range(1, 7):
        sample_emails.append(
            EmailCreateInput(
                message_id=f"msg_promo_noisy_{i}",
                thread_id=f"thd_promo_noisy_{i}",
                sender_email="deals@mega-fashion-blasts.example.com",
                sender_name="Mega Fashion Blasts",
                recipient_email="me@gmail.com",
                subject=f"🔥 70% OFF Flash Sale #{i} - Limited Time Offer Promo Code!",
                snippet="Use promo code FLASH70 before midnight to save on everything in store.",
                body_text="Unsubscribe anytime. Massive promotional discount blast.",
                internal_date=now - timedelta(days=35 + i),
                size_estimate=65536,
                is_read=False,
                gmail_labels=["INBOX", "UNREAD", "CATEGORY_PROMOTIONS"],
                raw_headers={
                    "List-Unsubscribe": "<https://mega-fashion-blasts.example.com/unsub?id=123>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            )
        )

    for item in sample_emails:
        await classifier.ingest_and_classify(db, item)

    intel = IntelligenceModulesService()
    await intel.scan_ghosted_sent_threads(db)
    logger.info("seeded_initial_demo_inbox", total_seeded=len(sample_emails))


SYNC_PROGRESS_STATE: Dict = {
    "is_running": False,
    "total_in_gmail": 0,
    "synced_in_db": 0,
    "newly_ingested": 0,
    "last_updated": None,
}


def get_sync_progress() -> Dict:
    return dict(SYNC_PROGRESS_STATE)


async def run_gmail_sync_job(db: AsyncSession, max_fetch: int | None = None) -> Dict:
    from app.models.entities import SystemSetting

    if SYNC_PROGRESS_STATE.get("is_running"):
        return {
            "status": "ALREADY_RUNNING",
            "ingested": SYNC_PROGRESS_STATE.get("newly_ingested", 0),
            "progress": get_sync_progress(),
        }

    gmail = GmailServiceClient()
    cfg_res = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "google_oauth_client_config")
    )
    cfg = cfg_res.scalar_one_or_none()
    if cfg and cfg.value_json:
        cid = cfg.value_json.get("client_id", "").strip()
        csec = cfg.value_json.get("client_secret", "").strip()
        if cid and csec:
            gmail.settings.GOOGLE_CLIENT_ID = cid
            gmail.settings.GOOGLE_CLIENT_SECRET = csec
    if not await gmail.is_connected(db):
        return {"status": "SKIPPED_NOT_CONNECTED", "ingested": 0}

    SYNC_PROGRESS_STATE["is_running"] = True
    SYNC_PROGRESS_STATE["newly_ingested"] = 0
    SYNC_PROGRESS_STATE["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        await gmail.ensure_smart_labels(db)

        # 1. Discover ALL message IDs in the Gmail account from day 1 to today
        all_gmail_ids = await gmail.list_all_message_ids(db, max_total=max_fetch)
        SYNC_PROGRESS_STATE["total_in_gmail"] = len(all_gmail_ids)

        # 2. Check which message IDs are already stored in PostgreSQL
        existing_rows = (await db.execute(select(EmailMetadata.message_id))).scalars().all()
        existing_set = set(existing_rows)
        SYNC_PROGRESS_STATE["synced_in_db"] = len(existing_set)

        missing_ids = [mid for mid in all_gmail_ids if mid not in existing_set]

        classifier = HybridClassificationEngine()
        intel = IntelligenceModulesService(gmail_client=gmail)

        new_count = 0
        chunk_size = 30
        for offset in range(0, len(missing_ids), chunk_size):
            chunk_ids = missing_ids[offset : offset + chunk_size]
            messages = await gmail.fetch_messages_by_ids(db, chunk_ids)
            for msg_in in messages:
                entity, is_new = await classifier.ingest_and_classify(db, msg_in)
                if is_new:
                    new_count += 1
                    SYNC_PROGRESS_STATE["newly_ingested"] = new_count
                    SYNC_PROGRESS_STATE["synced_in_db"] = len(existing_set) + new_count
                    SYNC_PROGRESS_STATE["last_updated"] = datetime.now(timezone.utc).isoformat()
                    if entity.severity == SeverityLevel.P0_CRITICAL.value and new_count <= 5:
                        await intel.send_telegram_push(
                            f"🚨 *P0 CRITICAL INCIDENT DETECTED*\n"
                            f"*From:* `{entity.sender_email}`\n"
                            f"*Category:* `{entity.category}`\n"
                            f"*Subject:* {entity.subject}\n"
                            f"*Summary:* {entity.ai_summary or entity.snippet[:160]}"
                        )

        await intel.scan_ghosted_sent_threads(db)
        return {
            "status": "SYNCED",
            "ingested": new_count,
            "total_in_gmail": len(all_gmail_ids),
            "progress": get_sync_progress(),
        }
    finally:
        SYNC_PROGRESS_STATE["is_running"] = False
        SYNC_PROGRESS_STATE["last_updated"] = datetime.now(timezone.utc).isoformat()


async def run_scheduled_cleanup_job(db: AsyncSession) -> Dict:
    engine = SafeBulkCleanupEngine()
    audit = await engine.execute_cleanup(
        db,
        CleanupExecuteRequest(
            before_date=datetime.now(timezone.utc) - timedelta(days=30),
            include_expired_ttl=True,
            override_protected=False,
        ),
    )
    return {"batch_id": audit.batch_id, "trashed_count": audit.total_messages}
