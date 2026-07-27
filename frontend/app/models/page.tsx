"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface Model {
  id: string;
  name: string;
  provider: string;
  status: string;
  type: string;
  max_tokens?: number;
  cost_per_1k_tokens?: number;
}

export default function ModelsPage() {
  const { data: models, loading } = useApi<Model[]>("/api/v1/models/list");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const grouped = (models || []).reduce<Record<string, Model[]>>((acc, m) => {
    (acc[m.provider] = acc[m.provider] || []).push(m);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader title="Models" description="Manage AI model providers and configurations" />
      {Object.entries(grouped).map(([provider, providerModels]) => (
        <div key={provider} className="mb-6">
          <h2 className="text-lg font-semibold text-gray-300 mb-3 capitalize">{provider}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {providerModels.map((model) => (
              <Card key={model.id}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-200">{model.name}</h3>
                  <StatusBadge status={model.status} />
                </div>
                <div className="flex gap-2 mb-2">
                  <Badge variant="info">{model.type}</Badge>
                  {model.max_tokens && <Badge>{(model.max_tokens / 1000).toFixed(0)}K tokens</Badge>}
                </div>
                {model.cost_per_1k_tokens !== undefined && (
                  <div className="text-xs text-gray-500">${model.cost_per_1k_tokens}/1K tokens</div>
                )}
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
