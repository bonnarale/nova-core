"use client";

import React from "react";

interface ChartProps {
  data: Array<{ label: string; value: number; color?: string }>;
  title?: string;
}

export function BarChart({ data, title }: ChartProps) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div>
      {title && <h3 className="text-sm font-medium text-gray-400 mb-3">{title}</h3>}
      <div className="flex items-end gap-2 h-40">
        {data.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full rounded-t ${d.color || "bg-indigo-500"}`}
              style={{ height: `${(d.value / max) * 100}%`, minHeight: 4 }}
            />
            <span className="text-xs text-gray-500 truncate w-full text-center">{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface LineChartProps {
  data: number[];
  color?: string;
  title?: string;
}

export function LineChart({ data, color = "bg-indigo-500", title }: LineChartProps) {
  const max = Math.max(...data, 1);
  const points = data.map((v, i) => `${(i / (data.length - 1 || 1)) * 100},${100 - (v / max) * 100}`).join(" ");
  return (
    <div>
      {title && <h3 className="text-sm font-medium text-gray-400 mb-3">{title}</h3>}
      <svg viewBox="0 0 100 100" className="w-full h-32" preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="0.5" className="text-indigo-500" />
      </svg>
    </div>
  );
}

interface PieChartProps {
  data: Array<{ label: string; value: number; color: string }>;
  title?: string;
}

export function PieChart({ data, title }: PieChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  let cumulative = 0;
  const segments = data.map((d) => {
    const start = cumulative;
    cumulative += d.value / total;
    return { ...d, start, end: cumulative };
  });
  return (
    <div className="flex items-center gap-4">
      {title && <h3 className="text-sm font-medium text-gray-400">{title}</h3>}
      <svg viewBox="0 0 100 100" className="w-24 h-24">
        {segments.map((s, i) => (
          <circle key={i} cx="50" cy="50" r="40" fill="none" stroke={s.color} strokeWidth="20"
            strokeDasharray={`${(s.end - s.start) * 251.3} 251.3`}
            strokeDashoffset={`${-s.start * 251.3}`}
          />
        ))}
      </svg>
      <div className="space-y-1">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
            <span className="text-gray-400">{d.label}</span>
            <span className="text-gray-300">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
