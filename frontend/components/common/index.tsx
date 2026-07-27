"use client";

import React from "react";

export function PageContainer({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`max-w-7xl mx-auto ${className}`}>{children}</div>;
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold text-gray-300 mb-3">{title}</h2>
      {children}
    </div>
  );
}

export function LoadingScreen() {
  return (
    <div className="fixed inset-0 bg-gray-950 flex items-center justify-center z-50">
      <div className="text-center">
        <div className="w-12 h-12 border-2 border-gray-700 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
        <div className="text-lg font-semibold text-indigo-400">NOVA CORE</div>
        <div className="text-sm text-gray-500 mt-1">Loading...</div>
      </div>
    </div>
  );
}

export function ErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-3">&#9888;</div>
        <h2 className="text-lg font-semibold text-gray-300 mb-2">Something went wrong</h2>
        <p className="text-sm text-gray-500 mb-4">{error.message}</p>
        <button onClick={reset} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 text-sm">Try again</button>
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, onConfirm, onCancel }: { open: boolean; title: string; message: string; onConfirm: () => void; onCancel: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-gray-200 mb-2">{title}</h3>
        <p className="text-sm text-gray-400 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 text-sm bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600">Cancel</button>
          <button onClick={onConfirm} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-500">Confirm</button>
        </div>
      </div>
    </div>
  );
}

export function Toast({ message, type = "info" }: { message: string; type?: "info" | "success" | "error" }) {
  const colors = { info: "bg-blue-600", success: "bg-green-600", error: "bg-red-600" };
  return (
    <div className={`fixed bottom-4 right-4 z-50 ${colors[type]} text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-fade-in`}>
      {message}
    </div>
  );
}
