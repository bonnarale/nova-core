"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Button, Textarea, Spinner } from "@/components/ui";
import { useAppStore } from "@/stores";

interface ChatResponse {
  actions_taken?: string[];
  objectives?: Array<{ id: string; title: string; category: string }>;
  projects?: Array<{ id: string; name: string }>;
  tasks?: unknown[];
  approval_required?: boolean;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  chatResponse?: ChatResponse;
}

const GREETINGS = [
  "Ready to help you build, plan, and execute.",
  "How can I help you today?",
  "What would you like to work on?",
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function NovaChat({
  onChatResponse,
  showDashboard = true,
  onToggleDashboard,
}: {
  onChatResponse?: () => void;
  showDashboard?: boolean;
  onToggleDashboard?: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [greeting, setGreeting] = useState(GREETINGS[0]);
  const { sessionId, setSessionId, userId, setUserId } = useAppStore();

  useEffect(() => {
    setGreeting(GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
    // Initialize session_id and user_id if not set
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
    if (!userId) {
      setUserId(crypto.randomUUID());
    }
  }, [sessionId, userId, setSessionId, setUserId]);

  // Load conversation history on mount
  useEffect(() => {
    if (sessionId) {
      loadConversationHistory();
    }
  }, [sessionId]);

  const loadConversationHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nova-web/chat/history/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const historyMessages: ChatMessage[] = data.messages.map((msg: any) => ({
            id: crypto.randomUUID(),
            role: msg.role,
            content: msg.content,
            timestamp: new Date().toISOString(),
          }));
          setMessages(historyMessages);
        }
      }
    } catch (err) {
      console.error("Failed to load conversation history:", err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const extractResponse = (data: any): { text: string; chatResponse?: ChatResponse } => {
    // Caso: el kernel ejecutó el agente LLM (conversación libre)
    if (data.result?.response?.message?.content) {
      return { text: data.result.response.message.content };
    }
    // Caso: el motor cognitivo resolvió una acción concreta
    if (data.cognitive_execution) {
      const exec = data.cognitive_execution;
      const chatResponse: ChatResponse = {
        actions_taken: exec.actions_taken || (data.cognitive_decision?.action ? [data.cognitive_decision.action] : []),
        objectives: exec.objectives,
        projects: exec.projects,
        tasks: exec.tasks,
        approval_required: exec.approval_required,
      };
      if (exec.error) return { text: `Error: ${exec.error}` };
      const summary = exec.created_plan
        ? "He creado un plan para tu objetivo. Podés revisarlo en el dashboard."
        : "Acción completada. Podés revisar el resultado en el dashboard.";
      return { text: summary, chatResponse };
    }
    return { text: "No se recibió una respuesta interpretable del servidor." };
  };

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/nova-web/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.content,
          session_id: sessionId,
        }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString(),
        chatResponse: {
          actions_taken: data.actions_taken,
          objectives: data.objectives,
          projects: data.projects,
          tasks: data.tasks,
          approval_required: data.approval_required,
        },
      };
      setMessages((prev) => [...prev, assistantMsg]);
      onChatResponse?.();
    } catch (err) {
      const errMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, onChatResponse]);

  const renderActions = (res: ChatResponse) => {
    if (!res.actions_taken || res.actions_taken.length === 0) return null;
    return (
      <div className="mt-3 p-2 bg-indigo-900/20 border border-indigo-800/30 rounded-lg">
        <span className="text-xs font-medium text-indigo-400">Actions Taken</span>
        {res.actions_taken.map((action, i) => (
          <div key={i} className="text-xs text-gray-300 mt-1">- {action}</div>
        ))}
        {res.objectives && res.objectives.length > 0 && (
          <div className="mt-2">
            <span className="text-xs font-medium text-green-400">Objectives Created</span>
            {res.objectives.map((o) => (
              <div key={o.id} className="text-xs text-gray-300 mt-1">- {o.title} ({o.category})</div>
            ))}
          </div>
        )}
        {res.projects && res.projects.length > 0 && (
          <div className="mt-2">
            <span className="text-xs font-medium text-blue-400">Projects Created</span>
            {res.projects.map((p) => (
              <div key={p.id} className="text-xs text-gray-300 mt-1">- {p.name}</div>
            ))}
          </div>
        )}
        {res.tasks && res.tasks.length > 0 && (
          <div className="mt-2">
            <span className="text-xs font-medium text-yellow-400">Tasks Created ({res.tasks.length})</span>
          </div>
        )}
        {res.approval_required && (
          <div className="mt-2 text-xs text-red-400 font-medium">Approval Required</div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-sm font-medium text-gray-200">NOVA Assistant</span>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setMessages([])}>Clear</Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={onToggleDashboard}
            title={showDashboard ? "Hide dashboard" : "Show dashboard"}
          >
            {showDashboard ? "◀ Hide Panel" : "▶ Show Panel"}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-indigo-600/20 rounded-2xl flex items-center justify-center mb-4">
              <span className="text-3xl">N</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-200 mb-1">NOVA</h2>
            <p className="text-sm text-gray-400 max-w-xs">{greeting}</p>
            <div className="mt-6 grid grid-cols-2 gap-2 max-w-sm">
              {[
                "I want to build a company",
                "I want to learn Artificial Intelligence",
                "Create a 20 year roadmap",
                "Show system status",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => { setInput(suggestion); }}
                  className="text-left text-xs text-gray-400 bg-gray-800/50 border border-gray-700/50 rounded-lg p-2.5 hover:bg-gray-800 hover:text-gray-300 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${msg.role === "user" ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-300 border border-gray-700/50"}`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.role === "assistant" && msg.chatResponse && renderActions(msg.chatResponse)}
              <div className="text-xs opacity-40 mt-2">{new Date(msg.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700/50 rounded-xl px-4 py-3 flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-sm text-gray-400">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-700/50 p-4">
        <div className="flex flex-col gap-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ask NOVA anything... (Shift+Enter for new line)"
            className="flex-1"
            minRows={3}
            disabled={loading}
          />
          <Button onClick={sendMessage} disabled={loading || !input.trim()} className="self-end">
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
