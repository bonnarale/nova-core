"use client";

import "./globals.css";
import React from "react";
import { Sidebar, Header } from "@/components/layout";
import { useAppStore } from "@/stores";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { theme } = useAppStore();
  return (
    <html lang="en" className={theme}>
      <body className="bg-gray-950 text-gray-200 min-h-screen">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
