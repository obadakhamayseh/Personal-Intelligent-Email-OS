"use client";

import React, { useEffect, useState } from "react";
import { BellOff, Archive, Ban, CheckCircle } from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { SenderStatItem } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function DeadSubscriptionsView() {
  const { t } = useLanguage();
  const [senders, setSenders] = useState<SenderStatItem[]>([]);
  const [deadOnly, setDeadOnly] = useState<boolean>(false);
  const [banner, setBanner] = useState<string | null>(null);

  const loadSenders = async (onlyDead: boolean) => {
    const res = await EmailOSApi.listSenders(onlyDead);
    setSenders(res);
  };

  useEffect(() => {
    loadSenders(deadOnly);
  }, [deadOnly]);

  const handleAutoArchive = async (email: string) => {
    const res = await EmailOSApi.autoArchiveSender(email);
    setBanner(`✅ #${res.rule_id} — ${email}`);
    loadSenders(deadOnly);
  };

  const handleUnsubscribe = async (email: string) => {
    const res = await EmailOSApi.unsubscribeSender(email);
    setBanner(`🔕 RFC-8058 — ${res.sender_email}`);
    loadSenders(deadOnly);
  };

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F1F1F]">
            {t.deadSubsTitle}
          </h2>
          <p className="text-xs text-[#444746] mt-0.5">{t.deadSubsSubtitle}</p>
        </div>

        <label className="smooth-pill flex items-center gap-2 text-xs font-bold text-purple-800 bg-purple-50 px-3.5 py-2 rounded-full border border-purple-200 cursor-pointer">
          <input
            type="checkbox"
            checked={deadOnly}
            onChange={(e) => setDeadOnly(e.target.checked)}
          />
          <span>{t.showDeadOnly}</span>
        </label>
      </div>

      {banner && (
        <div className="animate-view-enter p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-900">
          {banner}
        </div>
      )}

      <div className="border border-gray-200 rounded-2xl overflow-hidden">
        <table className="w-full text-start text-xs">
          <thead className="bg-[#F6F8FC] border-b border-gray-200 text-[#444746]">
            <tr>
              <th className="py-3 px-4 text-start">{t.colSender}</th>
              <th className="py-3 px-4 text-start">{t.colReceivedRead}</th>
              <th className="py-3 px-4 text-start">{t.colUnreadRate}</th>
              <th className="py-3 px-4 text-start">{t.colNoiseScore}</th>
              <th className="py-3 px-4 text-start">{t.colStatus}</th>
              <th className="py-3 px-4 text-end">{t.colActions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {senders.map((s, idx) => (
              <tr
                key={s.id}
                style={{ animationDelay: `${idx * 30}ms` }}
                className="animate-row-enter hover:bg-gray-50 transition"
              >
                <td className="py-3 px-4">
                  <div className="font-bold text-[#1F1F1F]">
                    {s.sender_name || s.sender_email}
                  </div>
                  <div className="text-gray-500">{s.sender_email}</div>
                </td>
                <td className="py-3 px-4">
                  {s.received_count} / {s.read_count}
                </td>
                <td className="py-3 px-4 font-bold">
                  {s.unread_rate_percent}%
                </td>
                <td className="py-3 px-4">
                  <span
                    className={`px-2.5 py-0.5 rounded-full font-bold ${
                      s.noise_score >= 90
                        ? "bg-red-100 text-red-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {s.noise_score.toFixed(0)} / 100
                  </span>
                </td>
                <td className="py-3 px-4">
                  {s.is_muted ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">
                      <CheckCircle className="w-3 h-3" /> {t.mutedRuleActive}
                    </span>
                  ) : s.is_dead_subscription ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 font-bold">
                      <BellOff className="w-3 h-3" /> {t.deadSubBadge}
                    </span>
                  ) : (
                    <span className="text-gray-500">{t.activeSenderBadge}</span>
                  )}
                </td>
                <td className="py-3 px-4 text-end space-x-2 space-x-reverse">
                  <button
                    onClick={() => handleAutoArchive(s.sender_email)}
                    className="smooth-pill inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#EAF1FB] hover:bg-[#D3E3FD] text-[#041E49] font-bold mx-1"
                  >
                    <Archive className="w-3.5 h-3.5" />
                    <span>{t.autoArchiveBtn}</span>
                  </button>
                  <button
                    onClick={() => handleUnsubscribe(s.sender_email)}
                    className="smooth-pill inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold mx-1"
                  >
                    <Ban className="w-3.5 h-3.5" />
                    <span>{t.unsubscribeBtn}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
