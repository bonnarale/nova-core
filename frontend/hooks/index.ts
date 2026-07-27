"use client";

import { useEffect, useState, useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useApi<T>(fetcherOrUrl: (() => Promise<T>) | string, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetcher = typeof fetcherOrUrl === "function"
    ? fetcherOrUrl
    : () => fetch(`${API_BASE}${fetcherOrUrl}`).then(async (r) => {
        if (!r.ok) {
          let msg = `HTTP ${r.status}`;
          try { const j = await r.json(); msg = j.detail || j.message || msg; } catch {}
          throw new Error(msg);
        }
        return r.json();
      });

  useEffect(() => {
    if (typeof fetcherOrUrl === "string" && !fetcherOrUrl) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetcher()
      .then((d) => { if (!cancelled) { setData(d); setError(null); } })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, deps);

  return { data, error, loading, refetch: () => { setLoading(true); fetcher().then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false)); } };
}

export function useWebSocket(url: string, onMessage: (data: unknown) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch {} };
    ws.onerror = () => setConnected(false);
    return () => ws.close();
  }, [url]);

  return { connected, send: (data: unknown) => wsRef.current?.send(JSON.stringify(data)) };
}

export function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try { const s = localStorage.getItem(key); return s ? JSON.parse(s) : initial; } catch { return initial; }
  });
  const set = useCallback((v: T) => { setValue(v); localStorage.setItem(key, JSON.stringify(v)); }, [key]);
  return [value, set];
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const t = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(t); }, [value, delay]);
  return debounced;
}

export function usePolling(fn: () => void, intervalMs: number) {
  const savedFn = useRef(fn);
  useEffect(() => { savedFn.current = fn; }, [fn]);
  useEffect(() => {
    const id = setInterval(() => savedFn.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}

export function useEventSource(url: string, onMessage: (data: unknown) => void) {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const es = new EventSource(url);
    es.onopen = () => setConnected(true);
    es.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch {} };
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, [url]);
  return { connected };
}
