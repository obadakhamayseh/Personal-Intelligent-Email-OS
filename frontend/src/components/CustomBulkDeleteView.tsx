"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Trash2,
  Calendar,
  Filter,
  CheckSquare,
  Square,
  RotateCcw,
  Search,
  Star,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import {
  CleanupAuditItem,
  CustomBulkPreviewResponse,
  SeverityLevel,
  SmartCategory,
} from "@/lib/types";
import { useLanguage } from "@/lib/i18n";
import { SMART_CATEGORY_META } from "./GmailSidebar";
import { getSeverityBadgeStyle } from "./EmailListView";

interface CustomBulkDeleteViewProps {
  onDeleted: () => void;
}

const ALL_SEVERITIES: SeverityLevel[] = [
  "P0_CRITICAL",
  "P1_HIGH",
  "P2_NORMAL",
  "P3_NOISE",
];

export default function CustomBulkDeleteView({
  onDeleted,
}: CustomBulkDeleteViewProps) {
  const { lang, t } = useLanguage();
  const isAr = lang === "ar";

  // User-controlled filter states (All categories & All severities enabled by default — user decides!)
  const [beforeDate, setBeforeDate] = useState<string>("");
  const [afterDate, setAfterDate] = useState<string>("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>(
    SMART_CATEGORY_META.map((c) => c.id)
  );
  const [selectedSeverities, setSelectedSeverities] =
    useState<string[]>(ALL_SEVERITIES);
  const [senderQuery, setSenderQuery] = useState<string>("");
  const [keywordQuery, setKeywordQuery] = useState<string>("");
  const [readFilter, setReadFilter] = useState<"ALL" | "UNREAD" | "READ">(
    "ALL"
  );
  const [excludeStarred, setExcludeStarred] = useState<boolean>(false);
  const [maxLimit, setMaxLimit] = useState<number>(1000);

  const [preview, setPreview] = useState<CustomBulkPreviewResponse | null>(
    null
  );
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [auditLogs, setAuditLogs] = useState<CleanupAuditItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [banner, setBanner] = useState<string | null>(null);

  const toEndOfDayIso = (dateStr: string) => {
    if (!dateStr) return undefined;
    return `${dateStr}T23:59:59.999Z`;
  };

  const toStartOfDayIso = (dateStr: string) => {
    if (!dateStr) return undefined;
    return `${dateStr}T00:00:00.000Z`;
  };

  const fetchCustomPreview = useCallback(async () => {
    setLoading(true);
    try {
      const payload = {
        before_date: toEndOfDayIso(beforeDate),
        after_date: toStartOfDayIso(afterDate),
        categories: selectedCategories,
        severities: selectedSeverities,
        sender_query: senderQuery.trim() || undefined,
        keyword_query: keywordQuery.trim() || undefined,
        unread_only:
          readFilter === "ALL" ? null : readFilter === "UNREAD" ? true : false,
        exclude_starred: excludeStarred,
        limit: maxLimit,
      };
      const [prevData, logsData] = await Promise.all([
        EmailOSApi.previewCustomBulkDelete(payload),
        EmailOSApi.listAuditLogs(),
      ]);
      setPreview(prevData);
      setSelectedIds(new Set(prevData.messages.map((m) => m.message_id)));
      setAuditLogs(logsData);
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [
    beforeDate,
    afterDate,
    selectedCategories,
    selectedSeverities,
    senderQuery,
    keywordQuery,
    readFilter,
    excludeStarred,
    maxLimit,
  ]);

  // Automatically apply filters whenever any filter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCustomPreview();
    }, 180);
    return () => clearTimeout(timer);
  }, [fetchCustomPreview]);

  const applyQuickPresetDays = (daysAgo: number | null) => {
    if (daysAgo === null) {
      setBeforeDate("");
      setAfterDate("");
      return;
    }
    const target = new Date();
    target.setDate(target.getDate() - daysAgo);
    const yyyy = target.getFullYear();
    const mm = String(target.getMonth() + 1).padStart(2, "0");
    const dd = String(target.getDate()).padStart(2, "0");
    setBeforeDate(`${yyyy}-${mm}-${dd}`);
  };

  const toggleCategory = (catId: string) => {
    setSelectedCategories((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId]
    );
  };

  const toggleSeverity = (sev: string) => {
    setSelectedSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev]
    );
  };

  const toggleMessageId = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllMessages = () => {
    if (!preview) return;
    if (selectedIds.size === preview.messages.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(preview.messages.map((m) => m.message_id)));
    }
  };

  const handleExecuteDirectDelete = async () => {
    if (selectedIds.size === 0) return;
    setExecuting(true);
    setBanner(null);
    try {
      const audit = await EmailOSApi.executeCustomBulkDelete({
        message_ids: Array.from(selectedIds),
      });
      setBanner(
        isAr
          ? `✅ تم نقل ${audit.total_messages} رسالة إلى مهملات Gmail بنجاح (رقم الدفعة: ${audit.batch_id}). يمكنك التراجع بضغطة واحدة من السجل بالأسفل.`
          : `✅ Moved ${audit.total_messages} messages to Gmail Trash (Batch: ${audit.batch_id}). You can undo anytime below.`
      );
      await fetchCustomPreview();
      onDeleted();
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleUndoBatch = async (batchId: string) => {
    setExecuting(true);
    try {
      const restored = await EmailOSApi.undoCleanup(batchId);
      setBanner(
        isAr
          ? `♻️ تمت استعادة ${restored.total_messages} رسالة من الدفعة ${restored.batch_id} إلى البريد الوارد بنجاح.`
          : `♻️ Restored ${restored.total_messages} messages from batch ${restored.batch_id} back to Inbox.`
      );
      await fetchCustomPreview();
      onDeleted();
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-[#1F1F1F]">
              {isAr
                ? "استوديو الحذف الجماعي المخصص (تحكم مباشر بالكامل)"
                : "Direct Bulk Delete Studio (100% User-Controlled)"}
            </h2>
            <span className="px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[11px] font-bold">
              {isAr ? "بدون قيود أو دروع إجبارية" : "No Forced Shields"}
            </span>
          </div>
          <p className="text-xs text-[#444746] mt-1">
            {isAr
              ? "أنت من يحدد التاريخ والفئات والأولويات والمرسلين بدقة. يتم تطبيق أي تغيير في التاريخ أو الفلاتر فوراً وعرض الرسائل لتحديد ما تريد حذفه."
              : "You decide the exact cutoff date, categories, priorities, and senders. Any filter change applies immediately."}
          </p>
        </div>

        <button
          onClick={handleExecuteDirectDelete}
          disabled={executing || selectedIds.size === 0}
          className="smooth-pill flex items-center gap-2 px-5 py-2.5 rounded-full bg-red-600 hover:bg-red-700 disabled:bg-gray-300 text-white text-xs font-bold shadow-md"
        >
          <Trash2 className="w-4 h-4" />
          <span>
            {executing
              ? isAr
                ? "جاري الحذف الجماعي..."
                : "Deleting Selected..."
              : isAr
              ? `حذف الرسائل المحددة الآن (${selectedIds.size} رسالة)`
              : `Delete Selected Now (${selectedIds.size} msgs)`}
          </span>
        </button>
      </div>

      {banner && (
        <div className="animate-view-enter p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs font-bold text-blue-900">
          {banner}
        </div>
      )}

      {/* Control Panel: Dates + Quick Presets + Search + Toggles */}
      <div className="p-5 rounded-2xl bg-[#F6F8FC] border border-[#E1E5EA] space-y-5">
        {/* Row 1: Date Range & Quick Presets */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs font-bold text-[#1F1F1F] mb-1">
                <Calendar className="w-3.5 h-3.5 inline mx-1 text-[#0B57D0]" />
                {isAr ? "من تاريخ (اختياري):" : "From Date (Optional):"}
              </label>
              <input
                type="date"
                value={afterDate}
                onChange={(e) => setAfterDate(e.target.value)}
                className="bg-white border border-gray-300 focus:border-[#0B57D0] rounded-xl px-3 py-2 text-xs font-semibold outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#1F1F1F] mb-1">
                <Calendar className="w-3.5 h-3.5 inline mx-1 text-red-600" />
                {isAr
                  ? "إلى / قبل تاريخ القطع (شامل هذا اليوم):"
                  : "Before / Up to Cutoff Date (Inclusive):"}
              </label>
              <input
                type="date"
                value={beforeDate}
                onChange={(e) => setBeforeDate(e.target.value)}
                className="bg-white border-2 border-red-300 focus:border-red-600 rounded-xl px-3 py-2 text-xs font-bold outline-none"
              />
            </div>
          </div>

          {/* Quick Date Presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-bold text-[#444746] mx-1">
              {isAr ? "اختيار سريع للتاريخ:" : "Quick Cutoff:"}
            </span>
            {[
              { label: isAr ? "كل التواريخ" : "All Dates", days: null },
              { label: isAr ? "أقدم من 7 أيام" : "> 7 Days", days: 7 },
              { label: isAr ? "أقدم من 30 يوماً" : "> 30 Days", days: 30 },
              { label: isAr ? "أقدم من 3 أشهر" : "> 3 Months", days: 90 },
              { label: isAr ? "أقدم من 6 أشهر" : "> 6 Months", days: 180 },
              { label: isAr ? "أقدم من سنة" : "> 1 Year", days: 365 },
            ].map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyQuickPresetDays(p.days)}
                className="smooth-pill px-3 py-1.5 rounded-full bg-white hover:bg-[#D3E3FD] text-[#041E49] border border-gray-200 text-xs font-semibold shadow-2xs"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Sender, Keyword, Read State, Starred */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2 border-t border-gray-200/80">
          <div>
            <label className="block text-[11px] font-bold text-[#444746] mb-1">
              {isAr ? "فلتر بالمرسل (اسم أو بريد):" : "Filter by Sender:"}
            </label>
            <div className="flex items-center bg-white rounded-xl border border-gray-300 px-3 py-1.5">
              <Search className="w-3.5 h-3.5 text-gray-400 mx-1" />
              <input
                type="text"
                value={senderQuery}
                onChange={(e) => setSenderQuery(e.target.value)}
                placeholder={isAr ? "مثال: linkedin أو vercel..." : "e.g. vercel..."}
                className="w-full text-xs outline-none bg-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#444746] mb-1">
              {isAr ? "فلتر بكلمة في الموضوع/المحتوى:" : "Filter by Keyword:"}
            </label>
            <div className="flex items-center bg-white rounded-xl border border-gray-300 px-3 py-1.5">
              <Filter className="w-3.5 h-3.5 text-gray-400 mx-1" />
              <input
                type="text"
                value={keywordQuery}
                onChange={(e) => setKeywordQuery(e.target.value)}
                placeholder={isAr ? "كلمة مفتاحية..." : "Keyword..."}
                className="w-full text-xs outline-none bg-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#444746] mb-1">
              {isAr ? "حالة القراءة:" : "Read Status:"}
            </label>
            <select
              value={readFilter}
              onChange={(e) =>
                setReadFilter(e.target.value as "ALL" | "UNREAD" | "READ")
              }
              className="w-full bg-white rounded-xl border border-gray-300 px-3 py-2 text-xs font-semibold outline-none"
            >
              <option value="ALL">
                {isAr ? "الكل (المقروءة وغير المقروءة)" : "All (Read & Unread)"}
              </option>
              <option value="UNREAD">
                {isAr ? "غير المقروءة فقط" : "Unread Only"}
              </option>
              <option value="READ">
                {isAr ? "المقروءة فقط" : "Read Only"}
              </option>
            </select>
          </div>

          <div className="flex flex-col justify-end">
            <label className="flex items-center gap-2 bg-white rounded-xl border border-gray-300 px-3 py-2 text-xs font-semibold cursor-pointer">
              <input
                type="checkbox"
                checked={excludeStarred}
                onChange={(e) => setExcludeStarred(e.target.checked)}
              />
              <span>
                {isAr
                  ? "استثناء الرسائل المميزة بنجمة ⭐"
                  : "Exclude Starred Messages ⭐"}
              </span>
            </label>
          </div>
        </div>

        {/* Row 3: Priority / Severity Checkboxes (User chooses whether P0/P1 are included!) */}
        <div className="pt-2 border-t border-gray-200/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#1F1F1F]">
              <SlidersHorizontal className="w-3.5 h-3.5 inline mx-1 text-[#0B57D0]" />
              {isAr
                ? "درجات الأهمية المشمولة في الحذف (أنت من يقرر):"
                : "Priorities Included in Deletion (You Decide):"}
            </span>
            <div className="flex gap-2 text-[11px]">
              <button
                type="button"
                onClick={() => setSelectedSeverities(ALL_SEVERITIES)}
                className="text-[#0B57D0] font-bold hover:underline"
              >
                {isAr ? "تحديد كل الأولويات" : "Select All"}
              </button>
              <span>•</span>
              <button
                type="button"
                onClick={() => setSelectedSeverities(["P2_NORMAL", "P3_NOISE"])}
                className="text-gray-600 font-semibold hover:underline"
              >
                {isAr ? "P2 و P3 فقط" : "P2 & P3 Only"}
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {ALL_SEVERITIES.map((sev) => {
              const active = selectedSeverities.includes(sev);
              return (
                <button
                  key={sev}
                  type="button"
                  onClick={() => toggleSeverity(sev)}
                  className={`smooth-pill px-3.5 py-1.5 rounded-full text-xs border flex items-center gap-1.5 ${
                    active
                      ? "bg-[#D3E3FD] border-[#0B57D0] text-[#041E49] font-bold"
                      : "bg-white border-gray-200 text-gray-400"
                  }`}
                >
                  {active ? (
                    <CheckSquare className="w-3.5 h-3.5 text-[#0B57D0]" />
                  ) : (
                    <Square className="w-3.5 h-3.5" />
                  )}
                  <span>{sev}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Row 4: Smart Categories Multi-Select */}
        <div className="pt-2 border-t border-gray-200/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#1F1F1F]">
              <Sparkles className="w-3.5 h-3.5 inline mx-1 text-[#0B57D0]" />
              {isAr
                ? "الفئات المشمولة في الحذف:"
                : "Categories Included in Deletion:"}
            </span>
            <div className="flex gap-2 text-[11px]">
              <button
                type="button"
                onClick={() =>
                  setSelectedCategories(SMART_CATEGORY_META.map((c) => c.id))
                }
                className="text-[#0B57D0] font-bold hover:underline"
              >
                {isAr ? "تحديد كل الفئات" : "Select All Categories"}
              </button>
              <span>•</span>
              <button
                type="button"
                onClick={() => setSelectedCategories([])}
                className="text-gray-600 font-semibold hover:underline"
              >
                {isAr ? "إلغاء تحديد الكل" : "Clear All"}
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {SMART_CATEGORY_META.map((cat) => {
              const active = selectedCategories.includes(cat.id);
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => toggleCategory(cat.id)}
                  className={`smooth-pill px-3 py-1.5 rounded-full text-xs border flex items-center gap-1.5 ${
                    active
                      ? "bg-[#D3E3FD] border-[#0B57D0] text-[#041E49] font-bold"
                      : "bg-white border-gray-200 text-gray-400"
                  }`}
                >
                  {active ? (
                    <CheckSquare className="w-3.5 h-3.5 text-[#0B57D0]" />
                  ) : (
                    <Square className="w-3.5 h-3.5" />
                  )}
                  <span>{t.categories[cat.id]}</span>
                  {preview && preview.category_counts[cat.id] ? (
                    <span className="px-1.5 py-0.2 rounded-full bg-white text-[10px] text-[#0B57D0]">
                      {preview.category_counts[cat.id]}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Live Preview Table of Matching Messages with Individual Selection */}
      {preview && (
        <div className="border border-gray-200 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleSelectAllMessages}
                className="flex items-center gap-1.5 text-xs font-bold text-[#0B57D0] hover:underline"
              >
                {selectedIds.size === preview.messages.length &&
                preview.messages.length > 0 ? (
                  <CheckSquare className="w-4 h-4" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
                <span>
                  {selectedIds.size === preview.messages.length
                    ? isAr
                      ? "إلغاء تحديد الكل"
                      : "Deselect All"
                    : isAr
                    ? "تحديد كل النتائج"
                    : "Select All"}
                </span>
              </button>
              <span className="text-xs font-bold text-[#1F1F1F]">
                {isAr
                  ? `الرسائل المطابقة للفلاتر: ${preview.total_matching} رسالة — المحدد للحذف: ${selectedIds.size} رسالة (${preview.estimated_mb} MB)`
                  : `Matching: ${preview.total_matching} msgs — Selected for deletion: ${selectedIds.size} msgs (${preview.estimated_mb} MB)`}
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-500">
                {isAr ? "حد الجلب:" : "Max fetch:"}
              </span>
              <select
                value={maxLimit}
                onChange={(e) => setMaxLimit(Number(e.target.value))}
                className="border border-gray-300 rounded-lg px-2 py-1 bg-white font-semibold"
              >
                <option value={500}>500</option>
                <option value={1000}>1000</option>
                <option value={2500}>2500</option>
                <option value={5000}>5000</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="p-10 text-center text-xs font-bold text-[#0B57D0] animate-pulse">
              {isAr
                ? "جاري تحديث قائمة الرسائل المطابقة..."
                : "Updating matching messages..."}
            </div>
          ) : preview.messages.length === 0 ? (
            <div className="p-10 text-center text-xs text-gray-500">
              {isAr
                ? "لا توجد رسائل مطابقة لتاريخ القطع أو الفلاتر المحددة حالياً."
                : "No messages match the current cutoff date or filters."}
            </div>
          ) : (
            <div className="max-h-[420px] overflow-y-auto divide-y divide-gray-100">
              {preview.messages.map((msg) => {
                const checked = selectedIds.has(msg.message_id);
                return (
                  <div
                    key={msg.message_id}
                    onClick={() => toggleMessageId(msg.message_id)}
                    className={`px-4 py-2.5 flex items-center justify-between gap-3 text-xs cursor-pointer transition ${
                      checked ? "bg-rose-50/40 hover:bg-rose-50/80" : "bg-white hover:bg-gray-50 opacity-60"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="rounded text-red-600 shrink-0"
                      />
                      {msg.is_starred && (
                        <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400 shrink-0" />
                      )}
                      <span className="w-40 truncate font-semibold text-[#1F1F1F] shrink-0">
                        {msg.sender_name || msg.sender_email}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full border shrink-0 ${getSeverityBadgeStyle(
                          msg.severity
                        )}`}
                      >
                        {msg.severity}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#EAF1FB] text-[#041E49] font-semibold shrink-0">
                        {t.categories[msg.category] || msg.category}
                      </span>
                      <span className="truncate text-[#1F1F1F]">
                        {msg.subject}
                      </span>
                    </div>

                    <div className="text-[11px] text-gray-500 shrink-0 font-mono">
                      {new Date(msg.internal_date).toLocaleDateString(
                        isAr ? "ar-EG" : "en-US",
                        {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        }
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Audit Trail & 1-Click Undo */}
      <div className="border border-gray-200 rounded-2xl overflow-hidden">
        <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200">
          <span className="text-xs font-bold text-[#1F1F1F]">
            {t.auditTrailTitle}
          </span>
        </div>
        {auditLogs.length === 0 ? (
          <div className="p-6 text-center text-xs text-gray-500">
            {t.noAuditBatches}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {auditLogs.map((log) => (
              <div
                key={log.batch_id}
                className="p-4 flex items-center justify-between text-xs hover:bg-gray-50 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-[#1F1F1F]">
                      {log.batch_id}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        log.status === "RESTORED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {log.status}
                    </span>
                  </div>
                  <div className="text-gray-500">
                    {t.affectedLabel} <strong>{log.total_messages}</strong> •{" "}
                    {t.executedAtLabel}{" "}
                    {new Date(log.created_at).toLocaleString()}
                  </div>
                </div>

                {log.status !== "RESTORED" && log.total_messages > 0 && (
                  <button
                    onClick={() => handleUndoBatch(log.batch_id)}
                    disabled={executing}
                    className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{t.undoRestoreBatch}</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
