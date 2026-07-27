"use client";

import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export function Button({ variant = "primary", size = "md", loading, children, className = "", ...props }: ButtonProps) {
  const base = "inline-flex items-center justify-center font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" };
  const variants = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-500",
    secondary: "bg-gray-700 text-gray-200 hover:bg-gray-600",
    ghost: "bg-transparent text-gray-400 hover:bg-gray-800 hover:text-gray-200",
    danger: "bg-red-600 text-white hover:bg-red-500",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} disabled={loading || props.disabled} {...props}>
      {loading && <span className="mr-2 animate-spin">&#9696;</span>}
      {children}
    </button>
  );
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-gray-300">{label}</label>}
      <input className={`bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${error ? "border-red-500" : ""} ${className}`} {...props} />
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  minRows?: number;
}

export function Textarea({ label, error, className = "", minRows = 3, ...props }: TextareaProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  };

  React.useEffect(() => {
    adjustHeight();
  }, [props.value]);

  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-gray-300">{label}</label>}
      <textarea
        ref={textareaRef}
        rows={minRows}
        className={`bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none overflow-y-auto ${error ? "border-red-500" : ""} ${className}`}
        onInput={adjustHeight}
        {...props}
      />
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  action?: React.ReactNode;
}

export function Card({ children, className = "", title, action }: CardProps) {
  return (
    <div className={`bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          {title && <h3 className="text-lg font-semibold text-gray-200">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "error" | "info";
  children: React.ReactNode;
}

export function Badge({ variant = "default", children }: BadgeProps) {
  const variants = {
    default: "bg-gray-700 text-gray-300",
    success: "bg-green-900/50 text-green-400",
    warning: "bg-yellow-900/50 text-yellow-400",
    error: "bg-red-900/50 text-red-400",
    info: "bg-blue-900/50 text-blue-400",
  };
  return <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${variants[variant]}`}>{children}</span>;
}

export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizes = { sm: "w-4 h-4", md: "w-6 h-6", lg: "w-8 h-8" };
  return <div className={`${sizes[size]} border-2 border-gray-600 border-t-indigo-500 rounded-full animate-spin`} />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-700/50 rounded ${className}`} />;
}

export function EmptyState({ icon, title, description }: { icon?: string; title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon && <span className="text-4xl mb-3">{icon}</span>}
      <h3 className="text-lg font-medium text-gray-300">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
    </div>
  );
}

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Modal({ open, onClose, title, children }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-lg mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-200">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200 text-xl">&times;</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    healthy: { color: "bg-green-500", label: "Healthy" },
    active: { color: "bg-green-500", label: "Active" },
    ok: { color: "bg-green-500", label: "OK" },
    degraded: { color: "bg-yellow-500", label: "Degraded" },
    warning: { color: "bg-yellow-500", label: "Warning" },
    down: { color: "bg-red-500", label: "Down" },
    error: { color: "bg-red-500", label: "Error" },
    failed: { color: "bg-red-500", label: "Failed" },
    pending: { color: "bg-blue-500", label: "Pending" },
    running: { color: "bg-blue-500", label: "Running" },
    completed: { color: "bg-green-500", label: "Completed" },
  };
  const info = map[status.toLowerCase()] || { color: "bg-gray-500", label: status };
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span className={`w-2 h-2 rounded-full ${info.color}`} />
      {info.label}
    </span>
  );
}
