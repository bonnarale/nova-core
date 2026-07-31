"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface DeploymentResponse {
  success: boolean;
  data: {
    variables: Record<string, string>;
    count: number;
  };
}

export default function AdminPage() {
  const { data: raw, loading } = useApi<DeploymentResponse>("/api/v1/deployment/environment");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const envVars = raw?.data?.variables || {};

  return (
    <div>
      <PageHeader title="Admin" description="System administration" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card title="Environment Info">
          <div className="space-y-2 text-sm">
            {Object.keys(envVars).length === 0 && (
              <p className="text-gray-500">No environment variables loaded.</p>
            )}
            {Object.entries(envVars).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-gray-400 capitalize">{k.replace(/_/g, " ")}</span>
                <span className="text-gray-200">{String(v)}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Quick Actions">
          <div className="space-y-2">
            {["Restart System", "Clear Cache", "Run Diagnostics", "Export Config"].map((action) => (
              <Button key={action} variant="secondary" className="w-full justify-start">{action}</Button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
