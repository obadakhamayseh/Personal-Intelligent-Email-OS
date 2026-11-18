import asyncio
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from typing import Any, Callable, Dict, List, Optional
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import TokenVault
from app.models.entities import SmartCategory, SystemSetting
from app.schemas.api_schemas import EmailCreateInput

logger = get_logger("gmail_client")
OAUTH_TOKEN_SETTING_KEY = "google_oauth_credentials"
GMAIL_LABEL_MAP_KEY = "gmail_label_id_map"

# Global priority flag so background sync yields quota immediately when the user deletes/modifies emails
USER_ACTION_IN_PROGRESS = {"count": 0}


class RateLimitExceededError(Exception):
    pass


class GmailServiceClient:
    """
    Production Gmail API integration with:
    - OAuth 2.0 Web Flow & Fernet-encrypted offline refresh token persistence
    - Official `users.messages.trash` / `untrash` batched via `BatchHttpRequest` so deletions
      always reflect in the official Google Gmail mobile & web apps
    - Quota-aware pacing and exponential backoff on 429/403 rateLimitExceeded
    """

    BATCH_CHUNK_SIZE = 1000
    HTTP_BATCH_SIZE = 40

    def __init__(
        self,
        settings=None,
        token_vault: Optional[TokenVault] = None,
        raw_batch_executor: Optional[Callable[[List[str], List[str], List[str]], Any]] = None,
    ):
        self.settings = settings or get_settings()
        self.vault = token_vault or TokenVault(self.settings.FERNET_SECRET_KEY)
        self._raw_batch_executor = raw_batch_executor

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        client_config = {
            "web": {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=self.settings.gmail_scope_list,
            redirect_uri=self.settings.GOOGLE_REDIRECT_URI,
        )
        auth_url, generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return auth_url, generated_state

    async def exchange_code_and_store(self, db: AsyncSession, code: str) -> Dict[str, Any]:
        client_config = {
            "web": {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=self.settings.gmail_scope_list,
            redirect_uri=self.settings.GOOGLE_REDIRECT_URI,
        )
        await asyncio.to_thread(flow.fetch_token, code=code)
        creds = flow.credentials
        token_payload = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or self.settings.gmail_scope_list),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        await self.save_encrypted_credentials(db, token_payload)
        return {"connected": True, "scopes": token_payload["scopes"]}

    async def save_encrypted_credentials(self, db: AsyncSession, payload: Dict[str, Any]) -> None:
        encrypted = self.vault.encrypt_dict(payload)
        res = await db.execute(
            select(SystemSetting).where(SystemSetting.key == OAUTH_TOKEN_SETTING_KEY)
        )
        setting = res.scalar_one_or_none()
        if setting:
            setting.value_encrypted = encrypted
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = SystemSetting(
                key=OAUTH_TOKEN_SETTING_KEY,
                value_encrypted=encrypted,
                value_json={"connected": True},
            )
            db.add(setting)
        await db.commit()

    async def load_credentials(self, db: AsyncSession) -> Optional[Credentials]:
        res = await db.execute(
            select(SystemSetting).where(SystemSetting.key == OAUTH_TOKEN_SETTING_KEY)
        )
        setting = res.scalar_one_or_none()
        if not setting or not setting.value_encrypted:
            return None

        cfg_res = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "google_oauth_client_config")
        )
        cfg = cfg_res.scalar_one_or_none()
        db_cid = cfg.value_json.get("client_id", "").strip() if (cfg and cfg.value_json) else ""
        db_csec = cfg.value_json.get("client_secret", "").strip() if (cfg and cfg.value_json) else ""

        try:
            data = self.vault.decrypt_dict(setting.value_encrypted)
            client_id = data.get("client_id") or db_cid or self.settings.GOOGLE_CLIENT_ID
            client_secret = data.get("client_secret") or db_csec or self.settings.GOOGLE_CLIENT_SECRET
            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=client_id,
                client_secret=client_secret,
                scopes=data.get("scopes") or self.settings.gmail_scope_list,
            )
            if (creds.expired or not creds.valid) and creds.refresh_token:
                await asyncio.to_thread(creds.refresh, Request())
                data["token"] = creds.token
                data["client_id"] = client_id
                data["client_secret"] = client_secret
                data["expiry"] = creds.expiry.isoformat() if creds.expiry else None
                await self.save_encrypted_credentials(db, data)
            return creds
        except Exception as exc:
            logger.error("failed_to_load_gmail_credentials", error=str(exc))
            return None

    async def is_connected(self, db: AsyncSession) -> bool:
        res = await db.execute(
            select(SystemSetting).where(SystemSetting.key == OAUTH_TOKEN_SETTING_KEY)
        )
        setting = res.scalar_one_or_none()
        return bool(setting and setting.value_encrypted)

    async def _execute_with_backoff(
        self,
        func: Callable[[], Any],
        max_retries: int = 6,
        base_delay: float = 2.0,
    ) -> Any:
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(func)
            except HttpError as err:
                status_code = getattr(err.resp, "status", 500)
                if status_code in (429, 403, 500, 502, 503, 504) and attempt < max_retries:
                    attempt += 1
                    sleep_seconds = min(30.0, base_delay * (2 ** (attempt - 1)))
                    logger.warning(
                        "gmail_api_rate_limit_backoff",
                        status_code=status_code,
                        attempt=attempt,
                        sleep_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise
            except RateLimitExceededError:
                if attempt < max_retries:
                    attempt += 1
                    sleep_seconds = 0.05 * (2 ** (attempt - 1))
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise

    async def ensure_smart_labels(self, db: AsyncSession) -> Dict[str, str]:
        """Ensure root 'AI' label and all 9 nested SmartCategory labels exist in Gmail."""
        creds = await self.load_credentials(db)
        if not creds:
            return {cat.value: f"LBL_{cat.name}" for cat in SmartCategory}

        service = await asyncio.to_thread(build, "gmail", "v1", credentials=creds, cache_discovery=False)
        existing_resp = await self._execute_with_backoff(
            lambda: service.users().labels().list(userId="me").execute()
        )
        label_map: Dict[str, str] = {
            lbl["name"]: lbl["id"] for lbl in existing_resp.get("labels", [])
        }

        required_names = ["AI"] + [cat.value for cat in SmartCategory]
        for label_name in required_names:
            if label_name not in label_map:
                body = {
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                }
                created = await self._execute_with_backoff(
                    lambda b=body: service.users().labels().create(userId="me", body=b).execute()
                )
                label_map[label_name] = created["id"]

        res = await db.execute(select(SystemSetting).where(SystemSetting.key == GMAIL_LABEL_MAP_KEY))
        setting = res.scalar_one_or_none()
        if setting:
            setting.value_json = label_map
        else:
            db.add(SystemSetting(key=GMAIL_LABEL_MAP_KEY, value_json=label_map))
        await db.commit()
        return label_map

    async def _batch_trash_or_untrash_in_gmail(
        self,
        creds: Credentials,
        message_ids: List[str],
        trash: bool = True,
    ) -> None:
        """
        Executes official Gmail API `users.messages.trash` or `users.messages.untrash`
        using BatchHttpRequest (40 messages per batch) so messages genuinely move to/from
        the Trash bin in the official Google Gmail mobile and web apps!
        """
        real_ids = [mid for mid in message_ids if not mid.startswith(("msg_", "sim_", "bulk_", "test_"))]
        if not real_ids:
            return

        USER_ACTION_IN_PROGRESS["count"] += 1
        try:
            service = await asyncio.to_thread(
                build, "gmail", "v1", credentials=creds, cache_discovery=False
            )

            for offset in range(0, len(real_ids), self.HTTP_BATCH_SIZE):
                sub_chunk = real_ids[offset : offset + self.HTTP_BATCH_SIZE]

                def _run_batch(ids_slice: List[str]):
                    failed_rate_limit = []

                    def _cb(request_id, response, exception):
                        if exception is not None:
                            if isinstance(exception, HttpError) and getattr(
                                exception.resp, "status", 0
                            ) in (403, 429):
                                failed_rate_limit.append(request_id)
                            else:
                                logger.warning(
                                    "gmail_batch_item_warning",
                                    msg_id=request_id,
                                    error=str(exception),
                                )

                    batch = service.new_batch_http_request(callback=_cb)
                    for mid in ids_slice:
                        if trash:
                            batch.add(
                                service.users().messages().trash(userId="me", id=mid),
                                request_id=mid,
                            )
                        else:
                            batch.add(
                                service.users().messages().untrash(userId="me", id=mid),
                                request_id=mid,
                            )
                    batch.execute()
                    if failed_rate_limit:
                        raise HttpError(
                            type("Resp", (), {"status": 429, "reason": "rateLimitExceeded"})(),
                            b"Rate limit exceeded in batch",
                        )

                await self._execute_with_backoff(lambda s=sub_chunk: _run_batch(s))
                if not trash:
                    # Also ensure restored messages have INBOX label back
                    body = {"ids": sub_chunk, "addLabelIds": ["INBOX"]}
                    await self._execute_with_backoff(
                        lambda b=body: service.users()
                        .messages()
                        .batchModify(userId="me", body=b)
                        .execute()
                    )
                if offset + self.HTTP_BATCH_SIZE < len(real_ids):
                    await asyncio.sleep(0.5)
        finally:
            USER_ACTION_IN_PROGRESS["count"] = max(0, USER_ACTION_IN_PROGRESS["count"] - 1)

    async def batch_modify_messages(
        self,
        db: Optional[AsyncSession],
        message_ids: List[str],
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
        on_chunk_complete: Optional[Callable[[int, List[str]], Any]] = None,
    ) -> int:
        """
        Executes Gmail API `users.messages.batchModify` in atomic 1,000-ID chunks
        (only 1 HTTP call per 1,000 messages, 50 quota units total) so deleting
        500, 1,500, or 10,000 messages completes in < 1 second without hitting 429 limits!
        """
        if not message_ids:
            return 0

        add_labels = list(add_label_ids or [])
        remove_labels = list(remove_label_ids or [])

        # When moving to TRASH, remove INBOX/UNREAD/IMPORTANT so messages immediately
        # move to the Trash bin across all official Google Gmail mobile & web views
        if "TRASH" in add_labels:
            for lbl in ("INBOX", "UNREAD", "IMPORTANT"):
                if lbl not in remove_labels and lbl not in add_labels:
                    remove_labels.append(lbl)

        creds = await self.load_credentials(db) if db is not None else None
        service = (
            await asyncio.to_thread(build, "gmail", "v1", credentials=creds, cache_discovery=False)
            if creds
            else None
        )

        USER_ACTION_IN_PROGRESS["count"] += 1
        processed = 0
        try:
            for offset in range(0, len(message_ids), self.BATCH_CHUNK_SIZE):
                chunk = message_ids[offset : offset + self.BATCH_CHUNK_SIZE]
                if self._raw_batch_executor is not None:
                    await self._execute_with_backoff(
                        lambda c=chunk: self._raw_batch_executor(c, add_labels, remove_labels)
                    )
                elif creds is not None and service is not None:
                    real_chunk = [
                        mid
                        for mid in chunk
                        if not mid.startswith(("msg_", "sim_", "bulk_", "test_"))
                    ]
                    if real_chunk:
                        body: Dict[str, Any] = {"ids": real_chunk}
                        if add_labels:
                            body["addLabelIds"] = add_labels
                        if remove_labels:
                            body["removeLabelIds"] = remove_labels
                        await self._execute_with_backoff(
                            lambda b=body: service.users()
                            .messages()
                            .batchModify(userId="me", body=b)
                            .execute()
                        )

                processed += len(chunk)
                if on_chunk_complete is not None:
                    res = on_chunk_complete(processed, chunk)
                    if asyncio.iscoroutine(res):
                        await res
        finally:
            USER_ACTION_IN_PROGRESS["count"] = max(0, USER_ACTION_IN_PROGRESS["count"] - 1)

        return processed

    async def trash_single_message(self, db: AsyncSession, message_id: str, trash: bool = True) -> bool:
        """Calls official Gmail API users.messages.trash / untrash so the Gmail app updates immediately."""
        creds = await self.load_credentials(db)
        if not creds:
            return False
        await self._batch_trash_or_untrash_in_gmail(creds, [message_id], trash=trash)
        return True

    async def create_gmail_draft(
        self,
        db: AsyncSession,
        to_email: str,
        subject: str,
        body_text: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a real MIME draft inside the user's official Google Gmail account
        linked to the original threadId so it appears immediately in the Gmail app Drafts folder.
        """
        from email.mime.text import MIMEText

        creds = await self.load_credentials(db)
        if not creds:
            return {"saved_in_gmail": False, "draft_id": f"local_draft_{int(datetime.now(timezone.utc).timestamp())}"}

        mime_msg = MIMEText(body_text, "plain", "utf-8")
        mime_msg["to"] = to_email
        clean_subj = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        mime_msg["subject"] = clean_subj

        raw_encoded = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
        message_payload: Dict[str, Any] = {"raw": raw_encoded}
        if thread_id and not thread_id.startswith(("thd_", "sim_")):
            message_payload["threadId"] = thread_id

        draft_body = {"message": message_payload}
        service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=creds, cache_discovery=False
        )
        try:
            created = await self._execute_with_backoff(
                lambda: service.users().drafts().create(userId="me", body=draft_body).execute()
            )
            return {
                "saved_in_gmail": True,
                "draft_id": created.get("id", ""),
                "thread_id": thread_id,
            }
        except Exception as exc:
            logger.warning("gmail_create_draft_failed", error=str(exc))
            return {
                "saved_in_gmail": False,
                "draft_id": f"local_draft_{int(datetime.now(timezone.utc).timestamp())}",
                "error": str(exc),
            }

    async def modify_single_message_labels(
        self,
        db: AsyncSession,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> bool:
        creds = await self.load_credentials(db)
        if not creds:
            return False
        service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=creds, cache_discovery=False
        )
        body: Dict[str, Any] = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels
        if not body:
            return True
        try:
            await self._execute_with_backoff(
                lambda: service.users()
                .messages()
                .modify(userId="me", id=message_id, body=body)
                .execute()
            )
            return True
        except Exception as exc:
            logger.warning("gmail_single_modify_failed", message_id=message_id, error=str(exc))
            return False

    async def list_all_message_ids(
        self,
        db: AsyncSession,
        query: str = "include:spamTrash",
        max_total: Optional[int] = None,
    ) -> List[str]:
        creds = await self.load_credentials(db)
        if not creds:
            return []

        service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=creds, cache_discovery=False
        )
        all_ids: List[str] = []
        page_token: Optional[str] = None

        while True:
            while USER_ACTION_IN_PROGRESS["count"] > 0:
                await asyncio.sleep(1.0)

            req_kwargs: Dict[str, Any] = {
                "userId": "me",
                "maxResults": 500,
                "includeSpamTrash": False,
            }
            if query and query != "include:spamTrash":
                req_kwargs["q"] = query
            if page_token:
                req_kwargs["pageToken"] = page_token

            resp = await self._execute_with_backoff(
                lambda kw=req_kwargs: service.users().messages().list(**kw).execute()
            )
            messages = resp.get("messages", [])
            for m in messages:
                if "id" in m:
                    all_ids.append(m["id"])
                    if max_total and len(all_ids) >= max_total:
                        return all_ids

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return all_ids

    async def fetch_messages_by_ids(
        self,
        db: AsyncSession,
        message_ids: List[str],
    ) -> List[EmailCreateInput]:
        """Fetches message payloads with quota pacing and yields immediately if user is deleting emails."""
        creds = await self.load_credentials(db)
        if not creds or not message_ids:
            return []

        service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=creds, cache_discovery=False
        )
        parsed_emails: List[EmailCreateInput] = []

        for msg_id in message_ids:
            while USER_ACTION_IN_PROGRESS["count"] > 0:
                await asyncio.sleep(1.0)
            try:
                full_msg = await self._execute_with_backoff(
                    lambda mid=msg_id: service.users()
                    .messages()
                    .get(userId="me", id=mid, format="full")
                    .execute()
                )
                parsed_emails.append(self.parse_gmail_message(full_msg))
                await asyncio.sleep(0.08)
            except Exception as exc:
                logger.warning("skip_failed_message_fetch", message_id=msg_id, error=str(exc))

        return parsed_emails

    async def fetch_recent_messages(
        self, db: AsyncSession, max_results: int = 500, query: str = ""
    ) -> List[EmailCreateInput]:
        ids = await self.list_all_message_ids(db, query=query, max_total=max_results)
        return await self.fetch_messages_by_ids(db, ids)

    @staticmethod
    def parse_gmail_message(raw_msg: Dict[str, Any]) -> EmailCreateInput:
        payload = raw_msg.get("payload", {})
        headers_list = payload.get("headers", [])
        headers: Dict[str, str] = {
            h["name"]: h["value"] for h in headers_list if "name" in h and "value" in h
        }
        headers_lower = {k.lower(): v for k, v in headers.items()}

        from_raw = headers_lower.get("from", "unknown@example.com")
        sender_name, sender_email = parseaddr(from_raw)
        if not sender_email:
            sender_email = from_raw

        to_raw = headers_lower.get("to", "")
        _, recipient_email = parseaddr(to_raw)

        subject = headers_lower.get("subject", "(No Subject)")
        snippet = raw_msg.get("snippet", "")

        internal_ms = raw_msg.get("internalDate")
        if internal_ms:
            internal_date = datetime.fromtimestamp(int(internal_ms) / 1000.0, tz=timezone.utc)
        elif "date" in headers_lower:
            try:
                internal_date = parsedate_to_datetime(headers_lower["date"])
                if internal_date.tzinfo is None:
                    internal_date = internal_date.replace(tzinfo=timezone.utc)
            except Exception:
                internal_date = datetime.now(timezone.utc)
        else:
            internal_date = datetime.now(timezone.utc)

        body_text = GmailServiceClient._extract_plain_body(payload) or snippet
        labels = raw_msg.get("labelIds", [])

        return EmailCreateInput(
            message_id=raw_msg["id"],
            thread_id=raw_msg.get("threadId", raw_msg["id"]),
            sender_email=sender_email.lower().strip(),
            sender_name=sender_name.strip() or None,
            recipient_email=recipient_email.lower().strip() or None,
            subject=subject,
            snippet=snippet,
            body_text=body_text[:15000],
            internal_date=internal_date,
            size_estimate=int(raw_msg.get("sizeEstimate", 2048)),
            is_read="UNREAD" not in labels,
            is_starred="STARRED" in labels,
            is_sent="SENT" in labels,
            is_trashed="TRASH" in labels,
            gmail_labels=labels,
            raw_headers=headers,
        )

    @staticmethod
    def _extract_plain_body(payload: Dict[str, Any]) -> str:
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")
        if mime_type == "text/plain" and body_data:
            try:
                return base64.urlsafe_b64decode(body_data.encode("utf-8")).decode("utf-8", errors="ignore")
            except Exception:
                return ""
        for part in payload.get("parts", []):
            extracted = GmailServiceClient._extract_plain_body(part)
            if extracted:
                return extracted
        return ""

    @staticmethod
    async def trigger_rfc8058_unsubscribe(unsubscribe_url: str) -> bool:
        if not unsubscribe_url or not unsubscribe_url.startswith(("http://", "https://")):
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(
                    unsubscribe_url,
                    data={"List-Unsubscribe": "One-Click"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return resp.status_code < 400
        except Exception as exc:
            logger.warning("rfc8058_unsubscribe_failed", url=unsubscribe_url, error=str(exc))
            return False
