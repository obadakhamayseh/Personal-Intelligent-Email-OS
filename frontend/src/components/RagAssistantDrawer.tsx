"use client";

import React, { useState } from "react";
import { X, Sparkles, Send, ExternalLink } from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { RagQueryResponse } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface RagAssistantDrawerProps {
  open: boolean;
  onClose: () => void;
}

const SAMPLE_QUESTIONS = [
  "ما هو الموعد النهائي لمشروع هندسة النظم الذكية وإيصال Google Play؟",
  "Why did the Vercel deployment fail and what is the Neon database warning?",
  "What failed payments or subscription receipts do I have?",
  "Which third-party OAuth apps were granted access to my Google account?",
];

export default function RagAssistantDrawer({
  open,
  onClose,
}: RagAssistantDrawerProps) {
  const { t, dir } = useLanguage();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleAsk = async (qText?: string) => {
    const queryStr = (qText ?? question).trim();
    if (!queryStr) return;
    setQuestion(queryStr);
    setLoading(true);
    setError(null);
    try {
      const res = await EmailOSApi.queryRag(queryStr, 5);
      setResult(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="animate-backdrop fixed inset-0 z-50 bg-black/35 backdrop-blur-[2px] flex justify-end"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`${
          dir === "rtl" ? "animate-drawer-rtl" : "animate-drawer-ltr"
        } w-full max-w-xl bg-white h-full shadow-2xl flex flex-col border-s border-gray-200`}
      >
        {/* Header */}
        <div className="px-6 py-4 bg-[#EAF1FB] border-b border-[#D3E3FD] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-[#0B57D0] text-white flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#041E49]">{t.ragTitle}</h3>
              <p className="text-[11px] text-[#444746]">{t.ragSubtitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-200 text-gray-600 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Quick Prompts */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-[#444746]">
              {t.quickQueries}
            </span>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_QUESTIONS.map((sq) => (
                <button
                  key={sq}
                  onClick={() => handleAsk(sq)}
                  className="smooth-pill text-start text-xs px-3.5 py-2 rounded-2xl bg-[#F6F8FC] hover:bg-[#D3E3FD] text-[#1F1F1F] border border-gray-200"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
              {error}
            </div>
          )}

          {loading && (
            <div className="p-8 text-center text-xs text-[#0B57D0] font-bold animate-pulse">
              {t.searchingVectors}
            </div>
          )}

          {result && !loading && (
            <div className="animate-view-enter space-y-4">
              <div className="p-4 rounded-2xl bg-[#F6F8FC] border border-gray-200 text-sm text-[#1F1F1F] whitespace-pre-wrap leading-relaxed shadow-2xs">
                {result.answer}
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#444746]">
                  {t.verifiedCitations} ({result.citations.length})
                </h4>
                {result.citations.map((cit, idx) => (
                  <div
                    key={cit.message_id}
                    style={{ animationDelay: `${idx * 40}ms` }}
                    className="animate-row-enter gmail-row-smooth p-3.5 rounded-2xl border border-gray-200 hover:border-blue-300 bg-white space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-[#1F1F1F] truncate">
                        {cit.subject}
                      </span>
                      <a
                        href={cit.gmail_thread_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-[11px] font-bold text-[#0B57D0] hover:underline shrink-0"
                      >
                        <span>{t.openThread}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <div className="text-[11px] text-gray-500 flex items-center justify-between">
                      <span>{cit.sender_email}</span>
                      <span>
                        {cit.category} •{" "}
                        {(cit.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-xs text-[#444746] pt-1">{cit.snippet}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="p-4 border-t border-gray-200 bg-white flex items-center gap-2"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t.ragInputPlaceholder}
            className="flex-1 rounded-full bg-[#EAF1FB] px-4 py-2.5 text-sm outline-none text-[#1F1F1F]"
          />
          <button
            type="submit"
            disabled={loading}
            className="smooth-pill px-5 py-2.5 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white text-xs font-bold flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{t.askBtn}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
