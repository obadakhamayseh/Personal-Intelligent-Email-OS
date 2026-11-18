from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.entities import (
    ClassificationRule,
    DeadlineItem,
    EmailMetadata,
    FinancialEvent,
    LifecycleTTL,
    OAuthServiceRegistry,
    SenderStat,
    SeverityLevel,
    SmartCategory,
)
from app.schemas.api_schemas import (
    DashboardStatusResponse,
    SenderStatResponse,
)
from app.services.gmail_client import GmailServiceClient
from app.services.llm_provider import LLMProviderService
from app.services.rag_service import build_gmail_thread_url

logger = get_logger("intelligence")


class IntelligenceModulesService:
    """
    Implements Advanced Intelligence Modules:
    1. Sender Noise Score & Dead Subscription Detector (>= 5 emails and > 90% unread rate over 60 days)
       + 1-click Auto-Archive Rule or RFC-8058 Unsubscribe.
    2. Ghosted Sent Thread Detector (SENT threads with no external reply within 72 hours).
    3. OAuth & Account Exposure Map.
    4. Weekly Bilingual Knowledge Digest + Telegram Real-Time Push Notifier.
    """

    def __init__(
        self,
        gmail_client: Optional[GmailServiceClient] = None,
        llm_service: Optional[LLMProviderService] = None,
    ):
        self.settings = get_settings()
        self.gmail = gmail_client or GmailServiceClient()
        self.llm = llm_service or LLMProviderService()

    async def get_sender_noise_report(
        self, db: AsyncSession, dead_only: bool = False
    ) -> List[SenderStatResponse]:
        cutoff_60d = datetime.now(timezone.utc) - timedelta(days=60)
        stmt = select(SenderStat).order_by(SenderStat.noise_score.desc(), SenderStat.received_count.desc())
        rows = list((await db.execute(stmt)).scalars().all())

        results: List[SenderStatResponse] = []
        for s in rows:
            unread_count = max(0, s.received_count - s.read_count)
            unread_rate = round((unread_count / max(1, s.received_count)) * 100.0, 2)
            last_dt = s.last_received_at
            if last_dt and last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            within_60d = bool(last_dt is None or last_dt >= cutoff_60d)
            is_dead = bool(s.received_count >= 5 and unread_rate > 90.0 and within_60d)

            if dead_only and not is_dead:
                continue

            results.append(
                SenderStatResponse(
                    id=s.id,
                    sender_email=s.sender_email,
                    sender_domain=s.sender_domain,
                    sender_name=s.sender_name,
                    received_count=s.received_count,
                    read_count=s.read_count,
                    replied_count=s.replied_count,
                    noise_score=s.noise_score,
                    unread_rate_percent=unread_rate,
                    is_dead_subscription=is_dead,
                    has_list_unsubscribe=s.has_list_unsubscribe,
                    unsubscribe_url=s.unsubscribe_url,
                    is_muted=s.is_muted,
                    last_received_at=s.last_received_at,
                )
            )
        return results

    async def create_auto_archive_rule_for_sender(
        self, db: AsyncSession, sender_email: str
    ) -> ClassificationRule:
        sender_clean = sender_email.lower().strip()
        rule_name = f"Auto-Archive Dead Subscription: {sender_clean}"
        existing_res = await db.execute(
            select(ClassificationRule).where(ClassificationRule.name == rule_name)
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            return existing

        new_rule = ClassificationRule(
            name=rule_name,
            description=f"Auto-created 1-click mute rule for noisy sender {sender_clean}",
            priority=10,
            is_active=True,
            sender_email=sender_clean,
            target_category=SmartCategory.PROMOTIONS_NOISE.value,
            target_severity=SeverityLevel.P3_NOISE.value,
            target_ttl=LifecycleTTL.TTL_7D.value,
        )
        db.add(new_rule)

        stat_res = await db.execute(
            select(SenderStat).where(SenderStat.sender_email == sender_clean)
        )
        stat = stat_res.scalar_one_or_none()
        if stat:
            stat.is_muted = True

        await db.commit()
        await db.refresh(new_rule)
        return new_rule

    async def unsubscribe_sender(self, db: AsyncSession, sender_email: str) -> Dict[str, Any]:
        sender_clean = sender_email.lower().strip()
        stat_res = await db.execute(
            select(SenderStat).where(SenderStat.sender_email == sender_clean)
        )
        stat = stat_res.scalar_one_or_none()
        rfc_triggered = False
        if stat and stat.unsubscribe_url:
            rfc_triggered = await self.gmail.trigger_rfc8058_unsubscribe(stat.unsubscribe_url)

        rule = await self.create_auto_archive_rule_for_sender(db, sender_clean)
        return {
            "sender_email": sender_clean,
            "rfc8058_dispatched": rfc_triggered,
            "auto_archive_rule_id": rule.id,
            "muted": True,
        }

    async def scan_ghosted_sent_threads(self, db: AsyncSession) -> List[EmailMetadata]:
        """
        Detects SENT threads where an outbound email to an external recipient
        received no reply within 72 hours, tags it as AI/Waiting-On-Ghosted,
        and schedules a follow-up reminder.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.settings.GHOSTED_SLA_HOURS)
        stmt = select(EmailMetadata).where(
            EmailMetadata.is_sent.is_(True),
            EmailMetadata.is_trashed.is_(False),
            EmailMetadata.internal_date <= cutoff,
        )
        sent_messages = list((await db.execute(stmt)).scalars().all())
        newly_flagged: List[EmailMetadata] = []

        for sent_msg in sent_messages:
            reply_stmt = select(func.count(EmailMetadata.message_id)).where(
                EmailMetadata.thread_id == sent_msg.thread_id,
                EmailMetadata.is_sent.is_(False),
                EmailMetadata.internal_date > sent_msg.internal_date,
            )
            reply_count = (await db.execute(reply_stmt)).scalar() or 0
            if reply_count == 0 and not sent_msg.ghosted_flagged:
                sent_msg.ghosted_flagged = True
                sent_msg.category = SmartCategory.WAITING_GHOSTED.value
                if SmartCategory.WAITING_GHOSTED.value not in (sent_msg.gmail_labels or []):
                    sent_msg.gmail_labels = list(sent_msg.gmail_labels or []) + [
                        SmartCategory.WAITING_GHOSTED.value
                    ]
                db.add(
                    DeadlineItem(
                        message_id=sent_msg.message_id,
                        thread_id=sent_msg.thread_id,
                        title=f"Follow up on ghosted thread: {sent_msg.subject[:120]}",
                        deadline_at=datetime.now(timezone.utc) + timedelta(hours=24),
                        is_completed=False,
                    )
                )
                newly_flagged.append(sent_msg)

        if newly_flagged:
            await db.commit()
        return newly_flagged

    async def generate_and_archive_weekly_digest(
        self, db: AsyncSession, send_telegram: bool = True
    ) -> Dict[str, Any]:
        stmt = (
            select(EmailMetadata)
            .where(
                EmailMetadata.category == SmartCategory.KNOWLEDGE_DIGEST.value,
                EmailMetadata.is_trashed.is_(False),
                EmailMetadata.digest_included.is_(False),
            )
            .order_by(EmailMetadata.internal_date.desc())
            .limit(25)
        )
        digest_emails = list((await db.execute(stmt)).scalars().all())
        if not digest_emails:
            stmt_fallback = (
                select(EmailMetadata)
                .where(
                    EmailMetadata.category == SmartCategory.KNOWLEDGE_DIGEST.value,
                    EmailMetadata.is_trashed.is_(False),
                )
                .order_by(EmailMetadata.internal_date.desc())
                .limit(5)
            )
            digest_emails = list((await db.execute(stmt_fallback)).scalars().all())

        payload_items = [
            {
                "message_id": e.message_id,
                "subject": e.subject,
                "sender_email": e.sender_email,
                "snippet": e.snippet,
                "ai_summary": e.ai_summary,
            }
            for e in digest_emails
        ]
        summary_markdown = await self.llm.generate_bilingual_digest(payload_items)

        msg_ids = [e.message_id for e in digest_emails]
        if msg_ids:
            await self.gmail.batch_modify_messages(
                db=db,
                message_ids=msg_ids,
                remove_label_ids=["INBOX", "UNREAD"],
            )
            for e in digest_emails:
                e.is_read = True
                e.is_archived = True
                e.digest_included = True
            await db.commit()

        if send_telegram and digest_emails:
            await self.send_telegram_push(summary_markdown)

        return {
            "processed_count": len(digest_emails),
            "summary_markdown": summary_markdown,
            "archived_message_ids": msg_ids,
        }

    async def send_telegram_push(self, text: str) -> bool:
        token = self.settings.TELEGRAM_BOT_TOKEN
        allowed_ids = self.settings.allowed_telegram_ids
        if not token or token.startswith("1234567890:") or not allowed_ids:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        sent_any = False
        async with httpx.AsyncClient(timeout=10.0) as client:
            for chat_id in allowed_ids:
                try:
                    resp = await client.post(
                        url,
                        json={
                            "chat_id": chat_id,
                            "text": text[:4000],
                        },
                    )
                    if resp.status_code == 200:
                        sent_any = True
                except Exception as exc:
                    logger.warning("telegram_push_failed", chat_id=chat_id, error=str(exc))
        return sent_any

    async def get_dashboard_status(self, db: AsyncSession) -> DashboardStatusResponse:
        total_emails = (
            await db.execute(
                select(func.count(EmailMetadata.message_id)).where(EmailMetadata.is_trashed.is_(False))
            )
        ).scalar() or 0

        unread_emails = (
            await db.execute(
                select(func.count(EmailMetadata.message_id)).where(
                    EmailMetadata.is_trashed.is_(False), EmailMetadata.is_read.is_(False)
                )
            )
        ).scalar() or 0

        active_p0 = (
            await db.execute(
                select(func.count(EmailMetadata.message_id)).where(
                    EmailMetadata.is_trashed.is_(False),
                    EmailMetadata.severity == SeverityLevel.P0_CRITICAL.value,
                )
            )
        ).scalar() or 0

        upcoming_deadlines = (
            await db.execute(
                select(func.count(DeadlineItem.id)).where(DeadlineItem.is_completed.is_(False))
            )
        ).scalar() or 0

        ghosted_count = (
            await db.execute(
                select(func.count(EmailMetadata.message_id)).where(
                    EmailMetadata.is_trashed.is_(False),
                    EmailMetadata.category == SmartCategory.WAITING_GHOSTED.value,
                )
            )
        ).scalar() or 0

        oauth_count = (
            await db.execute(select(func.count(OAuthServiceRegistry.id)))
        ).scalar() or 0

        financial_count = (
            await db.execute(select(func.count(FinancialEvent.id)))
        ).scalar() or 0

        cat_rows = (
            await db.execute(
                select(EmailMetadata.category, func.count(EmailMetadata.message_id))
                .where(EmailMetadata.is_trashed.is_(False))
                .group_by(EmailMetadata.category)
            )
        ).all()
        category_counts = {cat: cnt for cat, cnt in cat_rows}

        sev_rows = (
            await db.execute(
                select(EmailMetadata.severity, func.count(EmailMetadata.message_id))
                .where(EmailMetadata.is_trashed.is_(False))
                .group_by(EmailMetadata.severity)
            )
        ).all()
        severity_counts = {sev: cnt for sev, cnt in sev_rows}

        dead_subs = await self.get_sender_noise_report(db, dead_only=True)
        gmail_connected = await self.gmail.is_connected(db)

        return DashboardStatusResponse(
            total_emails=total_emails,
            unread_emails=unread_emails,
            active_p0_incidents=active_p0,
            upcoming_deadlines_count=upcoming_deadlines,
            ghosted_threads_count=ghosted_count,
            dead_subscriptions_count=len(dead_subs),
            oauth_apps_count=oauth_count,
            financial_events_count=financial_count,
            category_counts=category_counts,
            severity_counts=severity_counts,
            gmail_connected=gmail_connected,
            next_scheduled_cleanup=f"Daily at {self.settings.CLEANUP_CRON_HOUR:02d}:00 UTC",
        )
