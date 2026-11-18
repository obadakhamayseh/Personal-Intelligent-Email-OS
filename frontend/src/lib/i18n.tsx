"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { SmartCategory } from "./types";

export type AppLanguage = "ar" | "en";

interface Translations {
  appName: string;
  appBadge: string;
  searchPlaceholder: string;
  clear: string;
  askAiRag: string;
  p0CriticalBadge: string;
  syncGmail: string;
  syncing: string;
  shieldsActive: string;
  simulateEmail: string;
  allInbox: string;
  starred: string;
  sent: string;
  trash: string;
  smartLabelsHeader: string;
  commandViewsHeader: string;
  safeCleanupSimulator: string;
  oauthAndSlaExposure: string;
  deadSubscriptions: string;
  tier1RuleEngine: string;
  nextCleanup: string;
  activeDeadlines: string;
  slaItems: string;
  allPriority: string;
  p0Critical: string;
  p1High: string;
  p2Normal: string;
  p3Noise: string;
  runWeeklyDigest: string;
  generatingDigest: string;
  ofTotal: string;
  tabPrimary: string;
  tabInfra: string;
  tabFinancial: string;
  tabSla: string;
  noMessagesMatch: string;
  openInGmail: string;
  aiSummaryLabel: string;
  protectedFromDelete: string;
  expiresLabel: string;
  toLabel: string;
  threadIdLabel: string;
  classificationEngineLabel: string;
  ruleNumber: string;
  // Cleanup Simulator
  cleanupTitle: string;
  cleanupSubtitle: string;
  cutoffDate: string;
  includeExpiredTtl: string;
  runDryRun: string;
  simulating: string;
  eligibleToTrash: string;
  estimatedStorageFreed: string;
  activeThreadShield: string;
  activeThreadShieldDesc: string;
  protectedLabelsShield: string;
  protectedLabelsShieldDesc: string;
  protectedWord: string;
  dryRunBreakdown: string;
  confirmMoveToTrash: string;
  movingToTrash: string;
  noEligibleCleanup: string;
  sampleSubjects: string;
  auditTrailTitle: string;
  noAuditBatches: string;
  undoRestoreBatch: string;
  affectedLabel: string;
  executedAtLabel: string;
  // RAG Drawer
  ragTitle: string;
  ragSubtitle: string;
  quickQueries: string;
  searchingVectors: string;
  verifiedCitations: string;
  openThread: string;
  ragInputPlaceholder: string;
  askBtn: string;
  // OAuth & SLA View
  oauthViewTitle: string;
  oauthViewSubtitle: string;
  oauthRegistryHeader: string;
  firstSeen: string;
  inspectSecurityEmail: string;
  upcomingSlaHeader: string;
  dueLabel: string;
  financialHeader: string;
  protectedReceipt: string;
  // Dead Subscriptions View
  deadSubsTitle: string;
  deadSubsSubtitle: string;
  showDeadOnly: string;
  colSender: string;
  colReceivedRead: string;
  colUnreadRate: string;
  colNoiseScore: string;
  colStatus: string;
  colActions: string;
  mutedRuleActive: string;
  deadSubBadge: string;
  activeSenderBadge: string;
  autoArchiveBtn: string;
  unsubscribeBtn: string;
  // Rules Manager View
  rulesTitle: string;
  rulesSubtitle: string;
  ruleNameLabel: string;
  senderDomainsLabel: string;
  subjectRegexLabel: string;
  targetCategoryLabel: string;
  addRuleBtn: string;
  colPriority: string;
  colRuleCriteria: string;
  col3dTarget: string;
  colHits: string;
  activeRule: string;
  pausedRule: string;
  // Simulate Modal & Digest
  simulateModalTitle: string;
  senderPlaceholder: string;
  subjectPlaceholder: string;
  bodyPlaceholder: string;
  pipelineHint: string;
  ingestBtn: string;
  classifyingBtn: string;
  weeklyDigestModalTitle: string;
  categories: Record<SmartCategory, string>;
}

