export class NovaError extends Error {
  statusCode?: number;
  response?: unknown;

  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message);
    this.name = "NovaError";
    this.statusCode = statusCode;
    this.response = response;
  }
}

export class NovaAPIError extends NovaError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "NovaAPIError";
  }
}

export class NovaAuthError extends NovaAPIError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode ?? 401, response);
    this.name = "NovaAuthError";
  }
}

export class NovaRateLimitError extends NovaAPIError {
  retryAfter?: number;

  constructor(message: string, retryAfter?: number, statusCode?: number, response?: unknown) {
    super(message, statusCode ?? 429, response);
    this.name = "NovaRateLimitError";
    this.retryAfter = retryAfter;
  }
}

export class NovaServerError extends NovaAPIError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode ?? 500, response);
    this.name = "NovaServerError";
  }
}

export class NovaConnectionError extends NovaError {
  constructor(message: string) {
    super(message);
    this.name = "NovaConnectionError";
  }
}

export class NovaTimeoutError extends NovaError {
  constructor(message: string) {
    super(message);
    this.name = "NovaTimeoutError";
  }
}

export class NovaValidationError extends NovaAPIError {
  errors: Array<Record<string, unknown>>;

  constructor(message: string, errors: Array<Record<string, unknown>> = [], statusCode?: number, response?: unknown) {
    super(message, statusCode ?? 422, response);
    this.name = "NovaValidationError";
    this.errors = errors;
  }
}
