import type { Configuration } from "./config.js";
import {
  NovaAPIError,
  NovaAuthError,
  NovaRateLimitError,
  NovaServerError,
  NovaTimeoutError,
} from "./errors.js";

type RequestFn = () => Promise<unknown>;

export class RetryHandler {
  private maxRetries: number;
  private baseDelay: number;
  private maxDelay: number;
  private backoff: number;
  private retryableStatuses: Set<number>;

  constructor(config: Configuration) {
    this.maxRetries = config.maxRetries;
    this.baseDelay = config.retryBaseDelay;
    this.maxDelay = config.retryMaxDelay;
    this.backoff = config.retryBackoff;
    this.retryableStatuses = new Set([429, 500, 502, 503, 504]);
  }

  private calculateDelay(attempt: number, retryAfter?: number): number {
    if (retryAfter !== undefined) return retryAfter * 1000;
    const delay = this.baseDelay * Math.pow(this.backoff, attempt);
    return Math.min(delay, this.maxDelay);
  }

  private shouldRetry(attempt: number, statusCode?: number): boolean {
    if (attempt >= this.maxRetries) return false;
    if (statusCode === undefined) return true;
    return this.retryableStatuses.has(statusCode);
  }

  async execute<T>(fn: RequestFn): Promise<T> {
    let lastError: Error | undefined;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return (await fn()) as T;
      } catch (error) {
        lastError = error as Error;
        let statusCode: number | undefined;
        let retryAfter: number | undefined;

        if (error instanceof NovaRateLimitError) {
          statusCode = error.statusCode;
          retryAfter = error.retryAfter;
        } else if (error instanceof NovaAPIError || error instanceof NovaServerError) {
          statusCode = error.statusCode;
        } else if (error instanceof NovaTimeoutError) {
          // connection/timeout errors are retryable
        }

        if (!this.shouldRetry(attempt, statusCode)) {
          throw error;
        }

        const delay = this.calculateDelay(attempt, retryAfter);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
    throw lastError;
  }
}
