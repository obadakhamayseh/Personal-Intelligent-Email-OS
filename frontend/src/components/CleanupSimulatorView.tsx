"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  Trash2,
  RotateCcw,
  SearchCheck,
  AlertTriangle,
  HardDrive,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { CleanupAuditItem, CleanupPreviewResponse, SmartCategory } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface CleanupSimulatorViewProps {
  onCleanupExecuted: () => void;
}

export default function CleanupSimulatorView({
  onCleanupExecuted,
}: CleanupSimulatorViewProps) {
  const { t } = useLanguage();
  const [beforeDate, setBeforeDate] = useState<string>("");
  const [includeExpiredTtl, setIncludeExpiredTtl] = useState<boolean>(true);
  const [preview, setPreview] = useState<CleanupPreviewResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<CleanupAuditItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [banner, setBanner] = useState<string | null>(null);

  const loadPreviewAndLogs = async () => {
    setLoading(true);
    try {
      const payload: {
        before_date?: string;
        include_expired_ttl: boolean;
      } = {
        include_expired_ttl: includeExpiredTtl,
      };
      if (beforeDate) {
        payload.before_date = `${beforeDate}T23:59:59.999Z`;
      }
      const [prevRes, logsRes] = await Promise.all([
        EmailOSApi.dryRunCleanup(payload),
        EmailOSApi.listAuditLogs(),
      ]);
      setPreview(prevRes);
      setAuditLogs(logsRes);
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPreviewAndLogs();
  }, [beforeDate, includeExpiredTtl]);

  const handleExecuteCleanup = async () => {
    setExecuting(true);
    setBanner(null);
    try {
      const payload: {
        before_date?: string;
        include_expired_ttl: boolean;
      } = {
        include_expired_ttl: includeExpiredTtl,
      };
      if (beforeDate) {
        payload.before_date = `${beforeDate}T23:59:59.999Z`;
      }
      const audit = await EmailOSApi.executeCleanup(payload);
      setBanner(
        `✅ ${audit.batch_id}: (${audit.total_messages})`
      );
      await loadPreviewAndLogs();
      onCleanupExecuted();
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleUndoBatch = async (batchId: string) => {
    setExecuting(true);
    try {
      const restored = await EmailOSApi.undoCleanup(batchId);
      setBanner(`♻️ ${restored.batch_id}: (${restored.total_messages})`);
      await loadPreviewAndLogs();
      onCleanupExecuted();
    } catch (err: any) {
      setBanner(`Error: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="animate-view-enter flex-1 bg-white rounded-2xl shadow-sm border border-[#E1E5EA] p-6 overflow-y-auto mx-3 mb-3 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F1F1F]">{t.cleanupTitle}</h2>
          <p className="text-xs text-[#444746] mt-0.5">{t.cleanupSubtitle}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <label className="text-[#444746] font-semibold">
              {t.cutoffDate}
            </label>
            <input
              type="date"
              value={beforeDate}
              onChange={(e) => setBeforeDate(e.target.value)}
              className="border border-gray-300 rounded-xl px-2.5 py-1.5 text-xs"
            />
          </div>

          <label className="flex items-center gap-1.5 text-xs text-[#444746] cursor-pointer font-medium">
            <input
              type="checkbox"
              checked={includeExpiredTtl}
              onChange={(e) => setIncludeExpiredTtl(e.target.checked)}
              className="rounded"
            />
            <span>{t.includeExpiredTtl}</span>
          </label>

          <button
            onClick={loadPreviewAndLogs}
            disabled={loading}
            className="smooth-pill flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#EAF1FB] hover:bg-[#D3E3FD] text-[#041E49] text-xs font-bold"
          >
            <SearchCheck className="w-4 h-4" />
            <span>{loading ? t.simulating : t.runDryRun}</span>
          </button>
        </div>
      </div>

      {banner && (
        <div className="animate-view-enter p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-900">
          {banner}
        </div>
      )}

      {/* Safety Shields & Summary Metrics */}
      {preview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="gmail-row-smooth p-4 rounded-2xl bg-rose-50 border border-rose-200">
            <div className="text-xs text-rose-700 font-semibold">
              {t.eligibleToTrash}
            </div>
            <div className="text-2xl font-bold text-rose-900 mt-1">
              {preview.total_candidate_messages}
            </div>
            <div className="text-[11px] text-rose-600 mt-1">
              {t.cutoffDate}{" "}
              {new Date(preview.cutoff_date).toLocaleDateString()}
            </div>
          </div>

          <div className="gmail-row-smooth p-4 rounded-2xl bg-blue-50 border border-blue-200">
            <div className="flex items-center gap-1.5 text-xs text-blue-700 font-semibold">
              <HardDrive className="w-3.5 h-3.5" />
              <span>{t.estimatedStorageFreed}</span>
            </div>
            <div className="text-2xl font-bold text-blue-900 mt-1">
              {(preview.estimated_bytes_freed / 1024).toFixed(1)} KB
            </div>
            <div className="text-[11px] text-blue-600 mt-1">
              ({preview.estimated_mb_freed} MB)
            </div>
          </div>

          <div className="gmail-row-smooth p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
            <div className="flex items-center gap-1.5 text-xs text-emerald-800 font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>{t.activeThreadShield}</span>
            </div>
            <div className="text-2xl font-bold text-emerald-900 mt-1">
              {preview.shielded_active_threads_count} {t.protectedWord}
            </div>
            <div className="text-[11px] text-emerald-700 mt-1">
              {t.activeThreadShieldDesc}
            </div>
          </div>

          <div className="gmail-row-smooth p-4 rounded-2xl bg-amber-50 border border-amber-200">
            <div className="flex items-center gap-1.5 text-xs text-amber-800 font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>{t.protectedLabelsShield}</span>
            </div>
            <div className="text-2xl font-bold text-amber-900 mt-1">
              {preview.shielded_protected_labels_count} {t.protectedWord}
            </div>
            <div className="text-[11px] text-amber-700 mt-1">
              {t.protectedLabelsShieldDesc}
            </div>
          </div>
        </div>
      )}

      {/* Category Breakdown & Execute Action */}
      {preview && (
        <div className="border border-gray-200 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200 flex items-center justify-between">
            <span className="text-xs font-bold text-[#1F1F1F]">
              {t.dryRunBreakdown}
            </span>
            <button
              onClick={handleExecuteCleanup}
              disabled={executing || preview.total_candidate_messages === 0}
              className="smooth-pill flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-600 hover:bg-red-700 disabled:bg-gray-300 text-white text-xs font-bold"
            >
              <Trash2 className="w-4 h-4" />
              <span>
                {executing
                  ? t.movingToTrash
                  : `${t.confirmMoveToTrash} (${preview.total_candidate_messages})`}
              </span>
            </button>
          </div>

          {preview.categories.length === 0 ? (
            <div className="p-6 text-center text-xs text-gray-500">
              {t.noEligibleCleanup}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {preview.categories.map((cat) => (
                <div key={cat.category} className="p-4 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-[#EAF1FB] text-[#041E49]">
                      {t.categories[cat.category as SmartCategory] ||
                        cat.category}
                    </span>
                    <span className="text-xs font-bold text-gray-800">
                      {cat.count} ({(cat.bytes_freed / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <div className="text-xs text-gray-600">
                    <strong>{t.sampleSubjects}</strong>{" "}
                    {cat.sample_subjects.join(" • ")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Audit Logs & 1-Click Undo */}
      <div className="border border-gray-200 rounded-2xl overflow-hidden">
        <div className="px-4 py-3 bg-[#F6F8FC] border-b border-gray-200">
          <span className="text-xs font-bold text-[#1F1F1F]">
            {t.auditTrailTitle}
          </span>
        </div>
        {auditLogs.length === 0 ? (
          <div className="p-6 text-center text-xs text-gray-500">
            {t.noAuditBatches}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {auditLogs.map((log) => (
              <div
                key={log.batch_id}
                className="p-4 flex items-center justify-between text-xs hover:bg-gray-50 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-[#1F1F1F]">
                      {log.batch_id}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        log.status === "RESTORED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {log.status}
                    </span>
                  </div>
                  <div className="text-gray-500">
                    {t.affectedLabel} <strong>{log.total_messages}</strong> •{" "}
                    {t.executedAtLabel}{" "}
                    {new Date(log.created_at).toLocaleString()}
                  </div>
                </div>

                {log.status !== "RESTORED" && log.total_messages > 0 && (
                  <button
                    onClick={() => handleUndoBatch(log.batch_id)}
                    disabled={executing}
                    className="smooth-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{t.undoRestoreBatch}</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
