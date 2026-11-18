import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.entities import LifecycleTTL, SeverityLevel, SmartCategory
from app.schemas.api_schemas import LLMClassificationResult

logger = get_logger("llm_provider")


CLASSIFICATION_SYSTEM_PROMPT = """You are the AI Semantic Classification Engine for a Personal Intelligent Email OS.
Analyze the incoming email (which may be in English or Arabic) and return a strict JSON object matching the schema.

Categories:
1. "AI/Ephemeral-SelfDestruct": OTPs, 2FA verification codes, magic login links, password reset codes. Default TTL: TTL_24H.
2. "AI/Security-OAuth-Radar": New sign-ins, OAuth app authorizations ("shared Google data with..."), 2FA modifications. Extract oauth_app_name, oauth_event_type, oauth_location_or_ip.
3. "AI/Infra-Incidents": Cloud/DevOps alerts (Vercel, Render, Neon, Supabase, Cloudflare, Namecheap, DigitalOcean, AWS, Oracle). Assign P0_CRITICAL for deploy failures, domain expiration, DB suspension/deletion, billing suspension; assign P2_NORMAL or P3_NOISE for successful builds or routine usage recaps.
4. "AI/Financial-Leakage": Receipts (Google Play, PayPal, Stripe), failed payment alerts (Netflix, Spotify), trial-ending warnings, refunds, upcoming auto-renewals. TTL MUST be NEVER_DELETE. Extract monetary_amount, currency, renewal_date, vendor_name, financial_event_type.
5. "AI/Action-SLA": Emails requiring user action with a countdown/deadline (quizzes, live sessions, support replies needed, domain restoration). Extract deadline_at and deadline_title.
6. "AI/Waiting-On-Ghosted": Outbound follow-up required threads.
7. "AI/Study-Training": Academic, LMS (Google Classroom, Coursera), hackathons, scholarships, training programs.
8. "AI/Knowledge-Digest": Tech changelogs, engineering blogs, high-signal newsletters. Default TTL: ARCHIVE_ONLY.
9. "AI/Promotions-Noise": Marketing offers, promotional blasts, discounts. Default TTL: TTL_30D, Severity: P3_NOISE.

Always write `ai_summary` as a concise 1-sentence summary in the SAME language as the email (Arabic if the email is in Arabic, English if in English).
"""


