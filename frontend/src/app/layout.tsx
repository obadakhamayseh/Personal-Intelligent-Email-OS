import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "بريد جيميل — نظام البريد الذكي | Personal Intelligent Email OS",
  description:
    "Self-hosted Personal Intelligent Email OS for Gmail with 3D Classification, Safe Bulk Cleanup, pgvector RAG, and Telegram Command Center.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body className="h-screen w-screen flex flex-col bg-[#F6F8FC]">
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
