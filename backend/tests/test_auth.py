import pytest
import jwt
from unittest.mock import patch
from fastapi import HTTPException
from backend.auth import verify_jwt


TEST_SECRET = "test-secret-key-at-least-32-characters-long"


def make_token(payload: dict) -> str:
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


def test_valid_token_returns_user_id():
    token = make_token({"sub": "user-123", "exp": 9999999999})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        user_id = verify_jwt(token)
    assert user_id == "user-123"


def test_expired_token_raises():
    token = make_token({"sub": "user-123", "exp": 1000000000})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(token)
        assert exc_info.value.status_code == 401


def test_invalid_token_raises():
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt("not-a-real-token")
        assert exc_info.value.status_code == 401


def test_missing_sub_raises():
    token = make_token({"exp": 9999999999})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(token)
        assert exc_info.value.status_code == 401
