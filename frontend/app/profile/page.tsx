"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Input, Button, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface ProfileStatus {
  status: string;
  user_id: string;
  session_active: boolean;
}

export default function ProfilePage() {
  const { data: profile, loading } = useApi<ProfileStatus>("/api/v1/profile/status");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Profile" description="Your account settings" />
      <Card className="max-w-lg">
        <div className="space-y-4">
          <Input label="Status" defaultValue={profile?.status || ""} disabled />
          <Input label="User ID" defaultValue={profile?.user_id || ""} disabled />
          <Input label="Session Active" defaultValue={profile?.session_active ? "Yes" : "No"} disabled />
          <Button>Save Changes</Button>
        </div>
      </Card>
    </div>
  );
}
