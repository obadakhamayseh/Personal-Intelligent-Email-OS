from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.agentic_ai import AgenticAIService

router = APIRouter(prefix="/agentic", tags=["Autonomous AI & Agentic Suite"])


class DraftReplyRequest(BaseModel):
    tone: str = "professional"  # professional | concise | followup_ghosted | polite_decline
    target_language: str = "auto"  # auto | ar | en
    custom_instructions: Optional[str] = None
    save_to_gmail_drafts: bool = False


class SaveGmailDraftRequest(BaseModel):
    draft_body: str


@router.post("/emails/{message_id}/draft-reply")
async def generate_persona_reply(
    message_id: str,
    payload: DraftReplyRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AgenticAIService()
    try:
        return await service.generate_persona_reply(
            db=db,
            message_id=message_id,
            tone=payload.tone,
            target_language=payload.target_language,
            custom_instructions=payload.custom_instructions,
            save_to_gmail_drafts=payload.save_to_gmail_drafts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/emails/{message_id}/save-gmail-draft")
async def save_reply_to_gmail_draft(
    message_id: str,
    payload: SaveGmailDraftRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AgenticAIService()
    try:
        return await service.save_reply_to_gmail_draft(
            db=db,
            message_id=message_id,
            draft_body=payload.draft_body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/emails/{message_id}/phishing-forensics")
async def analyze_email_phishing_forensics(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = AgenticAIService()
    try:
        return await service.analyze_phishing_forensics(db=db, message_id=message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/emails/{message_id}/calendar-extract")
async def extract_email_calendar_event(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = AgenticAIService()
    try:
        return await service.extract_calendar_event(db=db, message_id=message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/financial-burn-rate")
async def get_financial_burn_rate_analytics(db: AsyncSession = Depends(get_db)):
    service = AgenticAIService()
    return await service.get_financial_burn_rate_analytics(db=db)


@router.get("/analytics")
async def get_executive_inbox_analytics(db: AsyncSession = Depends(get_db)):
    service = AgenticAIService()
    return await service.get_executive_analytics(db=db)


class NaturalLanguageRuleRequest(BaseModel):
    prompt: str


@router.post("/rules/from-natural-language", status_code=status.HTTP_201_CREATED)
async def create_rule_from_natural_language(
    payload: NaturalLanguageRuleRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.api_schemas import ClassificationRuleResponse

    service = AgenticAIService()
    try:
        rule = await service.create_rule_from_natural_language(db, payload.prompt)
        return ClassificationRuleResponse.model_validate(rule)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
