"use client";

import React from "react";
import {
  Menu,
  Search,
  Sparkles,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  CheckCircle2,
  Globe,
  LogIn,
  Moon,
  Sun,
  Command,
} from "lucide-react";
import { DashboardStatus } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface GmailHeaderProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onToggleSidebar: () => void;
  onOpenRagDrawer: () => void;
  onTriggerSync: () => void;
  onOpenGoogleModal: () => void;
  onOpenCommandPalette: () => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  syncing: boolean;
  status: DashboardStatus | null;
}

export default function GmailHeader({
  searchQuery,
  onSearchChange,
  onToggleSidebar,
  onOpenRagDrawer,
  onTriggerSync,
  onOpenGoogleModal,
  onOpenCommandPalette,
  darkMode,
  onToggleDarkMode,
  syncing,
  status,
}: GmailHeaderProps) {
  const { lang, t, toggleLanguage } = useLanguage();
  const isAr = lang === "ar";
  const isConnected = Boolean(status?.gmail_connected);

  return (
    <header className="h-16 px-4 flex items-center justify-between bg-[#F6F8FC] select-none shrink-0 border-b border-transparent transition-all duration-200">
      {/* Start: Hamburger + Gmail Logo */}
      <div className="flex items-center gap-3 min-w-[230px]">
        <button
          onClick={onToggleSidebar}
          className="p-2.5 rounded-full hover:bg-gray-200/80 active:scale-95 text-[#444746] transition-all duration-150"
          title="Menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-6 rounded-md flex items-center justify-center bg-white shadow-sm border border-gray-200 relative overflow-hidden transition-transform hover:scale-105">
            <span className="text-red-600 font-extrabold text-lg leading-none">
              M
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[19px] font-semibold tracking-tight text-[#444746]">
              {t.appName}
            </span>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#D3E3FD] text-[#041E49] shadow-2xs">
              {t.appBadge}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Authentic Gmail Search Bar */}
      <div className="flex-1 max-w-3xl mx-4">
        <div className="flex items-center bg-[#EAF1FB] focus-within:bg-white focus-within:shadow-md focus-within:ring-2 focus-within:ring-[#0B57D0]/15 rounded-full px-4 py-2 transition-all duration-200 border border-transparent focus-within:border-blue-200">
          <Search className="w-5 h-5 text-[#444746] mx-2 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t.searchPlaceholder}
            className="w-full bg-transparent outline-none text-sm text-[#1F1F1F] placeholder-[#444746]"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="text-xs text-gray-500 hover:text-gray-800 px-2 transition"
            >
              {t.clear}
            </button>
          )}
          <button
            onClick={onOpenRagDrawer}
            className="mx-1.5 flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-[#0B57D0] to-blue-600 text-white text-xs font-semibold hover:shadow-md hover:brightness-105 active:scale-95 transition-all duration-200 shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t.askAiRag}</span>
          </button>
          <SlidersHorizontal className="w-4 h-4 text-[#444746] mx-1.5 shrink-0" />
        </div>
      </div>

      {/* End: Command Palette, Dark Mode, Language Toggle, Google Sign-In, Sync */}
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenCommandPalette}
          className="smooth-pill hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-white hover:bg-[#D3E3FD] text-[#444746] border border-gray-200 shadow-2xs text-xs font-mono font-bold"
          title="Command Palette (Ctrl+K)"
        >
          <Command className="w-3.5 h-3.5 text-[#0B57D0]" />
          <span>Ctrl+K</span>
        </button>

        <button
          onClick={onToggleDarkMode}
          className="smooth-pill p-2 rounded-full bg-white hover:bg-[#D3E3FD] text-[#444746] border border-gray-200 shadow-2xs"
          title={isAr ? "تبديل الوضع الليلي / النهاري" : "Toggle Dark / Light Mode"}
        >
          {darkMode ? (
            <Sun className="w-4 h-4 text-amber-500" />
          ) : (
            <Moon className="w-4 h-4 text-[#0B57D0]" />
          )}
        </button>

        <button
          onClick={toggleLanguage}
          className="smooth-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white hover:bg-[#D3E3FD] text-[#041E49] border border-gray-200 shadow-2xs text-xs font-bold"
          title="تغيير اللغة / Switch Language"
        >
          <Globe className="w-3.5 h-3.5 text-[#0B57D0]" />
          <span>{isAr ? "English" : "العربية"}</span>
        </button>

        {status && status.active_p0_incidents > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-100 text-red-800 text-xs font-bold border border-red-200 shadow-2xs">
            <ShieldAlert className="w-4 h-4 text-red-600 animate-pulse" />
            <span>
              {status.active_p0_incidents} {t.p0CriticalBadge}
            </span>
          </div>
        )}

        {/* Google Account Sign-In / Connection Button */}
        {isConnected ? (
          <button
            onClick={onOpenGoogleModal}
            className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{isAr ? "حساب Gmail متصل" : "Gmail Connected"}</span>
          </button>
        ) : (
          <button
            onClick={onOpenGoogleModal}
            className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white shadow-sm text-xs font-bold"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>
              {isAr ? "تسجيل الدخول بحساب Google" : "Sign in with Google"}
            </span>
          </button>
        )}

        <button
          onClick={onTriggerSync}
          disabled={syncing}
          className="smooth-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-gray-200/80 text-xs font-medium text-[#444746]"
        >
          <RefreshCw
            className={`w-4 h-4 ${syncing ? "animate-spin text-[#0B57D0]" : ""}`}
          />
          <span className="hidden md:inline">
            {syncing ? t.syncing : t.syncGmail}
          </span>
        </button>

        <button
          onClick={onOpenGoogleModal}
          className="w-9 h-9 rounded-full bg-[#0B57D0] text-white flex items-center justify-center font-bold text-sm shadow-sm mx-1 hover:ring-2 hover:ring-blue-300 transition"
          title={isAr ? "إعدادات الحساب" : "Account Settings"}
        >
          G
        </button>
      </div>
    </header>
  );
}
