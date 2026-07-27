"use client";

import React from "react";
import { Badge, StatusBadge } from "@/components/ui";

interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  agentName?: string;
  metadata?: Record<string, string>;
}

export function MessageBubble({ role, content, timestamp, agentName, metadata }: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[75%] ${isUser ? "order-2" : ""}`}>
        {!isUser && agentName && <div className="text-xs text-gray-500 mb-1">{agentName}</div>}
        <div className={`rounded-xl px-4 py-2.5 text-sm ${isUser ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-300"}`}>
          <div className="whitespace-pre-wrap">{content}</div>
        </div>
        <div className="text-xs text-gray-600 mt-1 px-1">{new Date(timestamp).toLocaleTimeString()}</div>
        {metadata && Object.keys(metadata).length > 0 && (
          <div className="flex gap-1.5 mt-1">
            {Object.entries(metadata).map(([k, v]) => <Badge key={k}>{k}: {v}</Badge>)}
          </div>
        )}
      </div>
    </div>
  );
}

interface TypingIndicatorProps {
  agentName: string;
}

export function TypingIndicator({ agentName }: TypingIndicatorProps) {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-400">
        <span className="animate-pulse">{agentName} is thinking...</span>
      </div>
    </div>
  );
}
