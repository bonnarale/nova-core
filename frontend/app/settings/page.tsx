"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Input, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { useAppStore } from "@/stores";

export default function SettingsPage() {
  const { theme, setTheme } = useAppStore();

  return (
    <div>
      <PageHeader title="Settings" description="System configuration" />
      <div className="max-w-2xl space-y-6">
        <Card title="Appearance">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Theme</span>
            <div className="flex gap-2">
              <Button size="sm" variant={theme === "dark" ? "primary" : "ghost"} onClick={() => setTheme("dark")}>Dark</Button>
              <Button size="sm" variant={theme === "light" ? "primary" : "ghost"} onClick={() => setTheme("light")}>Light</Button>
            </div>
          </div>
        </Card>
        <Card title="API Configuration">
          <div className="space-y-3">
            <Input label="API Base URL" defaultValue="http://localhost:8000" />
            <Input label="Request Timeout (ms)" defaultValue="30000" type="number" />
            <Button>Save</Button>
          </div>
        </Card>
        <Card title="Notifications">
          <div className="space-y-3">
            {["Task completions", "Error alerts", "System health"].map((item) => (
              <div key={item} className="flex items-center justify-between">
                <span className="text-sm text-gray-300">{item}</span>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-indigo-600" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
