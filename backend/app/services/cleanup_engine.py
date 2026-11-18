import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import (
    CleanupAuditLog,
    EmailMetadata,
    LifecycleTTL,
    PROTECTED_CATEGORIES,
    SeverityLevel,
    SmartCategory,
)
from app.schemas.api_schemas import (
    CleanupAuditResponse,
    CleanupCategoryStat,
    CleanupExecuteRequest,
    CleanupPreviewRequest,
    CleanupPreviewResponse,
    CustomBulkDeleteExecuteRequest,
    CustomBulkFilterRequest,
    CustomBulkMessageItem,
    CustomBulkPreviewResponse,
)
from app.services.gmail_client import GmailServiceClient

logger = get_logger("cleanup_engine")


class SafeBulkCleanupEngine:
    """
    High-Scale Safe Bulk Cleanup Engine capable of trashing tens of thousands of old emails
    with mandatory safety shields:
    1. Active Thread Shield: Never trash a message older than cutoff T if the thread's newest
       message is newer than T.
    2. Protected Labels Shield: Never auto-delete STARRED, AI/Financial-Leakage,
       AI/Security-OAuth-Radar (except AI/Ephemeral-SelfDestruct OTPs), or P0_CRITICAL
       unless explicitly overridden.
    3. Two-Stage Deletion + Audit Log + Checkpointing: Moves to TRASH in 1,000-ID chunks,
       records full metadata in `cleanup_audit_logs`, and supports 1-click Undo/Restore.
    """

    def __init__(self, gmail_client: Optional[GmailServiceClient] = None):
        self.gmail = gmail_client or GmailServiceClient()

    async def compute_candidates(
        self,
        db: AsyncSession,
        before_date: Optional[datetime] = None,
        categories: Optional[List[SmartCategory]] = None,
        include_expired_ttl: bool = True,
        override_protected: bool = False,
    ) -> Tuple[datetime, List[EmailMetadata], int, int]:
        now = datetime.now(timezone.utc)
        cutoff = before_date or (now - timedelta(days=30))
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        # Step 1: Compute per-thread maximum internal_date across ALL non-trashed messages
        thread_max_stmt = (
            select(
                EmailMetadata.thread_id,
                func.max(EmailMetadata.internal_date).label("newest_date"),
            )
            .where(EmailMetadata.is_trashed.is_(False))
            .group_by(EmailMetadata.thread_id)
        )
        thread_rows = (await db.execute(thread_max_stmt)).all()
        thread_newest_map: Dict[str, datetime] = {}
        for tid, max_dt in thread_rows:
            if max_dt is not None:
                if max_dt.tzinfo is None:
                    max_dt = max_dt.replace(tzinfo=timezone.utc)
                thread_newest_map[tid] = max_dt

        # Step 2: Load non-trashed candidate pool
        stmt = select(EmailMetadata).where(EmailMetadata.is_trashed.is_(False))
        if categories:
            cat_values = [c.value if isinstance(c, SmartCategory) else str(c) for c in categories]
            stmt = stmt.where(EmailMetadata.category.in_(cat_values))

        all_emails: List[EmailMetadata] = list((await db.execute(stmt)).scalars().all())

        eligible: List[EmailMetadata] = []
        shielded_active_threads = 0
        shielded_protected = 0

        for msg in all_emails:
            msg_dt = msg.internal_date
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)

            exp_dt = msg.expires_at
            if exp_dt and exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)

            is_older_than_cutoff = msg_dt <= cutoff
            is_ephemeral_expired = bool(
                include_expired_ttl
                and msg.category == SmartCategory.EPHEMERAL.value
                and exp_dt is not None
                and exp_dt <= now
            )

            if not (is_older_than_cutoff or is_ephemeral_expired):
                continue

            # Shield 2: Protected Labels & Critical Severity Shield
            if not override_protected:
                if (
                    msg.is_starred
                    or msg.ttl_policy == LifecycleTTL.NEVER_DELETE.value
                    or msg.severity == SeverityLevel.P0_CRITICAL.value
                    or msg.category in PROTECTED_CATEGORIES
                ):
                    shielded_protected += 1
                    continue

            # Shield 1: Active Thread Shield
            # If the message is being evaluated against cutoff T, ensure the newest message
            # in the entire thread is also older than cutoff T.
            newest_in_thread = thread_newest_map.get(msg.thread_id, msg_dt)
            if newest_in_thread > cutoff and not is_ephemeral_expired:
                shielded_active_threads += 1
                continue

            eligible.append(msg)

        return cutoff, eligible, shielded_active_threads, shielded_protected

    async def preview_cleanup(
        self, db: AsyncSession, req: CleanupPreviewRequest
    ) -> CleanupPreviewResponse:
        cutoff, eligible, shielded_threads, shielded_protected = await self.compute_candidates(
            db=db,
            before_date=req.before_date,
            categories=req.categories,
            include_expired_ttl=req.include_expired_ttl,
            override_protected=req.override_protected,
        )

        cat_groups: Dict[str, List[EmailMetadata]] = defaultdict(list)
        total_bytes = 0
        for msg in eligible:
            cat_groups[msg.category].append(msg)
            total_bytes += msg.size_estimate or 2048

        cat_stats: List[CleanupCategoryStat] = []
        for cat, items in sorted(cat_groups.items(), key=lambda x: len(x[1]), reverse=True):
            cat_bytes = sum(i.size_estimate or 2048 for i in items)
            samples = [i.subject for i in items[:5]]
            cat_stats.append(
                CleanupCategoryStat(
                    category=cat,
                    count=len(items),
                    bytes_freed=cat_bytes,
                    sample_subjects=samples,
                )
            )

        return CleanupPreviewResponse(
            cutoff_date=cutoff,
            total_candidate_messages=len(eligible),
            estimated_bytes_freed=total_bytes,
            estimated_mb_freed=round(total_bytes / (1024 * 1024), 3),
            shielded_active_threads_count=shielded_threads,
            shielded_protected_labels_count=shielded_protected,
            categories=cat_stats,
            candidate_message_ids=[m.message_id for m in eligible],
        )

    async def execute_cleanup(
        self, db: AsyncSession, req: CleanupExecuteRequest
    ) -> CleanupAuditLog:
        cutoff, eligible, _, _ = await self.compute_candidates(
            db=db,
            before_date=req.before_date,
            categories=req.categories,
            include_expired_ttl=req.include_expired_ttl,
            override_protected=req.override_protected,
        )

        batch_id = f"cln_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        total_bytes = sum(m.size_estimate or 2048 for m in eligible)
        category_breakdown: Dict[str, int] = defaultdict(int)
        affected_records: List[Dict[str, Any]] = []

        for m in eligible:
            category_breakdown[m.category] += 1
            affected_records.append(
                {
                    "message_id": m.message_id,
                    "thread_id": m.thread_id,
                    "subject": m.subject,
                    "sender": m.sender_email,
                    "category": m.category,
                    "rule_id": m.matched_rule_id,
                }
            )

        audit_log = CleanupAuditLog(
            batch_id=batch_id,
            execution_mode="TRASH_BATCH",
            cutoff_date=cutoff,
            total_messages=len(eligible),
            estimated_bytes_freed=total_bytes,
            category_breakdown=dict(category_breakdown),
            affected_messages_json=affected_records,
            checkpoint_offset=0,
            status="IN_PROGRESS" if eligible else "COMPLETED",
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)

        if not eligible:
            return audit_log

        msg_ids = [m.message_id for m in eligible]
        msg_by_id = {m.message_id: m for m in eligible}

        async def _checkpoint_callback(processed_count: int, chunk_ids: List[str]) -> None:
            for cid in chunk_ids:
                item = msg_by_id.get(cid)
                if item:
                    item.is_trashed = True
                    if "TRASH" not in (item.gmail_labels or []):
                        item.gmail_labels = list(item.gmail_labels or []) + ["TRASH"]
            audit_log.checkpoint_offset = processed_count
            await db.commit()

        await self.gmail.batch_modify_messages(
            db=db,
            message_ids=msg_ids,
            add_label_ids=["TRASH"],
            remove_label_ids=["INBOX"],
            on_chunk_complete=_checkpoint_callback,
        )

        audit_log.status = "COMPLETED"
        await db.commit()
        await db.refresh(audit_log)
        return audit_log

    async def undo_cleanup_batch(
        self, db: AsyncSession, batch_id: str
    ) -> CleanupAuditLog:
        """Restores all trashed messages from a specific cleanup audit batch."""
        res = await db.execute(
            select(CleanupAuditLog).where(CleanupAuditLog.batch_id == batch_id)
        )
        audit = res.scalar_one_or_none()
        if not audit:
            raise ValueError(f"Cleanup batch '{batch_id}' not found")

        affected_ids = [
            entry["message_id"]
            for entry in (audit.affected_messages_json or [])
            if "message_id" in entry
        ]

        if affected_ids:
            await self.gmail.batch_modify_messages(
                db=db,
                message_ids=affected_ids,
                add_label_ids=["INBOX"],
                remove_label_ids=["TRASH"],
            )
            stmt = select(EmailMetadata).where(EmailMetadata.message_id.in_(affected_ids))
            emails = list((await db.execute(stmt)).scalars().all())
            for em in emails:
                em.is_trashed = False
                em.gmail_labels = [lbl for lbl in (em.gmail_labels or []) if lbl != "TRASH"]

        audit.status = "RESTORED"
        audit.restored_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(audit)
        return audit

    async def filter_custom_bulk_messages(
        self, db: AsyncSession, flt: CustomBulkFilterRequest
    ) -> List[EmailMetadata]:
        """
        Direct User-Controlled Bulk Filter:
        Strictly obeys the user's chosen date range, categories, severities, sender, and keywords
        WITHOUT imposing forced importance shields. The user is in 100% control.
        """
        from sqlalchemy import or_

        stmt = select(EmailMetadata).where(EmailMetadata.is_trashed.is_(False))

        if flt.before_date is not None:
            b_dt = flt.before_date
            if b_dt.tzinfo is None:
                b_dt = b_dt.replace(tzinfo=timezone.utc)
            stmt = stmt.where(EmailMetadata.internal_date <= b_dt)

        if flt.after_date is not None:
            a_dt = flt.after_date
            if a_dt.tzinfo is None:
                a_dt = a_dt.replace(tzinfo=timezone.utc)
            stmt = stmt.where(EmailMetadata.internal_date >= a_dt)

        if flt.categories is not None:
            if len(flt.categories) == 0:
                return []
            stmt = stmt.where(EmailMetadata.category.in_(flt.categories))

        if flt.severities is not None:
            if len(flt.severities) == 0:
                return []
            stmt = stmt.where(EmailMetadata.severity.in_(flt.severities))

        if flt.sender_query and flt.sender_query.strip():
            sp = f"%{flt.sender_query.strip()}%"
            stmt = stmt.where(
                or_(
                    EmailMetadata.sender_email.ilike(sp),
                    EmailMetadata.sender_name.ilike(sp),
                )
            )

        if flt.keyword_query and flt.keyword_query.strip():
            kp = f"%{flt.keyword_query.strip()}%"
            stmt = stmt.where(
                or_(
                    EmailMetadata.subject.ilike(kp),
                    EmailMetadata.snippet.ilike(kp),
                )
            )

        if flt.unread_only is True:
            stmt = stmt.where(EmailMetadata.is_read.is_(False))
        elif flt.unread_only is False:
            stmt = stmt.where(EmailMetadata.is_read.is_(True))

        if flt.exclude_starred:
            stmt = stmt.where(EmailMetadata.is_starred.is_(False))

        stmt = stmt.order_by(EmailMetadata.internal_date.desc()).limit(flt.limit)
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)

    async def preview_custom_bulk_delete(
        self, db: AsyncSession, flt: CustomBulkFilterRequest
    ) -> CustomBulkPreviewResponse:
        matched = await self.filter_custom_bulk_messages(db, flt)
        total_bytes = sum(m.size_estimate or 2048 for m in matched)
        cat_counts: Dict[str, int] = defaultdict(int)
        sev_counts: Dict[str, int] = defaultdict(int)
        items: List[CustomBulkMessageItem] = []

        for m in matched:
            cat_counts[m.category] += 1
            sev_counts[m.severity] += 1
            items.append(
                CustomBulkMessageItem(
                    message_id=m.message_id,
                    thread_id=m.thread_id,
                    sender_email=m.sender_email,
                    sender_name=m.sender_name,
                    subject=m.subject,
                    internal_date=m.internal_date,
                    size_estimate=m.size_estimate or 2048,
                    category=m.category,
                    severity=m.severity,
                    is_read=m.is_read,
                    is_starred=m.is_starred,
                )
            )

        return CustomBulkPreviewResponse(
            total_matching=len(matched),
            estimated_bytes=total_bytes,
            estimated_mb=round(total_bytes / (1024 * 1024), 3),
            category_counts=dict(cat_counts),
            severity_counts=dict(sev_counts),
            messages=items,
        )

    async def execute_custom_bulk_delete(
        self, db: AsyncSession, req: CustomBulkDeleteExecuteRequest
    ) -> CleanupAuditLog:
        if req.message_ids is not None and len(req.message_ids) > 0:
            stmt = select(EmailMetadata).where(
                EmailMetadata.message_id.in_(req.message_ids),
                EmailMetadata.is_trashed.is_(False),
            )
            eligible = list((await db.execute(stmt)).scalars().all())
            cutoff_dt = datetime.now(timezone.utc)
        elif req.filter_criteria is not None:
            eligible = await self.filter_custom_bulk_messages(db, req.filter_criteria)
            cutoff_dt = req.filter_criteria.before_date or datetime.now(timezone.utc)
        else:
            eligible = []
            cutoff_dt = datetime.now(timezone.utc)

        batch_id = f"usr_del_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        total_bytes = sum(m.size_estimate or 2048 for m in eligible)
        category_breakdown: Dict[str, int] = defaultdict(int)
        affected_records: List[Dict[str, Any]] = []

        for m in eligible:
            category_breakdown[m.category] += 1
            affected_records.append(
                {
                    "message_id": m.message_id,
                    "thread_id": m.thread_id,
                    "subject": m.subject,
                    "sender": m.sender_email,
                    "category": m.category,
                    "severity": m.severity,
                }
            )

        audit_log = CleanupAuditLog(
            batch_id=batch_id,
            execution_mode="USER_DIRECT_BULK",
            cutoff_date=cutoff_dt,
            total_messages=len(eligible),
            estimated_bytes_freed=total_bytes,
            category_breakdown=dict(category_breakdown),
            affected_messages_json=affected_records,
            checkpoint_offset=0,
            status="IN_PROGRESS" if eligible else "COMPLETED",
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)

        if not eligible:
            return audit_log

        msg_ids = [m.message_id for m in eligible]
        msg_by_id = {m.message_id: m for m in eligible}

        async def _checkpoint_callback(processed_count: int, chunk_ids: List[str]) -> None:
            for cid in chunk_ids:
                item = msg_by_id.get(cid)
                if item:
                    item.is_trashed = True
                    if "TRASH" not in (item.gmail_labels or []):
                        item.gmail_labels = list(item.gmail_labels or []) + ["TRASH"]
            audit_log.checkpoint_offset = processed_count
            await db.commit()

        await self.gmail.batch_modify_messages(
            db=db,
            message_ids=msg_ids,
            add_label_ids=["TRASH"],
            remove_label_ids=["INBOX"],
            on_chunk_complete=_checkpoint_callback,
        )

        audit_log.status = "COMPLETED"
        await db.commit()
        await db.refresh(audit_log)
        return audit_log
