"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface EnterpriseFeature {
  name: string;
  enabled: boolean;
  status: string;
  description: string;
}

export default function EnterprisePage() {
  const { data, loading } = useApi<{ features: EnterpriseFeature[] }>("/api/v1/enterprise/status");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const features = data?.features || [];

  return (
    <div>
      <PageHeader title="Enterprise" description="Enterprise features and licensing" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {features.map((f) => (
          <Card key={f.name}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-200 capitalize">{f.name.replace(/_/g, " ")}</h3>
                  <StatusBadge status={f.enabled ? "active" : "degraded"} />
                </div>
                <p className="text-sm text-gray-400">{f.description}</p>
              </div>
              <Button size="sm" variant={f.enabled ? "danger" : "primary"}>{f.enabled ? "Disable" : "Enable"}</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
