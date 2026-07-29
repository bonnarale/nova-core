export type MiddlewareFn = (context: MiddlewareContext) => MiddlewareContext | Promise<MiddlewareContext>;
export type ErrorMiddlewareFn = (error: Error) => Error;

export interface MiddlewareContext {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: unknown;
  startTime?: number;
}

export class Middleware {
  private requestHooks: MiddlewareFn[] = [];
  private responseHooks: MiddlewareFn[] = [];
  private errorHooks: ErrorMiddlewareFn[] = [];

  addRequestHook(hook: MiddlewareFn): void {
    this.requestHooks.push(hook);
  }

  addResponseHook(hook: MiddlewareFn): void {
    this.responseHooks.push(hook);
  }

  addErrorHook(hook: ErrorMiddlewareFn): void {
    this.errorHooks.push(hook);
  }

  async processRequest(context: MiddlewareContext): Promise<MiddlewareContext> {
    let result = context;
    for (const hook of this.requestHooks) {
      result = await hook(result);
    }
    return result;
  }

  async processResponse(context: MiddlewareContext): Promise<MiddlewareContext> {
    let result = context;
    for (const hook of this.responseHooks) {
      result = await hook(result);
    }
    return result;
  }

  processError(error: Error): Error {
    let result: Error = error;
    for (const hook of this.errorHooks) {
      result = hook(result);
    }
    return result;
  }
}

export class LoggingMiddleware extends Middleware {
  constructor(private logger: Console = console) {
    super();
  }

  override async processRequest(context: MiddlewareContext): Promise<MiddlewareContext> {
    this.logger.debug(`SDK Request: ${context.method} ${context.url}`);
    return super.processRequest(context);
  }

  override async processResponse(context: MiddlewareContext): Promise<MiddlewareContext> {
    this.logger.debug(`SDK Response processed`);
    return super.processResponse(context);
  }
}

export class TelemetryMiddleware extends Middleware {
  metrics = { requests: 0, errors: 0, totalLatencyMs: 0 };

  override async processRequest(context: MiddlewareContext): Promise<MiddlewareContext> {
    context.startTime = Date.now();
    this.metrics.requests++;
    return super.processRequest(context);
  }

  override async processResponse(context: MiddlewareContext): Promise<MiddlewareContext> {
    if (context.startTime) {
      this.metrics.totalLatencyMs += Date.now() - context.startTime;
    }
    return super.processResponse(context);
  }

  override processError(error: Error): Error {
    this.metrics.errors++;
    return super.processError(error);
  }
}
