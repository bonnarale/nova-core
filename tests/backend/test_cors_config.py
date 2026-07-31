"""Tests for CORS configuration."""
import pytest
from app.core.config import Settings


def test_cors_origins_default():
    """Default CORS origins include localhost dev servers."""
    s = Settings(_env_file=None)
    origins = s.cors_origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_cors_origins_from_env():
    """ALLOWED_ORIGINS env var is parsed correctly."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://app.example.com,https://admin.example.com"}):
        s = Settings(_env_file=None)
        origins = s.cors_origins
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins
        assert len(origins) == 2


def test_cors_origins_single_origin():
    """Single origin works correctly."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://myapp.com"}):
        s = Settings(_env_file=None)
        origins = s.cors_origins
        assert origins == ["https://myapp.com"]


def test_cors_origins_strips_whitespace():
    """Whitespace around origins is stripped."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"ALLOWED_ORIGINS": " https://a.com , https://b.com "}):
        s = Settings(_env_file=None)
        origins = s.cors_origins
        assert origins == ["https://a.com", "https://b.com"]
