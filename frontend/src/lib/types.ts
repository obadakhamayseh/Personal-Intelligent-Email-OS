export type SmartCategory =
  | "AI/Ephemeral-SelfDestruct"
  | "AI/Security-OAuth-Radar"
  | "AI/Infra-Incidents"
  | "AI/Financial-Leakage"
  | "AI/Action-SLA"
  | "AI/Waiting-On-Ghosted"
  | "AI/Study-Training"
  | "AI/Knowledge-Digest"
  | "AI/Promotions-Noise";

export type SeverityLevel = "P0_CRITICAL" | "P1_HIGH" | "P2_NORMAL" | "P3_NOISE";

export type LifecycleTTL =
  | "NEVER_DELETE"
  | "TTL_24H"
  | "TTL_7D"
  | "TTL_14D"
  | "TTL_30D"
  | "TTL_60D"
  | "ARCHIVE_ONLY";

export interface EmailItem {
  message_id: string;
  thread_id: string;
  sender_email: string;
  sender_name: string | null;
  recipient_email: string | null;
  subject: string;
  snippet: string;
  body_text: string;
  internal_date: string;
  size_estimate: number;
  is_read: boolean;
  is_starred: boolean;
  is_sent: boolean;
  is_trashed: boolean;
  is_archived: boolean;
  category: SmartCategory;
  severity: SeverityLevel;
  ttl_policy: LifecycleTTL;
  expires_at: string | null;
  ai_summary: string | null;
  classified_by: string;
  matched_rule_id: number | null;
  has_unsubscribe: boolean;
  unsubscribe_header: string | null;
  gmail_labels: string[];
  ghosted_flagged: boolean;
  digest_included: boolean;
  gmail_link?: string;
}

export interface EmailListResponse {
  total: number;
  unread_count: number;
  p0_count: number;
  items: EmailItem[];
}

export interface DashboardStatus {
  total_emails: number;
  unread_emails: number;
  active_p0_incidents: number;
  upcoming_deadlines_count: number;
  ghosted_threads_count: number;
  dead_subscriptions_count: number;
  oauth_apps_count: number;
  financial_events_count: number;
  category_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  gmail_connected: boolean;
  next_scheduled_cleanup: string;
}

export interface ClassificationRule {
  id: number;
  name: string;
  description: string | null;
  priority: number;
  is_active: boolean;
  sender_domain: string | null;
  sender_email: string | null;
  subject_regex: string | null;
  snippet_regex: string | null;
  header_key: string | null;
  header_regex: string | null;
  target_category: SmartCategory;
  target_severity: SeverityLevel;
  target_ttl: LifecycleTTL;
  hit_count: number;
  created_at: string;
}

export interface CleanupCategoryStat {
  category: string;
  count: number;
  bytes_freed: number;
  sample_subjects: string[];
}

export interface CleanupPreviewResponse {
  cutoff_date: string;
  total_candidate_messages: number;
  estimated_bytes_freed: number;
  estimated_mb_freed: number;
  shielded_active_threads_count: number;
  shielded_protected_labels_count: number;
  categories: CleanupCategoryStat[];
  candidate_message_ids: string[];
}

export interface CleanupAuditItem {
  id: number;
  batch_id: string;
  execution_mode: string;
  cutoff_date: string;
  total_messages: number;
  estimated_bytes_freed: number;
  category_breakdown: Record<string, number>;
  status: string;
  restored_at: string | null;
  created_at: string;
}

export interface CustomBulkMessageItem {
  message_id: string;
  thread_id: string;
  sender_email: string;
  sender_name: string | null;
  subject: string;
  internal_date: string;
  size_estimate: number;
  category: SmartCategory;
  severity: SeverityLevel;
  is_read: boolean;
  is_starred: boolean;
}

export interface CustomBulkPreviewResponse {
  total_matching: number;
  estimated_bytes: number;
  estimated_mb: number;
  category_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  messages: CustomBulkMessageItem[];
}

export interface RagCitation {
  message_id: string;
  thread_id: string;
  subject: string;
  sender_email: string;
  internal_date: string;
  category: string;
  similarity_score: number;
  gmail_thread_url: string;
  snippet: string;
}

