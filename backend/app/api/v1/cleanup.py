from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.entities import CleanupAuditLog
from app.schemas.api_schemas import (
    CleanupAuditResponse,
    CleanupExecuteRequest,
    CleanupPreviewRequest,
    CleanupPreviewResponse,
    CustomBulkDeleteExecuteRequest,
    CustomBulkFilterRequest,
    CustomBulkPreviewResponse,
)
from app.services.cleanup_engine import SafeBulkCleanupEngine

router = APIRouter(prefix="/cleanup", tags=["Safe Bulk Cleanup & Custom Bulk Delete"])


@router.post("/dry-run", response_model=CleanupPreviewResponse)
async def dry_run_cleanup(
    payload: CleanupPreviewRequest, db: AsyncSession = Depends(get_db)
):
    engine = SafeBulkCleanupEngine()
    return await engine.preview_cleanup(db, payload)


@router.post("/execute", response_model=CleanupAuditResponse)
async def execute_cleanup(
    payload: CleanupExecuteRequest, db: AsyncSession = Depends(get_db)
):
    engine = SafeBulkCleanupEngine()
    audit = await engine.execute_cleanup(db, payload)
    return audit


@router.post("/custom/preview", response_model=CustomBulkPreviewResponse)
async def preview_custom_bulk_delete(
    payload: CustomBulkFilterRequest, db: AsyncSession = Depends(get_db)
):
    engine = SafeBulkCleanupEngine()
    return await engine.preview_custom_bulk_delete(db, payload)


@router.post("/custom/execute", response_model=CleanupAuditResponse)
async def execute_custom_bulk_delete(
    payload: CustomBulkDeleteExecuteRequest, db: AsyncSession = Depends(get_db)
):
    engine = SafeBulkCleanupEngine()
    return await engine.execute_custom_bulk_delete(db, payload)


@router.get("/audit-logs", response_model=List[CleanupAuditResponse])
async def list_cleanup_audit_logs(db: AsyncSession = Depends(get_db)):
    stmt = select(CleanupAuditLog).order_by(CleanupAuditLog.created_at.desc()).limit(50)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


@router.post("/undo/{batch_id}", response_model=CleanupAuditResponse)
async def undo_cleanup(batch_id: str, db: AsyncSession = Depends(get_db)):
    engine = SafeBulkCleanupEngine()
    try:
        return await engine.undo_cleanup_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sync-trashed-to-gmail")
async def sync_trashed_messages_to_gmail(db: AsyncSession = Depends(get_db)):
    """Ensures all messages marked is_trashed=True in the local DB are moved to TRASH in the official Gmail app."""
    from app.models.entities import EmailMetadata
    from app.services.gmail_client import GmailServiceClient

    rows = (
        await db.execute(
            select(EmailMetadata.message_id).where(EmailMetadata.is_trashed.is_(True))
        )
    ).scalars().all()
    trashed_ids = [mid for mid in rows if not mid.startswith(("msg_", "sim_"))]
    if not trashed_ids:
        return {"synced_to_gmail_trash": 0}

    gmail = GmailServiceClient()
    processed = await gmail.batch_modify_messages(
        db=db,
        message_ids=trashed_ids,
        add_label_ids=["TRASH"],
        remove_label_ids=["INBOX", "UNREAD"],
    )
    return {"synced_to_gmail_trash": processed}
