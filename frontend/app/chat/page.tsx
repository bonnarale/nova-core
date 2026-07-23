"use client";
import React, { useState, useRef, useEffect } from "react";
import { Card, Button, Textarea } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { useAppStore } from "@/stores";

interface Message {
  role: string;
  content: string;
  timestamp: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { sessionId, setSessionId, userId, setUserId } = useAppStore();

  useEffect(() => {
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
          const historyMessages: Message[] = data.messages.map((msg: any) => ({
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

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input, timestamp: new Date().toISOString() };
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
      setMessages((prev) => [...prev, { role: "assistant", content: data.response, timestamp: new Date().toISOString() }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`, timestamp: new Date().toISOString() }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <PageHeader title="Chat" description="Communicate with NOVA agents" />
      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && <div className="text-center text-gray-500 py-12">Start a conversation with an agent</div>}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[70%] rounded-xl px-4 py-2.5 text-sm ${msg.role === "user" ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-300"}`}>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                <div className="text-xs opacity-50 mt-1">{new Date(msg.timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-400">Thinking...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t border-gray-700 p-4 -mx-6 -mb-6">
          <div className="flex gap-3">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Type a message... (Shift+Enter for new line)"
              className="flex-1"
              minRows={3}
              disabled={loading}
            />
            <Button onClick={sendMessage} disabled={loading || !input.trim()} className="self-end">Send</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
