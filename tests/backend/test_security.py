"""Tests for Security subsystem — enums, models, base ABCs, crypto, token, password,
RBAC, sessions, audit, API keys, rate limiter, IP filter, headers, sanitize, policy,
repository, engine, factory, and API routes.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from app.security.api_keys import APIKeyManager
from app.security.audit import AuditLogger
from app.security.base import (
    AuditProvider,
    AuthProvider,
    CryptoProvider,
    PermissionProvider,
    SessionProvider,
    TokenProvider,
)
from app.security.crypto import (
    HMACSigner,
    PasswordHasher,
    ScryptHasher,
    SimpleCipher,
    TokenGenerator,
)
from app.security.engine import SecurityEngine
from app.security.enums import (
    AccountState,
    AuthMethod,
    AuditAction,
    CipherMode,
    IPFilterAction,
    PasswordHashAlgorithm,
    PermissionLevel,
    RateLimitStrategy,
    SessionState,
    TokenType,
)
from app.security.factory import SecurityFactory
from app.security.headers import SecurityConfig, SecurityHeaders
from app.security.ip_filter import IPFilter
from app.security.models import (
    APIKey,
    AuditEntry,
    Permission,
    RateLimitRule,
    Role,
    SecurityPolicy,
    SecurityStatistics,
    Session,
    Token,
    User,
)
from app.security.password import PasswordService
from app.security.policy import PolicyEngine
from app.security.rbac import RBACEngine
from app.security.rate_limiter import RateLimiter
from app.security.repository import InMemorySecurityRepository
from app.security.sanitize import InputSanitizer
from app.security.sessions import SessionManager
from app.security.token import TokenService
from app.security.token_manager import TokenManager


# ======================================================================
# Enums
# ======================================================================

class TestEnums:
    def test_token_type_values(self):
        assert TokenType.ACCESS.value == "access"
        assert TokenType.REFRESH.value == "refresh"
        assert TokenType.API_KEY.value == "api_key"

    def test_permission_level_values(self):
        assert PermissionLevel.NONE.value == "none"
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.ADMIN.value == "admin"
        assert PermissionLevel.SUPER_ADMIN.value == "super_admin"

    def test_auth_method_values(self):
        assert AuthMethod.PASSWORD.value == "password"
        assert AuthMethod.TOKEN.value == "token"
        assert AuthMethod.API_KEY.value == "api_key"

    def test_audit_action_values(self):
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.LOGIN_FAILED.value == "login_failed"

    def test_session_state_values(self):
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.EXPIRED.value == "expired"
        assert SessionState.REVOKED.value == "revoked"

    def test_account_state_values(self):
        assert AccountState.ACTIVE.value == "active"
        assert AccountState.LOCKED.value == "locked"
        assert AccountState.DISABLED.value == "disabled"

    def test_rate_limit_strategy_values(self):
        assert RateLimitStrategy.FIXED_WINDOW.value == "fixed_window"
        assert RateLimitStrategy.SLIDING_WINDOW.value == "sliding_window"

    def test_ip_filter_action_values(self):
        assert IPFilterAction.ALLOW.value == "allow"
        assert IPFilterAction.DENY.value == "deny"


# ======================================================================
# Models
# ======================================================================

class TestModels:
    def test_token_defaults(self):
        t = Token()
        assert t.token_type == TokenType.ACCESS
        assert t.revoked is False

    def test_token_is_valid(self):
        t = Token(expires_at=time.time() + 3600)
        assert t.is_valid is True

    def test_token_is_expired(self):
        t = Token(expires_at=time.time() - 1)
        assert t.is_expired is True
        assert t.is_valid is False

    def test_token_revoked(self):
        t = Token(revoked=True, expires_at=time.time() + 3600)
        assert t.is_valid is False

    def test_token_to_dict(self):
        t = Token(token_id="t1", user_id="u1")
        d = t.to_dict()
        assert d["token_id"] == "t1"

    def test_user_defaults(self):
        u = User()
        assert u.state == AccountState.ACTIVE

    def test_user_to_dict(self):
        u = User(user_id="u1", username="alice")
        d = u.to_dict()
        assert d["user_id"] == "u1"

    def test_role_defaults(self):
        r = Role()
        assert r.permissions == []

    def test_role_to_dict(self):
        r = Role(role_id="admin", name="Admin")
        d = r.to_dict()
        assert d["role_id"] == "admin"

    def test_permission_defaults(self):
        p = Permission()
        assert p.action == PermissionLevel.READ

    def test_session_defaults(self):
        s = Session()
        assert s.state == SessionState.ACTIVE

    def test_session_is_expired(self):
        s = Session(expires_at=time.time() - 1)
        assert s.is_expired is True

    def test_audit_entry_to_dict(self):
        e = AuditEntry(entry_id="e1", action=AuditAction.LOGIN)
        d = e.to_dict()
        assert d["entry_id"] == "e1"

    def test_api_key_is_valid(self):
        k = APIKey()
        assert k.is_valid is True

    def test_api_key_revoked(self):
        k = APIKey(revoked=True)
        assert k.is_valid is False

    def test_api_key_expired(self):
        k = APIKey(expires_at=time.time() - 1)
        assert k.is_valid is False

    def test_rate_limit_rule_to_dict(self):
        r = RateLimitRule(rule_id="r1", resource="api", max_requests=50)
        d = r.to_dict()
        assert d["max_requests"] == 50

    def test_security_policy_to_dict(self):
        p = SecurityPolicy(policy_id="p1", name="test")
        d = p.to_dict()
        assert d["name"] == "test"

    def test_security_statistics_to_dict(self):
        s = SecurityStatistics(total_users=10)
        d = s.to_dict()
        assert d["total_users"] == 10


# ======================================================================
# Base ABCs
# ======================================================================

class TestBaseABCs:
    def test_auth_provider_is_abstract(self):
        with pytest.raises(TypeError):
            AuthProvider()

    def test_token_provider_is_abstract(self):
        with pytest.raises(TypeError):
            TokenProvider()

    def test_crypto_provider_is_abstract(self):
        with pytest.raises(TypeError):
            CryptoProvider()

    def test_permission_provider_is_abstract(self):
        with pytest.raises(TypeError):
            PermissionProvider()

    def test_audit_provider_is_abstract(self):
        with pytest.raises(TypeError):
            AuditProvider()

    def test_session_provider_is_abstract(self):
        with pytest.raises(TypeError):
            SessionProvider()


# ======================================================================
# Crypto
# ======================================================================

class TestPasswordHasher:
    def test_hash_and_verify(self):
        h = PasswordHasher()
        pwd_hash, salt = h.hash_password("secret")
        assert h.verify_password("secret", pwd_hash, salt) is True
        assert h.verify_password("wrong", pwd_hash, salt) is False

    def test_different_salts(self):
        h = PasswordHasher()
        h1, s1 = h.hash_password("secret")
        h2, s2 = h.hash_password("secret")
        assert s1 != s2

    def test_generate_salt(self):
        s = PasswordHasher.generate_salt()
        assert len(s) == 64


class TestScryptHasher:
    def test_hash_and_verify(self):
        h = ScryptHasher(n=1024, r=8, p=1)
        pwd_hash, salt = h.hash_password("secret")
        assert h.verify_password("secret", pwd_hash, salt) is True
        assert h.verify_password("wrong", pwd_hash, salt) is False


class TestHMACSigner:
    def test_sign_and_verify(self):
        s = HMACSigner("key123")
        sig = s.sign("hello")
        assert s.verify("hello", sig) is True
        assert s.verify("world", sig) is False

    def test_sign_json(self):
        s = HMACSigner("key123")
        sig = s.sign_json({"a": 1})
        assert s.verify_json({"a": 1}, sig) is True


class TestSimpleCipher:
    def test_encrypt_decrypt(self):
        c = SimpleCipher()
        ct = c.encrypt("hello", "key")
        pt = c.decrypt(ct, "key")
        assert pt == "hello"

    def test_wrong_key(self):
        c = SimpleCipher()
        ct = c.encrypt("hello", "key1")
        with pytest.raises(Exception):
            c.decrypt(ct, "key2")


class TestTokenGenerator:
    def test_generate(self):
        t = TokenGenerator.generate()
        assert len(t) >= 32

    def test_generate_hex(self):
        t = TokenGenerator.generate_hex(16)
        assert len(t) == 32

    def test_generate_numeric(self):
        t = TokenGenerator.generate_numeric(6)
        assert len(t) == 6
        assert t.isdigit()


# ======================================================================
# Token Service
# ======================================================================

class TestTokenService:
    def test_create_and_verify(self):
        ts = TokenService(secret_key="test_secret")
        token, value = ts.create_token("user1")
        assert token.user_id == "user1"
        verified = ts.verify_token(value)
        assert verified is not None
        assert verified.user_id == "user1"

    def test_verify_invalid(self):
        ts = TokenService()
        assert ts.verify_token("invalid.token.value") is None

    def test_verify_expired(self):
        ts = TokenService()
        _, value = ts.create_token("user1", expires_in_seconds=-1)
        assert ts.verify_token(value) is None

    def test_token_types(self):
        ts = TokenService()
        token, _ = ts.create_token("user1", token_type=TokenType.REFRESH)
        assert token.token_type == TokenType.REFRESH

    def test_decode_payload(self):
        ts = TokenService()
        _, value = ts.create_token("user1")
        payload = ts.decode_payload(value)
        assert payload is not None
        assert payload["sub"] == "user1"


# ======================================================================
# Token Manager
# ======================================================================

class TestTokenManager:
    def test_create_and_verify(self):
        tm = TokenManager()
        token, value = tm.create_token("user1")
        verified = tm.verify_token(value)
        assert verified is not None

    def test_revoke(self):
        tm = TokenManager()
        token, value = tm.create_token("user1")
        assert tm.revoke_token(token.token_id) is True
        assert tm.verify_token(value) is None

    def test_revoke_user_tokens(self):
        tm = TokenManager()
        tm.create_token("user1")
        tm.create_token("user1")
        count = tm.revoke_user_tokens("user1")
        assert count == 2

    def test_count(self):
        tm = TokenManager()
        tm.create_token("user1")
        assert tm.count() == 1

    def test_cleanup_expired(self):
        tm = TokenManager()
        tm.create_token("user1", expires_in_seconds=-1)
        count = tm.cleanup_expired()
        assert count >= 0


# ======================================================================
# Password Service
# ======================================================================

class TestPasswordService:
    def test_hash_verify(self):
        ps = PasswordService()
        h, s = ps.hash_password("secret")
        assert ps.verify_password("secret", h, s) is True

    def test_check_strength(self):
        ps = PasswordService()
        result = ps.check_strength("weak")
        assert result["strength"] in ("weak", "medium")
        result = ps.check_strength("StrongP@ssw0rd!")
        assert result["strength"] in ("strong", "very_strong")

    def test_generate_password(self):
        ps = PasswordService()
        pwd = ps.generate_password(20)
        assert len(pwd) == 20


# ======================================================================
# RBAC
# ======================================================================

class TestRBAC:
    def test_create_role(self):
        rbac = RBACEngine()
        role = Role(role_id="admin", name="Admin", permissions=["read", "write"])
        rbac.create_role(role)
        assert rbac.get_role("admin") is not None

    def test_assign_role(self):
        rbac = RBACEngine()
        rbac.create_role(Role(role_id="admin", permissions=["read"]))
        assert rbac.assign_role("user1", "admin") is True

    def test_check_permission(self):
        rbac = RBACEngine()
        rbac.create_role(Role(role_id="admin", permissions=["read", "write"]))
        rbac.assign_role("user1", "admin")
        assert rbac.check_permission("user1", "read") is True
        assert rbac.check_permission("user1", "delete") is False

    def test_resource_access(self):
        rbac = RBACEngine()
        rbac.create_role(Role(role_id="admin", permissions=["files:read", "files:write"]))
        rbac.assign_role("user1", "admin")
        assert rbac.check_resource_access("user1", "files", PermissionLevel.READ) is True
        assert rbac.check_resource_access("user1", "files", PermissionLevel.DELETE) is False

    def test_delete_role(self):
        rbac = RBACEngine()
        rbac.create_role(Role(role_id="r1"))
        assert rbac.delete_role("r1") is True
        assert rbac.get_role("r1") is None

    def test_count(self):
        rbac = RBACEngine()
        rbac.create_role(Role(role_id="r1"))
        count = rbac.count()
        assert count["roles"] == 1


# ======================================================================
# Sessions
# ======================================================================

class TestSessionManager:
    def test_create_and_validate(self):
        sm = SessionManager()
        session = sm.create_session("user1")
        assert sm.validate_session(session.session_id) is True

    def test_destroy(self):
        sm = SessionManager()
        session = sm.create_session("user1")
        assert sm.destroy_session(session.session_id) is True
        assert sm.validate_session(session.session_id) is False

    def test_destroy_all(self):
        sm = SessionManager()
        sm.create_session("user1")
        sm.create_session("user1")
        count = sm.destroy_all_sessions("user1")
        assert count == 2

    def test_count(self):
        sm = SessionManager()
        sm.create_session("user1")
        assert sm.count() == 1

    def test_cleanup_expired(self):
        sm = SessionManager()
        sm.create_session("user1", expires_in_seconds=-1)
        sm.cleanup_expired()
        assert sm.count_active() == 0


# ======================================================================
# Audit
# ======================================================================

class TestAuditLogger:
    def test_log_and_query(self):
        al = AuditLogger()
        entry = al.log_event(AuditAction.LOGIN, user_id="u1")
        assert entry.user_id == "u1"
        results = al.query(user_id="u1")
        assert len(results) == 1

    def test_count(self):
        al = AuditLogger()
        al.log_event(AuditAction.LOGIN, user_id="u1")
        assert al.count("u1") == 1
        assert al.count() == 1

    def test_get_recent(self):
        al = AuditLogger()
        al.log_event(AuditAction.LOGIN)
        al.log_event(AuditAction.LOGOUT)
        recent = al.get_recent(limit=1)
        assert len(recent) == 1

    def test_clear(self):
        al = AuditLogger()
        al.log_event(AuditAction.LOGIN)
        count = al.clear()
        assert count == 1
        assert al.count() == 0

    def test_failed_logins(self):
        al = AuditLogger()
        al.log_event(AuditAction.LOGIN_FAILED, user_id="u1")
        failed = al.get_failed_logins()
        assert len(failed) == 1


# ======================================================================
# API Keys
# ======================================================================

class TestAPIKeyManager:
    def test_create_key(self):
        km = APIKeyManager()
        key, raw = km.create_key("user1", "test_key")
        assert key.user_id == "user1"
        assert len(raw) > 0

    def test_revoke(self):
        km = APIKeyManager()
        key, raw = km.create_key("user1", "test")
        assert km.revoke_key(key.key_id) is True
        assert km.verify_key(raw) is None

    def test_count(self):
        km = APIKeyManager()
        km.create_key("user1", "k1")
        km.create_key("user1", "k2")
        assert km.count() == 2


# ======================================================================
# Rate Limiter
# ======================================================================

class TestRateLimiter:
    def test_fixed_window(self):
        rl = RateLimiter()
        rl.add_rule(RateLimitRule(resource="api", max_requests=2, window_seconds=60))
        r1 = rl.check("api", "client1")
        assert r1["allowed"] is True
        r2 = rl.check("api", "client1")
        assert r2["allowed"] is True
        r3 = rl.check("api", "client1")
        assert r3["allowed"] is False

    def test_sliding_window(self):
        rl = RateLimiter()
        rl.add_rule(RateLimitRule(resource="api", max_requests=1, window_seconds=60, strategy="sliding_window"))
        rl.check("api", "c1")
        r = rl.check("api", "c1")
        assert r["allowed"] is False

    def test_block_count(self):
        rl = RateLimiter()
        rl.add_rule(RateLimitRule(resource="api", max_requests=0, window_seconds=60))
        rl.check("api")
        assert rl.get_block_count() >= 1

    def test_remove_rule(self):
        rl = RateLimiter()
        rl.add_rule(RateLimitRule(resource="api"))
        assert rl.remove_rule("api") is True


# ======================================================================
# IP Filter
# ======================================================================

class TestIPFilter:
    def test_block_ip(self):
        f = IPFilter()
        f.block_ip("1.2.3.4")
        assert f.is_blocked("1.2.3.4") is True
        assert f.is_blocked("5.6.7.8") is False

    def test_allow_ip(self):
        f = IPFilter()
        f.block_ip("1.2.3.4")
        f.allow_ip("1.2.3.4")
        assert f.is_blocked("1.2.3.4") is False

    def test_pattern(self):
        f = IPFilter()
        f.add_rule("192.168.*", IPFilterAction.DENY)
        assert f.is_blocked("192.168.1.1") is True

    def test_cidr(self):
        f = IPFilter()
        f.add_rule("10.0.0.0/8", IPFilterAction.DENY)
        assert f.is_blocked("10.1.2.3") is True
        assert f.is_blocked("11.0.0.0") is False

    def test_check(self):
        f = IPFilter()
        result = f.check("1.2.3.4")
        assert result["allowed"] is True

    def test_clear(self):
        f = IPFilter()
        f.block_ip("1.2.3.4")
        f.clear()
        assert f.is_blocked("1.2.3.4") is False


# ======================================================================
# Headers
# ======================================================================

class TestSecurityHeaders:
    def test_get_headers(self):
        h = SecurityHeaders()
        headers = h.get_headers()
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers

    def test_cors_headers(self):
        h = SecurityHeaders()
        headers = h.get_cors_headers("*")
        assert "Access-Control-Allow-Origin" in headers

    def test_config_to_dict(self):
        c = SecurityConfig()
        d = c.to_dict()
        assert "token_expiry" in d


# ======================================================================
# Sanitize
# ======================================================================

class TestInputSanitizer:
    def test_sanitize_string(self):
        result = InputSanitizer.sanitize_string("<script>alert(1)</script>")
        assert "<script>" not in result

    def test_detect_sql_injection(self):
        assert InputSanitizer.detect_sql_injection("1' OR '1'='1") is True
        assert InputSanitizer.detect_sql_injection("hello world") is False

    def test_detect_xss(self):
        assert InputSanitizer.detect_xss("<script>alert(1)</script>") is True
        assert InputSanitizer.detect_xss("hello") is False

    def test_sanitize_identifier(self):
        result = InputSanitizer.sanitize_identifier("user@name!")
        assert result == "username"

    def test_strip_html(self):
        result = InputSanitizer.strip_html("<b>bold</b>")
        assert result == "bold"

    def test_sanitize_url(self):
        result = InputSanitizer.sanitize_url("example.com")
        assert result.startswith("https://")

    def test_sanitize_email(self):
        result = InputSanitizer.sanitize_email("  User@Example.COM  ")
        assert result == "user@example.com"

    def test_validate_input(self):
        result = InputSanitizer.validate_input("hello", {"required": True, "max_length": 10})
        assert result["valid"] is True
        result = InputSanitizer.validate_input("", {"required": True})
        assert result["valid"] is False


# ======================================================================
# Policy Engine
# ======================================================================

class TestPolicyEngine:
    def test_add_and_evaluate(self):
        pe = PolicyEngine()
        policy = SecurityPolicy(
            policy_id="p1",
            rules=[{"conditions": {"role": "admin"}, "operator": "eq"}],
        )
        pe.add_policy(policy)
        result = pe.evaluate({"role": "admin"})
        assert result["allowed"] is True

    def test_remove_policy(self):
        pe = PolicyEngine()
        pe.add_policy(SecurityPolicy(policy_id="p1"))
        assert pe.remove_policy("p1") is True
        assert pe.get_policy("p1") is None

    def test_count(self):
        pe = PolicyEngine()
        pe.add_policy(SecurityPolicy(policy_id="p1"))
        assert pe.count() == 1


# ======================================================================
# Repository
# ======================================================================

class TestRepository:
    @pytest.mark.asyncio
    async def test_store_and_get(self):
        repo = InMemorySecurityRepository()
        await repo.store("k1", {"a": 1})
        data = await repo.get("k1")
        assert data["a"] == 1

    @pytest.mark.asyncio
    async def test_delete(self):
        repo = InMemorySecurityRepository()
        await repo.store("k1", {"a": 1})
        assert await repo.delete("k1") is True
        assert await repo.get("k1") is None

    @pytest.mark.asyncio
    async def test_count(self):
        repo = InMemorySecurityRepository()
        await repo.store("a", {})
        await repo.store("b", {})
        assert await repo.count() == 2

    @pytest.mark.asyncio
    async def test_clear(self):
        repo = InMemorySecurityRepository()
        await repo.store("a", {})
        count = await repo.clear()
        assert count == 1

    @pytest.mark.asyncio
    async def test_contains(self):
        repo = InMemorySecurityRepository()
        await repo.store("k1", {})
        assert "k1" in repo


# ======================================================================
# Engine
# ======================================================================

class TestSecurityEngine:
    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        engine = SecurityEngine()
        await engine.start()
        assert engine._running is True
        await engine.shutdown()
        assert engine._running is False

    @pytest.mark.asyncio
    async def test_register_and_authenticate(self):
        engine = SecurityEngine()
        await engine.start()
        result = await engine.register_user("alice", "alice@test.com", "StrongP@ss1")
        assert result["success"] is True
        auth = await engine.authenticate("alice", "StrongP@ss1")
        assert auth["success"] is True
        assert "token" in auth

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self):
        engine = SecurityEngine()
        await engine.start()
        await engine.register_user("bob", "bob@test.com", "StrongP@ss1")
        auth = await engine.authenticate("bob", "wrong")
        assert auth["success"] is False

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self):
        engine = SecurityEngine()
        await engine.start()
        auth = await engine.authenticate("nobody", "pass")
        assert auth["success"] is False

    def test_verify_token(self):
        engine = SecurityEngine()
        token, value = engine.tokens.create_token("user1")
        verified = engine.verify_token(value)
        assert verified is not None

    def test_statistics(self):
        engine = SecurityEngine()
        stats = engine.get_statistics()
        assert "running" in stats

    def test_security_headers(self):
        engine = SecurityEngine()
        headers = engine.get_security_headers()
        assert "X-Frame-Options" in headers


# ======================================================================
# Factory
# ======================================================================

class TestSecurityFactory:
    def test_create_engine(self):
        engine = SecurityFactory.create_engine()
        assert engine is not None
        assert isinstance(engine, SecurityEngine)

    def test_create_with_components(self):
        components = SecurityFactory.create_engine_with_components()
        assert "engine" in components
        assert "tokens" in components
        assert "passwords" in components
        assert "rbac" in components
        assert "sessions" in components
        assert "audit" in components
        assert "api_keys" in components
        assert "rate_limiter" in components
        assert "ip_filter" in components
        assert "headers" in components