const dict: Record<AppLanguage, Translations> = {
  ar: {
    appName: "بريد جيميل",
    appBadge: "نظام البريد الذكي",
    searchPlaceholder: "ابحث في البريد (الموضوع، المرسل، ملخص الذكاء الاصطناعي، بالعربية أو الإنجليزية)...",
    clear: "مسح",
    askAiRag: "اسأل المساعد الذكي",
    p0CriticalBadge: "طوارئ حرجة P0",
    syncGmail: "مزامنة جيميل",
    syncing: "جاري المزامنة...",
    shieldsActive: "دروع الحماية نشطة",
    simulateEmail: "محاكاة رسالة جديدة",
    allInbox: "كل الوارد",
    starred: "المميزة بنجمة",
    sent: "المرسلة",
    trash: "المهملات",
    smartLabelsHeader: "التصنيفات الذكية (AI/*)",
    commandViewsHeader: "مركز التحكم الذكي",
    safeCleanupSimulator: "محاكي التنظيف الآمن",
    oauthAndSlaExposure: "رادار الأمان والمواعيد",
    deadSubscriptions: "الاشتراكات الميتة والإزعاج",
    tier1RuleEngine: "محرك القواعد الفوري",
    nextCleanup: "التنظيف القادم:",
    activeDeadlines: "مواعيد نهائية نشطة:",
    slaItems: "مهام",
    allPriority: "كل الأولويات",
    p0Critical: "🚨 P0 حرج جداً",
    p1High: "⚡ P1 هام",
    p2Normal: "P2 عادي",
    p3Noise: "P3 ترويجي/ضجيج",
    runWeeklyDigest: "توليد الملخص الأسبوعي",
    generatingDigest: "جاري التلخيص...",
    ofTotal: "من أصل",
    tabPrimary: "البريد الأساسي",
    tabInfra: "طوارئ السيرفرات والسحابة",
    tabFinancial: "المالية والفواتير",
    tabSla: "المواعيد النهائية SLA",
    noMessagesMatch: "لا توجد رسائل مطابقة لهذا القسم أو الفلتر.",
    openInGmail: "فتح في جيميل",
    aiSummaryLabel: "ملخص الذكاء الاصطناعي:",
    protectedFromDelete: "محمي من الحذف التلقائي",
    expiresLabel: "ينتهي في:",
    toLabel: "إلى:",
    threadIdLabel: "معرّف المحادثة:",
    classificationEngineLabel: "محرك التصنيف ثلاثي الأبعاد",
    ruleNumber: "قاعدة رقم #",
    cleanupTitle: "محاكي التنظيف الآمن واسع النطاق وسجل التدقيق",
    cleanupSubtitle: "يطبق درع المحادثات النشطة، ودرع الفئات المحمية، والحذف على دفعات 1000 رسالة مع إمكانية التراجع بضغطة واحدة.",
    cutoffDate: "تاريخ القطع:",
    includeExpiredTtl: "تضمين الرسائل منتهية الصلاحية (أكواد OTP)",
    runDryRun: "تشغيل فحص تجريبي (Dry-Run)",
    simulating: "جاري الفحص...",
    eligibleToTrash: "مؤهلة للنقل إلى المهملات",
    estimatedStorageFreed: "المساحة المقدرة المستعادة",
    activeThreadShield: "درع المحادثات النشطة",
    activeThreadShieldDesc: "تم استثناء المحادثات التي تحتوي على ردود حديثة",
    protectedLabelsShield: "درع الفئات المحمية",
    protectedLabelsShieldDesc: "تم استثناء المميزة بنجمة والمالية والأمان و P0",
    protectedWord: "محمية",
    dryRunBreakdown: "تفصيل الرسائل المرشحة للحذف حسب الفئة",
    confirmMoveToTrash: "تأكيد النقل إلى المهملات",
    movingToTrash: "جاري النقل للمهملات...",
    noEligibleCleanup: "لا توجد رسائل مؤهلة للحذف حالياً في ظل دروع الحماية النشطة.",
    sampleSubjects: "أمثلة العناوين:",
    auditTrailTitle: "سجل عمليات التنظيف والتراجع بضغطة واحدة (Undo / Restore)",
    noAuditBatches: "لم يتم تنفيذ أي دفعات تنظيف حتى الآن.",
    undoRestoreBatch: "تراجع واستعادة الدفعة",
    affectedLabel: "الرسائل المتأثرة:",
    executedAtLabel: "تاريخ التنفيذ:",
    ragTitle: "المساعد الدلالي الذكي للبريد (pgvector RAG)",
    ragSubtitle: "اسأل بالعربية أو الإنجليزية — يجيب مع روابط موثقة لمحادثات جيميل",
    quickQueries: "أسئلة سريعة مقترحة:",
    searchingVectors: "جاري البحث الدلالي في المتجهات وتوليد الإجابة الموثقة...",
    verifiedCitations: "المصادر والمحادثات الموثقة",
    openThread: "فتح المحادثة",
    ragInputPlaceholder: "اسأل أي سؤال حول رسائلك وفواتيرك ومواعيدك...",
    askBtn: "إرسال",
    oauthViewTitle: "خريطة انكشاف الحسابات (OAuth) والمواعيد النهائية والفواتير",
    oauthViewSubtitle: "يتم استخراجها وتحديثها تلقائياً بواسطة محرك التصنيف ثلاثي الأبعاد.",
    oauthRegistryHeader: "التطبيقات والخدمات المرتبطة بحسابك (OAuth Exposure Map)",
    firstSeen: "أول ظهور:",
    inspectSecurityEmail: "فحص رسالة الأمان",
    upcomingSlaHeader: "المواعيد النهائية القادمة والمحادثات بانتظار الرد",
    dueLabel: "الموعد النهائي:",
    financialHeader: "الأحداث المالية والإيصالات المحمية",
    protectedReceipt: "إيصال محمي",
    deadSubsTitle: "مؤشر إزعاج المرسلين وكاشف الاشتراكات الميتة",
    deadSubsSubtitle: "يكتشف المرسلين الذين أرسلوا 5 رسائل فأكثر بنسبة عدم قراءة تتجاوز 90% خلال 60 يوماً.",
    showDeadOnly: "عرض الاشتراكات الميتة فقط (>=5 رسائل و >90% غير مقروءة)",
    colSender: "المرسل",
    colReceivedRead: "المستلمة / المقروءة",
    colUnreadRate: "نسبة عدم القراءة",
    colNoiseScore: "مؤشر الإزعاج",
    colStatus: "الحالة",
    colActions: "إجراءات بضغطة واحدة",
    mutedRuleActive: "قاعدة الكتم مفعّلة",
    deadSubBadge: "اشتراك ميت",
    activeSenderBadge: "مرسل نشط",
    autoArchiveBtn: "قاعدة أرشفة تلقائية",
    unsubscribeBtn: "إلغاء اشتراك RFC-8058",
    rulesTitle: "محرك القواعد الحتمية الفوري (Tier 1 — 0ms بدون تكلفة API)",
    rulesSubtitle: "يفحص نطاق المرسل والعنوان والترويسات والتعابير النمطية (Regex) في PostgreSQL قبل اللجوء لنموذج الذكاء الاصطناعي.",
    ruleNameLabel: "اسم القاعدة",
    senderDomainsLabel: "نطاق المرسل (Domain)",
    subjectRegexLabel: "نمط الموضوع (Regex)",
    targetCategoryLabel: "الفئة المستهدفة",
    addRuleBtn: "إضافة",
    colPriority: "الأولوية",
    colRuleCriteria: "اسم القاعدة وشروط المطابقة",
    col3dTarget: "التصنيف الثلاثي المستهدف",
    colHits: "التطابقات",
    activeRule: "مفعّلة",
    pausedRule: "متوقفة",
    simulateModalTitle: "محاكاة رسالة واردة جديدة (اختبار التصنيف الثلاثي والبحث الدلالي)",
    senderPlaceholder: "بريد المرسل (مثال: alerts@cloudflare.com)",
    subjectPlaceholder: "عنوان الرسالة (بالعربية أو الإنجليزية)",
    bodyPlaceholder: "محتوى الرسالة...",
    pipelineHint: "يمر عبر محرك القواعد ⬅ الذكاء الاصطناعي ⬅ الفهرسة الدلالية",
    ingestBtn: "إدراج وتصنيف ذكي",
    classifyingBtn: "جاري التصنيف...",
    weeklyDigestModalTitle: "الملخص المعرفي الأسبوعي التنفيذي (ثنائي اللغة)",
    categories: {
      "AI/Infra-Incidents": "طوارئ البنية التحتية",
      "AI/Financial-Leakage": "المالية والاشتراكات",
      "AI/Security-OAuth-Radar": "رادار الأمان و OAuth",
      "AI/Action-SLA": "مواعيد وإجراءات مطلوبة",
      "AI/Ephemeral-SelfDestruct": "أكواد التحقق المؤقتة (24س)",
      "AI/Waiting-On-Ghosted": "بانتظار الرد (72س)",
      "AI/Study-Training": "الدراسة والتدريب",
      "AI/Knowledge-Digest": "النشرات المعرفية",
      "AI/Promotions-Noise": "العروض والترويج",
    },
  },
  en: {
    appName: "Gmail",
    appBadge: "AI Email OS",
    searchPlaceholder: "Search in mail (subject, sender, AI summary, Arabic or English)...",
    clear: "Clear",
    askAiRag: "Ask AI RAG",
    p0CriticalBadge: "P0 Critical",
    syncGmail: "Sync Gmail",
    syncing: "Syncing...",
    shieldsActive: "Shields Active",
    simulateEmail: "Simulate Email",
    allInbox: "All Inbox",
    starred: "Starred",
    sent: "Sent",
    trash: "Trash",
    smartLabelsHeader: "Smart 3D Labels (AI/*)",
    commandViewsHeader: "Email OS Command Views",
    safeCleanupSimulator: "Safe Cleanup Simulator",
    oauthAndSlaExposure: "OAuth & SLA Exposure",
    deadSubscriptions: "Dead Subscriptions",
    tier1RuleEngine: "Tier 1 Rule Engine",
    nextCleanup: "Next Cleanup:",
    activeDeadlines: "Active Deadlines:",
    slaItems: "SLA items",
    allPriority: "All Priority",
    p0Critical: "🚨 P0 Critical",
    p1High: "⚡ P1 High",
    p2Normal: "P2 Normal",
    p3Noise: "P3 Noise",
    runWeeklyDigest: "Run Weekly Digest",
    generatingDigest: "Generating Digest...",
    ofTotal: "of",
    tabPrimary: "Primary",
    tabInfra: "Infra & Cloud Alerts",
    tabFinancial: "Financial & Receipts",
    tabSla: "Action SLA Deadlines",
    noMessagesMatch: "No messages match this view or filter.",
    openInGmail: "Open in Gmail",
    aiSummaryLabel: "AI Summary:",
    protectedFromDelete: "Protected from Auto-Delete",
    expiresLabel: "Expires:",
    toLabel: "To:",
    threadIdLabel: "Thread ID:",
    classificationEngineLabel: "3D Classification Engine",
    ruleNumber: "Rule #",
    cleanupTitle: "High-Scale Safe Bulk Cleanup Simulator & Audit Center",
    cleanupSubtitle: "Enforces Active Thread Shield, Protected Labels Shield, 1,000-ID chunked batchModify, and 1-click Undo/Restore.",
    cutoffDate: "Cutoff Date:",
    includeExpiredTtl: "Include Expired TTL (OTPs)",
    runDryRun: "Run Dry-Run Preview",
    simulating: "Simulating...",
    eligibleToTrash: "Eligible to Move to Trash",
    estimatedStorageFreed: "Estimated Storage Freed",
    activeThreadShield: "Active Thread Shield",
    activeThreadShieldDesc: "Threads with recent replies spared",
    protectedLabelsShield: "Protected Labels Shield",
    protectedLabelsShieldDesc: "Starred, Financial, OAuth & P0 spared",
    protectedWord: "protected",
    dryRunBreakdown: "Dry-Run Candidate Breakdown by Category",
    confirmMoveToTrash: "Confirm Move to Trash",
    movingToTrash: "Moving to Trash...",
    noEligibleCleanup: "No messages currently eligible for cleanup under the active safety shields.",
    sampleSubjects: "Sample subjects:",
    auditTrailTitle: "Cleanup Audit Trail & 1-Click Undo / Restore",
    noAuditBatches: "No cleanup batches executed yet.",
    undoRestoreBatch: "Undo / Restore Batch",
    affectedLabel: "Affected:",
    executedAtLabel: "Executed:",
    ragTitle: "Semantic Email RAG (pgvector)",
    ragSubtitle: "Ask in English or Arabic — returns verified Gmail thread citations",
    quickQueries: "Quick Bilingual Queries:",
    searchingVectors: "Searching pgvector embeddings & synthesizing answer...",
    verifiedCitations: "Verified Gmail Thread Citations",
    openThread: "Open Thread",
    ragInputPlaceholder: "Ask anything about your emails (English or العربية)...",
    askBtn: "Ask",
    oauthViewTitle: "OAuth & Account Exposure Map + Action SLA & Financial Radar",
    oauthViewSubtitle: "Automatically populated by the 3D Classification Engine from Security, Action-SLA, and Financial emails.",
    oauthRegistryHeader: "Third-Party OAuth & Connected Services Exposure Map",
    firstSeen: "First seen:",
    inspectSecurityEmail: "Inspect Security Email",
    upcomingSlaHeader: "Upcoming Action SLA Deadlines & Ghosted Follow-Ups",
    dueLabel: "Due:",
    financialHeader: "Protected Financial Events & Receipts",
    protectedReceipt: "Protected Receipt",
    deadSubsTitle: "Sender Noise Score & Dead Subscription Detector",
    deadSubsSubtitle: "Flags senders with >= 5 emails and > 90% unread rate over 60 days.",
    showDeadOnly: "Show Dead Subscriptions Only (>=5 msgs & >90% unread)",
    colSender: "Sender",
    colReceivedRead: "Received / Read",
    colUnreadRate: "Unread Rate",
    colNoiseScore: "Noise Score",
    colStatus: "Status",
    colActions: "1-Click Actions",
    mutedRuleActive: "Muted Rule Active",
    deadSubBadge: "Dead Subscription",
    activeSenderBadge: "Active Sender",
    autoArchiveBtn: "1-Click Auto-Archive Rule",
    unsubscribeBtn: "RFC-8058 Unsubscribe",
    rulesTitle: "Tier 1 Deterministic Rule Engine (0ms, Zero API Cost)",
    rulesSubtitle: "Evaluates sender domains, exact addresses, headers, and regex patterns in PostgreSQL before Tier 2 LLM.",
    ruleNameLabel: "Rule Name",
    senderDomainsLabel: "Sender Domain(s)",
    subjectRegexLabel: "Subject Regex",
    targetCategoryLabel: "Target Category",
    addRuleBtn: "Add",
    colPriority: "Priority",
    colRuleCriteria: "Rule Name & Match Criteria",
    col3dTarget: "3D Target Assignment",
    colHits: "Hits",
    activeRule: "Active",
    pausedRule: "Paused",
    simulateModalTitle: "Simulate Incoming Email (Test 3D Hybrid Classifier & RAG)",
    senderPlaceholder: "Sender email (e.g. alerts@cloudflare.com)",
    subjectPlaceholder: "Subject (English or Arabic)",
    bodyPlaceholder: "Email body text...",
    pipelineHint: "Runs Tier 1 Rule Engine → Tier 2 LLM → pgvector RAG",
    ingestBtn: "Ingest & Classify",
    classifyingBtn: "Classifying...",
    weeklyDigestModalTitle: "Weekly Executive Knowledge Digest (Bilingual)",
    categories: {
      "AI/Infra-Incidents": "Infra Incidents",
      "AI/Financial-Leakage": "Financial & Receipts",
      "AI/Security-OAuth-Radar": "Security & OAuth Radar",
      "AI/Action-SLA": "Action SLA Deadlines",
      "AI/Ephemeral-SelfDestruct": "Ephemeral OTP (24h)",
      "AI/Waiting-On-Ghosted": "Waiting On / Ghosted",
      "AI/Study-Training": "Study & Training",
      "AI/Knowledge-Digest": "Knowledge Digest",
      "AI/Promotions-Noise": "Promotions & Noise",
    },
  },
};

interface LanguageContextValue {
  lang: AppLanguage;
  dir: "rtl" | "ltr";
  t: Translations;
  toggleLanguage: () => void;
  setLanguage: (lang: AppLanguage) => void;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "ar",
  dir: "rtl",
  t: dict.ar,
  toggleLanguage: () => {},
  setLanguage: () => {},
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<AppLanguage>("ar");

  useEffect(() => {
    const saved = localStorage.getItem("emailos_lang") as AppLanguage | null;
    if (saved === "ar" || saved === "en") {
      setLangState(saved);
    }
  }, []);

  const setLanguage = (next: AppLanguage) => {
    setLangState(next);
    localStorage.setItem("emailos_lang", next);
  };

  const toggleLanguage = () => {
    setLanguage(lang === "ar" ? "en" : "ar");
  };

  const dir = lang === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  return (
    <LanguageContext.Provider
      value={{
        lang,
        dir,
        t: dict[lang],
        toggleLanguage,
        setLanguage,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
