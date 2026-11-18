import asyncio
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable
from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.models.entities import (
    DeadlineItem,
    EmailMetadata,
    OAuthServiceRegistry,
    SeverityLevel,
)
from app.schemas.api_schemas import (
    CleanupExecuteRequest,
    CleanupPreviewRequest,
    RagQueryRequest,
)
from app.services.cleanup_engine import SafeBulkCleanupEngine
from app.services.intelligence import IntelligenceModulesService
from app.services.rag_service import SemanticEmailRAGService, build_gmail_thread_url

logger = get_logger("telegram_bot")


def require_authorized_user(func: Callable):
    """Strictly restricts Telegram commands and callbacks to ALLOWED_TELEGRAM_USER_IDS."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        settings = get_settings()
        allowed = set(settings.allowed_telegram_ids)
        user = update.effective_user
        if not user or user.id not in allowed:
            logger.warning(
                "unauthorized_telegram_access_blocked",
                user_id=user.id if user else None,
                username=user.username if user else None,
            )
            if update.message:
                await update.message.reply_text("⛔ Access Denied: Unauthorized Telegram User ID.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Access Denied", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


@require_authorized_user
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        intel = IntelligenceModulesService()
        st = await intel.get_dashboard_status(db)

    msg = (
        "📬 *Personal Intelligent Email OS — Health Status*\n\n"
        f"• *Total Active Emails:* `{st.total_emails}`\n"
        f"• *Unread Messages:* `{st.unread_emails}`\n"
        f"• *Active P0 Critical Incidents:* `{st.active_p0_incidents}` 🚨\n"
        f"• *Upcoming Action SLA Deadlines:* `{st.upcoming_deadlines_count}` ⏳\n"
        f"• *Ghosted Sent Threads (>72h):* `{st.ghosted_threads_count}` 👻\n"
        f"• *Dead Subscriptions Flagged:* `{st.dead_subscriptions_count}` 🔕\n"
        f"• *OAuth Apps in Exposure Map:* `{st.oauth_apps_count}` 🔐\n"
        f"• *Gmail API Connected:* `{'Yes' if st.gmail_connected else 'Local/Demo Mode'}`\n"
        f"• *Next Scheduled Cleanup:* `{st.next_scheduled_cleanup}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


@require_authorized_user
async def cmd_p0(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        p0_stmt = (
            select(EmailMetadata)
            .where(
                EmailMetadata.is_trashed.is_(False),
                EmailMetadata.severity == SeverityLevel.P0_CRITICAL.value,
            )
            .order_by(EmailMetadata.internal_date.desc())
            .limit(10)
        )
        p0_emails = list((await db.execute(p0_stmt)).scalars().all())

        dl_stmt = (
            select(DeadlineItem)
            .where(DeadlineItem.is_completed.is_(False))
            .order_by(DeadlineItem.deadline_at.asc())
            .limit(10)
        )
        deadlines = list((await db.execute(dl_stmt)).scalars().all())

    lines = ["🚨 *Active P0 Critical Alerts & Upcoming SLA Deadlines*\n"]
    if not p0_emails:
        lines.append("✅ No active P0 critical incidents.")
    else:
        lines.append("*P0 Critical Incidents:*")
        for idx, em in enumerate(p0_emails, start=1):
            url = build_gmail_thread_url(em.thread_id)
            lines.append(
                f"{idx}. *{em.subject}*\n"
                f"   From: `{em.sender_email}` | Category: `{em.category}`\n"
                f"   [Open in Gmail]({url})"
            )

    lines.append("\n⏳ *Upcoming Action SLA Deadlines:*")
    if not deadlines:
        lines.append("✅ No pending deadlines.")
    else:
        for idx, dl in enumerate(deadlines, start=1):
            url = build_gmail_thread_url(dl.thread_id)
            lines.append(
                f"{idx}. *{dl.title}*\n"
                f"   Due: `{dl.deadline_at.strftime('%Y-%m-%d %H:%M UTC')}` — [Thread]({url})"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_authorized_user
async def cmd_cleanup_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    before_dt = datetime.now(timezone.utc) - timedelta(days=30)
    date_arg = "default_30d"
    if context.args:
        raw_arg = context.args[0].strip()
        try:
            parsed = datetime.fromisoformat(raw_arg)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            before_dt = parsed
            date_arg = parsed.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid date format. Use ISO format `YYYY-MM-DD`, e.g., `/cleanup_preview 2026-10-01`",
                parse_mode="Markdown",
            )
            return

    async with AsyncSessionLocal() as db:
        engine = SafeBulkCleanupEngine()
        preview = await engine.preview_cleanup(
            db,
            CleanupPreviewRequest(before_date=before_dt, include_expired_ttl=True),
        )

    cat_lines = [
        f"• `{c.category}`: *{c.count}* msgs ({round(c.bytes_freed / 1024, 1)} KB)"
        for c in preview.categories
    ] or ["• No eligible messages to trash."]

    report = (
        "🧹 *Safe Bulk Cleanup — Dry-Run Preview*\n\n"
        f"• *Cutoff Date:* `{preview.cutoff_date.strftime('%Y-%m-%d %H:%M UTC')}`\n"
        f"• *Candidate Messages:* `{preview.total_candidate_messages}`\n"
        f"• *Estimated Storage Freed:* `{preview.estimated_mb_freed} MB`\n"
        f"• *Active Thread Shield Protected:* `{preview.shielded_active_threads_count}`\n"
        f"• *Protected Labels Shielded:* `{preview.shielded_protected_labels_count}`\n\n"
        "*Breakdown by Category:*\n" + "\n".join(cat_lines)
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=f"🗑️ Confirm Move to Trash ({preview.total_candidate_messages} msgs)",
                    callback_data=f"confirm_cleanup:{date_arg}",
                )
            ]
        ]
    )
    await update.message.reply_text(report, parse_mode="Markdown", reply_markup=keyboard)


@require_authorized_user
async def callback_confirm_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Executing safe bulk cleanup...")
    data = query.data or ""
    date_part = data.split(":", 1)[1] if ":" in data else "default_30d"

    if date_part == "default_30d":
        before_dt = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        before_dt = datetime.fromisoformat(date_part).replace(tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        engine = SafeBulkCleanupEngine()
        audit = await engine.execute_cleanup(
            db,
            CleanupExecuteRequest(before_date=before_dt, include_expired_ttl=True),
        )

    await query.edit_message_text(
        f"✅ *Cleanup Batch Executed Successfully*\n\n"
        f"• *Batch Audit ID:* `{audit.batch_id}`\n"
        f"• *Moved to Trash:* `{audit.total_messages}` messages\n"
        f"• *Status:* `{audit.status}`\n\n"
        f"To restore these messages within 30 days, run:\n`/undo {audit.batch_id}`",
        parse_mode="Markdown",
    )


@require_authorized_user
async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: `/undo <batch_id>`", parse_mode="Markdown")
        return
    batch_id = context.args[0].strip()

    async with AsyncSessionLocal() as db:
        engine = SafeBulkCleanupEngine()
        try:
            audit = await engine.undo_cleanup_batch(db, batch_id)
            await update.message.reply_text(
                f"♻️ *Batch Restored Successfully*\n"
                f"• *Batch ID:* `{audit.batch_id}`\n"
                f"• *Restored Messages:* `{audit.total_messages}`\n"
                f"• *Status:* `{audit.status}`",
                parse_mode="Markdown",
            )
        except ValueError as exc:
            await update.message.reply_text(f"❌ {str(exc)}")


@require_authorized_user
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: `/ask <your question in English or Arabic>`", parse_mode="Markdown"
        )
        return
    question = " ".join(context.args).strip()

    async with AsyncSessionLocal() as db:
        rag = SemanticEmailRAGService()
        res = await rag.query(db, RagQueryRequest(question=question, top_k=4))

    await update.message.reply_text(res.answer[:4000], parse_mode="Markdown")


@require_authorized_user
async def cmd_oauth_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        stmt = select(OAuthServiceRegistry).order_by(OAuthServiceRegistry.last_seen_at.desc())
        apps = list((await db.execute(stmt)).scalars().all())

    if not apps:
        await update.message.reply_text("🔐 No third-party OAuth services detected yet.")
        return

    lines = ["🔐 *OAuth & Account Exposure Map*\n"]
    for idx, app in enumerate(apps, start=1):
        lines.append(
            f"{idx}. *{app.service_name}* (`{app.risk_level}`)\n"
            f"   • Event: `{app.last_event_type}` | Count: `{app.event_count}`\n"
            f"   • First Seen: `{app.first_seen_at.strftime('%Y-%m-%d')}` | Last Location: `{app.last_ip_or_location or 'N/A'}`"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_authorized_user
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        intel = IntelligenceModulesService()
        res = await intel.generate_and_archive_weekly_digest(db, send_telegram=False)

    await update.message.reply_text(res["summary_markdown"][:4000], parse_mode="Markdown")


def build_telegram_application() -> Application:
    settings = get_settings()
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("p0", cmd_p0))
    application.add_handler(CommandHandler("cleanup_preview", cmd_cleanup_preview))
    application.add_handler(CommandHandler("undo", cmd_undo))
    application.add_handler(CommandHandler("ask", cmd_ask))
    application.add_handler(CommandHandler("oauth_map", cmd_oauth_map))
    application.add_handler(CommandHandler("digest", cmd_digest))
    application.add_handler(
        CallbackQueryHandler(callback_confirm_cleanup, pattern=r"^confirm_cleanup:")
    )
    return application


async def run_bot() -> None:
    configure_logging()
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN.startswith("1234567890:"):
        logger.warning(
            "telegram_bot_token_placeholder_detected_idling",
            info="Set a real TELEGRAM_BOT_TOKEN in .env to enable live Telegram polling.",
        )
        while True:
            await asyncio.sleep(3600)

    app = build_telegram_application()
    logger.info("starting_telegram_command_center", allowed_users=settings.allowed_telegram_ids)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    stop_event = asyncio.Event()
    await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(run_bot())