class LLMProviderService:
    """
    Unified LLM & Embedding layer supporting:
    - Primary: Google Gemini API (structured JSON responseSchema + text-embedding-004)
    - Fallback 1: OpenAI-compatible API (structured json_object + embeddings)
    - Fallback 2: Deterministic bilingual heuristic analyzer + hashing embeddings (when API keys are absent or offline)
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.dimension = self.settings.EMBEDDING_DIMENSION

    def _has_real_gemini_key(self) -> bool:
        key = self.settings.GEMINI_API_KEY
        return bool(key and not key.startswith("your-"))

    def _has_real_openai_key(self) -> bool:
        key = self.settings.OPENAI_API_KEY
        return bool(key and not key.startswith("your-"))

    async def classify_email(
        self,
        sender_email: str,
        subject: str,
        snippet: str,
        body_text: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> LLMClassificationResult:
        user_prompt = (
            f"Sender: {sender_email}\n"
            f"Subject: {subject}\n"
            f"Snippet: {snippet}\n"
            f"Headers: {json.dumps(headers or {}, ensure_ascii=False)}\n"
            f"Body:\n{body_text[:4000]}"
        )

        if self.settings.PRIMARY_LLM_PROVIDER.lower() == "gemini" and self._has_real_gemini_key():
            try:
                return await self._classify_with_gemini(user_prompt)
            except Exception as exc:
                logger.warning("gemini_classification_failed_trying_fallback", error=str(exc))

        if self._has_real_openai_key():
            try:
                return await self._classify_with_openai(user_prompt)
            except Exception as exc:
                logger.warning("openai_classification_failed_using_local_semantic", error=str(exc))

        return self._local_bilingual_semantic_fallback(sender_email, subject, snippet, body_text)

    async def _classify_with_gemini(self, user_prompt: str) -> LLMClassificationResult:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.GEMINI_MODEL}:generateContent?key={self.settings.GEMINI_API_KEY}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": CLASSIFICATION_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json)
            return LLMClassificationResult.model_validate(parsed)

    async def _classify_with_openai(self, user_prompt: str) -> LLMClassificationResult:
        url = f"{self.settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.OPENAI_MODEL,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_json = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_json)
            return LLMClassificationResult.model_validate(parsed)

    def _local_bilingual_semantic_fallback(
        self, sender_email: str, subject: str, snippet: str, body_text: str
    ) -> LLMClassificationResult:
        """
        Deterministic bilingual (Arabic + English) semantic analyzer ensuring 100% reliability
        even when external LLM APIs are unreachable or unconfigured.
        """
        combined = f"{subject} {snippet} {body_text}".lower()
        is_arabic = bool(re.search(r"[\u0600-\u06FF]", combined))
        now = datetime.now(timezone.utc)

        # 1. Ephemeral OTP / 2FA (English + Arabic)
        if re.search(
            r"\b(otp|verification code|security code|magic link|login code|رمز التحقق|كود التفعيل|كلمة مرور لمرة واحدة)\b",
            combined,
        ):
            summary = (
                f"رمز تحقق أو رابط تسجيل دخول مؤقت: {subject[:80]}"
                if is_arabic
                else f"Temporary verification code or sign-in link: {subject[:80]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.EPHEMERAL,
                severity=SeverityLevel.P2_NORMAL,
                ttl_policy=LifecycleTTL.TTL_24H,
                ai_summary=summary,
            )

        # 2. Security & OAuth Radar
        if re.search(
            r"(shared google data with|new sign-in|oauth|authorized access|third-party access|تسجيل دخول جديد|تم منح صلاحية|تنبيه أمني)",
            combined,
        ):
            app_match = re.search(r"(?:with|to|for|لتطبيق)\s+([A-Za-z0-9._\- ]{2,30})", f"{subject} {snippet}")
            app_name = app_match.group(1).strip() if app_match else sender_email.split("@")[0].capitalize()
            summary = (
                f"تنبيه أمني خاص بصلاحيات الدخول أو OAuth لتطبيق {app_name}."
                if is_arabic
                else f"Security or OAuth authorization alert detected for {app_name}."
            )
            return LLMClassificationResult(
                category=SmartCategory.SECURITY_OAUTH,
                severity=SeverityLevel.P1_HIGH,
                ttl_policy=LifecycleTTL.NEVER_DELETE,
                ai_summary=summary,
                oauth_app_name=app_name,
                oauth_event_type="OAUTH_GRANT" if "oauth" in combined or "shared" in combined else "NEW_SIGN_IN",
                oauth_location_or_ip="Detected via Security Alert",
                oauth_risk_level="ELEVATED",
            )

        # 3. Infra & Cloud Incidents
        if re.search(
            r"(vercel|render|neon|supabase|cloudflare|namecheap|digitalocean|aws|oracle|deployment|database|domain)",
            combined + " " + sender_email.lower(),
        ):
            is_critical = bool(
                re.search(
                    r"(failed|error|critical|expired|suspension|deletion|outage|down|فشل|خطأ حرج|انتهاء نطاق)",
                    combined,
                )
            )
            summary = (
                f"{'حادث بنية تحتية حرج' if is_critical else 'إشعار بنية تحتية روتيني'}: {subject[:80]}"
                if is_arabic
                else f"{'Critical infrastructure failure' if is_critical else 'Routine infrastructure notification'}: {subject[:80]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.INFRA_INCIDENTS,
                severity=SeverityLevel.P0_CRITICAL if is_critical else SeverityLevel.P2_NORMAL,
                ttl_policy=LifecycleTTL.NEVER_DELETE if is_critical else LifecycleTTL.TTL_14D,
                ai_summary=summary,
            )

        # 4. Financial & Subscriptions
        if re.search(
            r"(receipt|invoice|payment failed|renewal|trial ending|refund|google play|paypal|netflix|stripe|فاتورة|إيصال|فشل الدفع|تجديد الاشتراك|استرداد)",
            combined,
        ):
            amount_match = re.search(r"(?:\$|usd|eur|egp|sar|ريال|جنيه)\s*(\d+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)\s*(?:usd|eur|egp|sar)", combined)
            amount = None
            if amount_match:
                raw_val = amount_match.group(1) or amount_match.group(2)
                amount = float(raw_val) if raw_val else None
            is_failed = "failed" in combined or "فشل الدفع" in combined
            event_type = "PAYMENT_FAILED" if is_failed else ("TRIAL_ENDING" if "trial" in combined else "RECEIPT")
            vendor = sender_email.split("@")[-1].split(".")[0].capitalize()
            summary = (
                f"معاملة مالية ({event_type}) من {vendor}: {subject[:75]}"
                if is_arabic
                else f"Financial event ({event_type}) from {vendor}: {subject[:75]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.FINANCIAL_LEAKAGE,
                severity=SeverityLevel.P0_CRITICAL if is_failed else SeverityLevel.P1_HIGH,
                ttl_policy=LifecycleTTL.NEVER_DELETE,
                ai_summary=summary,
                monetary_amount=amount,
                currency="USD",
                renewal_date=now + timedelta(days=7) if "trial" in combined or "renewal" in combined else None,
                financial_event_type=event_type,
                vendor_name=vendor,
            )

        # 5. Action SLA / Deadlines
        if re.search(
            r"(deadline|due by|action required|respond within|quiz|live session|موعد نهائي|مطلوب إجراء|قبل تاريخ|امتحان|اختبار)",
            combined,
        ):
            summary = (
                f"يتطلب إجراء قبل الموعد النهائي: {subject[:80]}"
                if is_arabic
                else f"Action required before upcoming SLA deadline: {subject[:80]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.ACTION_SLA,
                severity=SeverityLevel.P1_HIGH,
                ttl_policy=LifecycleTTL.TTL_30D,
                ai_summary=summary,
                deadline_at=now + timedelta(hours=48),
                deadline_title=subject[:120] or "Pending Action SLA",
            )

        # 6. Study & Training
        if re.search(
            r"(classroom|hackathon|scholarship|course|lecture|assignment|university|منحة|دورة تدريبية|محاضرة|هاكاثون|واجب دراسي)",
            combined,
        ):
            summary = (
                f"تحديث تعليمي أو تدريبي: {subject[:80]}"
                if is_arabic
                else f"Academic or training program update: {subject[:80]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.STUDY_TRAINING,
                severity=SeverityLevel.P2_NORMAL,
                ttl_policy=LifecycleTTL.TTL_60D,
                ai_summary=summary,
            )

        # 7. Knowledge Digest
        if re.search(
            r"(changelog|digest|newsletter|weekly roundup|release notes|نشرة بريدية|ملخص أسبوعي)",
            combined,
        ):
            summary = (
                f"نشرة معرفية وتقنية للتلخيص الأسبوعي: {subject[:80]}"
                if is_arabic
                else f"Knowledge newsletter queued for weekly executive digest: {subject[:80]}"
            )
            return LLMClassificationResult(
                category=SmartCategory.KNOWLEDGE_DIGEST,
                severity=SeverityLevel.P2_NORMAL,
                ttl_policy=LifecycleTTL.ARCHIVE_ONLY,
                ai_summary=summary,
            )

        # Default: Promotions & Noise
        summary = (
            f"رسالة ترويجية أو عامة: {subject[:80]}"
            if is_arabic
            else f"Promotional or general notification email: {subject[:80]}"
        )
        return LLMClassificationResult(
            category=SmartCategory.PROMOTIONS_NOISE,
            severity=SeverityLevel.P3_NOISE,
            ttl_policy=LifecycleTTL.TTL_30D,
            ai_summary=summary,
        )

    async def generate_embedding(self, text: str) -> List[float]:
        clean_text = (text or "").strip()[:6000]
        if not clean_text:
            return [0.0] * self.dimension

        if self._has_real_gemini_key():
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/"
                    f"{self.settings.GEMINI_EMBEDDING_MODEL}:embedContent?key={self.settings.GEMINI_API_KEY}"
                )
                payload = {
                    "model": self.settings.GEMINI_EMBEDDING_MODEL,
                    "content": {"parts": [{"text": clean_text}]},
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    values = resp.json()["embedding"]["values"]
                    return self._normalize_dim(values)
            except Exception as exc:
                logger.warning("gemini_embedding_failed_using_fallback", error=str(exc))

        if self._has_real_openai_key():
            try:
                url = f"{self.settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"
                headers = {"Authorization": f"Bearer {self.settings.OPENAI_API_KEY}"}
                payload = {
                    "model": self.settings.OPENAI_EMBEDDING_MODEL,
                    "input": clean_text,
                    "dimensions": self.dimension,
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    values = resp.json()["data"][0]["embedding"]
                    return self._normalize_dim(values)
            except Exception as exc:
                logger.warning("openai_embedding_failed_using_deterministic_vector", error=str(exc))

        return self._deterministic_semantic_vector(clean_text)

    def _normalize_dim(self, vec: List[float]) -> List[float]:
        if len(vec) == self.dimension:
            return vec
        if len(vec) > self.dimension:
            return vec[: self.dimension]
        return vec + [0.0] * (self.dimension - len(vec))

    def _deterministic_semantic_vector(self, text: str) -> List[float]:
        """
        Feature-hashing token n-gram embedding (768-dim L2-normalized) so semantic cosine similarity
        works reliably in offline/local environments and unit tests without external API keys.
        """
        vec = [0.0] * self.dimension
        tokens = re.findall(r"[\w\u0600-\u06FF]{2,}", text.lower())
        if not tokens:
            tokens = ["empty"]
        for idx, token in enumerate(tokens):
            grams = [token]
            if idx + 1 < len(tokens):
                grams.append(f"{token}_{tokens[idx + 1]}")
            for gram in grams:
                digest = hashlib.sha256(gram.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if (digest[4] % 2 == 0) else -1.0
                vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]

    async def synthesize_rag_answer(
        self, question: str, context_blocks: List[Dict[str, Any]]
    ) -> str:
        is_arabic = bool(re.search(r"[\u0600-\u06FF]", question))
        if not context_blocks:
            return (
                "لم يتم العثور على رسائل بريد إلكتروني مطابقة لسؤالك في قاعدة البيانات الدلالية."
                if is_arabic
                else "No matching emails were found in the semantic knowledge base for your query."
            )

        formatted_ctx = "\n\n".join(
            [
                f"[{i+1}] Subject: {c['subject']} | From: {c['sender_email']} | Date: {c['internal_date']}\n"
                f"Thread Link: {c['gmail_thread_url']}\n"
                f"Summary/Content: {c['snippet']}"
                for i, c in enumerate(context_blocks)
            ]
        )
        prompt = (
            f"Question: {question}\n\n"
            f"Relevant Emails:\n{formatted_ctx}\n\n"
            "Answer the user's question accurately in the SAME language as the question (Arabic or English), "
            "citing the exact subject, sender, and Gmail thread link for each referenced email."
        )

        if self._has_real_gemini_key():
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self.settings.GEMINI_MODEL}:generateContent?key={self.settings.GEMINI_API_KEY}"
                )
                payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as exc:
                logger.warning("gemini_rag_synthesis_failed", error=str(exc))

        lines = []
        if is_arabic:
            lines.append(f"بناءً على البحث الدلالي في بريدك الإلكتروني حول: «{question}»، إليك أهم النتائج الموثقة:")
            for i, c in enumerate(context_blocks, start=1):
                lines.append(
                    f"{i}. **{c['subject']}** (من `{c['sender_email']}` — الفئة: `{c['category']}`)\n"
                    f"   - الملخص: {c['snippet']}\n"
                    f"   - [فتح المحادثة في Gmail]({c['gmail_thread_url']})"
                )
        else:
            lines.append(f"Based on semantic search across your indexed emails for \"{question}\", here are the verified findings:")
            for i, c in enumerate(context_blocks, start=1):
                lines.append(
                    f"{i}. **{c['subject']}** (From `{c['sender_email']}` — Category: `{c['category']}`)\n"
                    f"   - Summary: {c['snippet']}\n"
                    f"   - [Open Thread in Gmail]({c['gmail_thread_url']})"
                )
        return "\n".join(lines)

    async def generate_bilingual_digest(self, emails: List[Dict[str, Any]]) -> str:
        if not emails:
            return "No unread AI/Knowledge-Digest emails pending summarization."

        bullets_en = []
        bullets_ar = []
        for idx, item in enumerate(emails[:5], start=1):
            subj = item.get("subject", "Tech Update")
            sender = item.get("sender_email", "newsletter")
            summary = item.get("ai_summary") or item.get("snippet", "")[:140]
            bullets_en.append(f"{idx}. **{subj}** (`{sender}`): {summary}")
            bullets_ar.append(f"{idx}. **{subj}** (`{sender}`): {summary}")

        return (
            "📚 **Weekly Knowledge Digest | الملخص المعرفي الأسبوعي**\n\n"
            "### 🌐 English Executive Summary (Top 5 Signals)\n"
            + "\n".join(bullets_en)
            + "\n\n### 🌍 الملخص التنفيذي بالعربية\n"
            + "\n".join(bullets_ar)
        )
