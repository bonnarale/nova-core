/**
 * Global toast emitter — usable from outside React (API client, services, etc.)
 * The ToastProvider subscribes to these events and renders them.
 */

type ToastType = "info" | "success" | "error" | "warning";

interface GlobalToastEvent {
  message: string;
  type: ToastType;
  duration?: number;
}

type Listener = (event: GlobalToastEvent) => void;

let listeners: Listener[] = [];

export const globalToast = {
  /** Subscribe to toast events (called by ToastProvider) */
  subscribe(fn: Listener) {
    listeners.push(fn);
    return () => {
      listeners = listeners.filter((l) => l !== fn);
    };
  },

  /** Emit a toast */
  emit(message: string, type: ToastType = "info", duration = 4000) {
    listeners.forEach((l) => l({ message, type, duration }));
  },

  /** Convenience methods */
  info: (msg: string, duration?: number) => globalToast.emit(msg, "info", duration),
  success: (msg: string, duration?: number) => globalToast.emit(msg, "success", duration),
  error: (msg: string, duration?: number) => globalToast.emit(msg, "error", duration),
  warning: (msg: string, duration?: number) => globalToast.emit(msg, "warning", duration),
};
