# NOVA CORE v1.0.0 — Security Guide

**Version:** 1.0.0
**Last Updated:** July 14, 2026

---

## Table of Contents

1. [Security Architecture Overview](#1-security-architecture-overview)
2. [Authentication](#2-authentication)
3. [Authorization](#3-authorization)
4. [Password Security](#4-password-security)
5. [API Security](#5-api-security)
6. [Security Headers](#6-security-headers)
7. [Audit Logging](#7-audit-logging)
8. [Secret Management](#8-secret-management)
9. [Network Security](#9-network-security)
10. [Plugin Security](#10-plugin-security)
11. [Workflow Security](#11-workflow-security)
12. [Incident Response](#12-incident-response)

---

## 1. Security Architecture Overview

NOVA CORE implements a defense-in-depth security model with 10 validated security components:

```
┌─────────────────────────────────────────────────┐
│                  CLIENT LAYER                    │
│         (TLS 1.3, CORS, Security Headers)       │
├─────────────────────────────────────────────────┤
│                  API GATEWAY                     │
│    (Rate Limiting, Input Sanitization, Auth)     │
├─────────────────────────────────────────────────┤
│               APPLICATION LAYER                  │
│   (RBAC, Session Management, Audit Logging)      │
├─────────────────────────────────────────────────┤
│                  DATA LAYER                      │
│    (Encryption at Rest, Access Controls)          │
└─────────────────────────────────────────────────┘
```

### Security Components

| Component | Status | Description |
|-----------|--------|-------------|
| Authentication | Validated | JWT tokens, API keys |
| RBAC | Validated | Role-based access control (4 roles) |
| Cryptography | Validated | PBKDF2, HMAC, Fernet encryption |
| Rate Limiting | Validated | Per-user, per-IP rate limiting |
| Input Sanitization | Validated | XSS prevention, SQL injection prevention |
| Security Headers | Validated | CSP, HSTS, X-Frame-Options |
| CORS | Validated | Configurable allowed origins |
| Audit Logging | Validated | Security event tracking |
| Secret Management | Validated | Environment-based secrets |
| Plugin Security | Validated | Sandboxing, permission system |

---

## 2. Authentication

### JWT Tokens

NOVA CORE uses JWT (JSON Web Tokens) for stateless authentication.

**Token Structure:**
```
Header:  { "alg": "HS256", "typ": "JWT" }
Payload: { "sub": "user_id", "role": "admin", "exp": 1721000000 }
Signature: HMAC-SHA256(header + payload, JWT_SECRET)
```

**Token Configuration:**
| Setting | Value |
|---------|-------|
| Algorithm | HS256 |
| Access Token TTL | 30 minutes |
| Refresh Token TTL | 7 days |
| Secret Key | `JWT_SECRET` env variable (min 32 chars) |

**Usage:**
```bash
# Authenticate
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secure_password"}'

# Use token
curl http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer <access_token>"
```

### API Keys

API keys provide long-lived authentication for programmatic access.

**Key Properties:**
- 256-bit random keys
- SHA-256 hashed with per-key salt for storage
- Scoped permissions (read, write, admin)
- Revocable without affecting user session

**Usage:**
```bash
# Use API key
curl http://localhost:8000/api/v1/me \
  -H "X-API-Key: nova_sk_..."
```

---

## 3. Authorization

### Role-Based Access Control (RBAC)

NOVA CORE implements 4 permission levels:

| Role | Permissions | Description |
|------|-------------|-------------|
| `viewer` | read | Read-only access to resources |
| `editor` | read, write | Read and modify resources |
| `admin` | read, write, delete | Full resource management |
| `superadmin` | * | System-wide administrative access |

### Permission Matrix

| Resource | viewer | editor | admin | superadmin |
|----------|--------|--------|-------|------------|
| Read resources | ✓ | ✓ | ✓ | ✓ |
| Create resources | ✗ | ✓ | ✓ | ✓ |
| Modify resources | ✗ | ✓ | ✓ | ✓ |
| Delete resources | ✗ | ✗ | ✓ | ✓ |
| Manage users | ✗ | ✗ | ✓ | ✓ |
| Manage API keys | ✗ | ✗ | ✓ | ✓ |
| System config | ✗ | ✗ | ✗ | ✓ |
| View audit logs | ✗ | ✗ | ✓ | ✓ |

### Middleware Enforcement

```python
# RBAC middleware checks
@require_role("admin")
async def delete_resource(resource_id: str):
    ...

@require_permission("write")
async def update_resource(resource_id: str):
    ...
```

---

## 4. Password Security

### Hashing Algorithm

| Setting | Value |
|---------|-------|
| Algorithm | PBKDF2-HMAC-SHA256 |
| Iterations | 260,000 |
| Salt Length | 16 bytes (random) |
| Key Length | 32 bytes |
| Expected Time | ~364ms per hash |

### Password Policy

| Requirement | Rule |
|-------------|------|
| Minimum Length | 8 characters |
| Maximum Length | 128 characters |
| Complexity | Uppercase, lowercase, digit, special character |
| History | Last 5 passwords remembered |
| Lockout | 5 failed attempts → 15-minute lockout |

### Password Storage

```
Algorithm: PBKDF2-HMAC-SHA256
Iterations: 260000
Salt: <16 random bytes>
Hash: <derived key>

Storage format: $pbkdf2-sha256$260000$<salt>$<hash>
```

---

## 5. API Security

### Rate Limiting

| Scope | Limit | Window |
|-------|-------|--------|
| Global | 1000 requests | 1 minute |
| Per User | 100 requests | 1 minute |
| Per IP | 60 requests | 1 minute |
| Login | 5 attempts | 15 minutes |

### Input Sanitization

All API inputs are validated and sanitized:

- **XSS Prevention:** HTML entities escaped, script tags stripped
- **SQL Injection:** Parameterized queries via ORM
- **Path Traversal:** File paths validated and normalized
- **JSON Schema Validation:** Request bodies validated against schemas
- **Max Payload Size:** 10 MB default

### Request Validation

```python
# Example: Input validation
@router.post("/resources")
async def create_resource(data: CreateResourceRequest):
    # Pydantic validates all fields
    # SQL injection prevented by ORM
    # XSS prevented by output encoding
    ...
```

### Error Handling

API errors never expose internal details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [],
    "request_id": "req_abc123"
  }
}
```

---

## 6. Security Headers

NOVA CORE applies the following security headers to all responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src 'self'; ...` | Prevents XSS, data injection |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer info |
| `Permissions-Policy` | `camera=(), microphone=()` | Disables unused features |

### CORS Configuration

```python
# Allowed origins (configure via CORS_ORIGINS)
CORS_ORIGINS = [
    "https://nova.example.com",
    "https://app.example.com",
]
```

---

## 7. Audit Logging

### What Gets Logged

| Event | Level | Details |
|-------|-------|---------|
| Login Success | INFO | User ID, IP, timestamp |
| Login Failure | WARN | Username, IP, reason |
| API Key Created | INFO | User ID, key prefix |
| API Key Revoked | WARN | User ID, key prefix |
| Permission Denied | WARN | User ID, resource, action |
| Role Changed | INFO | Admin ID, target user, old/new role |
| Resource Deleted | INFO | User ID, resource type, resource ID |
| Security Violation | ERROR | Type, IP, payload |

### Log Format

```json
{
  "timestamp": "2026-07-14T12:00:00Z",
  "level": "INFO",
  "event": "login_success",
  "user_id": "usr_abc123",
  "ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0 ...",
  "request_id": "req_xyz789",
  "details": {
    "method": "password",
    "session_id": "ses_def456"
  }
}
```

### Retention

| Log Type | Retention |
|----------|-----------|
| Security events | 1 year |
| Access logs | 90 days |
| Error logs | 30 days |
| Debug logs | 7 days |

---

## 8. Secret Management

### Environment Variables

All secrets must be stored as environment variables, never in code:

```bash
# Required secrets
DATABASE_URL=postgresql://nova:<password>@host:5432/nova_core
JWT_SECRET=<64-character-hex-string>
API_KEY_SALT=<32-character-hex-string>
REDIS_URL=redis://:<password>@host:6379/0

# Optional secrets
OLLAMA_API_KEY=<api-key-if-using-cloud>
```

### Production Secrets

For production deployments, use a secrets manager:

| Provider | Service |
|----------|---------|
| AWS | Secrets Manager / Parameter Store |
| GCP | Secret Manager |
| Azure | Key Vault |
| Kubernetes | Secrets + External Secrets Operator |

### Secret Rotation

| Secret | Rotation Period | Method |
|--------|----------------|--------|
| JWT Secret | 90 days | Environment update + restart |
| Database Password | 90 days | PostgreSQL `ALTER USER` |
| API Key Salt | 180 days | Re-hash all API keys |
| Redis Password | 90 days | Redis `CONFIG SET` |

### What NOT to Commit

- [ ] Database passwords
- [ ] JWT secrets
- [ ] API keys
- [ ] Salt values
- [ ] TLS certificates
- [ ] Service account credentials

---

## 9. Network Security

### CORS

- Only explicitly allowed origins can make cross-origin requests
- Credentials are only sent to trusted origins
- Preflight requests are cached for 24 hours

### TLS (Production)

```yaml
# Traefik TLS configuration
tls:
  certResolver: letsencrypt
  domains:
    - main: nova.example.com
      sans:
        - "*.nova.example.com"
```

### Network Isolation

| Service | Access | Network |
|---------|--------|---------|
| API (8000) | Public (via LB) | Public |
| Frontend (3000) | Public (via LB) | Public |
| PostgreSQL (5432) | Internal only | Private |
| Redis (6379) | Internal only | Private |
| ChromaDB (8001) | Internal only | Private |
| Prometheus (9090) | Internal only | Private |

---

## 10. Plugin Security

### Sandboxing

Plugins run in isolated environments with restricted permissions:

- No direct filesystem access (except designated directories)
- No network access (except whitelisted endpoints)
- No subprocess execution
- Resource limits (CPU, memory, time)

### Permission System

```python
# Plugin permission declarations
@plugin(
    permissions=["read:files", "write:memory"],
    network=["api.openai.com"],
    max_memory="512MB",
    max_time="30s"
)
class MyPlugin:
    ...
```

### Validation

- All plugins are validated before loading
- Dependency scanning for known vulnerabilities
- Code signing verification (optional)

---

## 11. Workflow Security

### Step Validation

- All workflow steps are validated before execution
- Input/output schemas enforced
- Resource limits applied per step

### Execution Controls

| Control | Description |
|---------|-------------|
| Max Steps | 100 per workflow |
| Max Duration | 30 minutes |
| Max Retries | 3 per step |
| Dead Letter Queue | Failed steps captured |

### Approval Workflows

For autonomous operations requiring approval:

```
Autonomous Decision → Approval Required → Approve/Reject → Execute/Abort
```

---

## 12. Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P0 | Data breach, system compromise | Immediate |
| P1 | Authentication bypass, privilege escalation | 1 hour |
| P2 | Vulnerability exploitation, data exposure | 4 hours |
| P3 | Security misconfiguration, minor vulnerability | 24 hours |
| P4 | Informational, hardening opportunity | 1 week |

### Response Steps

1. **Detect** — Automated alerting via monitoring
2. **Contain** — Isolate affected systems
3. **Eradicate** — Remove threat, patch vulnerability
4. **Recover** — Restore from clean backups
5. **Learn** — Post-incident review, update procedures

### Contact

| Role | Contact |
|------|---------|
| Security Lead | security@nova-core.example.com |
| On-Call Engineer | +1-555-0100 |
| Escalation | CTO / Engineering VP |
