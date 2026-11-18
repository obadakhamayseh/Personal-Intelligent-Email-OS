"use client";

import React, { useEffect, useState } from "react";
import { Plus, Trash2, Zap, Sparkles, Wand2 } from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import {
  ClassificationRule,
  LifecycleTTL,
  SeverityLevel,
  SmartCategory,
} from "@/lib/types";
import { SMART_CATEGORY_META } from "./GmailSidebar";
import { useLanguage } from "@/lib/i18n";

export default function RulesManagerView() {
  const { t, lang } = useLanguage();
  const isAr = lang === "ar";

  const [rules, setRules] = useState<ClassificationRule[]>([]);
  const [name, setName] = useState("");
  const [senderDomain, setSenderDomain] = useState("");
  const [subjectRegex, setSubjectRegex] = useState("");
  const [targetCategory, setTargetCategory] = useState<SmartCategory>(
    "AI/Infra-Incidents"
  );
  const [targetSeverity, setTargetSeverity] =
    useState<SeverityLevel>("P0_CRITICAL");
  const [targetTtl] = useState<LifecycleTTL>("NEVER_DELETE");
  const [priority] = useState<number>(30);

  // Natural-Language Rule Builder State
  const [nlPrompt, setNlPrompt] = useState("");
  const [nlCreating, setNlCreating] = useState(false);
  const [nlBanner, setNlBanner] = useState<string | null>(null);

  const loadRules = async () => {
    const data = await EmailOSApi.listRules();
    setRules(data);
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleCreateFromNaturalLanguage = async (
    e?: React.FormEvent,
    customText?: string
  ) => {
    if (e) e.preventDefault();
    const promptToUse = (customText ?? nlPrompt).trim();
    if (!promptToUse) return;
    setNlPrompt(promptToUse);
    setNlCreating(true);
    setNlBanner(null);
    try {
      const created = await EmailOSApi.createRuleFromNaturalLanguage(
        promptToUse
      );
      setNlBanner(
        isAr
          ? `✅ تم تحويل جملتك إلى قاعدة حتمية Tier 1 بنجاح: «${created.name}» → (${created.target_category} | ${created.target_severity} | ${created.target_ttl})`
          : `✅ Converted natural language into Tier 1 Rule: "${created.name}" → (${created.target_category} | ${created.target_severity} | ${created.target_ttl})`
      );
      setNlPrompt("");
      loadRules();
    } catch (err: any) {
      setNlBanner(`Error: ${err.message}`);
    } finally {
      setNlCreating(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await EmailOSApi.createRule({
      name: name.trim(),
      priority,
      is_active: true,
      sender_domain: senderDomain.trim() || null,
      subject_regex: subjectRegex.trim() || null,
      target_category: targetCategory,
      target_severity: targetSeverity,
      target_ttl: targetTtl,
    });
    setName("");
    setSenderDomain("");
    setSubjectRegex("");
    loadRules();
  };

  const handleToggle = async (rule: ClassificationRule) => {
    await EmailOSApi.toggleRule(rule.id, !rule.is_active);
    loadRules();
  };

  const handleDelete = async (ruleId: number) => {
    await EmailOSApi.deleteRule(ruleId);
    loadRules();
  };

  const sampleNlPrompts = isAr
    ? [
        "أي رسالة من لينكدإن أو تحتوي على كلمة وظائف ضعها في الترويج واحذفها بعد 7 أيام",
        "أي رسالة من جيتهاب أو فيرسل تحتوي على كلمة عطل أو فشل اجعلها P0 حرج في طوارئ البنية التحتية ولا تحذفها أبداً",
        "أي رسالة تحتوي على كلمة فاتورة أو إيصال ضعها في المالية ولا تحذفها أبداً",
      ]
    : [
        "Any email from linkedin.com or containing jobs put in Promotions and delete after 7 days",
        "Any email from github.com or vercel.com containing outage or failed mark as P0 Critical Infra and never delete",
        "Any email containing invoice or receipt put in Financial and never delete",
      ];

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-[#1F1F1F]">{t.rulesTitle}</h2>
        <p className="text-xs text-[#444746] mt-0.5">{t.rulesSubtitle}</p>
      </div>

      {/* Natural-Language AI Rule Builder Studio */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-[#EAF1FB] to-indigo-50 border border-[#D3E3FD] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#0B57D0]" />
            <span className="text-xs font-extrabold text-[#041E49]">
              {isAr
                ? "منشئ القواعد الذكي باللغة الطبيعية (اكتب جملة عادية وسيحولها النظام لقاعدة Tier 1 بـ Regex تلقائياً)"
                : "AI Natural-Language Rule Builder (Type plain English/Arabic to generate a Tier 1 Regex Rule)"}
            </span>
          </div>
          <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#0B57D0] text-white font-bold">
            NL → SQL Regex
          </span>
        </div>

        <form
          onSubmit={(e) => handleCreateFromNaturalLanguage(e)}
          className="flex flex-wrap items-center gap-2"
        >
          <input
            type="text"
            value={nlPrompt}
            onChange={(e) => setNlPrompt(e.target.value)}
            placeholder={
              isAr
                ? "مثال: أي رسالة من لينكدإن أو تحتوي على كلمة عروض ضعها في الترويج واحذفها بعد 7 أيام..."
                : "e.g., Any email from linkedin.com or with word promo put in Promotions and delete after 7 days..."
            }
            className="flex-1 bg-white rounded-full border border-blue-200 focus:border-[#0B57D0] px-4 py-2.5 text-xs outline-none text-[#1F1F1F]"
          />
          <button
            type="submit"
            disabled={nlCreating}
            className="smooth-pill px-5 py-2.5 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm"
          >
            <Wand2 className="w-3.5 h-3.5" />
            <span>
              {nlCreating
                ? isAr
                  ? "جاري التوليد..."
                  : "Generating..."
                : isAr
                ? "تحويل وإنشاء القاعدة تلقائياً"
                : "Generate & Save Rule"}
            </span>
          </button>
        </form>

        {/* Quick 1-Click NL Examples */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] font-bold text-[#444746]">
            {isAr ? "أمثلة سريعة بضغطة واحدة:" : "1-Click Examples:"}
          </span>
          {sampleNlPrompts.map((sp) => (
            <button
              key={sp}
              type="button"
              onClick={() => handleCreateFromNaturalLanguage(undefined, sp)}
              className="smooth-pill text-[11px] px-3 py-1 rounded-full bg-white hover:bg-[#D3E3FD] text-[#041E49] border border-blue-200 font-medium"
            >
              {sp}
            </button>
          ))}
        </div>

        {nlBanner && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-900">
            {nlBanner}
          </div>
        )}
      </div>

      {/* Manual Add New Rule Form */}
      <form
        onSubmit={handleCreate}
        className="p-4 rounded-2xl bg-[#F6F8FC] border border-gray-200 grid grid-cols-1 md:grid-cols-6 gap-3 items-end text-xs"
      >
        <div className="md:col-span-2">
          <label className="block font-bold text-gray-700 mb-1">
            {t.ruleNameLabel}
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. DigitalOcean Outage Alerts"
            className="w-full rounded-xl border border-gray-300 px-3 py-2 bg-white"
          />
        </div>
        <div>
          <label className="block font-bold text-gray-700 mb-1">
            {t.senderDomainsLabel}
          </label>
          <input
            type="text"
            value={senderDomain}
            onChange={(e) => setSenderDomain(e.target.value)}
            placeholder="digitalocean.com"
            className="w-full rounded-xl border border-gray-300 px-3 py-2 bg-white"
          />
        </div>
        <div>
          <label className="block font-bold text-gray-700 mb-1">
            {t.subjectRegexLabel}
          </label>
          <input
            type="text"
            value={subjectRegex}
            onChange={(e) => setSubjectRegex(e.target.value)}
            placeholder="(droplet|outage|failed)"
            className="w-full rounded-xl border border-gray-300 px-3 py-2 bg-white"
          />
        </div>
        <div>
          <label className="block font-bold text-gray-700 mb-1">
            {t.targetCategoryLabel}
          </label>
          <select
            value={targetCategory}
            onChange={(e) =>
              setTargetCategory(e.target.value as SmartCategory)
            }
            className="w-full rounded-xl border border-gray-300 px-2 py-2 bg-white"
          >
            {SMART_CATEGORY_META.map((c) => (
              <option key={c.id} value={c.id}>
                {t.categories[c.id]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={targetSeverity}
            onChange={(e) =>
              setTargetSeverity(e.target.value as SeverityLevel)
            }
            className="rounded-xl border border-gray-300 px-2 py-2 bg-white"
          >
            <option value="P0_CRITICAL">P0_CRITICAL</option>
            <option value="P1_HIGH">P1_HIGH</option>
            <option value="P2_NORMAL">P2_NORMAL</option>
            <option value="P3_NOISE">P3_NOISE</option>
          </select>
          <button
            type="submit"
            className="smooth-pill px-4 py-2 rounded-full bg-[#0B57D0] text-white font-bold flex items-center gap-1 hover:bg-blue-800 shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>{t.addRuleBtn}</span>
          </button>
        </div>
      </form>

      {/* Rules Table */}
      <div className="border border-gray-200 rounded-2xl overflow-hidden">
        <table className="w-full text-start text-xs">
          <thead className="bg-[#F6F8FC] border-b border-gray-200 text-[#444746]">
            <tr>
              <th className="py-3 px-4 text-start">{t.colPriority}</th>
              <th className="py-3 px-4 text-start">{t.colRuleCriteria}</th>
              <th className="py-3 px-4 text-start">{t.col3dTarget}</th>
              <th className="py-3 px-4 text-start">{t.colHits}</th>
              <th className="py-3 px-4 text-end">{t.colActions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map((r, idx) => (
              <tr
                key={r.id}
                style={{ animationDelay: `${idx * 25}ms` }}
                className="animate-row-enter hover:bg-gray-50 transition"
              >
                <td className="py-3 px-4 font-mono font-bold">#{r.priority}</td>
                <td className="py-3 px-4 space-y-1">
                  <div className="font-bold text-[#1F1F1F]">{r.name}</div>
                  <div className="text-gray-500 font-mono text-[11px]">
                    {r.sender_domain && `domain:${r.sender_domain} `}
                    {r.sender_email && `from:${r.sender_email} `}
                    {r.subject_regex && `subj:/${r.subject_regex}/i `}
                    {r.header_key && `hdr:${r.header_key}`}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1.5">
                    <span className="px-2.5 py-0.5 rounded-full bg-[#EAF1FB] text-[#041E49] font-bold">
                      {t.categories[r.target_category] || r.target_category}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-800">
                      {r.target_severity}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800">
                      {r.target_ttl}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4 font-bold">
                  <span className="inline-flex items-center gap-1 text-blue-700">
                    <Zap className="w-3 h-3" />
                    {r.hit_count}
                  </span>
                </td>
                <td className="py-3 px-4 text-end">
                  <div className="inline-flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(r)}
                      className={`smooth-pill px-3 py-1 rounded-full font-bold ${
                        r.is_active
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-gray-200 text-gray-600"
                      }`}
                    >
                      {r.is_active ? t.activeRule : t.pausedRule}
                    </button>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="p-1.5 rounded-full hover:bg-red-100 text-red-600 transition"
                    >
                      <Trash2 className="w-4 h-4 inline" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
