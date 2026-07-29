# Security

## Overview

NOVA CORE provides authentication, authorization (RBAC), API key management, audit logging, encryption, rate limiting, and IP filtering.

## Components

| Component | Package | Description |
|-----------|---------|-------------|
| Auth Provider | `app.security.base` | User authentication ABC |
| Token Provider | `app.security.base` | JWT/token management ABC |
| Crypto Provider | `app.security.base` | Encryption/hashing ABC |
| Permission Provider | `app.security.base` | RBAC permission checks |
| Audit Provider | `app.security.base` | Audit logging |
| Session Provider | `app.security.base` | Session management |

## Authentication

### Token Types
- **Access Token** — Short-lived JWT for API access
- **Refresh Token** — Long-lived token for renewal

### Login Flow
1. User submits credentials to `POST /security/auth/login`
2. Credentials validated against user store
3. Access + refresh tokens generated
4. Tokens returned in response

## Authorization (RBAC)

### Permission Levels
- `read` — Read-only access
- `write` — Read/write access
- `admin` — Full access

### Roles
- `user` — Default role (read + write)
- `editor` — Enhanced write access
- `admin` — Full access

## API Keys

```bash
# Create API key
curl -X POST /security/api-keys \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "my-key"}'
```

## Security Headers

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Strict-Transport-Security` | `max-age=31536000` |
| `Content-Security-Policy` | `default-src 'self'` |

## Encryption

- Password hashing: Scrypt
- HMAC signing for API keys
- Token signing: HMAC-SHA256

## Audit Logging

All authentication events, permission changes, and API key operations are logged with timestamps, user IDs, and action details.
