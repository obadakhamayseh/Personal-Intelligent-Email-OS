"use client";

import React, { useEffect, useState } from "react";
import {
  CreditCard,
  TrendingUp,
  AlertTriangle,
  Calendar,
  ExternalLink,
  DollarSign,
  Receipt,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { FinancialBurnRateResponse } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function FinancialBurnRateView() {
  const { lang } = useLanguage();
  const isAr = lang === "ar";

  const [data, setData] = useState<FinancialBurnRateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    EmailOSApi.getFinancialBurnRate()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-[#1F1F1F]">
              {isAr
                ? "الرادار المالي ولوحة استهلاك الاشتراكات (Subscription Burn-Rate Studio)"
                : "Subscription Burn-Rate & Financial Leakage Radar"}
            </h2>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
              AI Financial Agent
            </span>
          </div>
          <p className="text-xs text-[#444746] mt-1">
            {isAr
              ? "يحلل إيصالات وفواتير بريدك الإلكتروني تلقائياً لحساب معدل الصرف الشهري والسنوي، ورصد عمليات الدفع الفاشلة والفترات التجريبية."
              : "Automatically analyzes receipts and billing alerts to compute monthly/annual burn rate, failed payments, and upcoming renewals."}
          </p>
        </div>
      </div>

      {loading || !data ? (
        <div className="py-16 text-center text-xs font-bold text-[#0B57D0] animate-pulse">
          {isAr
            ? "جاري تحليل الفواتير وحساب معدل استهلاك الاشتراكات..."
            : "Analyzing receipts and computing subscription burn rate..."}
        </div>
      ) : (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="gmail-row-smooth p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
              <div className="flex items-center gap-1.5 text-xs text-emerald-800 font-bold">
                <DollarSign className="w-4 h-4" />
                <span>
                  {isAr
                    ? "معدل الاشتراكات الشهري المقدر"
                    : "Estimated Monthly Burn"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-emerald-950 mt-1">
                ${data.monthly_burn_usd.toFixed(2)}{" "}
                <span className="text-xs font-normal">USD/mo</span>
              </div>
              <div className="text-[11px] text-emerald-700 mt-1">
                {data.active_vendors_count}{" "}
                {isAr ? "جهات فوترة نشطة" : "active billing vendors"}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-blue-50 border border-blue-200">
              <div className="flex items-center gap-1.5 text-xs text-blue-800 font-bold">
                <TrendingUp className="w-4 h-4" />
                <span>
                  {isAr
                    ? "التكلفة السنوية المتوقعة"
                    : "Projected Annual Spend"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-blue-950 mt-1">
                ${data.annual_projected_usd.toFixed(2)}{" "}
                <span className="text-xs font-normal">USD/yr</span>
              </div>
              <div className="text-[11px] text-blue-700 mt-1">
                {isAr
                  ? `إجمالي المرصود: $${data.total_recorded_spend_usd.toFixed(2)}`
                  : `Total recorded: $${data.total_recorded_spend_usd.toFixed(2)}`}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-rose-50 border border-rose-200">
              <div className="flex items-center gap-1.5 text-xs text-rose-800 font-bold">
                <AlertTriangle className="w-4 h-4" />
                <span>
                  {isAr
                    ? "عمليات دفع فاشلة / معلّقة"
                    : "Failed Payment Alerts"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-rose-950 mt-1">
                {data.failed_payments_count}
              </div>
              <div className="text-[11px] text-rose-700 mt-1">
                {isAr
                  ? "تتطلب تحديث وسيلة الدفع"
                  : "Require payment method update"}
              </div>
            </div>

            <div className="gmail-row-smooth p-4 rounded-2xl bg-amber-50 border border-amber-200">
              <div className="flex items-center gap-1.5 text-xs text-amber-800 font-bold">
                <Calendar className="w-4 h-4" />
                <span>
                  {isAr
                    ? "فترات تجريبية / تجديدات قريبة"
                    : "Trials & Auto-Renewals"}
                </span>
              </div>
              <div className="text-2xl font-extrabold text-amber-950 mt-1">
                {data.trials_ending_count}
              </div>
              <div className="text-[11px] text-amber-700 mt-1">
                {isAr
                  ? `من إجمالي ${data.total_financial_emails} رسالة مالية`
                  : `Across ${data.total_financial_emails} financial emails`}
              </div>
            </div>
          </div>

          {/* Active Subscriptions & Vendors Breakdown */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-[#0B57D0]" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {isAr
                  ? `خريطة الاشتراكات وجهات الفوترة (${data.vendors.length})`
                  : `Detected Subscriptions & Billing Vendors (${data.vendors.length})`}
              </span>
            </div>

            {data.vendors.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">
                {isAr
                  ? "لا توجد إيصالات أو اشتراكات مرصودة حالياً."
                  : "No subscriptions or receipts detected yet."}
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {data.vendors.map((v, idx) => (
                  <div
                    key={v.vendor}
                    style={{ animationDelay: `${idx * 30}ms` }}
                    className="animate-row-enter gmail-row-smooth p-4 flex flex-wrap items-center justify-between gap-4 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-[#1F1F1F]">
                          {v.vendor}
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            v.latest_event_type === "PAYMENT_FAILED"
                              ? "bg-red-100 text-red-800"
                              : v.latest_event_type === "TRIAL_ENDING"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-emerald-100 text-emerald-800"
                          }`}
                        >
                          {v.latest_event_type}
                        </span>
                        <span className="text-gray-400">({v.sender_email})</span>
                      </div>
                      <div className="text-[11px] text-gray-500 flex flex-wrap items-center gap-4">
                        <span>
                          {isAr ? "عدد الفواتير:" : "Invoices:"}{" "}
                          <strong>{v.emails_count}</strong>
                        </span>
                        <span>
                          {isAr ? "آخر فوترة:" : "Last billed:"}{" "}
                          {new Date(v.last_billed_at).toLocaleDateString()}
                        </span>
                        <span className="text-[#0B57D0] font-semibold">
                          {isAr ? "التجديد المتوقع:" : "Est. next renewal:"}{" "}
                          {new Date(
                            v.estimated_next_renewal
                          ).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-end">
                        <div className="text-sm font-extrabold text-[#1F1F1F]">
                          {v.latest_amount
                            ? `${v.latest_amount} ${v.currency}`
                            : `$${v.total_spent_usd.toFixed(2)} USD`}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {isAr
                            ? `الإجمالي: $${v.total_spent_usd.toFixed(2)}`
                            : `Total: $${v.total_spent_usd.toFixed(2)}`}
                        </div>
                      </div>
                      <a
                        href={v.gmail_link}
                        target="_blank"
                        rel="noreferrer"
                        className="smooth-pill flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#EAF1FB] text-[#0B57D0] font-bold hover:bg-[#D3E3FD]"
                      >
                        <span>{isAr ? "فتح الفاتورة" : "Open"}</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Financial Transactions Table */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <Receipt className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {isAr
                  ? "سجل العمليات والإيصالات المالية الأخيرة"
                  : "Recent Financial Receipts & Billing Events"}
              </span>
            </div>
            <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
              {data.recent_transactions.map((tx) => (
                <div
                  key={tx.message_id}
                  className="p-3.5 flex items-center justify-between gap-3 text-xs hover:bg-gray-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#1F1F1F]">
                        {tx.vendor}
                      </span>
                      <span className="text-gray-400">•</span>
                      <span className="truncate text-[#444746]">
                        {tx.subject}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {tx.amount && (
                      <span className="font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                        {tx.amount} {tx.currency}
                      </span>
                    )}
                    <span className="text-gray-400 font-mono text-[11px]">
                      {new Date(tx.date).toLocaleDateString()}
                    </span>
                    <a
                      href={tx.gmail_link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#0B57D0] hover:underline font-bold"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
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
