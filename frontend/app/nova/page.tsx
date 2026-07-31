"use client";

import React, { useState } from "react";
import { NovaChat } from "./chat";
import { NovaDashboard } from "./dashboard";

export default function NovaPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [showDashboard, setShowDashboard] = useState(true);

  return (
    <div className="flex h-[calc(100vh-8rem)]">
      <div className={`${showDashboard ? "w-[60%]" : "w-full"} transition-all duration-300 bg-gray-800/30 border border-gray-700/50 rounded-xl overflow-hidden flex flex-col`}>
        <NovaChat
          onChatResponse={() => setRefreshKey((k) => k + 1)}
          showDashboard={showDashboard}
          onToggleDashboard={() => setShowDashboard(!showDashboard)}
        />
      </div>
      {showDashboard && (
        <div className="w-[40%] ml-4 bg-gray-800/30 border border-gray-700/50 rounded-xl overflow-hidden">
          <NovaDashboard refreshKey={refreshKey} />
        </div>
      )}
    </div>
  );
}
