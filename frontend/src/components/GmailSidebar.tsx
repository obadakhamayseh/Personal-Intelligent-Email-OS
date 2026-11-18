"use client";

import React from "react";
import {
  Inbox,
  Star,
  Send,
  Trash2,
  Flame,
  Shield,
  ServerCrash,
  CreditCard,
  Clock,
  Ghost,
  GraduationCap,
  BookOpen,
  Megaphone,
  Plus,
  Trash,
  Radio,
  BellOff,
  Sliders,
  BarChart3,
} from "lucide-react";
import { DashboardStatus, SmartCategory } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export type ActiveWorkspaceView =
  | "INBOX"
  | "STARRED"
  | "SENT"
  | "TRASH"
  | "CATEGORY"
  | "ANALYTICS_DASHBOARD"
  | "CUSTOM_BULK_DELETE"
  | "CLEANUP_SIMULATOR"
  | "FINANCIAL_BURN_RATE"
  | "OAUTH_RADAR"
  | "DEAD_SUBSCRIPTIONS"
  | "RULES_MANAGER";

interface GmailSidebarProps {
  collapsed: boolean;
  activeView: ActiveWorkspaceView;
  selectedCategory: SmartCategory | null;
  onSelectView: (
    view: ActiveWorkspaceView,
    category?: SmartCategory | null
  ) => void;
  onOpenIngestModal: () => void;
  status: DashboardStatus | null;
}

export const SMART_CATEGORY_META: {
  id: SmartCategory;
  icon: React.ComponentType<{ className?: string }>;
  dotColor: string;
}[] = [
  {
    id: "AI/Infra-Incidents",
    icon: ServerCrash,
    dotColor: "text-red-600",
  },
  {
    id: "AI/Financial-Leakage",
    icon: CreditCard,
    dotColor: "text-emerald-600",
  },
  {
    id: "AI/Security-OAuth-Radar",
    icon: Shield,
    dotColor: "text-amber-600",
  },
  {
    id: "AI/Action-SLA",
    icon: Clock,
    dotColor: "text-orange-600",
  },
  {
    id: "AI/Ephemeral-SelfDestruct",
    icon: Flame,
    dotColor: "text-purple-600",
  },
  {
    id: "AI/Waiting-On-Ghosted",
    icon: Ghost,
    dotColor: "text-indigo-600",
  },
  {
    id: "AI/Study-Training",
    icon: GraduationCap,
    dotColor: "text-blue-600",
  },
  {
    id: "AI/Knowledge-Digest",
    icon: BookOpen,
    dotColor: "text-teal-600",
  },
  {
    id: "AI/Promotions-Noise",
    icon: Megaphone,
    dotColor: "text-gray-500",
  },
];

