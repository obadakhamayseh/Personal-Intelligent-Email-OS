import {
  CalendarExtractResponse,
  ClassificationRule,
  CleanupAuditItem,
  CleanupPreviewResponse,
  CustomBulkPreviewResponse,
  DashboardStatus,
  DeadlineItem,
  EmailItem,
  EmailListResponse,
  ExecutiveAnalyticsResponse,
  FinancialBurnRateResponse,
  FinancialEventItem,
  OAuthServiceItem,
  PersonaReplyResponse,
  PhishingForensicsResponse,
  RagQueryResponse,
  SenderStatItem,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || `HTTP ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export const EmailOSApi = {
  getStatus: () => apiFetch<DashboardStatus>("/intelligence/status"),

  listEmails: (params: {
    category?: string;
    severity?: string;
    q?: string;
    starred_only?: boolean;
    sent_only?: boolean;
    trashed_only?: boolean;
    unread_only?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params.category) search.set("category", params.category);
    if (params.severity) search.set("severity", params.severity);
    if (params.q) search.set("q", params.q);
    if (params.starred_only) search.set("starred_only", "true");
    if (params.sent_only) search.set("sent_only", "true");
    if (params.trashed_only) search.set("trashed_only", "true");
    if (params.unread_only) search.set("unread_only", "true");
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined)
      search.set("offset", String(params.offset));
    const qs = search.toString();
    return apiFetch<EmailListResponse>(`/emails${qs ? `?${qs}` : ""}`);
  },

  updateEmailState: (
    messageId: string,
    updates: { is_read?: boolean; is_starred?: boolean; is_trashed?: boolean }
  ) => {
    const search = new URLSearchParams();
    if (updates.is_read !== undefined)
      search.set("is_read", String(updates.is_read));
    if (updates.is_starred !== undefined)
      search.set("is_starred", String(updates.is_starred));
    if (updates.is_trashed !== undefined)
      search.set("is_trashed", String(updates.is_trashed));
    return apiFetch<EmailItem>(
      `/emails/${encodeURIComponent(messageId)}/state?${search.toString()}`,
      { method: "PATCH" }
    );
  },

  ingestSimulatedEmail: (payload: {
    message_id: string;
    thread_id: string;
    sender_email: string;
    sender_name?: string;
    subject: string;
    snippet: string;
    body_text: string;
    internal_date: string;
  }) =>
    apiFetch<EmailItem>("/emails/ingest", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  triggerSync: () =>
    apiFetch<{
      status: string;
      progress?: {
        is_running: boolean;
        total_in_gmail: number;
        synced_in_db: number;
        newly_ingested: number;
      };
    }>("/emails/sync", {
      method: "POST",
    }),

  getSyncProgress: () =>
    apiFetch<{
      is_running: boolean;
      total_in_gmail: number;
      synced_in_db: number;
      newly_ingested: number;
      last_updated: string | null;
    }>("/emails/sync/progress"),

  listRules: () => apiFetch<ClassificationRule[]>("/rules"),

  createRule: (payload: Partial<ClassificationRule>) =>
    apiFetch<ClassificationRule>("/rules", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  toggleRule: (ruleId: number, is_active: boolean) =>
    apiFetch<ClassificationRule>(`/rules/${ruleId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active }),
    }),

  deleteRule: (ruleId: number) =>
    apiFetch<void>(`/rules/${ruleId}`, { method: "DELETE" }),

  dryRunCleanup: (payload: {
    before_date?: string;
    include_expired_ttl?: boolean;
    override_protected?: boolean;
  }) =>
    apiFetch<CleanupPreviewResponse>("/cleanup/dry-run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  executeCleanup: (payload: {
    before_date?: string;
    include_expired_ttl?: boolean;
    override_protected?: boolean;
  }) =>
    apiFetch<CleanupAuditItem>("/cleanup/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  previewCustomBulkDelete: (payload: {
    before_date?: string;
    after_date?: string;
    categories?: string[];
    severities?: string[];
    sender_query?: string;
    keyword_query?: string;
    unread_only?: boolean | null;
    exclude_starred?: boolean;
    limit?: number;
  }) =>
    apiFetch<CustomBulkPreviewResponse>("/cleanup/custom/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  executeCustomBulkDelete: (payload: {
    message_ids?: string[];
    filter_criteria?: {
      before_date?: string;
      after_date?: string;
      categories?: string[];
      severities?: string[];
      sender_query?: string;
      keyword_query?: string;
      unread_only?: boolean | null;
      exclude_starred?: boolean;
      limit?: number;
    };
  }) =>
    apiFetch<CleanupAuditItem>("/cleanup/custom/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listAuditLogs: () => apiFetch<CleanupAuditItem[]>("/cleanup/audit-logs"),

  undoCleanup: (batchId: string) =>
    apiFetch<CleanupAuditItem>(`/cleanup/undo/${encodeURIComponent(batchId)}`, {
      method: "POST",
    }),

  queryRag: (question: string, top_k = 5) =>
    apiFetch<RagQueryResponse>("/rag/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    }),

  listSenders: (deadOnly = false) =>
    apiFetch<SenderStatItem[]>(
      `/intelligence/senders${deadOnly ? "?dead_only=true" : ""}`
    ),

  autoArchiveSender: (sender_email: string) =>
    apiFetch<{ status: string; rule_id: number }>(
      "/intelligence/senders/auto-archive",
      {
        method: "POST",
        body: JSON.stringify({ sender_email }),
      }
    ),

  unsubscribeSender: (sender_email: string) =>
    apiFetch<{
      sender_email: string;
      rfc8058_dispatched: boolean;
      auto_archive_rule_id: number;
      muted: boolean;
    }>("/intelligence/senders/unsubscribe", {
      method: "POST",
      body: JSON.stringify({ sender_email }),
    }),

  getOAuthMap: () => apiFetch<OAuthServiceItem[]>("/intelligence/oauth-map"),

  getDeadlines: () => apiFetch<DeadlineItem[]>("/intelligence/deadlines"),

  getFinancialEvents: () =>
    apiFetch<FinancialEventItem[]>("/intelligence/financial"),

  triggerWeeklyDigest: () =>
    apiFetch<{
      processed_count: number;
      summary_markdown: string;
      archived_message_ids: string[];
    }>("/intelligence/digest", { method: "POST" }),

  getGoogleOAuthStatus: () =>
    apiFetch<{
      connected: boolean;
      configured: boolean;
      redirect_uri: string;
    }>("/auth/google/status"),

  saveGoogleOAuthConfig: (payload: {
    client_id: string;
    client_secret: string;
    redirect_uri?: string;
  }) =>
    apiFetch<{ configured: boolean; redirect_uri: string }>(
      "/auth/google/configure",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  getGoogleOAuthUrl: () =>
    apiFetch<{ authorization_url: string; state: string }>("/auth/google/url"),

  disconnectGoogleAccount: () =>
    apiFetch<{ connected: boolean }>("/auth/google/disconnect", {
      method: "POST",
    }),

  purgeAllData: () =>
    apiFetch<{ status: string }>("/auth/purge-data", {
      method: "DELETE",
    }),

  generatePersonaReply: (
    messageId: string,
    payload: {
      tone: string;
      target_language?: string;
      custom_instructions?: string;
      save_to_gmail_drafts?: boolean;
    }
  ) =>
    apiFetch<PersonaReplyResponse>(
      `/agentic/emails/${encodeURIComponent(messageId)}/draft-reply`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  saveGmailDraft: (messageId: string, draft_body: string) =>
    apiFetch<{
      saved_in_gmail: boolean;
      draft_id: string;
      error?: string;
    }>(`/agentic/emails/${encodeURIComponent(messageId)}/save-gmail-draft`, {
      method: "POST",
      body: JSON.stringify({ draft_body }),
    }),

  getPhishingForensics: (messageId: string) =>
    apiFetch<PhishingForensicsResponse>(
      `/agentic/emails/${encodeURIComponent(messageId)}/phishing-forensics`
    ),

  extractCalendarEvent: (messageId: string) =>
    apiFetch<CalendarExtractResponse>(
      `/agentic/emails/${encodeURIComponent(messageId)}/calendar-extract`
    ),

  getFinancialBurnRate: () =>
    apiFetch<FinancialBurnRateResponse>("/agentic/financial-burn-rate"),

  getExecutiveAnalytics: () =>
    apiFetch<ExecutiveAnalyticsResponse>("/agentic/analytics"),

  createRuleFromNaturalLanguage: (prompt: string) =>
    apiFetch<ClassificationRule>("/agentic/rules/from-natural-language", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};
