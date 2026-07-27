"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface Plugin {
  id: string;
  name: string;
  description: string;
  version: string;
  status: string;
  author: string;
  enabled: boolean;
}

export default function PluginsPage() {
  const { data: plugins, loading } = useApi<Plugin[]>("/api/v1/plugins");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Plugins" description="Extend NOVA CORE with plugins" action={<Button>Install Plugin</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(plugins || []).map((plugin) => (
          <Card key={plugin.id}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-200">{plugin.name}</h3>
                  <Badge>v{plugin.version}</Badge>
                </div>
                <p className="text-sm text-gray-400 mb-2">{plugin.description}</p>
                <span className="text-xs text-gray-500">by {plugin.author}</span>
              </div>
              <div className="flex flex-col items-end gap-2">
                <StatusBadge status={plugin.enabled ? "active" : "degraded"} />
                <Button size="sm" variant={plugin.enabled ? "danger" : "primary"}>{plugin.enabled ? "Disable" : "Enable"}</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
