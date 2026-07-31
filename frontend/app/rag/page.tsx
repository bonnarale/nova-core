"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface RAGStatistics {
  total_documents: number;
  total_chunks: number;
  index_size: number;
}

export default function RAGPage() {
  const { data: stats, loading } = useApi<RAGStatistics>("/api/v1/rag/statistics");
  const [query, setQuery] = useState("");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="RAG" description="Retrieval-Augmented Generation management" action={<Button>Create Collection</Button>} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <Card>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-gray-400">Total Documents</div>
                <div className="text-2xl font-bold text-gray-200">{stats?.total_documents ?? 0}</div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Total Chunks</div>
                <div className="text-2xl font-bold text-gray-200">{stats?.total_chunks ?? 0}</div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Index Size</div>
                <div className="text-2xl font-bold text-gray-200">{stats?.index_size ?? 0}</div>
              </div>
            </div>
          </Card>
        </div>
        <div>
          <Card title="Test Query">
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Enter a search query..." className="mb-3" />
            <Button className="w-full">Run Query</Button>
          </Card>
        </div>
      </div>
    </div>
  );
}
