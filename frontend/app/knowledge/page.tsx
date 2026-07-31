"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner } from "@/components/ui";
import { PageHeader, DataTable } from "@/components/dashboard";

interface KnowledgeEntity {
  id: string;
  name: string;
  type: string;
  description: string;
  created_at: string;
}

export default function KnowledgePage() {
  const { data: entries, loading } = useApi<KnowledgeEntity[]>("/api/v1/knowledge-graph/entities");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const categories = ["all"];
  const filtered = (entries || []).filter((e) => {
    const matchSearch = !searchQuery || e.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCat = selectedCategory === "all" || e.type === selectedCategory;
    return matchSearch && matchCat;
  });

  const columns = [
    { key: "name", label: "Name", render: (v: unknown) => <span className="text-gray-300 max-w-md truncate block">{String(v)}</span> },
    { key: "type", label: "Type", render: (v: unknown) => <Badge variant="info">{String(v)}</Badge> },
    { key: "description", label: "Description", render: (v: unknown) => <span className="text-gray-400 max-w-md truncate block">{String(v)}</span> },
    { key: "created_at", label: "Created", render: (v: unknown) => <span className="text-gray-500">{new Date(v as string).toLocaleDateString()}</span> },
  ];

  return (
    <div>
      <PageHeader title="Knowledge Graph" description="Explore knowledge graph entities" action={<Button>Add Entity</Button>} />
      <div className="flex gap-3 mb-4">
        <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search memory..." className="max-w-sm" />
        <div className="flex gap-1">
          {categories.map((c) => (
            <Button key={c} size="sm" variant={selectedCategory === c ? "primary" : "ghost"} onClick={() => setSelectedCategory(c)}>{c.charAt(0).toUpperCase() + c.slice(1)}</Button>
          ))}
        </div>
      </div>
      <Card>
        <DataTable columns={columns} data={filtered as unknown as Record<string, unknown>[]} />
      </Card>
    </div>
  );
}
