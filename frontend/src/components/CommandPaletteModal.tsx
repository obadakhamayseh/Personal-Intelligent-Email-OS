"use client";

import React, { useEffect, useState } from "react";
import {
  Command,
  Search,
  Inbox,
  Trash2,
  CreditCard,
  BarChart3,
  Sliders,
  Sparkles,
  RefreshCw,
  Globe,
  Moon,
  Sun,
  BellOff,
  Radio,
} from "lucide-react";
import { ActiveWorkspaceView } from "./GmailSidebar";
import { SmartCategory } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface CommandPaletteModalProps {
  open: boolean;
  onClose: () => void;
  onSelectView: (
    view: ActiveWorkspaceView,
    category?: SmartCategory | null
  ) => void;
  onOpenRag: () => void;
  onTriggerSync: () => void;
  onOpenSimulate: () => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
}

export default function CommandPaletteModal({
  open,
  onClose,
  onSelectView,
  onOpenRag,
  onTriggerSync,
  onOpenSimulate,
  darkMode,
  onToggleDarkMode,
}: CommandPaletteModalProps) {
  const { lang, toggleLanguage } = useLanguage();
  const isAr = lang === "ar";
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  if (!open) return null;

  const actions = [
    {
      id: "inbox",
      title: isAr ? "الانتقال إلى: كل البريد الوارد" : "Go to: All Inbox",
      icon: Inbox,
      category: isAr ? "تنقل" : "Navigation",
      run: () => onSelectView("INBOX", null),
    },
    {
      id: "analytics",
      title: isAr
        ? "فتح: لوحة التحليلات والإحصائيات البصرية"
        : "Open: Executive Inbox Analytics Dashboard",
      icon: BarChart3,
      category: isAr ? "ذكاء وتحليلات" : "Analytics",
      run: () => onSelectView("ANALYTICS_DASHBOARD", null),
    },
    {
      id: "financial",
      title: isAr
        ? "فتح: الرادار المالي ومعدل استهلاك الاشتراكات"
        : "Open: Subscription Burn-Rate & Financial Studio",
      icon: CreditCard,
      category: isAr ? "ذكاء وتحليلات" : "Analytics",
      run: () => onSelectView("FINANCIAL_BURN_RATE", null),
    },
    {
      id: "bulk_delete",
      title: isAr
        ? "فتح: استوديو الحذف الجماعي المخصص (تحكم مباشر)"
        : "Open: Direct Bulk Delete Studio",
      icon: Trash2,
      category: isAr ? "تنظيف وحذف" : "Cleanup",
      run: () => onSelectView("CUSTOM_BULK_DELETE", null),
    },
    {
      id: "rules",
      title: isAr
        ? "فتح: محرك القواعد الفوري ومنشئ القواعد باللغة الطبيعية"
        : "Open: Tier 1 Rule Engine & Natural-Language Builder",
      icon: Sliders,
      category: isAr ? "أتمتة" : "Automation",
      run: () => onSelectView("RULES_MANAGER", null),
    },
    {
      id: "dead_subs",
      title: isAr
        ? "فتح: كاشف الاشتراكات الميتة ومؤشر الإزعاج"
        : "Open: Dead Subscriptions & Sender Noise Detector",
      icon: BellOff,
      category: isAr ? "تنظيف وحذف" : "Cleanup",
      run: () => onSelectView("DEAD_SUBSCRIPTIONS", null),
    },
    {
      id: "oauth_radar",
      title: isAr
        ? "فتح: رادار الأمان و OAuth والمواعيد النهائية"
        : "Open: OAuth Security & Action SLA Radar",
      icon: Radio,
      category: isAr ? "أمان" : "Security",
      run: () => onSelectView("OAUTH_RADAR", null),
    },
    {
      id: "ask_rag",
      title: isAr
        ? "تشغيل: المساعد الدلالي الذكي للبريد (Ask AI RAG)"
        : "Action: Ask Semantic Email RAG Assistant",
      icon: Sparkles,
      category: isAr ? "ذكاء اصطناعي" : "AI Assistant",
      run: () => onOpenRag(),
    },
    {
      id: "sync_gmail",
      title: isAr
        ? "تشغيل: مزامنة حساب Gmail الآن"
        : "Action: Trigger Live Gmail Sync Now",
      icon: RefreshCw,
      category: isAr ? "أوامر" : "Actions",
      run: () => onTriggerSync(),
    },
    {
      id: "dark_mode",
      title: isAr
        ? darkMode
          ? "المظهر: التبديل إلى الوضع النهاري الفاتح ☀️"
          : "المظهر: التبديل إلى الوضع الليلي الداكن 🌙"
        : darkMode
        ? "Theme: Switch to Light Mode ☀️"
        : "Theme: Switch to Dark Mode 🌙",
      icon: darkMode ? Sun : Moon,
      category: isAr ? "المظهر" : "Preferences",
      run: () => onToggleDarkMode(),
    },
    {
      id: "toggle_lang",
      title: isAr
        ? "اللغة: التبديل إلى الإنجليزية (Switch to English)"
        : "Language: Switch to Arabic (التبديل للعربية)",
      icon: Globe,
      category: isAr ? "المظهر" : "Preferences",
      run: () => toggleLanguage(),
    },
    {
      id: "simulate",
      title: isAr
        ? "تجربة: محاكاة رسالة واردة جديدة"
        : "Action: Simulate Incoming Email",
      icon: Command,
      category: isAr ? "أوامر" : "Actions",
      run: () => onOpenSimulate(),
    },
  ];

  const filtered = actions.filter(
    (a) =>
      !query.trim() ||
      a.title.toLowerCase().includes(query.toLowerCase()) ||
      a.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      onClick={onClose}
      className="animate-backdrop fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] flex items-start justify-center pt-20 p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-modal-enter bg-white rounded-2xl shadow-2xl max-w-xl w-full overflow-hidden border border-gray-200"
      >
        <div className="px-4 py-3.5 border-b border-gray-200 flex items-center gap-3 bg-[#F6F8FC]">
          <Search className="w-5 h-5 text-[#0B57D0] shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              isAr
                ? "اكتب أمراً أو اسم قسم للانتقال السريع (Ctrl+K)..."
                : "Type a command or section name to jump (Ctrl+K)..."
            }
            className="w-full bg-transparent outline-none text-sm font-medium text-[#1F1F1F]"
          />
          <kbd className="px-2 py-0.5 text-[10px] font-mono bg-white border border-gray-300 rounded text-gray-500">
            ESC
          </kbd>
        </div>

        <div className="max-h-96 overflow-y-auto divide-y divide-gray-100 p-2">
          {filtered.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  item.run();
                  onClose();
                }}
                className="w-full px-3.5 py-2.5 rounded-xl hover:bg-[#EAF1FB] flex items-center justify-between text-xs transition group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-[#F6F8FC] group-hover:bg-white flex items-center justify-center text-[#0B57D0] border border-gray-200">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="font-bold text-[#1F1F1F] group-hover:text-[#0B57D0]">
                    {item.title}
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-semibold">
                  {item.category}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
