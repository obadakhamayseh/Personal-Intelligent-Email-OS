from typing import List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.entities import DeadlineItem, FinancialEvent, OAuthServiceRegistry
from app.schemas.api_schemas import (
    DashboardStatusResponse,
    DeadlineResponse,
    FinancialEventResponse,
    OAuthServiceResponse,
    SenderStatResponse,
)
from app.services.intelligence import IntelligenceModulesService
from app.services.rag_service import build_gmail_thread_url

router = APIRouter(prefix="/intelligence", tags=["Advanced Intelligence Modules"])


class SenderActionInput(BaseModel):
    sender_email: str


@router.get("/status", response_model=DashboardStatusResponse)
async def get_inbox_status(db: AsyncSession = Depends(get_db)):
    service = IntelligenceModulesService()
    return await service.get_dashboard_status(db)


@router.get("/senders", response_model=List[SenderStatResponse])
async def get_sender_noise_scores(
    dead_only: bool = Query(default=False), db: AsyncSession = Depends(get_db)
):
    service = IntelligenceModulesService()
    return await service.get_sender_noise_report(db, dead_only=dead_only)


@router.post("/senders/auto-archive")
async def create_auto_archive_rule(
    payload: SenderActionInput, db: AsyncSession = Depends(get_db)
):
    service = IntelligenceModulesService()
    rule = await service.create_auto_archive_rule_for_sender(db, payload.sender_email)
    return {"status": "RULE_CREATED", "rule_id": rule.id, "rule_name": rule.name}


@router.post("/senders/unsubscribe")
async def unsubscribe_and_mute_sender(
    payload: SenderActionInput, db: AsyncSession = Depends(get_db)
):
    service = IntelligenceModulesService()
    return await service.unsubscribe_sender(db, payload.sender_email)


@router.get("/oauth-map", response_model=List[OAuthServiceResponse])
async def get_oauth_exposure_map(db: AsyncSession = Depends(get_db)):
    stmt = select(OAuthServiceRegistry).order_by(OAuthServiceRegistry.last_seen_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    out: List[OAuthServiceResponse] = []
    for r in rows:
        item = OAuthServiceResponse.model_validate(r)
        item.gmail_link = build_gmail_thread_url(r.source_message_id)
        out.append(item)
    return out


@router.get("/deadlines", response_model=List[DeadlineResponse])
async def list_upcoming_deadlines(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(DeadlineItem)
        .where(DeadlineItem.is_completed.is_(False))
        .order_by(DeadlineItem.deadline_at.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: List[DeadlineResponse] = []
    for r in rows:
        item = DeadlineResponse.model_validate(r)
        item.gmail_link = build_gmail_thread_url(r.thread_id)
        out.append(item)
    return out


@router.get("/financial", response_model=List[FinancialEventResponse])
async def list_financial_events(db: AsyncSession = Depends(get_db)):
    stmt = select(FinancialEvent).order_by(FinancialEvent.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [FinancialEventResponse.model_validate(r) for r in rows]


@router.post("/digest")
async def trigger_weekly_digest(db: AsyncSession = Depends(get_db)):
    service = IntelligenceModulesService()
    return await service.generate_and_archive_weekly_digest(db, send_telegram=True)
