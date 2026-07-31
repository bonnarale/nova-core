"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

// ─── ErrorBoundary (class component — React requirement) ──────────────
interface ErrorBoundaryState {
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ error: null, errorInfo: null });
  };

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="text-5xl mb-4">&#9888;</div>
            <h2 className="text-xl font-semibold text-gray-200 mb-2">Something went wrong</h2>
            <p className="text-sm text-gray-400 mb-2">{this.state.error.message}</p>
            {this.state.errorInfo && (
              <details className="mt-3 text-left">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400 mb-2">
                  Stack trace
                </summary>
                <pre className="text-xs text-gray-500 bg-gray-900 rounded-lg p-3 overflow-auto max-h-48">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={this.handleReset}
              className="mt-4 px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 text-sm font-medium transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Toast System ────────────────────────────────────────────────────
export interface ToastItem {
  id: string;
  message: string;
  type: "info" | "success" | "error" | "warning";
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (message: string, type?: ToastItem["type"], duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastItem["type"] = "info", duration = 4000) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, message, type, duration }]);
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  // Subscribe to global toast events (for use outside React)
  useEffect(() => {
    // Lazy import to avoid circular deps in test environments
    import("@/lib/toast").then(({ globalToast }) => {
      const unsub = globalToast.subscribe(({ message, type, duration }) => {
        addToast(message, type, duration);
      });
      return unsub;
    }).catch(() => {
      // toast module not available (e.g. in tests) — silently ignore
    });
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast container — fixed bottom-right */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => {
          const colors = {
            info: "bg-blue-600",
            success: "bg-green-600",
            error: "bg-red-600",
            warning: "bg-yellow-600",
          };
          return (
            <div
              key={t.id}
              className={`${colors[t.type]} text-white px-4 py-3 rounded-lg shadow-lg text-sm pointer-events-auto flex items-center justify-between gap-3 min-w-[280px] animate-slide-in`}
            >
              <span>{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                className="text-white/70 hover:text-white text-lg leading-none ml-2"
              >
                &times;
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

// ─── ConfirmDialog ───────────────────────────────────────────────────
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

// ─── Other common components ─────────────────────────────────────────
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
