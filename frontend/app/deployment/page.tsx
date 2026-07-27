"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface DeploymentHealth {
  status: string;
  environment: string;
  version: string;
  uptime: number;
  last_check: string;
}

export default function DeploymentPage() {
  const { data: health, loading } = useApi<DeploymentHealth>("/api/v1/deployment/health");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Deployment" description="Manage deployments and rollbacks" action={<Button>Deploy</Button>} />
      <div className="space-y-3">
        {health && (
          <Card>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <StatusBadge status={health.status} />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-200">v{health.version}</span>
                    <Badge variant="info">{health.environment}</Badge>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Uptime: {Math.floor(health.uptime / 3600)}h &middot; Last check: {new Date(health.last_check).toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost">View</Button>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
