"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  HardDrive,
  Clock,
  Zap,
  PieChart,
  Users,
  Calendar,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { ExecutiveAnalyticsResponse } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function AnalyticsDashboardView() {
  const { lang, t } = useLanguage();
  const isAr = lang === "ar";

  const [data, setData] = useState<ExecutiveAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    EmailOSApi.getExecutiveAnalytics()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const dayMapAr: Record<string, string> = {
    Mon: "الإثنين",
    Tue: "الثلاثاء",
    Wed: "الأربعاء",
    Thu: "الخميس",
    Fri: "الجمعة",
    Sat: "السبت",
    Sun: "الأحد",
  };

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-[#1F1F1F]">
              {isAr
                ? "لوحة التحليلات والإحصائيات البصرية للبريد (Executive Inbox Analytics)"
                : "Executive Inbox Analytics & Telemetry Dashboard"}
            </h2>
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-800 text-[11px] font-bold">
              Telemetry & ROI
            </span>
          </div>
          <p className="text-xs text-[#444746] mt-1">
            {isAr
              ? "تحليل شامل لحجم بريدك، المساحة المستعادة، ساعات القراءة الموفّرة، وكفاءة محرك القواعد الفوري Tier 1 مقابل الذكاء الاصطناعي."
              : "Comprehensive telemetry across inbox volume, storage reclaimed, hours saved by AI summaries, and Tier 1 vs Tier 2 engine efficiency."}
          </p>
        </div>
      </div>

      {loading || !data ? (
        <div className="py-16 text-center text-xs font-bold text-[#0B57D0] animate-pulse">
          {isAr
            ? "جاري حساب الإحصائيات والرسوم البيانية لبريدك..."
            : "Computing inbox analytics and visual charts..."}
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="gmail-row-smooth p-4 rounded-2xl bg-indigo-50 border border-indigo-200">
              <div className="flex items-center gap-1.5 text-xs text-indigo-800 font-bold">
                <BarChart3 className="w-4 h-4" />
                <span>
                  {isAr
                    ? "إجمالي الرسائل المصنّفة"
                    : "Total Classified Emails"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-indigo-950 mt-1">
                {data.total_all_time_emails.toLocaleString()}
              </div>
              <div className="text-[11px] text-indigo-700 mt-1">
                {isAr
                  ? `${data.active_inbox_emails} نشطة • ${data.trashed_emails_count} محذوفة`
                  : `${data.active_inbox_emails} active • ${data.trashed_emails_count} trashed`}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
              <div className="flex items-center gap-1.5 text-xs text-emerald-800 font-bold">
                <HardDrive className="w-4 h-4" />
                <span>
                  {isAr
                    ? "المساحة التخزينية المستعادة"
                    : "Storage Space Freed"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-emerald-950 mt-1">
                {data.storage_freed_mb.toFixed(1)} MB
              </div>
              <div className="text-[11px] text-emerald-700 mt-1">
                {isAr
                  ? `الحجم النشط الحالي: ${data.active_storage_mb} MB`
                  : `Current active size: ${data.active_storage_mb} MB`}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-amber-50 border border-amber-200">
              <div className="flex items-center gap-1.5 text-xs text-amber-800 font-bold">
                <Clock className="w-4 h-4" />
                <span>
                  {isAr
                    ? "وقت القراءة الموفّر بالذكاء الاصطناعي"
                    : "Reading Time Saved by AI"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-amber-950 mt-1">
                {data.estimated_hours_saved}{" "}
                <span className="text-xs font-normal">
                  {isAr ? "ساعة" : "hours"}
                </span>
              </div>
              <div className="text-[11px] text-amber-700 mt-1">
                {isAr
                  ? "عبر التلخيص الفوري والفرز التلقائي"
                  : "Via 1-sentence AI summaries & auto-triage"}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-blue-50 border border-blue-200">
              <div className="flex items-center gap-1.5 text-xs text-blue-800 font-bold">
                <Zap className="w-4 h-4" />
                <span>
                  {isAr
                    ? "كفاءة محرك Tier 1 (0ms مجاني)"
                    : "Tier 1 (0ms Zero-Cost) Ratio"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-blue-950 mt-1">
                {data.tier1_efficiency_percent}%
              </div>
              <div className="text-[11px] text-blue-700 mt-1">
                Tier 1: {data.tier1_zero_cost_count} • Tier 2 LLM:{" "}
                {data.tier2_llm_count}
              </div>
            </div>
          </div>

          {/* Row 2: Category Distribution & Weekly Activity Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Smart Category Visual Bars */}
            <div className="lg:col-span-2 border border-gray-200 rounded-2xl p-5 space-y-4">
              <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                <PieChart className="w-4 h-4 text-[#0B57D0]" />
                <h3 className="text-xs font-bold text-[#1F1F1F]">
                  {isAr
                    ? "التوزيع البصري للرسائل والحجم حسب الفئات الذكية (AI/*)"
                    : "Smart Category Volume & Storage Breakdown"}
                </h3>
              </div>

              <div className="space-y-3">
                {data.category_distribution.map((item) => (
                  <div key={item.category} className="space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#1F1F1F]">
                        {t.categories[item.category] || item.category}
                      </span>
                      <span className="text-gray-600 font-medium">
                        <strong>{item.count}</strong>{" "}
                        {isAr ? "رسالة" : "msgs"} ({item.percentage}%) •{" "}
                        <span className="text-[#0B57D0] font-semibold">
                          {item.size_mb} MB
                        </span>
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#0B57D0] to-blue-400 rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.max(3, item.percentage)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Day of Week Traffic Chart & Severity Distribution */}
            <div className="border border-gray-200 rounded-2xl p-5 flex flex-col justify-between space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                  <Calendar className="w-4 h-4 text-purple-600" />
                  <h3 className="text-xs font-bold text-[#1F1F1F]">
                    {isAr
                      ? "كثافة البريد الوارد حسب أيام الأسبوع"
                      : "Inbox Traffic by Day of Week"}
                  </h3>
                </div>

                {(() => {
                  const maxDay = Math.max(
                    1,
                    ...data.day_of_week_activity.map((d) => d.count)
                  );
                  return (
                    <div className="space-y-2">
                      {data.day_of_week_activity.map((d) => {
                        const pct = Math.round((d.count / maxDay) * 100);
                        return (
                          <div
                            key={d.day}
                            className="flex items-center gap-2 text-xs"
                          >
                            <span className="w-16 font-semibold text-gray-600">
                              {isAr ? dayMapAr[d.day] || d.day : d.day}
                            </span>
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-purple-600 rounded-full"
                                style={{ width: `${Math.max(4, pct)}%` }}
                              />
                            </div>
                            <span className="w-10 text-end font-bold text-[#1F1F1F]">
                              {d.count}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>

              {/* Priority Breakdown */}
              <div className="pt-4 border-t border-gray-100 space-y-2">
                <span className="text-xs font-bold text-[#1F1F1F] block">
                  {isAr ? "توزيع درجات الأهمية:" : "Severity Breakdown:"}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  {data.severity_distribution.map((s) => (
                    <div
                      key={s.severity}
                      className="p-2.5 rounded-xl bg-[#F6F8FC] border border-gray-200 flex items-center justify-between text-xs"
                    >
                      <span className="font-bold text-gray-700">
                        {s.severity.replace("_", " ")}
                      </span>
                      <span className="font-extrabold text-[#0B57D0]">
                        {s.count} ({s.percentage}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Row 3: Top 10 Storage & Volume Senders */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <Users className="w-4 h-4 text-[#0B57D0]" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {isAr
                  ? "أكثر 10 مرسلين إرسالاً واستهلاكاً لمساحة بريدك"
                  : "Top 10 Highest-Volume & Storage-Consuming Senders"}
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {data.top_senders.map((s, idx) => (
                <div
                  key={s.sender_email}
                  className="p-3.5 flex items-center justify-between gap-4 text-xs hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-6 h-6 rounded-full bg-[#EAF1FB] text-[#0B57D0] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <div className="truncate">
                      <div className="font-bold text-[#1F1F1F] truncate">
                        {s.sender_name}
                      </div>
                      <div className="text-gray-500 truncate">
                        {s.sender_email}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <span className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-900 font-bold">
                      {s.count} {isAr ? "رسالة" : "msgs"} (
                      {s.unread_count} {isAr ? "غير مقروءة" : "unread"})
                    </span>
                    <span className="w-20 text-end font-mono font-bold text-gray-700">
                      {s.total_mb} MB
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
