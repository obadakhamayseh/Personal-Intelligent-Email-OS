"use client";

import React from "react";
import {
  Star,
  Trash2,
  MailOpen,
  Mail,
  RefreshCw,
  BookOpenCheck,
  Inbox,
  ServerCrash,
  CreditCard,
  Clock,
  ExternalLink,
  LogIn,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { EmailItem, SeverityLevel, SmartCategory } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface SyncProgressState {
  is_running: boolean;
  total_in_gmail: number;
  synced_in_db: number;
  newly_ingested: number;
}

interface EmailListViewProps {
  emails: EmailItem[];
  total: number;
  pageOffset: number;
  pageSize: number;
  onPageOffsetChange: (newOffset: number) => void;
  onPageSizeChange: (newSize: number) => void;
  loading: boolean;
  gmailConnected: boolean;
  syncProgress: SyncProgressState | null;
  selectedSeverity: SeverityLevel | "";
  onSelectSeverity: (sev: SeverityLevel | "") => void;
  activeTabCategory: SmartCategory | null;
  onSelectTabCategory: (cat: SmartCategory | null) => void;
  onOpenEmail: (email: EmailItem) => void;
  onToggleStar: (email: EmailItem, e: React.MouseEvent) => void;
  onToggleRead: (email: EmailItem, e: React.MouseEvent) => void;
  onMoveToTrash: (email: EmailItem, e: React.MouseEvent) => void;
  onRefresh: () => void;
  onTriggerDigest: () => void;
  onOpenGoogleModal: () => void;
  digestLoading: boolean;
}

export function getSeverityBadgeStyle(sev: SeverityLevel) {
  switch (sev) {
    case "P0_CRITICAL":
      return "bg-red-100 text-red-800 border-red-300 font-bold";
    case "P1_HIGH":
      return "bg-orange-100 text-orange-800 border-orange-300 font-semibold";
    case "P2_NORMAL":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "P3_NOISE":
    default:
      return "bg-gray-100 text-gray-600 border-gray-200";
  }
}

export default function EmailListView({
  emails,
  total,
  pageOffset,
  pageSize,
  onPageOffsetChange,
  onPageSizeChange,
  loading,
  gmailConnected,
  syncProgress,
  selectedSeverity,
  onSelectSeverity,
  activeTabCategory,
  onSelectTabCategory,
  onOpenEmail,
  onToggleStar,
  onToggleRead,
  onMoveToTrash,
  onRefresh,
  onTriggerDigest,
  onOpenGoogleModal,
  digestLoading,
}: EmailListViewProps) {
  const { t, lang } = useLanguage();
  const isAr = lang === "ar";

  const startIdx = total === 0 ? 0 : pageOffset + 1;
  const endIdx = Math.min(pageOffset + emails.length, total);
  const canPrev = pageOffset > 0;
  const canNext = pageOffset + pageSize < total;

  const tabs: {
    label: string;
    category: SmartCategory | null;
    icon: React.ComponentType<{ className?: string }>;
    accentColor: string;
  }[] = [
    {
      label: t.tabPrimary,
      category: null,
      icon: Inbox,
      accentColor: "border-[#0B57D0] text-[#0B57D0]",
    },
    {
      label: t.tabInfra,
      category: "AI/Infra-Incidents",
      icon: ServerCrash,
      accentColor: "border-red-600 text-red-700",
    },
    {
      label: t.tabFinancial,
      category: "AI/Financial-Leakage",
      icon: CreditCard,
      accentColor: "border-emerald-600 text-emerald-700",
    },
    {
      label: t.tabSla,
      category: "AI/Action-SLA",
      icon: Clock,
      accentColor: "border-orange-600 text-orange-700",
    },
  ];

  const pct =
    syncProgress && syncProgress.total_in_gmail > 0
      ? Math.min(
          100,
          Math.round(
            (syncProgress.synced_in_db / syncProgress.total_in_gmail) * 100
          )
        )
      : 0;

  return (
    <div
      key={`${activeTabCategory || "ALL"}_${selectedSeverity}_${lang}`}
      className="animate-view-enter flex-1 flex flex-col bg-white rounded-2xl shadow-sm border border-[#E1E5EA] overflow-hidden mx-3 mb-3"
    >
      {/* Live Full Historical Sync Progress Banner */}
      {syncProgress && syncProgress.is_running && (
        <div className="px-4 py-2 bg-[#EAF1FB] border-b border-[#D3E3FD] flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 font-bold text-[#041E49]">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#0B57D0]" />
            <span>
              {isAr
                ? `جاري سحب وتصنيف جميع رسائل الحساب من أول يوم حتى اليوم: ${syncProgress.synced_in_db} من أصل ${
                    syncProgress.total_in_gmail || "..."
                  } رسالة (${pct}%)`
                : `Syncing entire account history: ${syncProgress.synced_in_db} of ${
                    syncProgress.total_in_gmail || "..."
                  } emails (${pct}%)`}
            </span>
          </div>
          <div className="w-48 h-2 bg-white rounded-full overflow-hidden border border-blue-200 shrink-0">
            <div
              className="h-full bg-[#0B57D0] transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Top Action Toolbar */}
      <div className="h-12 px-4 border-b border-[#E1E5EA] flex items-center justify-between bg-white shrink-0">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            onClick={onRefresh}
            className="p-2 rounded-full hover:bg-gray-100 active:scale-90 text-[#444746] transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          {/* 3D Severity Filter Pills */}
          <div className="flex items-center gap-1 mx-1">
            {(
              [
                { id: "", label: t.allPriority },
                { id: "P0_CRITICAL", label: t.p0Critical },
                { id: "P1_HIGH", label: t.p1High },
                { id: "P2_NORMAL", label: t.p2Normal },
                { id: "P3_NOISE", label: t.p3Noise },
              ] as { id: SeverityLevel | ""; label: string }[]
            ).map((pill) => (
              <button
                key={pill.id}
                onClick={() => onSelectSeverity(pill.id)}
                className={`smooth-pill px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                  selectedSeverity === pill.id
                    ? "bg-[#D3E3FD] text-[#041E49] font-bold shadow-2xs"
                    : "text-[#444746] hover:bg-gray-100"
                }`}
              >
                {pill.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Weekly Digest + Page Size + Pagination Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={onTriggerDigest}
            disabled={digestLoading}
            className="smooth-pill hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 text-xs font-semibold"
          >
            <BookOpenCheck className="w-3.5 h-3.5" />
            <span>
              {digestLoading ? t.generatingDigest : t.runWeeklyDigest}
            </span>
          </button>

          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-[#F6F8FC] text-[#444746] font-medium outline-none"
            title={isAr ? "عدد الرسائل في الصفحة" : "Messages per page"}
          >
            <option value={100}>100 / {isAr ? "صفحة" : "page"}</option>
            <option value={250}>250 / {isAr ? "صفحة" : "page"}</option>
            <option value={500}>500 / {isAr ? "صفحة" : "page"}</option>
            <option value={1000}>1000 / {isAr ? "صفحة" : "page"}</option>
          </select>

          <span className="text-xs text-[#444746] font-medium whitespace-nowrap">
            {startIdx}–{endIdx} {t.ofTotal} {total}
          </span>

          <div className="flex items-center gap-0.5">
            <button
              onClick={() =>
                onPageOffsetChange(Math.max(0, pageOffset - pageSize))
              }
              disabled={!canPrev}
              className="p-1.5 rounded-full hover:bg-gray-100 disabled:opacity-35 text-[#444746] transition"
              title={isAr ? "الصفحة السابقة" : "Previous page"}
            >
              {isAr ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={() => onPageOffsetChange(pageOffset + pageSize)}
              disabled={!canNext}
              className="p-1.5 rounded-full hover:bg-gray-100 disabled:opacity-35 text-[#444746] transition"
              title={isAr ? "الصفحة التالية" : "Next page"}
            >
              {isAr ? (
                <ChevronLeft className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Authentic Gmail Category Tabs */}
      <div className="flex items-center border-b border-[#E1E5EA] px-2 bg-white shrink-0 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTabCategory === tab.category;
          return (
            <button
              key={tab.label}
              onClick={() => onSelectTabCategory(tab.category)}
              className={`smooth-pill flex items-center gap-2.5 px-6 py-3 text-xs font-medium border-b-[3px] min-w-[175px] ${
                isActive
                  ? `${tab.accentColor} font-bold bg-blue-50/30`
                  : "border-transparent text-[#444746] hover:bg-gray-50"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Email Rows or Sign-In Onboarding Card */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#E1E5EA]">
        {emails.length === 0 ? (
          <div className="py-16 px-4 flex flex-col items-center justify-center text-center animate-view-enter">
            {!gmailConnected ? (
              <div className="max-w-md w-full bg-[#F6F8FC] border border-[#D3E3FD] rounded-2xl p-6 space-y-4 shadow-2xs">
                <div className="w-12 h-12 rounded-2xl bg-[#D3E3FD] text-[#0B57D0] flex items-center justify-center mx-auto font-extrabold text-xl">
                  M
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-base font-bold text-[#1F1F1F]">
                    {isAr
                      ? "اربط حساب Gmail الخاص بك لبدء التصنيف الذكي"
                      : "Connect your Gmail account to start smart 3D classification"}
                  </h3>
                  <p className="text-xs text-[#444746] leading-relaxed">
                    {isAr
                      ? "تم تفريغ جميع البيانات التجريبية. سجّل الدخول بحساب Google الخاص بك مباشرة من هنا لسحب رسائلك الحقيقية وتصنيفها وحمايتها."
                      : "All demo data has been cleared. Sign in with your Google account directly from here to sync and classify your real inbox."}
                  </p>
                </div>
                <button
                  onClick={onOpenGoogleModal}
                  className="smooth-pill w-full py-3 px-5 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md"
                >
                  <LogIn className="w-4 h-4" />
                  <span>
                    {isAr
                      ? "تسجيل الدخول وربط حساب Google الآن"
                      : "Sign in & Connect Google Account"}
                  </span>
                </button>
                <div className="flex items-center justify-center gap-1.5 text-[11px] text-emerald-700 font-medium">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>
                    {isAr
                      ? "تشفير Fernet محلي للتوكن — لا يغادر جهازك أبداً"
                      : "Local Fernet token encryption — never leaves your server"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-sm text-[#444746]">{t.noMessagesMatch}</div>
            )}
          </div>
        ) : (
          emails.map((email, idx) => {
            const formattedDate = new Date(
              email.internal_date
            ).toLocaleDateString(isAr ? "ar-EG" : "en-US", {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });

            return (
              <div
                key={email.message_id}
                style={{ animationDelay: `${Math.min(idx * 15, 200)}ms` }}
                onClick={() => onOpenEmail(email)}
                className={`animate-row-enter gmail-row-smooth group flex items-center px-4 py-2.5 cursor-pointer relative ${
                  email.is_read
                    ? "bg-[#F2F6FC]/70 text-[#444746]"
                    : "bg-white text-[#1F1F1F] font-semibold"
                }`}
              >
                <button
                  onClick={(e) => onToggleStar(email, e)}
                  className="mx-2 text-gray-400 hover:text-amber-400 active:scale-125 transition-transform focus:outline-none shrink-0"
                >
                  <Star
                    className={`w-4 h-4 ${
                      email.is_starred
                        ? "fill-amber-400 text-amber-400"
                        : "text-gray-400"
                    }`}
                  />
                </button>

                <div className="w-44 shrink-0 truncate px-2 text-sm">
                  {email.sender_name || email.sender_email}
                </div>

                <div className="flex-1 min-w-0 flex items-center gap-2 px-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full border shrink-0 ${getSeverityBadgeStyle(
                      email.severity
                    )}`}
                  >
                    {email.severity.replace("_", " ")}
                  </span>

                  <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#EAF1FB] text-[#041E49] font-semibold shrink-0">
                    {t.categories[email.category] ||
                      email.category.replace("AI/", "")}
                  </span>

                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 ${
                      email.ttl_policy === "NEVER_DELETE"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {email.ttl_policy}
                  </span>

                  <div className="truncate text-sm">
                    <span className="text-[#1F1F1F]">{email.subject}</span>
                    <span className="mx-1.5 text-gray-400">—</span>
                    <span className="font-normal text-[#444746]">
                      {email.ai_summary || email.snippet}
                    </span>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-1">
                  <span className="text-xs text-[#444746] group-hover:hidden">
                    {formattedDate}
                  </span>

                  <div className="hidden group-hover:flex items-center gap-1 animate-view-enter">
                    <button
                      onClick={(e) => onToggleRead(email, e)}
                      className="p-1.5 rounded-full hover:bg-gray-200 text-[#444746] transition"
                    >
                      {email.is_read ? (
                        <Mail className="w-4 h-4" />
                      ) : (
                        <MailOpen className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={(e) => onMoveToTrash(email, e)}
                      className="p-1.5 rounded-full hover:bg-red-100 text-red-600 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    {email.gmail_link && (
                      <a
                        href={email.gmail_link}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-full hover:bg-blue-100 text-[#0B57D0] transition"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
