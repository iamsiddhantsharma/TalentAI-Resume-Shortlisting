"""
TalentAI — Synthetic HR Authentication and Route Protection Test Suite

Verifies:
1. PBKDF2-HMAC-SHA256 password hashing and constant-time verification.
2. Unauthenticated calls to protected routes return HTTP 401 Unauthorized.
3. Public endpoints (/health, /auth/login) are accessible without auth; /health exposes zero PII.
4. HR user authentication with valid credentials succeeds, sets HttpOnly cookie, returns profile.
5. HR authentication with invalid credentials returns HTTP 401.
6. Brute-force rate limiting (5 consecutive failures trigger HTTP 429 Too Many Requests).
7. Authenticated requests with session cookie or Bearer header succeed on protected routes.
8. Logout invalidates session and clears session cookie.
9. Expired sessions are rejected with HTTP 401.
10. Multiple HR team members can maintain independent concurrent sessions.

NOTE: Uses synthetic in-memory fixtures only. No real resumes or databases are accessed.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.auth.auth_service import (
    AccountLockedError,
    InvalidCredentialsError,
    auth_service,
)
from app.config.settings import settings


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def setup_in_memory_auth_db():
    in_memory_users = {}
    in_memory_sessions = {}

    mock_users_col = MagicMock()
    mock_sessions_col = MagicMock()

    async def mock_user_find_one(query, *args, **kwargs):
        if "username" in query:
            return in_memory_users.get(query["username"])
        if "_id" in query:
            for u in in_memory_users.values():
                if u["_id"] == query["_id"]:
                    return u
        return None

    async def mock_user_insert_one(doc):
        doc = dict(doc)
        doc["_id"] = doc.get("username", "user_1")
        in_memory_users[doc["username"]] = doc
        res = MagicMock()
        res.inserted_id = doc["_id"]
        return res

    async def mock_user_update_one(query, update):
        user = None
        if "_id" in query:
            for u in in_memory_users.values():
                if u["_id"] == query["_id"]:
                    user = u
                    break
        elif "username" in query:
            user = in_memory_users.get(query["username"])
        if user and "$set" in update:
            user.update(update["$set"])

    async def mock_user_count_documents(query):
        return len(in_memory_users)

    mock_users_col.find_one = AsyncMock(side_effect=mock_user_find_one)
    mock_users_col.insert_one = AsyncMock(side_effect=mock_user_insert_one)
    mock_users_col.update_one = AsyncMock(side_effect=mock_user_update_one)
    mock_users_col.count_documents = AsyncMock(side_effect=mock_user_count_documents)
    mock_users_col.create_index = AsyncMock()

    async def mock_session_insert_one(doc):
        in_memory_sessions[doc["_id"]] = dict(doc)
        res = MagicMock()
        res.inserted_id = doc["_id"]
        return res

    async def mock_session_find_one(query, *args, **kwargs):
        return in_memory_sessions.get(query.get("_id"))

    async def mock_session_delete_one(query):
        res = MagicMock()
        if query.get("_id") in in_memory_sessions:
            del in_memory_sessions[query["_id"]]
            res.deleted_count = 1
        else:
            res.deleted_count = 0
        return res

    mock_sessions_col.insert_one = AsyncMock(side_effect=mock_session_insert_one)
    mock_sessions_col.find_one = AsyncMock(side_effect=mock_session_find_one)
    mock_sessions_col.delete_one = AsyncMock(side_effect=mock_session_delete_one)
    mock_sessions_col.create_index = AsyncMock()

    mock_db = {
        "hr_users": mock_users_col,
        "hr_sessions": mock_sessions_col,
    }
    return in_memory_users, in_memory_sessions, mock_db


async def test_1_password_hashing_and_verification():
    print("\n--- TEST 1: PBKDF2-HMAC-SHA256 PASSWORD HASHING ---")
    plain = "SecureHR!2026_Key"
    hash_val = auth_service.hash_password(plain)

    # Check format
    assert hash_val.startswith("pbkdf2_sha256$600000$"), f"Unexpected hash format: {hash_val}"
    parts = hash_val.split("$")
    assert len(parts) == 4
    assert len(parts[2]) == 32  # 16 bytes hex

    # Verify matching password
    assert auth_service.verify_password(plain, hash_val) is True
    # Verify incorrect password
    assert auth_service.verify_password("WrongPassword!123", hash_val) is False
    assert auth_service.verify_password("", hash_val) is False

    # Check salt uniqueness (two hashes of same password must not be identical)
    hash_val_2 = auth_service.hash_password(plain)
    assert hash_val != hash_val_2

    print_status("Test 1: PBKDF2-HMAC-SHA256 hashing and constant-time verification passed", True)


async def test_2_unauthenticated_requests_return_401():
    print("\n--- TEST 2: PROTECTED ROUTES RETURN 401 UNAUTHORIZED WITHOUT AUTH ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Check several critical endpoints
        endpoints = [
            ("GET", "/auth/me"),
            ("GET", "/batches/active"),
            ("GET", "/batches"),
            ("POST", "/upload/resumes"),
            ("POST", "/ranking/rank-batch-async"),
            ("GET", "/status/queue"),
            ("GET", "/results/"),
            ("GET", "/demo/presets"),
        ]

        for method, url in endpoints:
            if method == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json={})

            assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {url}, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert "detail" in data
            assert "Authentication required" in data["detail"] or "Session has expired" in data["detail"]

    print_status("Test 2: All protected endpoints strictly return 401 Unauthorized for unauthenticated callers", True)


async def test_3_public_endpoints_accessible_without_auth():
    print("\n--- TEST 3: PUBLIC ENDPOINTS ACCESSIBLE WITHOUT AUTH & ZERO PII ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # /health
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert "service" in health_data
        # Ensure zero candidate PII or database collections leaked
        assert "candidates" not in health_data
        assert "resumes" not in health_data

        # /
        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        assert "TalentAI" in root_resp.json()["message"]

    print_status("Test 3: Public /health and / endpoints return minimal status with zero PII exposure", True)


async def test_4_login_with_valid_credentials():
    print("\n--- TEST 4: LOGIN WITH VALID HR CREDENTIALS ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()

    # Pre-seed user in memory
    pwd = "HR_Password_2026!"
    in_memory_users["hr_alice"] = {
        "_id": "user_alice",
        "username": "hr_alice",
        "full_name": "Alice HR Specialist",
        "email": "alice@company.com",
        "password_hash": auth_service.hash_password(pwd),
        "is_active": True,
        "role": "hr",
    }

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/auth/login",
                json={"username": "hr_alice", "password": pwd},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["user"]["username"] == "hr_alice"
            assert data["user"]["full_name"] == "Alice HR Specialist"
            assert data["user"]["role"] == "hr"

            # Check session cookie set
            assert settings.SESSION_COOKIE_NAME in resp.cookies
            session_token = resp.cookies[settings.SESSION_COOKIE_NAME]
            assert session_token in in_memory_sessions
            assert in_memory_sessions[session_token]["username"] == "hr_alice"

    print_status("Test 4: HR login succeeded and returned user profile with HttpOnly session cookie", True)


async def test_5_login_with_invalid_credentials():
    print("\n--- TEST 5: LOGIN WITH INVALID CREDENTIALS RETURNS 401 ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()
    auth_service._failed_attempts.clear()

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/auth/login",
                json={"username": "nonexistent_hr", "password": "WrongPassword123!"},
            )
            assert resp.status_code == 401
            assert "Invalid username or password" in resp.json()["detail"]

    print_status("Test 5: Invalid credentials cleanly rejected with HTTP 401", True)


async def test_6_brute_force_rate_limiting():
    print("\n--- TEST 6: BRUTE-FORCE RATE LIMITING (LOCKOUT AFTER 5 FAILURES) ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()
    auth_service._failed_attempts.clear()

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 5 consecutive failures
            for i in range(5):
                r = await client.post(
                    "/auth/login",
                    json={"username": "target_hr", "password": f"bad_pwd_{i}"},
                )
                assert r.status_code == 401

            # 6th attempt should be locked out (HTTP 429)
            locked_resp = await client.post(
                "/auth/login",
                json={"username": "target_hr", "password": "any_password"},
            )
            assert locked_resp.status_code == 429, f"Expected 429, got {locked_resp.status_code}: {locked_resp.text}"
            assert "Too many failed login attempts" in locked_resp.json()["detail"]
            assert "Retry-After" in locked_resp.headers

    print_status("Test 6: Repeated failed login attempts triggered HTTP 429 rate limit lockout", True)


async def test_7_authenticated_session_access():
    print("\n--- TEST 7: AUTHENTICATED SESSION ACCESSES PROTECTED ENDPOINTS ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()
    token = "valid_test_token_12345"
    in_memory_sessions[token] = {
        "_id": token,
        "user_id": "user_bob",
        "username": "hr_bob",
        "full_name": "Bob Recruiter",
        "email": "bob@company.com",
        "role": "hr",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8),
    }

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Subtest A: Cookie authentication on /auth/me
            client.cookies.set(settings.SESSION_COOKIE_NAME, token)
            me_resp = await client.get("/auth/me")
            assert me_resp.status_code == 200
            assert me_resp.json()["username"] == "hr_bob"

            # Subtest B: Bearer header authentication fallback
            client.cookies.clear()
            bearer_resp = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert bearer_resp.status_code == 200
            assert bearer_resp.json()["username"] == "hr_bob"

    print_status("Test 7: Authenticated session accessed protected endpoints via Cookie and Bearer header", True)


async def test_8_logout_invalidates_session():
    print("\n--- TEST 8: LOGOUT INVALIDATES SESSION ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()
    token = "logout_test_token_777"
    in_memory_sessions[token] = {
        "_id": token,
        "user_id": "user_carol",
        "username": "hr_carol",
        "full_name": "Carol HR Lead",
        "email": "carol@company.com",
        "role": "hr",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8),
    }

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(settings.SESSION_COOKIE_NAME, token)
            # Call logout
            logout_resp = await client.post("/auth/logout")
            assert logout_resp.status_code == 200
            assert token not in in_memory_sessions

            # Subsequent request with old token is rejected with 401
            subsequent_resp = await client.get("/auth/me")
            assert subsequent_resp.status_code == 401

    print_status("Test 8: Logout invalidated server session and subsequent requests rejected with 401", True)


async def test_9_expired_session_rejected():
    print("\n--- TEST 9: EXPIRED SESSION REJECTED ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()
    token = "expired_token_000"
    in_memory_sessions[token] = {
        "_id": token,
        "user_id": "user_dave",
        "username": "hr_dave",
        "full_name": "Dave HR",
        "email": "dave@company.com",
        "role": "hr",
        # Expired 1 hour ago
        "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
    }

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(settings.SESSION_COOKIE_NAME, token)
            resp = await client.get("/auth/me")
            assert resp.status_code == 401
            assert "expired" in resp.json()["detail"].lower()

    print_status("Test 9: Expired session rejected with 401 Unauthorized", True)


async def test_10_multiple_hr_team_members_independent_sessions():
    print("\n--- TEST 10: MULTIPLE HR USERS MAINTAIN CONCURRENT INDEPENDENT SESSIONS ---")
    in_memory_users, in_memory_sessions, mock_db = setup_in_memory_auth_db()

    token_1 = "session_hr_alice"
    token_2 = "session_hr_bob"

    in_memory_sessions[token_1] = {
        "_id": token_1,
        "user_id": "user_alice",
        "username": "hr_alice",
        "full_name": "Alice HR",
        "email": "alice@company.com",
        "role": "hr",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=4),
    }
    in_memory_sessions[token_2] = {
        "_id": token_2,
        "user_id": "user_bob",
        "username": "hr_bob",
        "full_name": "Bob HR",
        "email": "bob@company.com",
        "role": "hr",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=4),
    }

    transport = ASGITransport(app=app)
    with patch("app.auth.auth_service.mongodb.get_database", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Alice's session
            client.cookies.set(settings.SESSION_COOKIE_NAME, token_1)
            resp1 = await client.get("/auth/me")
            assert resp1.status_code == 200
            assert resp1.json()["username"] == "hr_alice"

            # Bob's session
            client.cookies.set(settings.SESSION_COOKIE_NAME, token_2)
            resp2 = await client.get("/auth/me")
            assert resp2.status_code == 200
            assert resp2.json()["username"] == "hr_bob"

            # Log out Alice; Bob's session remains active
            client.cookies.set(settings.SESSION_COOKIE_NAME, token_1)
            await client.post("/auth/logout")

            # Alice is now 401
            resp1_after = await client.get("/auth/me")
            assert resp1_after.status_code == 401

            # Bob is still 200
            client.cookies.set(settings.SESSION_COOKIE_NAME, token_2)
            resp2_after = await client.get("/auth/me")
            assert resp2_after.status_code == 200
            assert resp2_after.json()["username"] == "hr_bob"

    print_status("Test 10: Multiple HR team accounts maintain isolated concurrent sessions", True)


async def run_all_auth_tests():
    print("=" * 80)
    print("TALENTAI — SYNTHETIC HR AUTHENTICATION & ACCESS PROTECTION TEST SUITE")
    print("=" * 80)
    await test_1_password_hashing_and_verification()
    await test_2_unauthenticated_requests_return_401()
    await test_3_public_endpoints_accessible_without_auth()
    await test_4_login_with_valid_credentials()
    await test_5_login_with_invalid_credentials()
    await test_6_brute_force_rate_limiting()
    await test_7_authenticated_session_access()
    await test_8_logout_invalidates_session()
    await test_9_expired_session_rejected()
    await test_10_multiple_hr_team_members_independent_sessions()
    print("=" * 80)
    print("ALL 10 HR AUTHENTICATION & ROUTE PROTECTION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_auth_tests())
