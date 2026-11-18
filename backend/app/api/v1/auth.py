import os
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import (
    CleanupAuditLog,
    DeadlineItem,
    EmailEmbedding,
    EmailMetadata,
    FinancialEvent,
    OAuthServiceRegistry,
    SenderStat,
    SystemSetting,
)
from app.services.gmail_client import GmailServiceClient, OAUTH_TOKEN_SETTING_KEY
from app.services.scheduler_jobs import run_gmail_sync_job

router = APIRouter(prefix="/auth", tags=["Google OAuth 2.0"])
OAUTH_CLIENT_CONFIG_KEY = "google_oauth_client_config"


class GoogleOAuthConfigInput(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = "http://localhost:8000/api/v1/auth/google/callback"


async def _resolve_client_credentials(db: AsyncSession) -> GmailServiceClient:
    """Loads Google Client ID/Secret from DB override or .env settings."""
    settings = get_settings()
    client = GmailServiceClient(settings=settings)

    res = await db.execute(
        select(SystemSetting).where(SystemSetting.key == OAUTH_CLIENT_CONFIG_KEY)
    )
    cfg = res.scalar_one_or_none()
    if cfg and cfg.value_json:
        cid = cfg.value_json.get("client_id", "").strip()
        csec = cfg.value_json.get("client_secret", "").strip()
        ruri = cfg.value_json.get("redirect_uri", "").strip()
        if cid and csec:
            client.settings.GOOGLE_CLIENT_ID = cid
            client.settings.GOOGLE_CLIENT_SECRET = csec
        if ruri:
            client.settings.GOOGLE_REDIRECT_URI = ruri
    return client


@router.get("/google/status")
async def google_oauth_status(db: AsyncSession = Depends(get_db)):
    client = await _resolve_client_credentials(db)
    connected = await client.is_connected(db)
    configured = bool(
        client.settings.GOOGLE_CLIENT_ID
        and not client.settings.GOOGLE_CLIENT_ID.startswith("your-")
        and client.settings.GOOGLE_CLIENT_SECRET
        and not client.settings.GOOGLE_CLIENT_SECRET.startswith("your-")
    )
    return {
        "connected": connected,
        "configured": configured,
        "redirect_uri": client.settings.GOOGLE_REDIRECT_URI,
    }


@router.post("/google/configure")
async def save_google_oauth_config(
    payload: GoogleOAuthConfigInput,
    db: AsyncSession = Depends(get_db),
):
    cid = payload.client_id.strip()
    csec = payload.client_secret.strip()
    ruri = (
        payload.redirect_uri.strip()
        if payload.redirect_uri
        else "http://localhost:8000/api/v1/auth/google/callback"
    )
    if not cid or not csec:
        raise HTTPException(
            status_code=400, detail="Client ID and Client Secret are required"
        )

    res = await db.execute(
        select(SystemSetting).where(SystemSetting.key == OAUTH_CLIENT_CONFIG_KEY)
    )
    setting = res.scalar_one_or_none()
    data = {"client_id": cid, "client_secret": csec, "redirect_uri": ruri}
    if setting:
        setting.value_json = data
    else:
        db.add(SystemSetting(key=OAUTH_CLIENT_CONFIG_KEY, value_json=data))
    await db.commit()
    return {"configured": True, "redirect_uri": ruri}


@router.get("/google/url")
async def get_google_oauth_url(
    state: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    client = await _resolve_client_credentials(db)
    if (
        not client.settings.GOOGLE_CLIENT_ID
        or client.settings.GOOGLE_CLIENT_ID.startswith("your-")
        or not client.settings.GOOGLE_CLIENT_SECRET
        or client.settings.GOOGLE_CLIENT_SECRET.startswith("your-")
    ):
        raise HTTPException(
            status_code=400,
            detail="OAUTH_NOT_CONFIGURED: يرجى إدخال GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET.",
        )
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    auth_url, generated_state = client.get_authorization_url(state=state)
    return {"authorization_url": auth_url, "state": generated_state}


@router.get("/google/login")
async def redirect_to_google_oauth(db: AsyncSession = Depends(get_db)):
    client = await _resolve_client_credentials(db)
    if (
        not client.settings.GOOGLE_CLIENT_ID
        or client.settings.GOOGLE_CLIENT_ID.startswith("your-")
        or not client.settings.GOOGLE_CLIENT_SECRET
        or client.settings.GOOGLE_CLIENT_SECRET.startswith("your-")
    ):
        return RedirectResponse(url="http://localhost:3005/?oauth_setup=required")
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    auth_url, _ = client.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_oauth_callback(
    background_tasks: BackgroundTasks,
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from app.api.v1.emails import _run_full_sync_background
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    client = await _resolve_client_credentials(db)
    await client.exchange_code_and_store(db, code=code)
    await client.ensure_smart_labels(db)
    background_tasks.add_task(_run_full_sync_background)
    return RedirectResponse(url="http://localhost:3005/?connected=true")


@router.post("/google/disconnect")
async def disconnect_google_account(db: AsyncSession = Depends(get_db)):
    await db.execute(
        delete(SystemSetting).where(SystemSetting.key == OAUTH_TOKEN_SETTING_KEY)
    )
    await db.commit()
    return {"connected": False}


@router.delete("/purge-data")
async def purge_all_email_data(db: AsyncSession = Depends(get_db)):
    """Deletes all demo/cached email data so the inbox only holds live synced user emails."""
    await db.execute(delete(EmailEmbedding))
    await db.execute(delete(DeadlineItem))
    await db.execute(delete(FinancialEvent))
    await db.execute(delete(OAuthServiceRegistry))
    await db.execute(delete(SenderStat))
    await db.execute(delete(CleanupAuditLog))
    await db.execute(delete(EmailMetadata))
    await db.commit()
    return {"status": "PURGED"}
