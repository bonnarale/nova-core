import { getDefaultHeaders } from "./config.js";
import type { Configuration } from "./config.js";
import type { WebSocketMessage } from "./types.js";

type MessageHandler = (message: WebSocketMessage) => void;
type ErrorHandler = (error: Error) => void;
type CloseHandler = () => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler | ErrorHandler | CloseHandler>> = new Map();

  constructor(
    private url: string,
    private headers: Record<string, string> = {},
  ) {}

  on(event: "message", handler: MessageHandler): void;
  on(event: "error", handler: ErrorHandler): void;
  on(event: "close", handler: CloseHandler): void;
  on(event: string, handler: MessageHandler | ErrorHandler | CloseHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = this.url.replace(/^http/, "ws");
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => resolve();
      this.ws.onerror = (event) => reject(new Error(`WebSocket error: ${event}`));
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(String(event.data)) as WebSocketMessage;
          this.handlers.get("message")?.forEach((h) => (h as MessageHandler)(message));
        } catch {
          // skip invalid messages
        }
      };
      this.ws.onclose = () => {
        this.handlers.get("close")?.forEach((h) => (h as CloseHandler)());
      };
    });
  }

  send(data: WebSocketMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket not connected");
    }
    this.ws.send(JSON.stringify(data));
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
