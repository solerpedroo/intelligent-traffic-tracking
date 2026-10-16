import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { SiteNav } from "@/components/site-nav";
import "./globals.css";

const geistSans = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-geist-sans",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "Intelligent Traffic Tracking",
  description: "Reproducible traffic video analysis and scientific evaluation.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-brand-foreground"
        >
          Skip to main content
        </a>
        <SiteNav />
        <div className="relative min-h-screen lg:pl-[260px]">
          <div
            className="canvas-grid pointer-events-none absolute inset-x-0 top-0 h-72"
            aria-hidden
          />
          <div
            id="main-content"
            className="relative mx-auto w-full max-w-6xl px-4 py-8 sm:px-6"
          >
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
