import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.entities import (
    ClassificationRule,
    CleanupAuditLog,
    DeadlineItem,
    EmailMetadata,
    FinancialEvent,
    LifecycleTTL,
    OAuthServiceRegistry,
    SenderStat,
    SeverityLevel,
    SmartCategory,
)
from app.services.gmail_client import GmailServiceClient
from app.services.llm_provider import LLMProviderService
from app.services.rag_service import build_gmail_thread_url

logger = get_logger("agentic_ai")

HIGH_VALUE_BRANDS = {
    "google": ["google.com", "youtube.com", "gmail.com", "android.com"],
    "paypal": ["paypal.com", "paypal-communication.com"],
    "netflix": ["netflix.com"],
    "apple": ["apple.com", "icloud.com"],
    "microsoft": ["microsoft.com", "office.com", "live.com", "outlook.com", "github.com"],
    "amazon": ["amazon.com", "amazonaws.com", "aws.amazon.com"],
    "stripe": ["stripe.com"],
    "vercel": ["vercel.com"],
    "cloudflare": ["cloudflare.com"],
    "namecheap": ["namecheap.com"],
    "github": ["github.com"],
}


class AgenticAIService:
    """
    Autonomous AI & Agentic Intelligence Suite:
    1. AI Persona Reply Drafter + Official Gmail Draft Sync
    2. AI Phishing, Spoofing & Header Forensics Shield
    3. Subscription Burn-Rate & Financial Leakage Analytics Studio
    4. 1-Click Google Calendar & Meeting Extractor (.ics + Google Calendar Template URL)
    """

    def __init__(
        self,
        gmail_client: Optional[GmailServiceClient] = None,
        llm_service: Optional[LLMProviderService] = None,
    ):
        self.settings = get_settings()
        self.gmail = gmail_client or GmailServiceClient()
        self.llm = llm_service or LLMProviderService()

    # =========================================================================
    # 1. AI Persona Auto-Draft & Ghost-Reply Studio
    # =========================================================================
    async def generate_persona_reply(
        self,
        db: AsyncSession,
        message_id: str,
        tone: str = "professional",
        target_language: str = "auto",
        custom_instructions: Optional[str] = None,
        save_to_gmail_drafts: bool = False,
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == message_id)
        )
        email = res.scalar_one_or_none()
        if not email:
            raise ValueError("Email not found")

        # Learn user's writing style from their recent SENT emails
        sent_stmt = (
            select(EmailMetadata)
            .where(EmailMetadata.is_sent.is_(True))
            .order_by(EmailMetadata.internal_date.desc())
            .limit(5)
        )
        sent_samples = list((await db.execute(sent_stmt)).scalars().all())
        style_snippets = [
            f"- Subject: {s.subject} | Snippet: {(s.body_text or s.snippet)[:200]}"
            for s in sent_samples
        ]
        style_profile = (
            "\n".join(style_snippets)
            if style_snippets
            else "Clear, direct, respectful executive engineering communication."
        )

        combined_text = f"{email.subject} {email.snippet} {email.body_text}"
        is_arabic_email = bool(re.search(r"[\u0600-\u06FF]", combined_text))
        use_arabic = (
            True
            if target_language == "ar"
            else (False if target_language == "en" else is_arabic_email)
        )

        draft_text = await self._generate_reply_with_llm_or_template(
            email=email,
            tone=tone,
            use_arabic=use_arabic,
            style_profile=style_profile,
            custom_instructions=custom_instructions,
        )

        reply_subject = (
            email.subject
            if email.subject.lower().startswith("re:")
            else f"Re: {email.subject}"
        )

        gmail_draft_info = None
        if save_to_gmail_drafts:
            gmail_draft_info = await self.gmail.create_gmail_draft(
                db=db,
                to_email=email.sender_email,
                subject=reply_subject,
                body_text=draft_text,
                thread_id=email.thread_id,
            )

        return {
            "message_id": email.message_id,
            "thread_id": email.thread_id,
            "recipient_email": email.sender_email,
            "reply_subject": reply_subject,
            "tone": tone,
            "language": "ar" if use_arabic else "en",
            "draft_body": draft_text,
            "learned_from_sent_count": len(sent_samples),
            "gmail_draft": gmail_draft_info,
        }

    async def save_reply_to_gmail_draft(
        self,
        db: AsyncSession,
        message_id: str,
        draft_body: str,
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == message_id)
        )
        email = res.scalar_one_or_none()
        if not email:
            raise ValueError("Email not found")

        reply_subject = (
            email.subject
            if email.subject.lower().startswith("re:")
            else f"Re: {email.subject}"
        )
        return await self.gmail.create_gmail_draft(
            db=db,
            to_email=email.sender_email,
            subject=reply_subject,
            body_text=draft_body,
            thread_id=email.thread_id,
        )

    async def _generate_reply_with_llm_or_template(
        self,
        email: EmailMetadata,
        tone: str,
        use_arabic: bool,
        style_profile: str,
        custom_instructions: Optional[str],
    ) -> str:
        lang_label = "Arabic (العربية)" if use_arabic else "English"
        prompt = (
            f"You are an AI Executive Email Ghostwriter learning from the user's sent emails.\n"
            f"User's Writing Style Samples:\n{style_profile}\n\n"
            f"Incoming Email to Reply To:\n"
            f"From: {email.sender_name or email.sender_email} <{email.sender_email}>\n"
            f"Subject: {email.subject}\n"
            f"Content:\n{(email.body_text or email.snippet)[:2500]}\n\n"
            f"Requested Tone: {tone}\n"
            f"Output Language: {lang_label}\n"
            f"Additional Instructions: {custom_instructions or 'None'}\n\n"
            f"Write ONLY the ready-to-send email reply body (no markdown code fences, no subject line prefix)."
        )

        if self.llm._has_real_gemini_key():
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self.settings.GEMINI_MODEL}:generateContent?key={self.settings.GEMINI_API_KEY}"
                )
                payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip()
            except Exception as exc:
                logger.warning("gemini_reply_generation_fallback", error=str(exc))

        sender_display = email.sender_name or email.sender_email.split("@")[0]
        extra = f"\n\nملاحظة إضافية: {custom_instructions}" if (use_arabic and custom_instructions) else (
            f"\n\nNote: {custom_instructions}" if custom_instructions else ""
        )

        if use_arabic:
            if tone == "concise":
                return (
                    f"مرحباً {sender_display}،\n\n"
                    f"شكراً لتواصلك بخصوص «{email.subject}». تم استلام رسالتك والاطلاع على التفاصيل، وسأقوم باتخاذ الإجراء اللازم وموافاتك بالتحديث قريباً.{extra}\n\n"
                    f"مع خالص التحية"
                )
            if tone == "followup_ghosted":
                return (
                    f"مرحباً {sender_display}،\n\n"
                    f"أود المتابعة معك بخصوص رسالتي السابقة حول «{email.subject}». هل تسنّى لكم مراجعة التفاصيل؟ أرجو إفادتي بأي مستجدات لنتمكن من المضي قدماً.{extra}\n\n"
                    f"تحياتي"
                )
            if tone == "polite_decline":
                return (
                    f"مرحباً {sender_display}،\n\n"
                    f"أشكرك جزيلاً على تواصلك بخصوص «{email.subject}». نظراً لارتباطي بأولويات ومشاريع حالية، لن أتمكن من الالتزام بذلك في الوقت الراهن، وأتمنى أن نبقى على تواصل مستقبلاً.{extra}\n\n"
                    f"مع أطيب التمنيات"
                )
            return (
                f"الأستاذ/ة {sender_display} المحترم/ة،\n\n"
                f"تحية طيبة وبعد،\n\n"
                f"أشكركم على رسالتكم المتعلقة بـ «{email.subject}». لقد قمت بمراجعة النقاط الواردة بعناية، وأؤكد لكم العمل على المطلوب وفق الجدول الزمني المحدد. سأوافيكم بأي استفسارات أو تحديثات إضافية فور توفرها.{extra}\n\n"
                f"وتفضلوا بقبول فائق الاحترام والتقدير"
            )
        else:
            if tone == "concise":
                return (
                    f"Hi {sender_display},\n\n"
                    f"Thanks for reaching out regarding \"{email.subject}\". Received and noted — I'll review and follow up shortly.{extra}\n\n"
                    f"Best regards"
                )
            if tone == "followup_ghosted":
                return (
                    f"Hi {sender_display},\n\n"
                    f"I wanted to quickly follow up on our thread regarding \"{email.subject}\". Please let me know if you have any updates or if you need anything else from my side to move this forward.{extra}\n\n"
                    f"Best regards"
                )
            if tone == "polite_decline":
                return (
                    f"Hi {sender_display},\n\n"
                    f"Thank you for reaching out regarding \"{email.subject}\". Due to current bandwidth and schedule priorities, I won't be able to move forward with this right now, but I appreciate you thinking of me.{extra}\n\n"
                    f"Kind regards"
                )
            return (
                f"Hello {sender_display},\n\n"
                f"Thank you for your email regarding \"{email.subject}\". I have reviewed the details carefully and am on track with the next steps. Please let me know if there are any additional requirements I should be aware of.{extra}\n\n"
                f"Best regards"
            )

    # =========================================================================
    # 2. AI Phishing, Spoofing & Header Forensics Shield
    # =========================================================================
    async def analyze_phishing_forensics(
        self, db: AsyncSession, message_id: str
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == message_id)
        )
        email = res.scalar_one_or_none()
        if not email:
            raise ValueError("Email not found")

        headers_lower = {k.lower(): str(v) for k, v in (email.raw_headers or {}).items()}
        sender_email = (email.sender_email or "").lower().strip()
        sender_domain = sender_email.split("@")[-1] if "@" in sender_email else sender_email
        sender_name = (email.sender_name or "").lower().strip()

        auth_results = (
            headers_lower.get("authentication-results", "")
            + " "
            + headers_lower.get("arc-authentication-results", "")
        ).lower()

        return_path = headers_lower.get("return-path", "").lower()
        reply_to = headers_lower.get("reply-to", "").lower()

        trust_score = 95
        findings_ar: List[str] = []
        findings_en: List[str] = []

        # 1. Evaluate SPF / DKIM / DMARC
        spf_status = "PASS"
        dkim_status = "PASS"
        dmarc_status = "PASS"

        if "spf=fail" in auth_results or "spf=softfail" in auth_results:
            spf_status = "FAIL"
            trust_score -= 30
            findings_ar.append("⚠️ فشل التحقق من هوية خادم الإرسال (SPF Fail).")
            findings_en.append("⚠️ Sender Policy Framework (SPF) verification failed.")
        elif "spf=pass" not in auth_results and auth_results.strip():
            spf_status = "NEUTRAL"

        if "dkim=fail" in auth_results:
            dkim_status = "FAIL"
            trust_score -= 25
            findings_ar.append("⚠️ التوقيع الرقمي للرسالة غير صالح (DKIM Fail).")
            findings_en.append("⚠️ DKIM cryptographic signature check failed.")

        if "dmarc=fail" in auth_results:
            dmarc_status = "FAIL"
            trust_score -= 30
            findings_ar.append("🚨 فشل سياسة حماية النطاق (DMARC Fail — احتمال انتحال مرتفع).")
            findings_en.append("🚨 DMARC domain alignment failed (high spoofing probability).")

        # 2. Check Return-Path / Reply-To mismatch
        domain_alignment = "ALIGNED"
        if reply_to and "@" in reply_to and sender_domain not in reply_to:
            domain_alignment = "MISMATCH"
            trust_score -= 20
            findings_ar.append(
                f"⚠️ بريد الرد (Reply-To: {reply_to}) يختلف عن نطاق المرسل ({sender_domain})."
            )
            findings_en.append(
                f"⚠️ Reply-To address ({reply_to}) does not match sender domain ({sender_domain})."
            )

        # 3. Dynamic Self-Learning Brand & Universal Impersonation Detection
        # Dynamically learns all companies/brands the user interacts with from their own account
        dynamic_brand_domains: Dict[str, set[str]] = {
            k: set(v) for k, v in HIGH_VALUE_BRANDS.items()
        }

        sender_rows = (
            await db.execute(
                select(SenderStat.sender_name, SenderStat.sender_domain).where(
                    SenderStat.received_count >= 2
                )
            )
        ).all()
        for s_name, s_dom in sender_rows:
            if s_name and s_dom:
                brand_key = re.sub(
                    r"[^a-z0-9\u0600-\u06FF]", "", s_name.lower().split()[0]
                )
                if len(brand_key) >= 3:
                    dynamic_brand_domains.setdefault(brand_key, set()).add(
                        s_dom.lower()
                    )

        # (A) Check against all learned user brands + global brands
        for brand, valid_domains in dynamic_brand_domains.items():
            if len(brand) >= 3 and re.search(rf"\b{re.escape(brand)}\b", sender_name):
                if not any(
                    sender_domain == vd
                    or sender_domain.endswith(f".{vd}")
                    or vd.endswith(f".{sender_domain}")
                    or brand in sender_domain
                    for vd in valid_domains
                ):
                    trust_score -= 40
                    domain_alignment = "SPOOFED_BRAND"
                    findings_ar.append(
                        f"🚨 اشتباه انتحال شركة: الاسم الظاهر يدّعي أنه ({email.sender_name}) ولكن النطاق الفعلي ({sender_domain}) يختلف عن النطاق الرسمي المعتاد في حسابك!"
                    )
                    findings_en.append(
                        f"🚨 Brand Impersonation Alert: Display name '{email.sender_name}' does not match its verified domain in your account (sent from '{sender_domain}')."
                    )
                    break

        # (B) Universal Check: Display name embeds a fake email/domain different from actual sender_domain
        embedded_dom_match = re.search(
            r"([a-z0-9\-]+\.(?:com|net|org|io|ai|co|edu|gov|me|tech))",
            sender_name,
        )
        if embedded_dom_match:
            claimed_dom = embedded_dom_match.group(1).lower()
            if claimed_dom not in sender_domain and sender_domain not in claimed_dom:
                trust_score -= 45
                domain_alignment = "SPOOFED_DOMAIN_IN_NAME"
                findings_ar.append(
                    f"🚨 خداع في الاسم الظاهر: الاسم يحتوي على النطاق ({claimed_dom}) بينما البريد الحقيقي مرسل من ({sender_domain})!"
                )
                findings_en.append(
                    f"🚨 Deceptive Display Name: Name claims domain '{claimed_dom}' while actual sender domain is '{sender_domain}'!"
                )

        # (C) Universal Check: Corporate/Billing/Security claim sent from a free personal webmail provider
        free_webmail_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "mail.ru", "yandex.com"}
        if sender_domain in free_webmail_domains and re.search(
            r"\b(support|billing|security|official|bank|team|invoice|admin|الدعم الفني|الفواتير|الأمان|البنك)\b",
            sender_name,
            flags=re.IGNORECASE,
        ):
            trust_score -= 35
            domain_alignment = "FREE_WEBMAIL_CORPORATE_CLAIM"
            findings_ar.append(
                f"⚠️ تنبيه: المرسل يدّعي صفة رسمية ({email.sender_name}) ولكنه يرسل من بريد شخصي مجاني ({sender_domain}) وليس نطاق شركة!"
            )
            findings_en.append(
                f"⚠️ Corporate Claim on Free Webmail: Sender claims '{email.sender_name}' but uses free personal webmail ({sender_domain})."
            )

        # 4. Scan URLs in body_text & snippet
        body_blob = f"{email.subject} {email.snippet} {email.body_text}"
        urls = list(set(re.findall(r"https?://[^\s<>\"')]+", body_blob)))
        suspicious_urls: List[str] = []

        for u in urls[:15]:
            u_low = u.lower()
            if re.search(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", u_low):
                suspicious_urls.append(u)
                trust_score -= 30
                findings_ar.append(f"🚨 تم رصد رابط يستخدم عنوان IP رقمي مباشر بدلاً من نطاق رسمي: {u[:60]}")
                findings_en.append(f"🚨 Raw IP address URL detected instead of a domain: {u[:60]}")
            elif any(
                shortener in u_low
                for shortener in ("bit.ly/", "tinyurl.com/", "rb.gy/", "is.gd/", "cutt.ly/")
            ):
                suspicious_urls.append(u)
                trust_score -= 15
                findings_ar.append(f"⚠️ تم رصد رابط مختصر يخفي الوجهة الحقيقية: {u[:60]}")
                findings_en.append(f"⚠️ Obfuscated shortened URL detected: {u[:60]}")

        # 5. Urgent Credential Harvesting Keywords
        if re.search(
            r"(verify your password|confirm your identity immediately|account will be terminated|update your bank details|تحديث بياناتك البنكية|تأكيد كلمة المرور فوراً|سيتم إغلاق حسابك نهائياً)",
            body_blob.lower(),
        ):
            trust_score -= 20
            findings_ar.append("⚠️ تحتوي الرسالة على عبارات استعجال شائعة في هجمات التصيّد الاحتيالي.")
            findings_en.append("⚠️ Contains high-urgency credential harvesting phrasing.")

        trust_score = max(0, min(100, trust_score))
        if trust_score >= 80:
            risk_level = "SAFE"
            if not findings_ar:
                findings_ar.append("✅ النطاق والترويسات الأمنية سليمة ولا توجد مؤشرات انتحال أو روابط خبيثة.")
                findings_en.append("✅ Sender domain, headers, and embedded links passed forensic inspection.")
        elif trust_score >= 50:
            risk_level = "CAUTION"
        else:
            risk_level = "HIGH_RISK_PHISHING"

        return {
            "message_id": email.message_id,
            "sender_email": email.sender_email,
            "sender_domain": sender_domain,
            "trust_score": trust_score,
            "risk_level": risk_level,
            "spf_status": spf_status,
            "dkim_status": dkim_status,
            "dmarc_status": dmarc_status,
            "domain_alignment": domain_alignment,
            "extracted_urls_count": len(urls),
            "suspicious_urls": suspicious_urls,
            "findings_ar": findings_ar,
            "findings_en": findings_en,
        }

    # =========================================================================
    # 3. Financial Burn-Rate & Subscription Radar Studio
    # =========================================================================
    async def get_financial_burn_rate_analytics(
        self, db: AsyncSession
    ) -> Dict[str, Any]:
        stmt = (
            select(EmailMetadata)
            .where(
                EmailMetadata.is_trashed.is_(False),
                EmailMetadata.category == SmartCategory.FINANCIAL_LEAKAGE.value,
            )
            .order_by(EmailMetadata.internal_date.desc())
        )
        fin_emails = list((await db.execute(stmt)).scalars().all())
        if not fin_emails:
            stmt_all = (
                select(EmailMetadata)
                .where(EmailMetadata.category == SmartCategory.FINANCIAL_LEAKAGE.value)
                .order_by(EmailMetadata.internal_date.desc())
            )
            fin_emails = list((await db.execute(stmt_all)).scalars().all())

        fe_stmt = select(FinancialEvent).order_by(FinancialEvent.created_at.desc())
        fe_rows = list((await db.execute(fe_stmt)).scalars().all())
        fe_by_msg = {r.message_id: r for r in fe_rows}

        vendor_map: Dict[str, Dict[str, Any]] = {}
        total_recorded_usd = 0.0
        failed_payments_count = 0
        trials_ending_count = 0
        recent_transactions: List[Dict[str, Any]] = []

        for em in fin_emails:
            fe = fe_by_msg.get(em.message_id)
            amount, currency = self._extract_amount_and_currency(
                f"{em.subject} {em.snippet} {em.body_text}",
                fallback_amount=fe.amount if fe else None,
                fallback_currency=fe.currency if fe else "USD",
            )
            amount_usd = self._convert_to_usd(amount, currency)

            combined_low = f"{em.subject} {em.snippet}".lower()
            if any(w in combined_low for w in ("fail", "declined", "unable to process", "فشل الدفع", "مرفوض")):
                event_type = "PAYMENT_FAILED"
                failed_payments_count += 1
            elif any(w in combined_low for w in ("trial", "تجريبية", "ending soon", "auto-renew")):
                event_type = "TRIAL_ENDING"
                trials_ending_count += 1
            elif any(w in combined_low for w in ("refund", "استرداد")):
                event_type = "REFUND"
            else:
                event_type = fe.event_type if fe else "RECEIPT"

            vendor = self._clean_vendor_name(em.sender_name, em.sender_email)
            if amount_usd and event_type != "REFUND":
                total_recorded_usd += amount_usd

            if vendor not in vendor_map:
                vendor_map[vendor] = {
                    "vendor": vendor,
                    "sender_email": em.sender_email,
                    "emails_count": 0,
                    "total_spent_usd": 0.0,
                    "latest_amount": amount,
                    "currency": currency,
                    "latest_event_type": event_type,
                    "last_billed_at": em.internal_date.isoformat(),
                    "estimated_next_renewal": (
                        em.internal_date + timedelta(days=30)
                    ).isoformat(),
                    "gmail_link": build_gmail_thread_url(em.thread_id),
                }

            v_entry = vendor_map[vendor]
            v_entry["emails_count"] += 1
            if amount_usd:
                v_entry["total_spent_usd"] = round(
                    v_entry["total_spent_usd"] + amount_usd, 2
                )
                if not v_entry["latest_amount"]:
                    v_entry["latest_amount"] = amount
                    v_entry["currency"] = currency
            if event_type in ("PAYMENT_FAILED", "TRIAL_ENDING"):
                v_entry["latest_event_type"] = event_type

            recent_transactions.append(
                {
                    "message_id": em.message_id,
                    "thread_id": em.thread_id,
                    "vendor": vendor,
                    "subject": em.subject,
                    "event_type": event_type,
                    "amount": amount,
                    "currency": currency,
                    "amount_usd": amount_usd,
                    "date": em.internal_date.isoformat(),
                    "gmail_link": build_gmail_thread_url(em.thread_id),
                }
            )

        # Estimate monthly burn rate from active recurring vendors
        monthly_burn_usd = 0.0
        for v in vendor_map.values():
            if v["latest_amount"]:
                monthly_burn_usd += self._convert_to_usd(
                    v["latest_amount"], v["currency"]
                ) or 0.0
            elif v["total_spent_usd"] > 0:
                monthly_burn_usd += v["total_spent_usd"] / max(1, v["emails_count"])

        monthly_burn_usd = round(monthly_burn_usd, 2)
        annual_projected_usd = round(monthly_burn_usd * 12, 2)

        vendors_list = sorted(
            vendor_map.values(),
            key=lambda x: (
                x["latest_event_type"] == "PAYMENT_FAILED",
                x["total_spent_usd"],
                x["emails_count"],
            ),
            reverse=True,
        )

        return {
            "total_financial_emails": len(fin_emails),
            "active_vendors_count": len(vendors_list),
            "monthly_burn_usd": monthly_burn_usd,
            "annual_projected_usd": annual_projected_usd,
            "total_recorded_spend_usd": round(total_recorded_usd, 2),
            "failed_payments_count": failed_payments_count,
            "trials_ending_count": trials_ending_count,
            "vendors": vendors_list,
            "recent_transactions": recent_transactions[:30],
        }

    @staticmethod
    def _extract_amount_and_currency(
        text: str,
        fallback_amount: Optional[float] = None,
        fallback_currency: Optional[str] = "USD",
    ) -> tuple[Optional[float], str]:
        if fallback_amount is not None and fallback_amount > 0:
            return round(float(fallback_amount), 2), (fallback_currency or "USD").upper()

        patterns = [
            (r"\$\s*(\d{1,5}(?:\.\d{1,2})?)", "USD"),
            (r"(\d{1,5}(?:\.\d{1,2})?)\s*(usd|eur|gbp|sar|aed|egp|jod)", None),
            (r"(usd|eur|gbp|sar|aed|egp|jod)\s*(\d{1,5}(?:\.\d{1,2})?)", "PREFIX"),
            (r"(\d{1,5}(?:\.\d{1,2})?)\s*(?:دولار|ريال|درهم|جنيه)", "AR"),
        ]
        for pat, mode in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                try:
                    if mode == "USD":
                        return round(float(m.group(1)), 2), "USD"
                    elif mode == "PREFIX":
                        return round(float(m.group(2)), 2), m.group(1).upper()
                    elif mode == "AR":
                        val = round(float(m.group(1)), 2)
                        cur = "SAR" if "ريال" in m.group(0) else ("EGP" if "جنيه" in m.group(0) else "USD")
                        return val, cur
                    else:
                        return round(float(m.group(1)), 2), m.group(2).upper()
                except ValueError:
                    continue
        return None, (fallback_currency or "USD").upper()

    @staticmethod
    def _convert_to_usd(amount: Optional[float], currency: str) -> Optional[float]:
        if amount is None:
            return None
        rates = {
            "USD": 1.0,
            "EUR": 1.08,
            "GBP": 1.27,
            "SAR": 0.266,
            "AED": 0.272,
            "JOD": 1.41,
            "EGP": 0.020,
        }
        factor = rates.get(currency.upper(), 1.0)
        return round(amount * factor, 2)

    @staticmethod
    def _clean_vendor_name(sender_name: Optional[str], sender_email: str) -> str:
        if sender_name and len(sender_name.strip()) >= 2:
            cleaned = re.sub(r"(<[^>]+>|billing|support|no-reply|noreply)", "", sender_name, flags=re.IGNORECASE).strip(" -_\"'")
            if cleaned:
                return cleaned[:45]
        domain_part = sender_email.split("@")[-1].split(".")[0]
        return domain_part.capitalize()

    # =========================================================================
    # 4. 1-Click Google Calendar & Meeting Extractor (.ics + Template URL)
    # =========================================================================
    async def extract_calendar_event(
        self, db: AsyncSession, message_id: str
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(EmailMetadata).where(EmailMetadata.message_id == message_id)
        )
        email = res.scalar_one_or_none()
        if not email:
            raise ValueError("Email not found")

        dl_res = await db.execute(
            select(DeadlineItem).where(DeadlineItem.message_id == message_id).limit(1)
        )
        dl = dl_res.scalar_one_or_none()

        body_blob = f"{email.subject}\n{email.snippet}\n{email.body_text}"

        # Detect any Meeting URL (Google Meet, Zoom, MS Teams)
        meet_match = re.search(
            r"https?://(?:meet\.google\.com/[a-z0-9\-]+|[a-z0-9.\-]*zoom\.us/j/[^\s<>\"')]+|teams\.microsoft\.com/l/meetup-join/[^\s<>\"')]+)",
            body_blob,
            flags=re.IGNORECASE,
        )
        meeting_url = meet_match.group(0) if meet_match else None

        now = datetime.now(timezone.utc)
        if dl and dl.deadline_at:
            start_dt = dl.deadline_at
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        else:
            start_dt = (now + timedelta(days=1)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )

        end_dt = start_dt + timedelta(hours=1)
        title = dl.title if dl else email.subject
        location = meeting_url or email.sender_email
        gmail_url = build_gmail_thread_url(email.thread_id)
        description = (
            f"{email.ai_summary or email.snippet}\n\n"
            f"From: {email.sender_name or ''} <{email.sender_email}>\n"
            f"Gmail Thread: {gmail_url}"
        )
        if meeting_url:
            description = f"Meeting Link: {meeting_url}\n\n" + description

        fmt_start = start_dt.strftime("%Y%m%dT%H%M%SZ")
        fmt_end = end_dt.strftime("%Y%m%dT%H%M%SZ")

        gcal_url = (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote(title)}"
            f"&dates={fmt_start}/{fmt_end}"
            f"&details={quote(description[:1200])}"
            f"&location={quote(location)}"
        )

        clean_title = title.replace("\n", " ").replace("\r", " ")
        clean_desc = description[:800].replace("\r", "").replace("\n", "\\n")

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Personal Intelligent Email OS//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{email.message_id}@intelligent-email-os.local\r\n"
            f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"DTSTART:{fmt_start}\r\n"
            f"DTEND:{fmt_end}\r\n"
            f"SUMMARY:{clean_title}\r\n"
            f"LOCATION:{location}\r\n"
            f"DESCRIPTION:{clean_desc}\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        return {
            "message_id": email.message_id,
            "title": title,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "meeting_url": meeting_url,
            "location": location,
            "google_calendar_url": gcal_url,
            "ics_content": ics_content,
        }

    # =========================================================================
    # 5. Executive Inbox Analytics & Telemetry Dashboard
    # =========================================================================
    async def get_executive_analytics(self, db: AsyncSession) -> Dict[str, Any]:
        all_rows = list((await db.execute(select(EmailMetadata))).scalars().all())
        active_emails = [e for e in all_rows if not e.is_trashed]
        trashed_emails = [e for e in all_rows if e.is_trashed]

        active_bytes = sum(e.size_estimate or 2048 for e in active_emails)
        trashed_bytes = sum(e.size_estimate or 2048 for e in trashed_emails)

        # Also add bytes freed from audit logs
        audit_rows = list((await db.execute(select(CleanupAuditLog))).scalars().all())
        audit_freed_bytes = sum(
            a.estimated_bytes_freed or 0
            for a in audit_rows
            if a.status == "COMPLETED"
        )
        total_freed_bytes = max(trashed_bytes, audit_freed_bytes)

        tier1_count = sum(1 for e in all_rows if e.classified_by == "TIER1_RULE")
        tier2_count = sum(1 for e in all_rows if e.classified_by != "TIER1_RULE")
        total_classified = max(1, len(all_rows))
        tier1_ratio = round((tier1_count / total_classified) * 100.0, 1)

        # Estimated reading time saved: ~45 seconds saved per AI-summarized or auto-trashed noise email
        hours_saved = round((len(all_rows) * 40.0) / 3600.0, 1)

        cat_counts: Dict[str, int] = defaultdict(int)
        cat_bytes: Dict[str, int] = defaultdict(int)
        sev_counts: Dict[str, int] = defaultdict(int)
        day_of_week_counts: Dict[str, int] = {
            "Mon": 0,
            "Tue": 0,
            "Wed": 0,
            "Thu": 0,
            "Fri": 0,
            "Sat": 0,
            "Sun": 0,
        }
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        sender_agg: Dict[str, Dict[str, Any]] = {}
        chart_pool = active_emails if len(active_emails) > 0 else all_rows

        for e in chart_pool:
            cat_counts[e.category] += 1
            cat_bytes[e.category] += e.size_estimate or 2048
            sev_counts[e.severity] += 1

            dt = e.internal_date
            if dt:
                day_of_week_counts[day_names[dt.weekday()]] += 1

            s_key = e.sender_email.lower().strip()
            if s_key not in sender_agg:
                sender_agg[s_key] = {
                    "sender_email": s_key,
                    "sender_name": e.sender_name or s_key.split("@")[0],
                    "count": 0,
                    "unread_count": 0,
                    "total_bytes": 0,
                }
            sender_agg[s_key]["count"] += 1
            if not e.is_read:
                sender_agg[s_key]["unread_count"] += 1
            sender_agg[s_key]["total_bytes"] += e.size_estimate or 2048

        top_senders = sorted(
            sender_agg.values(),
            key=lambda x: (x["count"], x["total_bytes"]),
            reverse=True,
        )[:10]
        for ts in top_senders:
            ts["total_mb"] = round(ts["total_bytes"] / (1024 * 1024), 2)

        category_distribution = [
            {
                "category": cat,
                "count": cnt,
                "percentage": round((cnt / max(1, len(chart_pool))) * 100.0, 1),
                "size_mb": round(cat_bytes[cat] / (1024 * 1024), 2),
            }
            for cat, cnt in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        severity_distribution = [
            {
                "severity": sev,
                "count": cnt,
                "percentage": round((cnt / max(1, len(chart_pool))) * 100.0, 1),
            }
            for sev, cnt in sorted(sev_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "total_all_time_emails": len(all_rows),
            "active_inbox_emails": len(active_emails),
            "trashed_emails_count": len(trashed_emails),
            "active_storage_mb": round(active_bytes / (1024 * 1024), 2),
            "storage_freed_mb": round(total_freed_bytes / (1024 * 1024), 2),
            "estimated_hours_saved": hours_saved,
            "tier1_zero_cost_count": tier1_count,
            "tier2_llm_count": tier2_count,
            "tier1_efficiency_percent": tier1_ratio,
            "category_distribution": category_distribution,
            "severity_distribution": severity_distribution,
            "day_of_week_activity": [
                {"day": d, "count": c} for d, c in day_of_week_counts.items()
            ],
            "top_senders": top_senders,
        }

    # =========================================================================
    # 6. Natural-Language Rule Builder (Arabic & English -> Tier 1 SQL Rule)
    # =========================================================================
    async def create_rule_from_natural_language(
        self, db: AsyncSession, prompt_text: str
    ) -> ClassificationRule:
        text = prompt_text.strip()
        if not text:
            raise ValueError("Prompt text cannot be empty")

        lower = text.lower()

        # 1. Extract any explicit domain(s) or well-known platform names
        domains_found = re.findall(
            r"\b([a-z0-9\-]+\.(?:com|net|org|io|ai|co|tech|dev|edu|gov|me))\b",
            lower,
        )
        known_brand_map = {
            "لينكدإن": "linkedin.com",
            "linkedin": "linkedin.com",
            "فيسبوك": "facebookmail.com",
            "facebook": "facebookmail.com",
            "جيتهاب": "github.com",
            "github": "github.com",
            "نتفلكس": "netflix.com",
            "netflix": "netflix.com",
            "أمازون": "amazon.com",
            "amazon": "amazon.com",
            "فيرسل": "vercel.com",
            "vercel": "vercel.com",
            "كلاودفلير": "cloudflare.com",
            "cloudflare": "cloudflare.com",
            "بايبال": "paypal.com",
            "paypal": "paypal.com",
            "جوجل": "google.com",
            "google": "google.com",
            "كورسيرا": "coursera.org",
            "coursera": "coursera.org",
        }
        for keyword, dom in known_brand_map.items():
            if keyword in lower and dom not in domains_found:
                domains_found.append(dom)

        sender_domain = ",".join(domains_found) if domains_found else None

        # 2. Extract quoted keywords or "كلمة X" / "containing X" for subject_regex
        quoted = re.findall(r"[\"'«»]([^\"'«»]{2,40})[\"'«»]", text)
        word_matches = re.findall(
            r"(?:كلمة|كلمات|يحتوي على|تحتوي على|contains|containing|with word|keywords?)\s+([A-Za-z0-9\u0600-\u06FF_\- ]{2,35})",
            text,
            flags=re.IGNORECASE,
        )
        regex_terms = [q.strip() for q in quoted if q.strip()]
        for wm in word_matches:
            cleaned_w = re.split(r"\b(?:أو|و|احذف|ضع|or|and|mark|set|move|delete)\b", wm)[0].strip()
            if cleaned_w and len(cleaned_w) >= 2:
                regex_terms.append(cleaned_w)

        subject_regex = (
            "(" + "|".join(re.escape(rt) for rt in regex_terms) + ")"
            if regex_terms
            else None
        )

        # Fallback if neither domain nor subject_regex was isolated
        if not sender_domain and not subject_regex:
            tokens = [
                w
                for w in re.findall(r"[A-Za-z0-9\u0600-\u06FF]{3,}", text)
                if w.lower()
                not in {
                    "رسالة",
                    "اي",
                    "أي",
                    "من",
                    "الى",
                    "إلى",
                    "على",
                    "تحتوي",
                    "ضعها",
                    "احذفها",
                    "بعد",
                    "يوم",
                    "أيام",
                    "ايام",
                    "email",
                    "from",
                    "with",
                    "any",
                    "put",
                    "move",
                    "delete",
                    "after",
                    "days",
                }
            ]
            if tokens:
                subject_regex = "(" + "|".join(re.escape(t) for t in tokens[:4]) + ")"

        # 3. Determine Target Category
        target_category = SmartCategory.PROMOTIONS_NOISE.value
        if any(w in lower for w in ("مالي", "فاتورة", "إيصال", "دفع", "financial", "receipt", "invoice", "billing")):
            target_category = SmartCategory.FINANCIAL_LEAKAGE.value
        elif any(w in lower for w in ("سيرفر", "بنية", "عطل", "فشل", "infra", "deploy", "outage", "server", "cloud")):
            target_category = SmartCategory.INFRA_INCIDENTS.value
        elif any(w in lower for w in ("أمان", "امان", "دخول", "security", "oauth", "login")):
            target_category = SmartCategory.SECURITY_OAUTH.value
        elif any(w in lower for w in ("تحقق", "كود", "رمز", "otp", "verification", "2fa")):
            target_category = SmartCategory.EPHEMERAL.value
        elif any(w in lower for w in ("موعد", "اجراء", "إجراء", "مهلة", "deadline", "sla", "action")):
            target_category = SmartCategory.ACTION_SLA.value
        elif any(w in lower for w in ("دراسة", "تدريب", "منحة", "كورس", "جامعة", "study", "course", "training")):
            target_category = SmartCategory.STUDY_TRAINING.value
        elif any(w in lower for w in ("نشرة", "ملخص", "معرف", "digest", "newsletter", "changelog")):
            target_category = SmartCategory.KNOWLEDGE_DIGEST.value

        # 4. Determine Target Severity
        target_severity = SeverityLevel.P3_NOISE.value
        if any(w in lower for w in ("p0", "حرج", "طارئ", "critical", "urgent")):
            target_severity = SeverityLevel.P0_CRITICAL.value
        elif any(w in lower for w in ("p1", "هام", "مهم", "high", "important")):
            target_severity = SeverityLevel.P1_HIGH.value
        elif any(w in lower for w in ("p2", "عادي", "normal")):
            target_severity = SeverityLevel.P2_NORMAL.value
        elif target_category in (SmartCategory.INFRA_INCIDENTS.value, SmartCategory.FINANCIAL_LEAKAGE.value):
            target_severity = SeverityLevel.P1_HIGH.value

        # 5. Determine Target TTL
        target_ttl = LifecycleTTL.TTL_30D.value
        if any(w in lower for w in ("لا تحذف", "أبداً", "ابدا", "حماية", "never delete", "keep forever", "protect")):
            target_ttl = LifecycleTTL.NEVER_DELETE.value
        elif any(w in lower for w in ("24 ساعة", "يوم واحد", "24h", "1 day", "24 hours")):
            target_ttl = LifecycleTTL.TTL_24H.value
        elif any(w in lower for w in ("7 أيام", "7 ايام", "أسبوع", "اسبوع", "7 days", "week", "7d")):
            target_ttl = LifecycleTTL.TTL_7D.value
        elif any(w in lower for w in ("14 يوم", "أسبوعين", "14 days", "2 weeks", "14d")):
            target_ttl = LifecycleTTL.TTL_14D.value
        elif any(w in lower for w in ("60 يوم", "شهرين", "60 days", "2 months", "60d")):
            target_ttl = LifecycleTTL.TTL_60D.value
        elif any(w in lower for w in ("أرشفة فقط", "ارشفة", "archive only")):
            target_ttl = LifecycleTTL.ARCHIVE_ONLY.value

        rule_name = f"AI Rule: {text[:55]}"
        existing = (
            await db.execute(
                select(ClassificationRule).where(ClassificationRule.name == rule_name)
            )
        ).scalar_one_or_none()
        if existing:
            rule_name = f"{rule_name} ({int(datetime.now(timezone.utc).timestamp()) % 1000})"

        new_rule = ClassificationRule(
            name=rule_name,
            description=f"Generated from natural language: {text}",
            priority=20,
            is_active=True,
            sender_domain=sender_domain,
            subject_regex=subject_regex,
            target_category=target_category,
            target_severity=target_severity,
            target_ttl=target_ttl,
        )
        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)
        return new_rule
