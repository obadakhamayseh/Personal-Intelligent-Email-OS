"use client";

import React, { useCallback, useEffect, useState } from "react";
import GmailHeader from "@/components/GmailHeader";
import GmailSidebar, { ActiveWorkspaceView } from "@/components/GmailSidebar";
import EmailListView from "@/components/EmailListView";
import EmailDetailModal from "@/components/EmailDetailModal";
import CleanupSimulatorView from "@/components/CleanupSimulatorView";
import CustomBulkDeleteView from "@/components/CustomBulkDeleteView";
import FinancialBurnRateView from "@/components/FinancialBurnRateView";
import AnalyticsDashboardView from "@/components/AnalyticsDashboardView";
import CommandPaletteModal from "@/components/CommandPaletteModal";
import RagAssistantDrawer from "@/components/RagAssistantDrawer";
import OAuthRadarView from "@/components/OAuthRadarView";
import DeadSubscriptionsView from "@/components/DeadSubscriptionsView";
import RulesManagerView from "@/components/RulesManagerView";
import GoogleConnectModal from "@/components/GoogleConnectModal";
import { EmailOSApi } from "@/lib/api";
import {
  DashboardStatus,
  EmailItem,
  SeverityLevel,
  SmartCategory,
} from "@/lib/types";
import { X, Send } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

