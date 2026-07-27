"use client";

import React, { useState } from "react";
import { Card, Input, Button } from "@/components/ui";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Auth logic via API
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <Card className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-indigo-400">NOVA CORE</h1>
          <p className="text-sm text-gray-400 mt-1">{isLogin ? "Sign in to your account" : "Create an account"}</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />}
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
          <Button className="w-full" type="submit">{isLogin ? "Sign In" : "Create Account"}</Button>
        </form>
        <div className="text-center mt-4">
          <button onClick={() => setIsLogin(!isLogin)} className="text-sm text-indigo-400 hover:text-indigo-300">
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </Card>
    </div>
  );
}