export default function GmailSidebar({
  collapsed,
  activeView,
  selectedCategory,
  onSelectView,
  onOpenIngestModal,
  status,
}: GmailSidebarProps) {
  const { t, dir } = useLanguage();
  const categoryCounts = status?.category_counts || {};
  const roundedClass = dir === "rtl" ? "rounded-l-full" : "rounded-r-full";

  const navItemClass = (isActive: boolean) =>
    `smooth-pill w-full flex items-center justify-between px-4 py-2 ${roundedClass} text-xs transition-all duration-200 ${
      isActive
        ? "bg-[#D3E3FD] text-[#041E49] font-bold shadow-2xs"
        : "text-[#444746] hover:bg-gray-200/70 hover:translate-x-0.5"
    }`;

  return (
    <aside
      className={`${
        collapsed ? "w-20" : "w-64"
      } shrink-0 bg-[#F6F8FC] px-2 py-2 flex flex-col justify-between overflow-y-auto transition-all duration-300 ease-in-out select-none`}
    >
      <div>
        {/* Authentic Gmail Compose Button (#C2E7FF) */}
        <div className="px-2 mb-4">
          <button
            onClick={onOpenIngestModal}
            className="smooth-pill flex items-center gap-3 bg-[#C2E7FF] hover:bg-[#B3D7EF] hover:shadow-md text-[#001D35] font-semibold rounded-2xl px-4 py-3.5 w-full justify-center md:justify-start"
          >
            <Plus className="w-5 h-5 shrink-0" />
            {!collapsed && <span className="text-sm">{t.simulateEmail}</span>}
          </button>
        </div>

        {/* Primary Mailboxes */}
        <nav className="space-y-1">
          <button
            onClick={() => onSelectView("INBOX", null)}
            className={navItemClass(activeView === "INBOX")}
          >
            <div className="flex items-center gap-3">
              <Inbox className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="text-sm">{t.allInbox}</span>}
            </div>
            {!collapsed && status && (
              <span className="text-xs font-bold">
                {status.unread_emails > 0
                  ? status.unread_emails
                  : status.total_emails}
              </span>
            )}
          </button>

          <button
            onClick={() => onSelectView("STARRED", null)}
            className={navItemClass(activeView === "STARRED")}
          >
            <div className="flex items-center gap-3">
              <Star className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="text-sm">{t.starred}</span>}
            </div>
          </button>

          <button
            onClick={() => onSelectView("SENT", null)}
            className={navItemClass(activeView === "SENT")}
          >
            <div className="flex items-center gap-3">
              <Send className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="text-sm">{t.sent}</span>}
            </div>
          </button>

          <button
            onClick={() => onSelectView("TRASH", null)}
            className={navItemClass(activeView === "TRASH")}
          >
            <div className="flex items-center gap-3">
              <Trash2 className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="text-sm">{t.trash}</span>}
            </div>
          </button>
        </nav>

        {/* Smart AI Labels Section */}
        <div className="mt-5">
          {!collapsed && (
            <div className="px-4 mb-1.5 flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#444746]/80">
                {t.smartLabelsHeader}
              </span>
            </div>
          )}
          <nav className="space-y-0.5">
            {SMART_CATEGORY_META.map((cat) => {
              const Icon = cat.icon;
              const isSelected =
                activeView === "CATEGORY" && selectedCategory === cat.id;
              const count = categoryCounts[cat.id] || 0;
              return (
                <button
                  key={cat.id}
                  onClick={() => onSelectView("CATEGORY", cat.id)}
                  className={navItemClass(isSelected)}
                  title={cat.id}
                >
                  <div className="flex items-center gap-3 truncate">
                    <Icon className={`w-4 h-4 shrink-0 ${cat.dotColor}`} />
                    {!collapsed && (
                      <span className="truncate">{t.categories[cat.id]}</span>
                    )}
                  </div>
                  {!collapsed && count > 0 && (
                    <span className="text-[11px] font-bold px-1.5 py-0.2 rounded-full bg-white/70">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* OS Intelligence & Safety Control Modules */}
        <div className="mt-5">
          {!collapsed && (
            <div className="px-4 mb-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#444746]/80">
                {t.commandViewsHeader}
              </span>
            </div>
          )}
          <nav className="space-y-0.5">
            <button
              onClick={() => onSelectView("ANALYTICS_DASHBOARD", null)}
              className={navItemClass(activeView === "ANALYTICS_DASHBOARD")}
            >
              <div className="flex items-center gap-3">
                <BarChart3 className="w-4 h-4 text-indigo-600 shrink-0" />
                {!collapsed && (
                  <span className="font-bold text-indigo-800">
                    {dir === "rtl"
                      ? "لوحة التحليلات والإحصائيات"
                      : "Executive Analytics"}
                  </span>
                )}
              </div>
            </button>

            <button
              onClick={() => onSelectView("CUSTOM_BULK_DELETE", null)}
              className={navItemClass(activeView === "CUSTOM_BULK_DELETE")}
            >
              <div className="flex items-center gap-3">
                <Trash2 className="w-4 h-4 text-red-600 shrink-0" />
                {!collapsed && (
                  <span className="font-bold text-red-700">
                    {dir === "rtl"
                      ? "الحذف الجماعي المخصص"
                      : "Direct Bulk Delete"}
                  </span>
                )}
              </div>
            </button>

            <button
              onClick={() => onSelectView("CLEANUP_SIMULATOR", null)}
              className={navItemClass(activeView === "CLEANUP_SIMULATOR")}
            >
              <div className="flex items-center gap-3">
                <Trash className="w-4 h-4 text-rose-500 shrink-0" />
                {!collapsed && <span>{t.safeCleanupSimulator}</span>}
              </div>
            </button>

            <button
              onClick={() => onSelectView("FINANCIAL_BURN_RATE", null)}
              className={navItemClass(activeView === "FINANCIAL_BURN_RATE")}
            >
              <div className="flex items-center gap-3">
                <CreditCard className="w-4 h-4 text-emerald-600 shrink-0" />
                {!collapsed && (
                  <span className="font-bold text-emerald-800">
                    {dir === "rtl"
                      ? "الرادار المالي والاشتراكات"
                      : "Subscription Burn-Rate"}
                  </span>
                )}
              </div>
              {!collapsed && status && status.financial_events_count > 0 && (
                <span className="text-[11px] font-bold text-emerald-700">
                  {status.financial_events_count}
                </span>
              )}
            </button>

            <button
              onClick={() => onSelectView("OAUTH_RADAR", null)}
              className={navItemClass(activeView === "OAUTH_RADAR")}
            >
              <div className="flex items-center gap-3">
                <Radio className="w-4 h-4 text-amber-600 shrink-0" />
                {!collapsed && <span>{t.oauthAndSlaExposure}</span>}
              </div>
              {!collapsed && status && status.oauth_apps_count > 0 && (
                <span className="text-[11px] font-bold text-amber-700">
                  {status.oauth_apps_count}
                </span>
              )}
            </button>

            <button
              onClick={() => onSelectView("DEAD_SUBSCRIPTIONS", null)}
              className={navItemClass(activeView === "DEAD_SUBSCRIPTIONS")}
            >
              <div className="flex items-center gap-3">
                <BellOff className="w-4 h-4 text-purple-600 shrink-0" />
                {!collapsed && <span>{t.deadSubscriptions}</span>}
              </div>
              {!collapsed && status && status.dead_subscriptions_count > 0 && (
                <span className="text-[11px] px-1.5 py-0.2 rounded-full bg-purple-100 text-purple-800 font-bold">
                  {status.dead_subscriptions_count}
                </span>
              )}
            </button>

            <button
              onClick={() => onSelectView("RULES_MANAGER", null)}
              className={navItemClass(activeView === "RULES_MANAGER")}
            >
              <div className="flex items-center gap-3">
                <Sliders className="w-4 h-4 text-blue-600 shrink-0" />
                {!collapsed && <span>{t.tier1RuleEngine}</span>}
              </div>
            </button>
          </nav>
        </div>
      </div>

      {/* Footer Storage / Policy Status */}
      {!collapsed && status && (
        <div className="px-4 pt-3 pb-2 border-t border-gray-200/80 text-[11px] text-[#444746] space-y-1">
          <div className="flex items-center justify-between">
            <span>{t.nextCleanup}</span>
            <span className="font-semibold text-gray-800">
              {status.next_scheduled_cleanup}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>{t.activeDeadlines}</span>
            <span className="font-bold text-orange-700">
              {status.upcoming_deadlines_count} {t.slaItems}
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