export default function PersonalEmailOSPage() {
  const { t, dir } = useLanguage();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState<ActiveWorkspaceView>("INBOX");
  const [selectedCategory, setSelectedCategory] =
    useState<SmartCategory | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<
    SeverityLevel | ""
  >("");
  const [searchQuery, setSearchQuery] = useState("");
  const [pageOffset, setPageOffset] = useState(0);
  const [pageSize, setPageSize] = useState(250);

  const [status, setStatus] = useState<DashboardStatus | null>(null);
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [totalEmails, setTotalEmails] = useState(0);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState<{
    is_running: boolean;
    total_in_gmail: number;
    synced_in_db: number;
    newly_ingested: number;
  } | null>(null);

  const [openedEmail, setOpenedEmail] = useState<EmailItem | null>(null);
  const [ragDrawerOpen, setRagDrawerOpen] = useState(false);
  const [googleModalOpen, setGoogleModalOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem("emailos_dark_mode");
    if (savedTheme === "true") {
      setDarkMode(true);
      document.documentElement.classList.add("dark-theme");
    }
  }, []);

  const handleToggleDarkMode = useCallback(() => {
    setDarkMode((prev) => {
      const next = !prev;
      localStorage.setItem("emailos_dark_mode", String(next));
      if (next) {
        document.documentElement.classList.add("dark-theme");
      } else {
        document.documentElement.classList.remove("dark-theme");
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((o) => !o);
      } else if (e.key === "Escape") {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Weekly Digest Modal state
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestMarkdown, setDigestMarkdown] = useState<string | null>(null);

  // Simulate / Ingest New Email Modal
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [simSender, setSimSender] = useState("alerts@cloudflare.com");
  const [simSubject, setSimSubject] = useState(
    "تنبيه طارئ P0: انتهاء شهادة SSL وتوقف النطاق الرئيسي خلال 24 ساعة"
  );
  const [simBody, setSimBody] = useState(
    "مطلوب إجراء عاجل: فشل تجديد شهادة الأمان والنطاق الخاص بالخادم الإنتاجي بقيمة 45.00 USD وسيتم إيقاف الخدمة خلال 24 ساعة."
  );
  const [simSubmitting, setSimSubmitting] = useState(false);

  const fetchStatusAndEmails = useCallback(async () => {
    setLoadingEmails(true);
    try {
      const [statusData, listData, progData] = await Promise.all([
        EmailOSApi.getStatus(),
        EmailOSApi.listEmails({
          category:
            activeView === "CATEGORY" && selectedCategory
              ? selectedCategory
              : activeView === "INBOX" && selectedCategory
              ? selectedCategory
              : undefined,
          severity: selectedSeverity || undefined,
          q: searchQuery || undefined,
          starred_only: activeView === "STARRED",
          sent_only: activeView === "SENT",
          trashed_only: activeView === "TRASH",
          limit: pageSize,
          offset: pageOffset,
        }),
        EmailOSApi.getSyncProgress().catch(() => null),
      ]);
      setStatus(statusData);
      setEmails(listData.items);
      setTotalEmails(listData.total);
      if (progData) {
        setSyncProgress(progData);
        setSyncing(progData.is_running);
      }
    } catch (err) {
      console.error("Failed to fetch Email OS data:", err);
    } finally {
      setLoadingEmails(false);
    }
  }, [
    activeView,
    selectedCategory,
    selectedSeverity,
    searchQuery,
    pageSize,
    pageOffset,
  ]);

  useEffect(() => {
    fetchStatusAndEmails();
  }, [fetchStatusAndEmails]);

  // Poll live sync progress while background historical sync is running
  useEffect(() => {
    if (!syncing && !(syncProgress && syncProgress.is_running)) return;
    const timer = setInterval(() => {
      fetchStatusAndEmails();
    }, 3500);
    return () => clearInterval(timer);
  }, [syncing, syncProgress, fetchStatusAndEmails]);

  const handleSelectSidebarView = (
    view: ActiveWorkspaceView,
    category?: SmartCategory | null
  ) => {
    setActiveView(view);
    setSelectedCategory(category ?? null);
    setPageOffset(0);
  };

  const handleOpenEmail = async (email: EmailItem) => {
    setOpenedEmail(email);
    if (!email.is_read) {
      try {
        await EmailOSApi.updateEmailState(email.message_id, { is_read: true });
        fetchStatusAndEmails();
      } catch (e) {
        console.error(e);
      }
    }
  };

  const handleToggleStar = async (email: EmailItem, e: React.MouseEvent) => {
    e.stopPropagation();
    await EmailOSApi.updateEmailState(email.message_id, {
      is_starred: !email.is_starred,
    });
    fetchStatusAndEmails();
  };

  const handleToggleRead = async (email: EmailItem, e: React.MouseEvent) => {
    e.stopPropagation();
    await EmailOSApi.updateEmailState(email.message_id, {
      is_read: !email.is_read,
    });
    fetchStatusAndEmails();
  };

  const handleMoveToTrash = async (email: EmailItem, e: React.MouseEvent) => {
    e.stopPropagation();
    await EmailOSApi.updateEmailState(email.message_id, {
      is_trashed: !email.is_trashed,
    });
    fetchStatusAndEmails();
  };

  const handleTriggerSync = async () => {
    if (status && !status.gmail_connected) {
      setGoogleModalOpen(true);
      return;
    }
    setSyncing(true);
    try {
      await EmailOSApi.triggerSync();
      await fetchStatusAndEmails();
    } catch (e) {
      console.error(e);
      setSyncing(false);
    }
  };

  const handleTriggerDigest = async () => {
    setDigestLoading(true);
    try {
      const res = await EmailOSApi.triggerWeeklyDigest();
      setDigestMarkdown(res.summary_markdown);
      await fetchStatusAndEmails();
    } finally {
      setDigestLoading(false);
    }
  };

  const handleSimulateIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimSubmitting(true);
    try {
      const id = `sim_${Date.now()}`;
      const created = await EmailOSApi.ingestSimulatedEmail({
        message_id: id,
        thread_id: `thd_${id}`,
        sender_email: simSender,
        sender_name: simSender.split("@")[0],
        subject: simSubject,
        snippet: simBody.slice(0, 160),
        body_text: simBody,
        internal_date: new Date().toISOString(),
      });
      setIngestModalOpen(false);
      await fetchStatusAndEmails();
      setOpenedEmail(created);
    } finally {
      setSimSubmitting(false);
    }
  };

  return (
    <div
      dir={dir}
      className="flex flex-col h-screen w-screen overflow-hidden bg-[#F6F8FC] transition-all duration-300"
    >
      {/* Authentic Gmail Top Header */}
      <GmailHeader
        searchQuery={searchQuery}
        onSearchChange={(q) => {
          setSearchQuery(q);
          setPageOffset(0);
        }}
        onToggleSidebar={() => setSidebarCollapsed((c) => !c)}
        onOpenRagDrawer={() => setRagDrawerOpen(true)}
        onTriggerSync={handleTriggerSync}
        onOpenGoogleModal={() => setGoogleModalOpen(true)}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        darkMode={darkMode}
        onToggleDarkMode={handleToggleDarkMode}
        syncing={syncing}
        status={status}
      />

      {/* Main Workspace Container */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <GmailSidebar
          collapsed={sidebarCollapsed}
          activeView={activeView}
          selectedCategory={selectedCategory}
          onSelectView={handleSelectSidebarView}
          onOpenIngestModal={() => setIngestModalOpen(true)}
          status={status}
        />

        {/* Dynamic Center Workspace with Smooth Keyed View Transitions */}
        <div
          key={activeView}
          className="flex-1 flex min-w-0 min-h-0 overflow-hidden animate-view-enter"
        >
          {activeView === "ANALYTICS_DASHBOARD" ? (
            <AnalyticsDashboardView />
          ) : activeView === "CUSTOM_BULK_DELETE" ? (
            <CustomBulkDeleteView onDeleted={fetchStatusAndEmails} />
          ) : activeView === "CLEANUP_SIMULATOR" ? (
            <CleanupSimulatorView onCleanupExecuted={fetchStatusAndEmails} />
          ) : activeView === "FINANCIAL_BURN_RATE" ? (
            <FinancialBurnRateView />
          ) : activeView === "OAUTH_RADAR" ? (
            <OAuthRadarView />
          ) : activeView === "DEAD_SUBSCRIPTIONS" ? (
            <DeadSubscriptionsView />
          ) : activeView === "RULES_MANAGER" ? (
            <RulesManagerView />
          ) : (
            <EmailListView
              emails={emails}
              total={totalEmails}
              pageOffset={pageOffset}
              pageSize={pageSize}
              onPageOffsetChange={setPageOffset}
              onPageSizeChange={(sz) => {
                setPageSize(sz);
                setPageOffset(0);
              }}
              loading={loadingEmails}
              gmailConnected={Boolean(status?.gmail_connected)}
              syncProgress={syncProgress}
              selectedSeverity={selectedSeverity}
              onSelectSeverity={(sev) => {
                setSelectedSeverity(sev);
                setPageOffset(0);
              }}
              activeTabCategory={selectedCategory}
              onSelectTabCategory={(cat) => {
                setSelectedCategory(cat);
                setActiveView(cat ? "CATEGORY" : "INBOX");
                setPageOffset(0);
              }}
              onOpenEmail={handleOpenEmail}
              onToggleStar={handleToggleStar}
              onToggleRead={handleToggleRead}
              onMoveToTrash={handleMoveToTrash}
              onRefresh={fetchStatusAndEmails}
              onTriggerDigest={handleTriggerDigest}
              onOpenGoogleModal={() => setGoogleModalOpen(true)}
              digestLoading={digestLoading}
            />
          )}
        </div>
      </div>

      {/* Email Detail Reader Modal */}
      <EmailDetailModal
        email={openedEmail}
        onClose={() => setOpenedEmail(null)}
        onMoveToTrash={handleMoveToTrash}
        onToggleStar={handleToggleStar}
      />

      {/* Google Account Sign-In & OAuth Configuration Modal */}
      <GoogleConnectModal
        open={googleModalOpen}
        onClose={() => setGoogleModalOpen(false)}
        onConnectedChange={fetchStatusAndEmails}
      />

      {/* Superhuman-Style Command Palette (Ctrl+K) */}
      <CommandPaletteModal
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onSelectView={handleSelectSidebarView}
        onOpenRag={() => setRagDrawerOpen(true)}
        onTriggerSync={handleTriggerSync}
        onOpenSimulate={() => setIngestModalOpen(true)}
        darkMode={darkMode}
        onToggleDarkMode={handleToggleDarkMode}
      />

      {/* Semantic Email RAG Slide-Over Drawer */}
      <RagAssistantDrawer
        open={ragDrawerOpen}
        onClose={() => setRagDrawerOpen(false)}
      />

      {/* Weekly Knowledge Digest Modal */}
      {digestMarkdown && (
        <div
          onClick={() => setDigestMarkdown(null)}
          className="animate-backdrop fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] flex items-center justify-center p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="animate-modal-enter bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 space-y-4 border border-gray-200"
          >
            <div className="flex items-center justify-between border-b border-gray-200 pb-3">
              <h3 className="text-base font-bold text-[#1F1F1F]">
                {t.weeklyDigestModalTitle}
              </h3>
              <button
                onClick={() => setDigestMarkdown(null)}
                className="p-1.5 rounded-full hover:bg-gray-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="text-xs text-[#1F1F1F] whitespace-pre-wrap leading-relaxed bg-[#F6F8FC] p-4 rounded-xl border border-gray-200 max-h-[65vh] overflow-y-auto">
              {digestMarkdown}
            </div>
          </div>
        </div>
      )}

      {/* Gmail Compose-Style Live 3D Email Simulator Modal */}
      {ingestModalOpen && (
        <div
          className={`animate-modal-enter fixed bottom-0 ${
            dir === "rtl" ? "left-10" : "right-10"
          } z-50 w-full max-w-lg bg-white rounded-t-2xl shadow-2xl border border-gray-300 overflow-hidden`}
        >
          <div className="px-4 py-3 bg-[#F2F6FC] border-b border-gray-200 flex items-center justify-between">
            <span className="text-xs font-bold text-[#1F1F1F]">
              {t.simulateModalTitle}
            </span>
            <button
              onClick={() => setIngestModalOpen(false)}
              className="p-1 rounded-full hover:bg-gray-200 text-gray-600 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <form onSubmit={handleSimulateIngest} className="p-4 space-y-3 text-xs">
            <div>
              <input
                type="email"
                required
                value={simSender}
                onChange={(e) => setSimSender(e.target.value)}
                placeholder={t.senderPlaceholder}
                className="w-full border-b border-gray-200 py-1.5 outline-none text-[#1F1F1F]"
              />
            </div>
            <div>
              <input
                type="text"
                required
                value={simSubject}
                onChange={(e) => setSimSubject(e.target.value)}
                placeholder={t.subjectPlaceholder}
                className="w-full border-b border-gray-200 py-1.5 outline-none font-bold text-[#1F1F1F]"
              />
            </div>
            <div>
              <textarea
                rows={4}
                required
                value={simBody}
                onChange={(e) => setSimBody(e.target.value)}
                placeholder={t.bodyPlaceholder}
                className="w-full border border-gray-200 rounded-xl p-2.5 outline-none text-[#1F1F1F]"
              />
            </div>
            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-gray-500">
                {t.pipelineHint}
              </span>
              <button
                type="submit"
                disabled={simSubmitting}
                className="smooth-pill px-5 py-2 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white font-bold flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{simSubmitting ? t.classifyingBtn : t.ingestBtn}</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
