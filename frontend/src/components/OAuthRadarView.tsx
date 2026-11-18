"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Clock,
  CreditCard,
  ExternalLink,
  MapPin,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import {
  DeadlineItem,
  FinancialEventItem,
  OAuthServiceItem,
} from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function OAuthRadarView() {
  const { t } = useLanguage();
  const [oauthApps, setOauthApps] = useState<OAuthServiceItem[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [financials, setFinancials] = useState<FinancialEventItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      EmailOSApi.getOAuthMap(),
      EmailOSApi.getDeadlines(),
      EmailOSApi.getFinancialEvents(),
    ])
      .then(([oa, dl, fn]) => {
        setOauthApps(oa);
        setDeadlines(dl);
        setFinancials(fn);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-[#1F1F1F]">{t.oauthViewTitle}</h2>
        <p className="text-xs text-[#444746] mt-0.5">{t.oauthViewSubtitle}</p>
      </div>

      {loading ? (
        <div className="py-12 text-center text-xs text-gray-500 animate-pulse">
          Loading...
        </div>
      ) : (
        <>
          {/* 1. OAuth & Connected Services Registry */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {t.oauthRegistryHeader} ({oauthApps.length})
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {oauthApps.map((app, idx) => (
                <div
                  key={app.id}
                  style={{ animationDelay: `${idx * 35}ms` }}
                  className="animate-row-enter gmail-row-smooth p-4 flex flex-wrap items-center justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#1F1F1F]">
                        {app.service_name}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px]">
                        {app.risk_level}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-700 text-[10px]">
                        {app.last_event_type}
                      </span>
                    </div>
                    <p className="text-gray-600">{app.scopes_summary}</p>
                    <div className="flex items-center gap-4 text-[11px] text-gray-500">
                      <span>
                        {t.firstSeen}{" "}
                        {new Date(app.first_seen_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {app.last_ip_or_location || "N/A"}
                      </span>
                    </div>
                  </div>
                  {app.gmail_link && (
                    <a
                      href={app.gmail_link}
                      target="_blank"
                      rel="noreferrer"
                      className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#EAF1FB] text-[#0B57D0] font-bold hover:bg-[#D3E3FD]"
                    >
                      <span>{t.inspectSecurityEmail}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 2. Action SLA Deadlines */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-orange-600" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {t.upcomingSlaHeader} ({deadlines.length})
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {deadlines.map((dl) => (
                <div
                  key={dl.id}
                  className="gmail-row-smooth p-4 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-[#1F1F1F]">{dl.title}</div>
                    <div className="text-orange-700 font-semibold mt-0.5">
                      {t.dueLabel} {new Date(dl.deadline_at).toLocaleString()}
                    </div>
                  </div>
                  {dl.gmail_link && (
                    <a
                      href={dl.gmail_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-[#0B57D0] font-bold hover:underline"
                    >
                      <span>{t.openThread}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 3. Financial Leakage & Receipts */}
          <div className="border border-gray-200 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-[#1F1F1F]">
                {t.financialHeader} ({financials.length})
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {financials.map((fn) => (
                <div
                  key={fn.id}
                  className="gmail-row-smooth p-4 flex items-center justify-between text-xs"
                >
                  <div>
                    <span className="font-bold text-[#1F1F1F]">
                      {fn.vendor}
                    </span>{" "}
                    <span
                      className={`mx-2 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${fn.event_type === "PAYMENT_FAILED"
                          ? "bg-red-100 text-red-800"
                          : "bg-emerald-100 text-emerald-800"
                        }`}
                    >
                      {fn.event_type}
                    </span>
                  </div>
                  <div className="font-bold text-gray-800">
                    {fn.amount
                      ? `${fn.amount} ${fn.currency || "USD"}`
                      : t.protectedReceipt}
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
