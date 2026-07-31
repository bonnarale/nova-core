"use client";

import "./globals.css";
import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar, Header } from "@/components/layout";
import { ErrorBoundary, ToastProvider } from "@/components/common";
import { useAppStore } from "@/stores";

const PUBLIC_PATHS = ["/auth"];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { theme, token } = useAppStore();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const [hydrated, setHydrated] = useState(false);

  // Wait for Zustand to hydrate from localStorage
  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated && !isPublic && !token) {
      router.push("/auth");
    }
  }, [hydrated, token, pathname, isPublic, router]);

  // Always render the auth page without chrome
  if (isPublic) {
    return (
      <html lang="en" className={theme}>
        <body className="bg-gray-950 text-gray-200 min-h-screen">
          <ErrorBoundary>
            <ToastProvider>{children}</ToastProvider>
          </ErrorBoundary>
        </body>
      </html>
    );
  }

  // Don't render protected content until hydrated and authenticated
  if (!hydrated || !token) {
    return (
      <html lang="en" className={theme}>
        <body className="bg-gray-950 text-gray-200 min-h-screen" />
      </html>
    );
  }

  return (
    <html lang="en" className={theme}>
      <body className="bg-gray-950 text-gray-200 min-h-screen">
        <ErrorBoundary>
          <ToastProvider>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              <div className="flex-1 flex flex-col overflow-hidden">
                <Header />
                <main className="flex-1 overflow-y-auto p-6">{children}</main>
              </div>
            </div>
          </ToastProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
