import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Notification, ChatMessage } from "@/types";
import { syncAuthToken } from "@/lib/api";

interface AuthUser {
  user_id: string;
  username: string;
  email: string;
}

interface AppState {
  theme: "light" | "dark";
  setTheme: (t: "light" | "dark") => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  notifications: Notification[];
  addNotification: (n: Omit<Notification, "id" | "timestamp" | "read">) => void;
  markRead: (id: string) => void;
  clearNotifications: () => void;
  sessionId: string;
  userId: string;
  setSessionId: (id: string) => void;
  setUserId: (id: string) => void;
  token: string;
  user: AuthUser | null;
  setToken: (token: string) => void;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      notifications: [],
      addNotification: (n) =>
        set((s) => ({
          notifications: [
            { ...n, id: crypto.randomUUID(), timestamp: Date.now(), read: false },
            ...s.notifications,
          ].slice(0, 100),
        })),
      markRead: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
        })),
      clearNotifications: () => set({ notifications: [] }),
      sessionId: "",
      userId: "",
      setSessionId: (sessionId) => set({ sessionId }),
      setUserId: (userId) => set({ userId }),
      token: "",
      user: null,
      setToken: (token) => {
        set({ token });
        syncAuthToken(token);
      },
      setUser: (user) => set({ user, userId: user?.user_id || "" }),
      logout: () => {
        set({ token: "", user: null, userId: "" });
        syncAuthToken("");
      },
      isAuthenticated: () => !!get().token && !!get().user,
    }),
    {
      name: "nova-app-store",
      onRehydrateStorage: () => (state) => {
        // Sync token with NovaAPI after hydration from localStorage
        if (state?.token) {
          syncAuthToken(state.token);
        }
      },
    }
  )
);

interface ChatState {
  messages: ChatMessage[];
  addMessage: (m: ChatMessage) => void;
  clearMessages: () => void;
  streaming: boolean;
  setStreaming: (v: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  clearMessages: () => set({ messages: [] }),
  streaming: false,
  setStreaming: (streaming) => set({ streaming }),
}));

interface CacheState {
  cache: Map<string, { data: unknown; timestamp: number }>;
  get: (key: string, ttlMs?: number) => unknown | null;
  set: (key: string, data: unknown) => void;
  invalidate: (key: string) => void;
  clear: () => void;
}

export const useCacheStore = create<CacheState>((set, get) => ({
  cache: new Map(),
  get: (key, ttlMs = 60000) => {
    const entry = get().cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > ttlMs) { get().invalidate(key); return null; }
    return entry.data;
  },
  set: (key, data) => set((s) => { const c = new Map(s.cache); c.set(key, { data, timestamp: Date.now() }); return { cache: c }; }),
  invalidate: (key) => set((s) => { const c = new Map(s.cache); c.delete(key); return { cache: c }; }),
  clear: () => set({ cache: new Map() }),
}));
