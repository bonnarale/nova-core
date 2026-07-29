import { Configuration, getAuthHeaders } from "./config.js";

export interface AuthProvider {
  getHeaders(): Record<string, string>;
}

export class APIKeyAuth implements AuthProvider {
  constructor(private apiKey: string) {}

  getHeaders(): Record<string, string> {
    return { "X-API-Key": this.apiKey };
  }
}

export class BearerTokenAuth implements AuthProvider {
  constructor(private token: string) {}

  getHeaders(): Record<string, string> {
    return { Authorization: `Bearer ${this.token}` };
  }
}

export function createAuth(config: Configuration): AuthProvider {
  if (config.bearerToken) {
    return new BearerTokenAuth(config.bearerToken);
  }
  if (config.apiKey) {
    return new APIKeyAuth(config.apiKey);
  }
  return {
    getHeaders: () => ({}),
  };
}
