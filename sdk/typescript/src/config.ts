export interface Configuration {
  baseUrl: string;
  apiKey?: string;
  bearerToken?: string;
  timeout: number;
  maxRetries: number;
  retryBaseDelay: number;
  retryMaxDelay: number;
  retryBackoff: number;
  verifySsl: boolean;
  headers: Record<string, string>;
  userAgent: string;
  telemetryEnabled: boolean;
}

export function createConfiguration(overrides: Partial<Configuration> = {}): Configuration {
  return {
    baseUrl: "http://localhost:8000",
    timeout: 30000,
    maxRetries: 3,
    retryBaseDelay: 500,
    retryMaxDelay: 30000,
    retryBackoff: 2,
    verifySsl: true,
    headers: {},
    userAgent: "nova-core-sdk-typescript/0.1.0",
    telemetryEnabled: false,
    ...overrides,
  };
}

export function getAuthHeaders(config: Configuration): Record<string, string> {
  if (config.bearerToken) {
    return { Authorization: `Bearer ${config.bearerToken}` };
  }
  if (config.apiKey) {
    return { "X-API-Key": config.apiKey };
  }
  return {};
}

export function getDefaultHeaders(config: Configuration): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "User-Agent": config.userAgent,
    ...getAuthHeaders(config),
    ...config.headers,
  };
}
