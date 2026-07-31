"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface VectorStatistics {
  total_vectors: number;
  collections: Array<{ name: string; count: number }>;
  index_size: number;
}

export default function VectorMemoryPage() {
  const [query, setQuery] = useState("");
  const { data: stats, loading } = useApi<VectorStatistics>("/api/v1/vector-memory/statistics");
  const [selectedCollection, setSelectedCollection] = useState("all");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const collections = ["all", ...(stats?.collections || []).map((c) => c.name)];

  return (
    <div>
      <PageHeader title="Vector Memory" description="Explore vector embeddings and similarity search" />
      <div className="flex gap-3 mb-4">
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search vectors..." className="max-w-md" />
        <Button>Search</Button>
        <div className="flex gap-1 ml-4">
          {collections.map((c) => (
            <Button key={c} size="sm" variant={selectedCollection === c ? "primary" : "ghost"} onClick={() => setSelectedCollection(c)}>
              {c === "all" ? "All" : c}
            </Button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(stats?.collections || []).map((col) => (
          <Card key={col.name} className="p-4">
            <div className="flex items-start justify-between mb-2">
              <Badge variant="info">{col.name}</Badge>
              <Badge>{col.count} vectors</Badge>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
