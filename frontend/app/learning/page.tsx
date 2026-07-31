"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Badge, Spinner } from "@/components/ui";
import { PageHeader, StatBar } from "@/components/dashboard";

interface LearningData {
  episodes_learned: number;
  patterns_discovered: number;
  improvements_applied: number;
  recent_insights: Array<{ insight: string; confidence: number; source: string }>;
}

export default function LearningPage() {
  const { data, loading } = useApi<LearningData>("/api/v1/learning/stats");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Learning" description="Agent learning and improvement tracking" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card title="Episodes Learned"><div className="text-3xl font-bold text-gray-200">{data?.episodes_learned || 0}</div></Card>
        <Card title="Patterns Found"><div className="text-3xl font-bold text-gray-200">{data?.patterns_discovered || 0}</div></Card>
        <Card title="Improvements"><div className="text-3xl font-bold text-gray-200">{data?.improvements_applied || 0}</div></Card>
      </div>
      <Card title="Recent Insights">
        <div className="space-y-3">
          {(data?.recent_insights || []).map((insight, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-900/50 rounded-lg">
              <div>
                <div className="text-sm text-gray-300">{insight.insight}</div>
                <div className="text-xs text-gray-500">Source: {insight.source}</div>
              </div>
              <Badge variant="info">{(insight.confidence * 100).toFixed(0)}%</Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
