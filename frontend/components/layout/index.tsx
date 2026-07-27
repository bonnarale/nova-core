"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppStore } from "@/stores";

const NAV_ITEMS = [
  { label: "NOVA", href: "/nova", icon: "\u25C9" },
  { label: "Projects", href: "/projects", icon: "\u25A3" },
  { label: "Roadmaps", href: "/roadmaps", icon: "\u25B7" },
  { label: "Backlog", href: "/backlog", icon: "\u2630" },
  { label: "Approvals", href: "/approvals", icon: "\u2714" },
  { label: "Chat", href: "/chat", icon: "\u2709" },
  { label: "Goals", href: "/goals", icon: "\u2B50" },
  { label: "Tasks", href: "/tasks", icon: "\u2611" },
  { label: "Memory", href: "/memory", icon: "\u2605" },
  { label: "Observability", href: "/observability", icon: "\u2609" },
  { label: "Tools", href: "/tools", icon: "\u2692" },
  { label: "Workflows", href: "/workflows", icon: "\u2699" },
  { label: "Dashboard", href: "/dashboard", icon: "\u25A0" },
  { label: "Settings", href: "/settings", icon: "\u2699" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);

  if (!sidebarOpen) return null;

  return (
    <aside className={`${collapsed ? "w-16" : "w-60"} h-screen bg-gray-900 border-r border-gray-800 flex flex-col transition-all duration-200 sticky top-0`}>
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        {!collapsed && <span className="text-lg font-bold text-indigo-400">NOVA CORE</span>}
        <button onClick={() => setCollapsed(!collapsed)} className="text-gray-500 hover:text-gray-300 p-1">
          {collapsed ? "\u25B6" : "\u25C0"}
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link key={item.href} href={item.href} className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${active ? "bg-indigo-600/20 text-indigo-400 border-r-2 border-indigo-500" : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"}`}>
              <span className="text-base">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function Header() {
  const { theme, setTheme, notifications } = useAppStore();
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <header className="h-14 bg-gray-900/80 backdrop-blur border-b border-gray-800 flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-400">NOVA CORE</span>
      </div>
      <div className="flex items-center gap-4">
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="text-gray-400 hover:text-gray-200 p-2 text-sm">
          {theme === "dark" ? "\u2600" : "\u263E"}
        </button>
        <div className="relative">
          <span className="text-gray-400 hover:text-gray-200 cursor-pointer p-2 text-sm">
            {"\u2666"}
            {unread > 0 && <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">{unread}</span>}
          </span>
        </div>
        <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-medium">U</div>
      </div>
    </header>
  );
}
