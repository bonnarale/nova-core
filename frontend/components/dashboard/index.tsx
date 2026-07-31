"use client";

import React from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: string;
}

export function MetricCard({ title, value, change, icon }: MetricCardProps) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{title}</span>
        {icon && <span className="text-gray-500">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-gray-200">{value}</div>
      {change !== undefined && (
        <div className={`text-xs mt-1 ${change >= 0 ? "text-green-400" : "text-red-400"}`}>
          {change >= 0 ? "+" : ""}{change}% from last period
        </div>
      )}
    </div>
  );
}

interface DataTableProps<T> {
  columns: Array<{ key: string; label: string; render?: (val: unknown, row: T) => React.ReactNode }>;
  data: T[];
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends Record<string, unknown>>({ columns, data, onRowClick }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            {columns.map((col) => (
              <th key={col.key} className="text-left py-3 px-4 text-gray-400 font-medium">{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} onClick={() => onRowClick?.(row)} className={`border-b border-gray-800/50 ${onRowClick ? "cursor-pointer hover:bg-gray-800/50" : ""}`}>
              {columns.map((col) => (
                <td key={col.key} className="py-3 px-4 text-gray-300">
                  {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && <div className="text-center py-8 text-gray-500">No data available</div>}
    </div>
  );
}

interface StatBarProps {
  label: string;
  value: number;
  max?: number;
  color?: string;
}

export function StatBar({ label, value, max = 100, color = "bg-indigo-500" }: StatBarProps) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-400 w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-700 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm text-gray-300 w-12 text-right">{value}</span>
    </div>
  );
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-200">{title}</h1>
        {description && <p className="text-sm text-gray-400 mt-1">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function HealthGrid({ items }: { items: Array<{ name: string; status: string; detail?: string }> }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {items.map((item) => (
        <div key={item.name} className="flex items-center gap-3 bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <span className={`w-3 h-3 rounded-full ${item.status === "healthy" ? "bg-green-500" : item.status === "degraded" ? "bg-yellow-500" : "bg-red-500"}`} />
          <div>
            <div className="text-sm font-medium text-gray-300">{item.name}</div>
            {item.detail && <div className="text-xs text-gray-500">{item.detail}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export { ActivityCard } from "./ActivityCard";
