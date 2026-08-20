import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { MobileNav } from "@/components/mobile-nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Wettportal",
  description: "Persönliches Portal für Sportwetten-Strategie, Bankroll und Spielplan",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="de"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex bg-slate-950 text-slate-100">
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col">
          <MobileNav />
          <main className="flex-1 min-w-0 px-4 py-6 sm:px-8 sm:py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
