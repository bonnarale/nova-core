export const themes = {
  dark: {
    name: "dark",
    colors: {
      bg: "#0a0a0f",
      bgSurface: "#12121a",
      bgCard: "#1a1a2e",
      bgHover: "#232340",
      border: "#2a2a4a",
      text: "#e8e8f0",
      textSecondary: "#8888a8",
      primary: "#6366f1",
      primaryHover: "#818cf8",
      success: "#22c55e",
      warning: "#f59e0b",
      error: "#ef4444",
      info: "#3b82f6",
    },
  },
  light: {
    name: "light",
    colors: {
      bg: "#f8f9fc",
      bgSurface: "#ffffff",
      bgCard: "#ffffff",
      bgHover: "#f1f3f9",
      border: "#e2e5f0",
      text: "#1a1a2e",
      textSecondary: "#6b7280",
      primary: "#6366f1",
      primaryHover: "#4f46e5",
      success: "#16a34a",
      warning: "#d97706",
      error: "#dc2626",
      info: "#2563eb",
    },
  },
} as const;

export type ThemeColors = typeof themes.dark.colors;