export interface RagQueryResponse {
  question: string;
  answer: string;
  citations: RagCitation[];
}

export interface SenderStatItem {
  id: number;
  sender_email: string;
  sender_domain: string;
  sender_name: string | null;
  received_count: number;
  read_count: number;
  replied_count: number;
  noise_score: number;
  unread_rate_percent: number;
  is_dead_subscription: boolean;
  has_list_unsubscribe: boolean;
  unsubscribe_url: string | null;
  is_muted: boolean;
  last_received_at: string | null;
}

export interface OAuthServiceItem {
  id: number;
  service_name: string;
  first_seen_at: string;
  last_seen_at: string;
  last_event_type: string;
  last_ip_or_location: string | null;
  scopes_summary: string | null;
  risk_level: string;
  source_message_id: string;
  event_count: number;
  gmail_link?: string;
}

export interface DeadlineItem {
  id: number;
  message_id: string;
  thread_id: string;
  title: string;
  deadline_at: string;
  is_completed: boolean;
  reminder_sent: boolean;
  gmail_link?: string;
}

export interface FinancialEventItem {
  id: number;
  message_id: string;
  vendor: string;
  event_type: string;
  amount: number | null;
  currency: string | null;
  renewal_date: string | null;
  status: string;
  created_at: string;
}

export interface PersonaReplyResponse {
  message_id: string;
  thread_id: string;
  recipient_email: string;
  reply_subject: string;
  tone: string;
  language: string;
  draft_body: string;
  learned_from_sent_count: number;
  gmail_draft?: {
    saved_in_gmail: boolean;
    draft_id: string;
    error?: string;
  } | null;
}

export interface PhishingForensicsResponse {
  message_id: string;
  sender_email: string;
  sender_domain: string;
  trust_score: number;
  risk_level: "SAFE" | "CAUTION" | "HIGH_RISK_PHISHING";
  spf_status: string;
  dkim_status: string;
  dmarc_status: string;
  domain_alignment: string;
  extracted_urls_count: number;
  suspicious_urls: string[];
  findings_ar: string[];
  findings_en: string[];
}

export interface CalendarExtractResponse {
  message_id: string;
  title: string;
  start_time: string;
  end_time: string;
  meeting_url: string | null;
  location: string;
  google_calendar_url: string;
  ics_content: string;
}

export interface VendorBurnItem {
  vendor: string;
  sender_email: string;
  emails_count: number;
  total_spent_usd: number;
  latest_amount: number | null;
  currency: string;
  latest_event_type: string;
  last_billed_at: string;
  estimated_next_renewal: string;
  gmail_link: string;
}

export interface FinancialBurnRateResponse {
  total_financial_emails: number;
  active_vendors_count: number;
  monthly_burn_usd: number;
  annual_projected_usd: number;
  total_recorded_spend_usd: number;
  failed_payments_count: number;
  trials_ending_count: number;
  vendors: VendorBurnItem[];
  recent_transactions: {
    message_id: string;
    thread_id: string;
    vendor: string;
    subject: string;
    event_type: string;
    amount: number | null;
    currency: string;
    amount_usd: number | null;
    date: string;
    gmail_link: string;
  }[];
}

export interface ExecutiveAnalyticsResponse {
  total_all_time_emails: number;
  active_inbox_emails: number;
  trashed_emails_count: number;
  active_storage_mb: number;
  storage_freed_mb: number;
  estimated_hours_saved: number;
  tier1_zero_cost_count: number;
  tier2_llm_count: number;
  tier1_efficiency_percent: number;
  category_distribution: {
    category: SmartCategory;
    count: number;
    percentage: number;
    size_mb: number;
  }[];
  severity_distribution: {
    severity: SeverityLevel;
    count: number;
    percentage: number;
  }[];
  day_of_week_activity: {
    day: string;
    count: number;
  }[];
  top_senders: {
    sender_email: string;
    sender_name: string;
    count: number;
    unread_count: number;
    total_bytes: number;
    total_mb: number;
  }[];
}
