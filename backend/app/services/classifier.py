import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import (
    ClassificationRule,
    DeadlineItem,
    EmailEmbedding,
    EmailMetadata,
    FinancialEvent,
    LifecycleTTL,
    OAuthServiceRegistry,
    SenderStat,
    SeverityLevel,
    SmartCategory,
    compute_expires_at,
)
from app.schemas.api_schemas import EmailCreateInput, LLMClassificationResult
from app.services.llm_provider import LLMProviderService

logger = get_logger("classifier")

RAG_INDEXABLE_CATEGORIES = {
    SmartCategory.FINANCIAL_LEAKAGE.value,
    SmartCategory.ACTION_SLA.value,
    SmartCategory.STUDY_TRAINING.value,
    SmartCategory.INFRA_INCIDENTS.value,
    SmartCategory.SECURITY_OAUTH.value,
}


class HybridClassificationEngine:
    """
    Two-Tier 3D Classification Engine:
    - Tier 1: Deterministic PostgreSQL Rule Engine (0ms, zero API cost) evaluating sender domain,
      exact sender address, headers (List-Unsubscribe, Auto-Submitted), and regex on subject/snippet.
    - Tier 2: LLM Semantic Classifier (Bilingual Arabic & English) with structured JSON extraction
      for deadlines, financial leakage events, and OAuth/security exposure radar.
    """

    def __init__(self, llm_service: Optional[LLMProviderService] = None):
        self.llm = llm_service or LLMProviderService()

    async def evaluate_tier1_rules(
        self, db: AsyncSession, email_in: EmailCreateInput
    ) -> Optional[ClassificationRule]:
        stmt = (
            select(ClassificationRule)
            .where(ClassificationRule.is_active.is_(True))
            .order_by(ClassificationRule.priority.asc(), ClassificationRule.id.asc())
        )
        result = await db.execute(stmt)
        rules: List[ClassificationRule] = list(result.scalars().all())

        sender_lower = email_in.sender_email.lower().strip()
        sender_domain = sender_lower.split("@")[-1] if "@" in sender_lower else sender_lower
        headers_lower = {k.lower(): str(v) for k, v in (email_in.raw_headers or {}).items()}

        for rule in rules:
            if self._rule_matches(rule, sender_lower, sender_domain, email_in.subject, email_in.snippet, headers_lower):
                rule.hit_count = (rule.hit_count or 0) + 1
                return rule
        return None

    @staticmethod
    def _rule_matches(
        rule: ClassificationRule,
        sender_email: str,
        sender_domain: str,
        subject: str,
        snippet: str,
        headers_lower: Dict[str, str],
    ) -> bool:
        has_any_condition = any(
            [
                rule.sender_email,
                rule.sender_domain,
                rule.subject_regex,
                rule.snippet_regex,
                rule.header_key,
            ]
        )
        if not has_any_condition:
            return False

        if rule.sender_email and rule.sender_email.lower().strip() != sender_email:
            return False

        if rule.sender_domain:
            domains = [d.strip().lower() for d in rule.sender_domain.split(",") if d.strip()]
            if not any(sender_domain == d or sender_domain.endswith(f".{d}") for d in domains):
                return False

        if rule.subject_regex:
            try:
                if not re.search(rule.subject_regex, subject or "", flags=re.IGNORECASE):
                    return False
            except re.error:
                return False

        if rule.snippet_regex:
            try:
                if not re.search(rule.snippet_regex, f"{subject} {snippet}", flags=re.IGNORECASE):
                    return False
            except re.error:
                return False

        if rule.header_key:
            h_key = rule.header_key.lower().strip()
            if h_key not in headers_lower:
                return False
            if rule.header_regex:
                try:
                    if not re.search(rule.header_regex, headers_lower[h_key], flags=re.IGNORECASE):
                        return False
                except re.error:
                    return False

        return True

    async def ingest_and_classify(
        self, db: AsyncSession, email_in: EmailCreateInput
    ) -> Tuple[EmailMetadata, bool]:
        """
        Ingests or updates an email, runs Tier 1 -> Tier 2 3D classification,
        extracts side-effect intelligence records (Deadlines, Financial, OAuth, Sender Stats),
        and embeds high-signal emails into pgvector.
        Returns (EmailMetadata, created_new).
        """
        existing_res = await db.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == email_in.message_id)
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            existing.is_read = email_in.is_read
            existing.is_starred = email_in.is_starred
            existing.is_trashed = email_in.is_trashed
            existing.gmail_labels = email_in.gmail_labels
            await db.commit()
            return existing, False

        matched_rule = await self.evaluate_tier1_rules(db, email_in)
        llm_result: Optional[LLMClassificationResult] = None

        if matched_rule is not None:
            category = matched_rule.target_category
            severity = matched_rule.target_severity
            ttl_policy = matched_rule.target_ttl
            classified_by = "TIER1_RULE"
            matched_rule_id = matched_rule.id
            ai_summary = f"[{matched_rule.name}] {email_in.subject[:110]}"

            # Extract structured metadata for Financial, OAuth, or SLA even if matched by Tier 1
            if category in (
                SmartCategory.FINANCIAL_LEAKAGE.value,
                SmartCategory.SECURITY_OAUTH.value,
                SmartCategory.ACTION_SLA.value,
            ):
                llm_result = await self.llm.classify_email(
                    sender_email=email_in.sender_email,
                    subject=email_in.subject,
                    snippet=email_in.snippet,
                    body_text=email_in.body_text,
                    headers=email_in.raw_headers,
                )
                if llm_result.ai_summary:
                    ai_summary = llm_result.ai_summary
        else:
            llm_result = await self.llm.classify_email(
                sender_email=email_in.sender_email,
                subject=email_in.subject,
                snippet=email_in.snippet,
                body_text=email_in.body_text,
                headers=email_in.raw_headers,
            )
            category = llm_result.category.value
            severity = llm_result.severity.value
            ttl_policy = llm_result.ttl_policy.value
            classified_by = "TIER2_LLM"
            matched_rule_id = None
            ai_summary = llm_result.ai_summary

        # Enforce mandatory Financial protection
        if category == SmartCategory.FINANCIAL_LEAKAGE.value:
            ttl_policy = LifecycleTTL.NEVER_DELETE.value

        # Enforce Ephemeral 24h TTL (or 3h if already read)
        internal_date = email_in.internal_date
        if internal_date.tzinfo is None:
            internal_date = internal_date.replace(tzinfo=timezone.utc)

        if category == SmartCategory.EPHEMERAL.value and email_in.is_read:
            expires_at = internal_date + timedelta(hours=3)
        else:
            expires_at = compute_expires_at(internal_date, ttl_policy)

        headers_lower = {k.lower(): v for k, v in (email_in.raw_headers or {}).items()}
        unsub_header = headers_lower.get("list-unsubscribe")
        has_unsub = bool(unsub_header)

        labels = list(set((email_in.gmail_labels or []) + [category]))

        email_entity = EmailMetadata(
            message_id=email_in.message_id,
            thread_id=email_in.thread_id,
            sender_email=email_in.sender_email.lower().strip(),
            sender_name=email_in.sender_name,
            recipient_email=email_in.recipient_email,
            subject=email_in.subject,
            snippet=email_in.snippet,
            body_text=email_in.body_text,
            internal_date=internal_date,
            size_estimate=email_in.size_estimate,
            is_read=email_in.is_read,
            is_starred=email_in.is_starred,
            is_sent=email_in.is_sent,
            is_trashed=email_in.is_trashed,
            is_archived=False,
            category=category,
            severity=severity,
            ttl_policy=ttl_policy,
            expires_at=expires_at,
            ai_summary=ai_summary,
            classified_by=classified_by,
            matched_rule_id=matched_rule_id,
            has_unsubscribe=has_unsub,
            unsubscribe_header=unsub_header,
            gmail_labels=labels,
            raw_headers=email_in.raw_headers or {},
        )
        db.add(email_entity)
        await db.flush()

        await self._record_derived_intelligence(db, email_entity, llm_result)
        await self._update_sender_stats(db, email_entity)

        if (
            category in RAG_INDEXABLE_CATEGORIES
            or severity == SeverityLevel.P0_CRITICAL.value
        ):
            await self._index_email_embedding(db, email_entity)

        await db.commit()
        await db.refresh(email_entity)
        return email_entity, True

    async def _record_derived_intelligence(
        self,
        db: AsyncSession,
        email_entity: EmailMetadata,
        llm_result: Optional[LLMClassificationResult],
    ) -> None:
        now = datetime.now(timezone.utc)

        # 1. Deadlines / Action SLA
        if email_entity.category == SmartCategory.ACTION_SLA.value or (
            llm_result and llm_result.deadline_at
        ):
            deadline_dt = (
                llm_result.deadline_at
                if (llm_result and llm_result.deadline_at)
                else (email_entity.internal_date + timedelta(hours=48))
            )
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            title = (
                llm_result.deadline_title
                if (llm_result and llm_result.deadline_title)
                else email_entity.subject[:200]
            )
            db.add(
                DeadlineItem(
                    message_id=email_entity.message_id,
                    thread_id=email_entity.thread_id,
                    title=title,
                    deadline_at=deadline_dt,
                    is_completed=False,
                )
            )

        # 2. Financial Leakage & Receipts
        if email_entity.category == SmartCategory.FINANCIAL_LEAKAGE.value:
            vendor = (
                llm_result.vendor_name
                if (llm_result and llm_result.vendor_name)
                else (email_entity.sender_name or email_entity.sender_email.split("@")[-1])
            )
            event_type = (
                llm_result.financial_event_type
                if (llm_result and llm_result.financial_event_type)
                else (
                    "PAYMENT_FAILED"
                    if "fail" in email_entity.subject.lower()
                    else "RECEIPT"
                )
            )
            amount = llm_result.monetary_amount if llm_result else None
            currency = (llm_result.currency if llm_result and llm_result.currency else "USD")
            renewal_dt = llm_result.renewal_date if llm_result else None
            db.add(
                FinancialEvent(
                    message_id=email_entity.message_id,
                    vendor=vendor[:255],
                    event_type=event_type,
                    amount=amount,
                    currency=currency,
                    renewal_date=renewal_dt,
                    status="ACTION_REQUIRED" if event_type == "PAYMENT_FAILED" else "RECORDED",
                )
            )

        # 3. Security & OAuth Radar Registry
        if email_entity.category == SmartCategory.SECURITY_OAUTH.value:
            service_name = (
                llm_result.oauth_app_name
                if (llm_result and llm_result.oauth_app_name)
                else self._extract_oauth_service_name(email_entity.subject, email_entity.snippet, email_entity.sender_email)
            )
            event_type = (
                llm_result.oauth_event_type
                if (llm_result and llm_result.oauth_event_type)
                else "OAUTH_OR_SIGNIN"
            )
            location = (
                llm_result.oauth_location_or_ip
                if (llm_result and llm_result.oauth_location_or_ip)
                else "New device / OAuth consent"
            )
            risk = (
                llm_result.oauth_risk_level
                if (llm_result and llm_result.oauth_risk_level)
                else ("CRITICAL" if email_entity.severity == SeverityLevel.P0_CRITICAL.value else "ELEVATED")
            )

            res = await db.execute(
                select(OAuthServiceRegistry).where(OAuthServiceRegistry.service_name == service_name)
            )
            reg = res.scalar_one_or_none()
            if reg:
                reg.last_seen_at = email_entity.internal_date or now
                reg.last_event_type = event_type
                reg.last_ip_or_location = location
                reg.source_message_id = email_entity.message_id
                reg.event_count = (reg.event_count or 1) + 1
            else:
                db.add(
                    OAuthServiceRegistry(
                        service_name=service_name,
                        first_seen_at=email_entity.internal_date or now,
                        last_seen_at=email_entity.internal_date or now,
                        last_event_type=event_type,
                        last_ip_or_location=location,
                        scopes_summary=email_entity.snippet[:250],
                        risk_level=risk,
                        source_message_id=email_entity.message_id,
                        event_count=1,
                    )
                )

    @staticmethod
    def _extract_oauth_service_name(subject: str, snippet: str, sender_email: str) -> str:
        text = f"{subject} {snippet}"
        match = re.search(
            r"(?:shared Google data with|access to your Google Account|signed in to|authorized)\s+([A-Za-z0-9._\- ]{2,35})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        domain = sender_email.split("@")[-1].split(".")[0]
        return domain.capitalize()

    async def _update_sender_stats(self, db: AsyncSession, email_entity: EmailMetadata) -> None:
        if email_entity.is_sent:
            return
        sender = email_entity.sender_email.lower().strip()
        domain = sender.split("@")[-1] if "@" in sender else sender
        res = await db.execute(select(SenderStat).where(SenderStat.sender_email == sender))
        stat = res.scalar_one_or_none()

        unsub_url = None
        if email_entity.unsubscribe_header:
            url_match = re.search(r"<(https?://[^>]+)>", email_entity.unsubscribe_header)
            if url_match:
                unsub_url = url_match.group(1)
            elif email_entity.unsubscribe_header.startswith("http"):
                unsub_url = email_entity.unsubscribe_header.strip()

        if stat is None:
            received = 1
            read = 1 if email_entity.is_read else 0
            noise = round(((received - read) / received) * 100.0, 2)
            stat = SenderStat(
                sender_email=sender,
                sender_domain=domain,
                sender_name=email_entity.sender_name,
                received_count=received,
                read_count=read,
                replied_count=0,
                noise_score=noise,
                has_list_unsubscribe=email_entity.has_unsubscribe,
                unsubscribe_url=unsub_url,
                first_received_at=email_entity.internal_date,
                last_received_at=email_entity.internal_date,
            )
            db.add(stat)
        else:
            stat.received_count += 1
            if email_entity.is_read:
                stat.read_count += 1
            if email_entity.has_unsubscribe:
                stat.has_list_unsubscribe = True
            if unsub_url:
                stat.unsubscribe_url = unsub_url
            last_dt = stat.last_received_at
            if last_dt and last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            curr_dt = email_entity.internal_date
            if curr_dt and curr_dt.tzinfo is None:
                curr_dt = curr_dt.replace(tzinfo=timezone.utc)
            if not last_dt or curr_dt > last_dt:
                stat.last_received_at = curr_dt
            unread_ratio = max(0, stat.received_count - stat.read_count) / max(1, stat.received_count)
            reply_penalty = 0.5 if stat.replied_count > 0 else 1.0
            stat.noise_score = round(unread_ratio * 100.0 * reply_penalty, 2)

    async def _index_email_embedding(self, db: AsyncSession, email_entity: EmailMetadata) -> None:
        chunk = (
            f"Subject: {email_entity.subject}\n"
            f"From: {email_entity.sender_name or ''} <{email_entity.sender_email}>\n"
            f"Category: {email_entity.category} | Severity: {email_entity.severity}\n"
            f"Summary: {email_entity.ai_summary or ''}\n"
            f"Content: {email_entity.body_text or email_entity.snippet}"
        )[:5000]
        vector = await self.llm.generate_embedding(chunk)
        existing_res = await db.execute(
            select(EmailEmbedding).where(EmailEmbedding.message_id == email_entity.message_id)
        )
        existing_emb = existing_res.scalar_one_or_none()
        if existing_emb:
            existing_emb.content_chunk = chunk
            existing_emb.embedding = vector
        else:
            db.add(
                EmailEmbedding(
                    message_id=email_entity.message_id,
                    thread_id=email_entity.thread_id,
                    category=email_entity.category,
                    content_chunk=chunk,
                    embedding=vector,
                )
            )
