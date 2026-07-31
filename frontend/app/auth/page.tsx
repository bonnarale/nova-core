"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Input, Button } from "@/components/ui";
import { useAppStore } from "@/stores";
import { syncAuthToken } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthPage() {
  const router = useRouter();
  const { setToken, setUser } = useAppStore();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const endpoint = isLogin ? "/api/v1/auth/login" : "/api/v1/auth/register";
      const body = isLogin
        ? { email, password }
        : { name, email, password };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Authentication failed" }));
        throw new Error(data.detail || "Authentication failed");
      }

      const data = await res.json();
      setToken(data.token);
      setUser(data.user);
      syncAuthToken(data.token);
      router.push("/nova");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <Card className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-indigo-400">NOVA CORE</h1>
          <p className="text-sm text-gray-400 mt-1">{isLogin ? "Sign in to your account" : "Create an account"}</p>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              required
            />
          )}
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            minLength={6}
          />
          <Button className="w-full" type="submit" disabled={loading}>
            {loading ? "Please wait..." : isLogin ? "Sign In" : "Create Account"}
          </Button>
        </form>
        <div className="text-center mt-4">
          <button
            onClick={() => { setIsLogin(!isLogin); setError(""); }}
            className="text-sm text-indigo-400 hover:text-indigo-300"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </Card>
    </div>
  );
}
