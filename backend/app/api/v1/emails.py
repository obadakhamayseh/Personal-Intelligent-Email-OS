import asyncio
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.models.entities import EmailMetadata, SeverityLevel
from app.schemas.api_schemas import (
    EmailCreateInput,
    EmailListResponse,
    EmailResponse,
)
from app.services.classifier import HybridClassificationEngine
from app.services.rag_service import build_gmail_thread_url
from app.services.scheduler_jobs import get_sync_progress, run_gmail_sync_job

router = APIRouter(prefix="/emails", tags=["Emails"])


def _enrich_email_response(entity: EmailMetadata) -> EmailResponse:
    resp = EmailResponse.model_validate(entity)
    resp.gmail_link = build_gmail_thread_url(entity.thread_id)
    return resp


async def _run_full_sync_background() -> None:
    async with AsyncSessionLocal() as db:
        await run_gmail_sync_job(db, max_fetch=None)


@router.get("/sync/progress")
async def get_gmail_sync_progress():
    return get_sync_progress()


@router.post("/sync")
async def trigger_gmail_sync(background_tasks: BackgroundTasks):
    prog = get_sync_progress()
    if not prog.get("is_running"):
        background_tasks.add_task(_run_full_sync_background)
    return {
        "status": "STARTED",
        "progress": get_sync_progress(),
    }


@router.get("", response_model=EmailListResponse)
async def list_emails(
    category: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    starred_only: bool = Query(default=False),
    sent_only: bool = Query(default=False),
    trashed_only: bool = Query(default=False),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EmailMetadata)
    if trashed_only:
        stmt = stmt.where(EmailMetadata.is_trashed.is_(True))
    else:
        stmt = stmt.where(EmailMetadata.is_trashed.is_(False))

    if category:
        stmt = stmt.where(EmailMetadata.category == category)
    if severity:
        stmt = stmt.where(EmailMetadata.severity == severity)
    if starred_only:
        stmt = stmt.where(EmailMetadata.is_starred.is_(True))
    if sent_only:
        stmt = stmt.where(EmailMetadata.is_sent.is_(True))
    if unread_only:
        stmt = stmt.where(EmailMetadata.is_read.is_(False))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                EmailMetadata.subject.ilike(pattern),
                EmailMetadata.snippet.ilike(pattern),
                EmailMetadata.sender_email.ilike(pattern),
                EmailMetadata.sender_name.ilike(pattern),
                EmailMetadata.ai_summary.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    unread_count = (
        await db.execute(
            select(func.count(EmailMetadata.message_id)).where(
                EmailMetadata.is_trashed.is_(False), EmailMetadata.is_read.is_(False)
            )
        )
    ).scalar() or 0

    p0_count = (
        await db.execute(
            select(func.count(EmailMetadata.message_id)).where(
                EmailMetadata.is_trashed.is_(False),
                EmailMetadata.severity == SeverityLevel.P0_CRITICAL.value,
            )
        )
    ).scalar() or 0

    rows = (
        await db.execute(
            stmt.order_by(EmailMetadata.internal_date.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    return EmailListResponse(
        total=total,
        unread_count=unread_count,
        p0_count=p0_count,
        items=[_enrich_email_response(r) for r in rows],
    )


@router.get("/{message_id}", response_model=EmailResponse)
async def get_email_detail(message_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EmailMetadata).where(EmailMetadata.message_id == message_id))
    entity = res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    return _enrich_email_response(entity)


@router.post("/ingest", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)
async def ingest_and_classify_email(
    payload: EmailCreateInput, db: AsyncSession = Depends(get_db)
):
    engine = HybridClassificationEngine()
    entity, _ = await engine.ingest_and_classify(db, payload)
    return _enrich_email_response(entity)


@router.patch("/{message_id}/state", response_model=EmailResponse)
async def update_email_state(
    message_id: str,
    is_read: Optional[bool] = None,
    is_starred: Optional[bool] = None,
    is_trashed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.gmail_client import GmailServiceClient

    res = await db.execute(select(EmailMetadata).where(EmailMetadata.message_id == message_id))
    entity = res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    gmail = GmailServiceClient()
    add_labels = []
    remove_labels = []

    if is_read is not None:
        entity.is_read = is_read
        if is_read:
            remove_labels.append("UNREAD")
        else:
            add_labels.append("UNREAD")

    if is_starred is not None:
        entity.is_starred = is_starred
        if is_starred:
            add_labels.append("STARRED")
        else:
            remove_labels.append("STARRED")

    if is_trashed is not None:
        entity.is_trashed = is_trashed
        await gmail.trash_single_message(db, message_id, trash=is_trashed)

    if add_labels or remove_labels:
        await gmail.modify_single_message_labels(
            db, message_id, add_labels=add_labels, remove_labels=remove_labels
        )

    await db.commit()
    await db.refresh(entity)
    return _enrich_email_response(entity)
