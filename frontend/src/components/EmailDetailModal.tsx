"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Cpu,
  Tag,
  Trash2,
  Star,
  Sparkles,
  Calendar,
  Download,
  Video,
  Send,
  Copy,
  Check,
  FileEdit,
} from "lucide-react";
import {
  CalendarExtractResponse,
  EmailItem,
  PhishingForensicsResponse,
} from "@/lib/types";
import { EmailOSApi } from "@/lib/api";
import { getSeverityBadgeStyle } from "./EmailListView";
import { useLanguage } from "@/lib/i18n";

interface EmailDetailModalProps {
  email: EmailItem | null;
  onClose: () => void;
  onMoveToTrash: (email: EmailItem, e: React.MouseEvent) => void;
  onToggleStar: (email: EmailItem, e: React.MouseEvent) => void;
}

export default function EmailDetailModal({
  email,
  onClose,
  onMoveToTrash,
  onToggleStar,
}: EmailDetailModalProps) {
  const { t, lang } = useLanguage();
  const isAr = lang === "ar";

  // Phishing Forensics & Calendar Extract State
  const [forensics, setForensics] = useState<PhishingForensicsResponse | null>(
    null
  );
  const [calendarEvent, setCalendarEvent] =
    useState<CalendarExtractResponse | null>(null);

  // AI Persona Reply Studio State
  const [tone, setTone] = useState<string>("professional");
  const [draftBody, setDraftBody] = useState<string>("");
  const [generatingReply, setGeneratingReply] = useState<boolean>(false);
  const [savingDraft, setSavingDraft] = useState<boolean>(false);
  const [draftSavedBanner, setDraftSavedBanner] = useState<string | null>(null);
  const [copiedReply, setCopiedReply] = useState<boolean>(false);

  useEffect(() => {
    if (!email) return;
    setForensics(null);
    setCalendarEvent(null);
    setDraftBody("");
    setDraftSavedBanner(null);

    EmailOSApi.getPhishingForensics(email.message_id)
      .then(setForensics)
      .catch(() => null);

    EmailOSApi.extractCalendarEvent(email.message_id)
      .then(setCalendarEvent)
      .catch(() => null);
  }, [email]);

  if (!email) return null;

  const handleGenerateReply = async (selectedTone: string) => {
    setTone(selectedTone);
    setGeneratingReply(true);
    setDraftSavedBanner(null);
    try {
      const res = await EmailOSApi.generatePersonaReply(email.message_id, {
        tone: selectedTone,
        target_language: "auto",
      });
      setDraftBody(res.draft_body);
    } catch (err: any) {
      setDraftSavedBanner(`Error: ${err.message}`);
    } finally {
      setGeneratingReply(false);
    }
  };

  const handleSaveToGmailDrafts = async () => {
    if (!draftBody.trim()) return;
    setSavingDraft(true);
    setDraftSavedBanner(null);
    try {
      const res = await EmailOSApi.saveGmailDraft(email.message_id, draftBody);
      if (res.saved_in_gmail) {
        setDraftSavedBanner(
          isAr
            ? `✅ تم حفظ مسودة الرد مباشرة داخل تطبيق Google Gmail الرسمي (Draft ID: ${res.draft_id})!`
            : `✅ Draft saved directly into your official Google Gmail account (Draft ID: ${res.draft_id})!`
        );
      } else {
        setDraftSavedBanner(
          isAr
            ? `ℹ️ تم حفظ المسودة محلياً (${res.draft_id}).`
            : `ℹ️ Draft saved locally (${res.draft_id}).`
        );
      }
    } catch (err: any) {
      setDraftSavedBanner(`Error: ${err.message}`);
    } finally {
      setSavingDraft(false);
    }
  };

  const handleDownloadIcs = () => {
    if (!calendarEvent) return;
    const blob = new Blob([calendarEvent.ics_content], {
      type: "text/calendar;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `event_${email.message_id}.ics`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyDraft = () => {
    navigator.clipboard.writeText(draftBody);
    setCopiedReply(true);
    setTimeout(() => setCopiedReply(false), 2000);
  };

  return (
    <div
      onClick={onClose}
      className="animate-backdrop fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px] flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-modal-enter bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-gray-200"
      >
        {/* Top Action Header */}
        <div className="px-6 py-3.5 border-b border-gray-200 flex items-center justify-between bg-[#F6F8FC] shrink-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full border ${getSeverityBadgeStyle(
                email.severity
              )}`}
            >
              {email.severity}
            </span>
            <span className="text-xs px-3 py-0.5 rounded-full bg-[#D3E3FD] text-[#041E49] font-bold">
              {t.categories[email.category] || email.category}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-gray-200 text-gray-800 font-medium">
              TTL: {email.ttl_policy}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={(e) => onToggleStar(email, e)}
              className="p-2 rounded-full hover:bg-gray-200 text-gray-600 transition"
            >
              <Star
                className={`w-4 h-4 ${
                  email.is_starred
                    ? "fill-amber-400 text-amber-400"
                    : "text-gray-500"
                }`}
              />
            </button>
            <button
              onClick={(e) => {
                onMoveToTrash(email, e);
                onClose();
              }}
              className="p-2 rounded-full hover:bg-red-100 text-red-600 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            {email.gmail_link && (
              <a
                href={email.gmail_link}
                target="_blank"
                rel="noreferrer"
                className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#0B57D0] text-white text-xs font-semibold hover:bg-blue-800"
              >
                <span>{t.openInGmail}</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-gray-200 text-gray-600 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h2 className="text-xl font-bold text-[#1F1F1F] flex-1">
              {email.subject}
            </h2>

            {/* 1-Click Google Calendar & Meeting Action Bar */}
            {calendarEvent && (
              <div className="flex flex-wrap items-center gap-2 shrink-0">
                {calendarEvent.meeting_url && (
                  <a
                    href={calendarEvent.meeting_url}
                    target="_blank"
                    rel="noreferrer"
                    className="smooth-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-2xs"
                  >
                    <Video className="w-3.5 h-3.5" />
                    <span>
                      {isAr ? "انضمام للاجتماع" : "Join Video Meeting"}
                    </span>
                  </a>
                )}
                <a
                  href={calendarEvent.google_calendar_url}
                  target="_blank"
                  rel="noreferrer"
                  className="smooth-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#EAF1FB] hover:bg-[#D3E3FD] text-[#041E49] border border-blue-200 text-xs font-bold"
                >
                  <Calendar className="w-3.5 h-3.5 text-[#0B57D0]" />
                  <span>
                    {isAr ? "إضافة إلى تقويم Google" : "Add to Google Calendar"}
                  </span>
                </a>
                <button
                  onClick={handleDownloadIcs}
                  className="smooth-pill flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold"
                  title="Download .ics Calendar File"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>.ics</span>
                </button>
              </div>
            )}
          </div>

          {/* Sender Info */}
          <div className="flex items-center justify-between text-xs text-[#444746] pb-3 border-b border-gray-100">
            <div>
              <p className="font-bold text-sm text-[#1F1F1F]">
                {email.sender_name || email.sender_email}{" "}
                <span className="font-normal text-gray-500">
                  &lt;{email.sender_email}&gt;
                </span>
              </p>
              <p className="mt-0.5">
                {t.toLabel} {email.recipient_email || "me"}
              </p>
            </div>
            <div className="text-end">
              <p>{new Date(email.internal_date).toLocaleString()}</p>
              <p className="text-[11px] text-gray-400">
                {t.threadIdLabel} {email.thread_id}
              </p>
            </div>
          </div>

          {/* Agentic Module 1: AI Phishing, Spoofing & Header Forensics Shield */}
          {forensics && (
            <div
              className={`rounded-2xl p-4 border space-y-2.5 transition ${
                forensics.risk_level === "SAFE"
                  ? "bg-emerald-50/70 border-emerald-200"
                  : forensics.risk_level === "CAUTION"
                  ? "bg-amber-50 border-amber-300"
                  : "bg-red-50 border-red-300"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {forensics.risk_level === "SAFE" ? (
                    <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <ShieldAlert className="w-5 h-5 text-red-600 animate-pulse" />
                  )}
                  <span className="text-xs font-bold text-[#1F1F1F]">
                    {isAr
                      ? "درع الفحص الجنائي للتصيّد والاحتيال (AI Phishing & Spoofing Forensics)"
                      : "AI Phishing, Spoofing & Header Forensics Shield"}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span
                    className={`px-2.5 py-0.5 rounded-full font-extrabold ${
                      forensics.trust_score >= 80
                        ? "bg-emerald-600 text-white"
                        : forensics.trust_score >= 50
                        ? "bg-amber-600 text-white"
                        : "bg-red-600 text-white"
                    }`}
                  >
                    {isAr ? "درجة الموثوقية:" : "Trust Score:"}{" "}
                    {forensics.trust_score}%
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white border border-gray-200 font-mono text-gray-700">
                    SPF: {forensics.spf_status}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white border border-gray-200 font-mono text-gray-700">
                    DKIM: {forensics.dkim_status}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white border border-gray-200 font-mono text-gray-700">
                    DMARC: {forensics.dmarc_status}
                  </span>
                </div>
              </div>

              <ul className="text-xs space-y-1 text-[#1F1F1F]">
                {(isAr ? forensics.findings_ar : forensics.findings_en).map(
                  (f, idx) => (
                    <li key={idx}>{f}</li>
                  )
                )}
              </ul>
            </div>
          )}

          {/* 3D AI Intelligence Panel */}
          <div className="rounded-2xl bg-[#EAF1FB]/90 border border-[#D3E3FD] p-4 space-y-2 shadow-2xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-[#041E49]">
                <Cpu className="w-4 h-4 text-[#0B57D0]" />
                <span>
                  {t.classificationEngineLabel} ({email.classified_by}
                  {email.matched_rule_id
                    ? ` • ${t.ruleNumber}${email.matched_rule_id}`
                    : ""}
                  )
                </span>
              </div>
              {email.expires_at ? (
                <div className="flex items-center gap-1 text-xs text-amber-800 font-medium">
                  <Clock className="w-3.5 h-3.5" />
                  <span>
                    {t.expiresLabel}{" "}
                    {new Date(email.expires_at).toLocaleString()}
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-emerald-700 font-bold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{t.protectedFromDelete}</span>
                </div>
              )}
            </div>
            <p className="text-sm text-[#1F1F1F] leading-relaxed">
              <strong>{t.aiSummaryLabel}</strong>{" "}
              {email.ai_summary || email.snippet}
            </p>
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <Tag className="w-3.5 h-3.5 text-gray-500" />
              {email.gmail_labels.map((lbl) => (
                <span
                  key={lbl}
                  className="text-[11px] px-2.5 py-0.5 rounded-full bg-white border border-gray-200 text-gray-700 font-medium"
                >
                  {lbl}
                </span>
              ))}
            </div>
          </div>

          {/* Plain Body Text */}
          <div className="bg-gray-50 rounded-2xl p-4 border border-gray-200 text-sm text-[#1F1F1F] whitespace-pre-wrap leading-relaxed">
            {email.body_text || email.snippet}
          </div>

          {/* Agentic Module 2: AI Persona Reply Drafter & Official Gmail Draft Sync */}
          <div className="rounded-2xl border-2 border-[#D3E3FD] bg-[#F6F8FC] p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#0B57D0]" />
                <span className="text-xs font-bold text-[#041E49]">
                  {isAr
                    ? "كاتب مسودات الردود الذكي بنفس أسلوبك الشخصي (AI Persona Ghostwriter)"
                    : "AI Persona Reply Ghostwriter & Official Gmail Draft Sync"}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  {
                    id: "professional",
                    label: isAr ? "✨ رد رسمي احترافي" : "✨ Professional",
                  },
                  {
                    id: "concise",
                    label: isAr ? "⚡ مختصر وسريع" : "⚡ Concise",
                  },
                  {
                    id: "followup_ghosted",
                    label: isAr ? "🔔 متابعة (Follow-up)" : "🔔 Follow-up",
                  },
                  {
                    id: "polite_decline",
                    label: isAr ? "🙏 اعتذار لبق" : "🙏 Polite Decline",
                  },
                ].map((btn) => (
                  <button
                    key={btn.id}
                    type="button"
                    onClick={() => handleGenerateReply(btn.id)}
                    disabled={generatingReply}
                    className={`smooth-pill px-3 py-1.5 rounded-full text-xs font-bold border ${
                      tone === btn.id && draftBody
                        ? "bg-[#0B57D0] text-white border-[#0B57D0]"
                        : "bg-white hover:bg-[#D3E3FD] text-[#041E49] border-gray-200"
                    }`}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
            </div>

            {generatingReply && (
              <div className="p-4 text-center text-xs font-bold text-[#0B57D0] animate-pulse">
                {isAr
                  ? "جاري تحليل أسلوبك وتوليد مسودة الرد الذكية..."
                  : "Analyzing your writing style & drafting reply..."}
              </div>
            )}

            {draftSavedBanner && (
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-900">
                {draftSavedBanner}
              </div>
            )}

            {draftBody && !generatingReply && (
              <div className="space-y-2.5 animate-view-enter">
                <textarea
                  rows={5}
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                  className="w-full rounded-xl border border-gray-300 bg-white p-3 text-xs text-[#1F1F1F] leading-relaxed outline-none focus:border-[#0B57D0]"
                />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={handleCopyDraft}
                    className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white border border-gray-300 text-xs font-bold text-gray-700 hover:bg-gray-100"
                  >
                    {copiedReply ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700">
                          {isAr ? "تم النسخ" : "Copied"}
                        </span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>{isAr ? "نسخ النص" : "Copy Draft"}</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleSaveToGmailDrafts}
                    disabled={savingDraft}
                    className="smooth-pill flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white text-xs font-bold shadow-sm"
                  >
                    <FileEdit className="w-3.5 h-3.5" />
                    <span>
                      {savingDraft
                        ? isAr
                          ? "جاري الحفظ في Gmail..."
                          : "Saving to Gmail..."
                        : isAr
                        ? "💾 حفظ كمسودة في تطبيق Gmail الرسمي"
                        : "💾 Save directly to Official Gmail Drafts"}
                    </span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
