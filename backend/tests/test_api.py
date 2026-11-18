import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scheduler_jobs import seed_initial_demo_inbox


@pytest.mark.asyncio
async def test_end_to_end_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    await seed_initial_demo_inbox(db_session)

    # 1. Health check
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # 2. Dashboard status
    status_resp = await client.get("/api/v1/intelligence/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["total_emails"] >= 15
    assert status_data["active_p0_incidents"] >= 2
    assert status_data["dead_subscriptions_count"] >= 1
    assert status_data["oauth_apps_count"] >= 2

    # 3. List emails & filter by category
    emails_resp = await client.get("/api/v1/emails", params={"category": "AI/Infra-Incidents"})
    assert emails_resp.status_code == 200
    assert emails_resp.json()["total"] == 3

    # 4. Semantic Email RAG query (English & Arabic) with clickable Gmail thread citations
    rag_en = await client.post(
        "/api/v1/rag/query",
        json={"question": "Why did the Vercel deployment fail and what is the Neon database warning?", "top_k": 3},
    )
    assert rag_en.status_code == 200
    rag_data = rag_en.json()
    assert len(rag_data["citations"]) >= 1
    assert rag_data["citations"][0]["gmail_thread_url"].startswith(
        "https://mail.google.com/mail/u/0/#all/"
    )

    rag_ar = await client.post(
        "/api/v1/rag/query",
        json={"question": "ما هو الموعد النهائي لمشروع هندسة النظم الذكية وإيصال Google Play؟", "top_k": 3},
    )
    assert rag_ar.status_code == 200
    assert len(rag_ar.json()["citations"]) >= 1

    # 5. Cleanup Dry-Run -> Execute -> Undo
    dry_resp = await client.post("/api/v1/cleanup/dry-run", json={"include_expired_ttl": True})
    assert dry_resp.status_code == 200
    dry_data = dry_resp.json()
    assert dry_data["total_candidate_messages"] >= 6

    exec_resp = await client.post("/api/v1/cleanup/execute", json={"include_expired_ttl": True})
    assert exec_resp.status_code == 200
    batch_id = exec_resp.json()["batch_id"]

    undo_resp = await client.post(f"/api/v1/cleanup/undo/{batch_id}")
    assert undo_resp.status_code == 200
    assert undo_resp.json()["status"] == "RESTORED"

    # 6. Dead Subscription Detector & 1-click Auto-Archive Rule
    senders_resp = await client.get("/api/v1/intelligence/senders", params={"dead_only": True})
    assert senders_resp.status_code == 200
    dead_senders = senders_resp.json()
    assert len(dead_senders) >= 1
    noisy_email = dead_senders[0]["sender_email"]

    mute_resp = await client.post(
        "/api/v1/intelligence/senders/auto-archive",
        json={"sender_email": noisy_email},
    )
    assert mute_resp.status_code == 200
    assert mute_resp.json()["status"] == "RULE_CREATED"

    # 7. Custom Direct Bulk Delete Studio (Preview -> Execute -> Undo)
    custom_prev = await client.post(
        "/api/v1/cleanup/custom/preview",
        json={"severities": ["P3_NOISE"], "limit": 50},
    )
    assert custom_prev.status_code == 200
    assert custom_prev.json()["total_matching"] >= 6

    # 8. Autonomous AI & Agentic Suite (Forensics, Calendar, Reply Drafter, Burn-Rate, Analytics, NL Rule)
    forensics_resp = await client.get("/api/v1/agentic/emails/msg_infra_p0_vercel/phishing-forensics")
    assert forensics_resp.status_code == 200
    assert "trust_score" in forensics_resp.json()

    cal_resp = await client.get("/api/v1/agentic/emails/msg_sla_namecheap/calendar-extract")
    assert cal_resp.status_code == 200
    assert "BEGIN:VCALENDAR" in cal_resp.json()["ics_content"]

    reply_resp = await client.post(
        "/api/v1/agentic/emails/msg_sla_quiz_ar/draft-reply",
        json={"tone": "professional", "target_language": "ar"},
    )
    assert reply_resp.status_code == 200
    assert len(reply_resp.json()["draft_body"]) > 20

    burn_resp = await client.get("/api/v1/agentic/financial-burn-rate")
    assert burn_resp.status_code == 200
    assert burn_resp.json()["total_financial_emails"] >= 2

    analytics_resp = await client.get("/api/v1/agentic/analytics")
    assert analytics_resp.status_code == 200
    assert analytics_resp.json()["total_all_time_emails"] >= 15

    nl_rule_resp = await client.post(
        "/api/v1/agentic/rules/from-natural-language",
        json={"prompt": "أي رسالة من لينكدإن أو تحتوي على كلمة وظائف ضعها في الترويج واحذفها بعد 7 أيام"},
    )
    assert nl_rule_resp.status_code == 201
    assert nl_rule_resp.json()["sender_domain"] == "linkedin.com"
    assert nl_rule_resp.json()["target_ttl"] == "TTL_7D"
