"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  KeyRound,
  ExternalLink,
  CheckCircle2,
  LogOut,
  Copy,
  Check,
  ShieldCheck,
} from "lucide-react";
import { EmailOSApi } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

interface GoogleConnectModalProps {
  open: boolean;
  onClose: () => void;
  onConnectedChange: () => void;
}

export default function GoogleConnectModal({
  open,
  onClose,
  onConnectedChange,
}: GoogleConnectModalProps) {
  const { lang } = useLanguage();
  const isAr = lang === "ar";

  const [connected, setConnected] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [redirectUri, setRedirectUri] = useState(
    "http://localhost:8000/api/v1/auth/google/callback"
  );
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadStatus = async () => {
    try {
      const st = await EmailOSApi.getGoogleOAuthStatus();
      setConnected(st.connected);
      setConfigured(st.configured);
      if (st.redirect_uri) setRedirectUri(st.redirect_uri);
      setShowConfigForm(!st.configured);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    if (open) {
      setError(null);
      loadStatus();
    }
  }, [open]);

  if (!open) return null;

  const handleCopyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveAndSignIn = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (showConfigForm || !configured) {
        if (!clientId.trim() || !clientSecret.trim()) {
          throw new Error(
            isAr
              ? "يرجى إدخال Google Client ID و Client Secret أولاً."
              : "Please enter both Google Client ID and Client Secret."
          );
        }
        await EmailOSApi.saveGoogleOAuthConfig({
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
          redirect_uri: redirectUri,
        });
        setConfigured(true);
      }

      const { authorization_url } = await EmailOSApi.getGoogleOAuthUrl();
      window.location.href = authorization_url;
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await EmailOSApi.disconnectGoogleAccount();
      setConnected(false);
      onConnectedChange();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="animate-backdrop fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px] flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-modal-enter bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-gray-200"
      >
        {/* Header */}
        <div className="px-6 py-4 bg-[#EAF1FB] border-b border-[#D3E3FD] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-white shadow-2xs flex items-center justify-center border border-gray-200">
              <span className="text-red-600 font-extrabold text-lg">G</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#041E49]">
                {isAr
                  ? "ربط وتسجيل الدخول بحساب Google Gmail"
                  : "Connect & Sign in with Google Gmail"}
              </h3>
              <p className="text-[11px] text-[#444746]">
                {isAr
                  ? "OAuth 2.0 مشفّر عبر Fernet مع مزامنة تلقائية للتصنيفات الذكية"
                  : "Fernet-encrypted OAuth 2.0 with automatic Smart Labels sync"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-gray-200 text-gray-600 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 text-xs">
          {error && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 font-medium">
              {error}
            </div>
          )}

          {connected ? (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold text-sm text-emerald-900">
                      {isAr
                        ? "حساب Gmail مربوط ومتصل بنجاح"
                        : "Gmail Account Connected & Active"}
                    </div>
                    <div className="text-emerald-700 mt-0.5">
                      {isAr
                        ? "المزامنة التلقائية والتصنيف ثلاثي الأبعاد يعملان على حسابك."
                        : "Live sync and 3D classification are active on your account."}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={() => setShowConfigForm((s) => !s)}
                  className="text-[#0B57D0] hover:underline font-semibold"
                >
                  {isAr
                    ? "تحديث بيانات Client ID / Secret"
                    : "Update Client ID / Secret"}
                </button>

                <button
                  onClick={handleDisconnect}
                  disabled={loading}
                  className="smooth-pill flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-bold"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>
                    {isAr ? "تسجيل الخروج / فصل الحساب" : "Disconnect Account"}
                  </span>
                </button>
              </div>
            </div>
          ) : null}

          {(!connected || showConfigForm) && (
            <form onSubmit={handleSaveAndSignIn} className="space-y-4">
              {/* Redirect URI Copy Box */}
              <div className="p-3.5 rounded-xl bg-[#F6F8FC] border border-gray-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-gray-700">
                    {isAr
                      ? "رابط الرجوع (Authorized Redirect URI) في Google Cloud:"
                      : "Authorized Redirect URI for Google Cloud Console:"}
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyRedirectUri}
                    className="flex items-center gap-1 text-[#0B57D0] font-bold hover:underline"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-600">
                          {isAr ? "تم النسخ" : "Copied"}
                        </span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>{isAr ? "نسخ الرابط" : "Copy"}</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="font-mono text-[11px] bg-white px-3 py-1.5 rounded-lg border border-gray-200 text-gray-800 select-all">
                  {redirectUri}
                </div>
              </div>

              {configured && !showConfigForm ? (
                <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-blue-900 font-medium">
                    <ShieldCheck className="w-4 h-4 text-[#0B57D0]" />
                    <span>
                      {isAr
                        ? "بيانات Google OAuth جاهزة ومهيأة."
                        : "Google OAuth credentials are configured."}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowConfigForm(true)}
                    className="text-[#0B57D0] font-bold hover:underline"
                  >
                    {isAr ? "تعديل المفاتيح" : "Edit Keys"}
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">
                      Google Client ID
                    </label>
                    <input
                      type="text"
                      required
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder="xxxx.apps.googleusercontent.com"
                      className="w-full rounded-xl border border-gray-300 px-3.5 py-2.5 outline-none focus:border-[#0B57D0]"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">
                      Google Client Secret
                    </label>
                    <input
                      type="password"
                      required
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="GOCSPX-xxxxxxxxxxxxxxxx"
                      className="w-full rounded-xl border border-gray-300 px-3.5 py-2.5 outline-none focus:border-[#0B57D0]"
                    />
                  </div>
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="smooth-pill w-full py-3 px-5 rounded-full bg-[#0B57D0] hover:bg-blue-800 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md"
                >
                  <KeyRound className="w-4 h-4" />
                  <span>
                    {loading
                      ? isAr
                        ? "جاري التحويل إلى Google..."
                        : "Redirecting to Google..."
                      : isAr
                      ? "تسجيل الدخول بحساب Google الآن"
                      : "Sign in with Google Now"}
                  </span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
