# Personal Intelligent Email OS (Full Production Build)

A self-hosted, production-grade **Personal Intelligent Email OS** for Gmail featuring a **3D Hybrid Classification Pipeline**, **Direct User-Controlled Bulk Delete Studio & Safe Cleanup Engine**, **PostgreSQL 16 + `pgvector` Semantic Email RAG**, **Autonomous AI & Agentic Suite**, **Authentic Google Gmail Next.js UI (Arabic `RTL` & English `LTR` + Dark Mode + `Ctrl+K` Command Palette)**, and an **Interactive Telegram Command Center**.

---

## 1. Flagship Capabilities & Architecture

### A. Three-Dimensional Hybrid Classification Engine
- Every incoming email is classified across **three orthogonal dimensions**:
  1. **Primary Smart Category** (`AI/Ephemeral-SelfDestruct`, `AI/Security-OAuth-Radar`, `AI/Infra-Incidents`, `AI/Financial-Leakage`, `AI/Action-SLA`, `AI/Waiting-On-Ghosted`, `AI/Study-Training`, `AI/Knowledge-Digest`, `AI/Promotions-Noise`)
  2. **Severity / Priority** (`P0_CRITICAL`, `P1_HIGH`, `P2_NORMAL`, `P3_NOISE`)
  3. **Lifecycle Policy / TTL** (`NEVER_DELETE`, `TTL_24H`, `TTL_7D`, `TTL_14D`, `TTL_30D`, `TTL_60D`, `ARCHIVE_ONLY`)
- **Tier 1 (Deterministic Rule Engine — `0ms`, zero API cost):** PostgreSQL-backed regex, sender domain, exact address, and header (`List-Unsubscribe`, `Auto-Submitted`) rules editable live from the UI + **AI Natural-Language Rule Builder** (convert plain Arabic/English sentences into deterministic SQL/Regex rules in 1 click).
- **Tier 2 (LLM Semantic Classifier — Bilingual Arabic & English):** Gemini primary (`responseMimeType: application/json`) + OpenAI fallback extracting `deadline_at`, `monetary_amount`, `currency`, `renewal_date`, `oauth_app_name`, and a 1-sentence summary in the email's language.

### B. Dual Bulk Cleanup Architecture (Direct User Studio + Safe Automated Engine)
1. **Direct Bulk Delete Studio (100% User-Controlled):**
   - Dedicated view allowing unrestricted filtering by exact date ranges (`From Date` / `Before Cutoff Date`), quick date presets (`>7d`, `>30d`, `>3m`, `>6m`, `>1y`), categories, priorities (`P0..P3`), sender, and keywords without forced shields.
   - Interactive message preview table with individual checkboxes and atomic 1,000-ID `users.messages.batchModify` execution that syncs directly to the official Google Gmail app + 1-click Undo/Restore.
2. **Automated Safe Bulk Cleanup Simulator:**
   - **Active Thread Shield:** Never trashes old messages belonging to an active thread with a recent reply.
   - **Protected Labels Shield:** Protects `STARRED`, `AI/Financial-Leakage`, `AI/Security-OAuth-Radar` (except expired `OTP`), and `P0_CRITICAL`.
   - **Two-Stage Deletion + Audit Log + 1-Click Undo:** Full checkpointed audit trail in `cleanup_audit_logs`.

### C. Autonomous AI & Agentic Intelligence Suite
1. **AI Persona Reply Ghostwriter & Official Gmail Draft Sync:**
   - Learns your writing style from `SENT` emails and drafts replies in Arabic or English across 4 tones (*Professional, Concise, Follow-up Ghosted, Polite Decline*), with 1-click saving directly into your **official Google Gmail Drafts folder** linked to the thread.
2. **AI Phishing, Spoofing & Header Forensics Shield:**
   - Self-learning brand & domain graph + cryptographic header analysis (`SPF`, `DKIM`, `DMARC`, `Reply-To` alignment, raw IP URLs, shorteners) producing a `0–100%` **Trust Score** and forensic report on every opened email.
3. **Subscription Burn-Rate & Financial Leakage Studio:**
   - Automatically calculates your estimated **Monthly Burn Rate (`$/mo`)**, **Projected Annual Spend (`$/yr`)**, failed payment alerts, trial-ending warnings, and per-vendor billing history.
4. **1-Click Google Calendar & Video Meeting Extractor:**
   - Extracts deadlines and video meeting links (`Google Meet`, `Zoom`, `MS Teams`), providing a 1-click **Add to Google Calendar** button and downloadable `.ics` file.
5. **Executive Inbox Analytics & Telemetry Dashboard:**
   - Tracks total storage reclaimed (`MB`), estimated reading hours saved by AI, Tier 1 (`0ms`) vs Tier 2 (`LLM`) efficiency ratio, category/severity visual charts, day-of-week traffic, and Top 10 storage-consuming senders.
6. **Semantic Email RAG (`pgvector`):**
   - Answers natural-language questions in **Arabic** or **English** with exact citations and clickable Gmail thread links (`https://mail.google.com/mail/u/0/#all/<thread_id>`).

### D. Modern Bilingual Gmail UI & Superhuman UX
- **Full Arabic (`RTL`) & English (`LTR`) Support:** 1-click language & direction toggle in the header.
- **Authentic Gmail Dark Mode:** Smooth Material 3 Dark/Light theme switcher (`🌙 / ☀️`).
- **`Ctrl+K` / `Cmd+K` Command Palette:** Instant keyboard-driven navigation and action execution.
- **In-App Google OAuth 2.0 Sign-In & Full Historical Pagination Sync:** Connect your Gmail account directly from the UI and stream your entire account history (`nextPageToken`) with a live progress bar.

---

## 2. Quick Start with Docker Compose

```bash
cp .env.example .env
# Generate a fresh Fernet key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker compose up -d --build
```

- **Next.js Gmail Web App (Arabic & English):** `http://localhost:3005`
- **FastAPI OpenAPI Swagger Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## 3. Running Automated Tests (`pytest`)

```bash
cd backend
pytest -v
```
