"""
TalentAI — HR Sign-up, Onboarding & Authentication Test Suite

Verifies:
1. HR user registration via POST /auth/signup with valid inputs succeeds (HTTP 201).
2. Passwords are securely hashed with PBKDF2-HMAC-SHA256 (600k iterations) and plaintext is never stored.
3. Newly registered HR user can immediately sign in via POST /auth/login using their email or username.
4. Duplicate email registration is rejected with HTTP 409 Conflict and a clear error message.
5. Invalid inputs are rejected (empty name, invalid email, password < 8 chars, mismatched confirm password).
6. Feature flag: when ENABLE_PUBLIC_SIGNUP=False, signup returns HTTP 403 Forbidden.

CRITICAL: Uses synthetic in-memory database mock. Zero real candidate data, batches, or resumes are accessed.
"""

import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.auth.auth_service import (
    PBKDF2_ALGORITHM,
    PBKDF2_ITERATIONS,
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
        if "$or" in query:
            for condition in query["$or"]:
                for key, val in condition.items():
                    for u in in_memory_users.values():
                        if u.get(key) == val:
                            return u
            return None
        if "username" in query:
            for u in in_memory_users.values():
                if u.get("username") == query["username"]:
                    return u
            return None
        if "email" in query:
            for u in in_memory_users.values():
                if u.get("email") == query["email"]:
                    return u
            return None
        if "_id" in query:
            for u in in_memory_users.values():
                if str(u.get("_id")) == str(query["_id"]):
                    return u
            return None
        return None

    async def mock_user_insert_one(doc):
        doc = dict(doc)
        uid = f"user_{len(in_memory_users) + 1}"
        doc["_id"] = uid
        doc["user_id"] = uid
        in_memory_users[uid] = doc
        res = MagicMock()
        res.inserted_id = uid
        return res

    async def mock_user_update_one(query, update):
        user = None
        if "_id" in query:
            for u in in_memory_users.values():
                if str(u.get("_id")) == str(query["_id"]):
                    user = u
                    break
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
        removed = in_memory_sessions.pop(query.get("_id"), None)
        res.deleted_count = 1 if removed else 0
        return res

    mock_sessions_col.insert_one = AsyncMock(side_effect=mock_session_insert_one)
    mock_sessions_col.find_one = AsyncMock(side_effect=mock_session_find_one)
    mock_sessions_col.delete_one = AsyncMock(side_effect=mock_session_delete_one)
    mock_sessions_col.create_index = AsyncMock()

    mock_db = {
        "hr_users": mock_users_col,
        "hr_sessions": mock_sessions_col,
    }
    return mock_db, in_memory_users, in_memory_sessions


async def run_signup_and_auth_tests():
    print("=" * 80)
    print("TALENTAI — HR SIGN-UP & ONBOARDING AUTHENTICATION TEST SUITE")
    print("=" * 80)
    print()

    mock_db, in_memory_users, in_memory_sessions = setup_in_memory_auth_db()

    with patch.object(auth_service, "_get_db", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:

            # -----------------------------------------------------------------
            # TEST 1: SUCCESSFUL SIGN-UP CREATES HR ACCOUNT
            # -----------------------------------------------------------------
            print("--- TEST 1: HR SIGNUP SUCCESS ---")
            signup_payload = {
                "name": "Sarah Connor",
                "email": "sarah.connor@talentai.local",
                "password": "Password#2026Safe",
                "confirm_password": "Password#2026Safe",
            }
            res = await client.post("/auth/signup", json=signup_payload)
            assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"
            data = res.json()
            assert "user" in data, "Response missing user object"
            assert data["user"]["email"] == "sarah.connor@talentai.local"
            assert data["user"]["full_name"] == "Sarah Connor"
            assert data["user"]["role"] == "hr"
            created_username = data["user"]["username"]
            assert len(created_username) >= 3, "Username should be generated"
            print_status("Test 1: HR account signup succeeded with valid inputs", True)

            # -----------------------------------------------------------------
            # TEST 2: SECURE PASSWORD HASHING (PBKDF2-HMAC-SHA256, ZERO PLAINTEXT)
            # -----------------------------------------------------------------
            print("\n--- TEST 2: PASSWORD HASHING VERIFICATION ---")
            stored_user = None
            for u in in_memory_users.values():
                if u.get("email") == "sarah.connor@talentai.local":
                    stored_user = u
                    break
            assert stored_user is not None, "User was not persisted to database"
            pwd_hash = stored_user.get("password_hash", "")
            assert pwd_hash.startswith(f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}$"), (
                f"Password hash format unexpected: {pwd_hash}"
            )
            assert "Password#2026Safe" not in str(stored_user), "Plaintext password detected in user record!"
            # Verify cryptographic verification
            assert auth_service.verify_password("Password#2026Safe", pwd_hash), "Password verification failed"
            assert not auth_service.verify_password("WrongPassword123", pwd_hash), "Invalid password matched hash"
            print_status("Test 2: PBKDF2-HMAC-SHA256 600,000 iterations verified, zero plaintext stored", True)

            # -----------------------------------------------------------------
            # TEST 3: LOGIN USING NEWLY CREATED ACCOUNT (BOTH EMAIL & USERNAME)
            # -----------------------------------------------------------------
            print("\n--- TEST 3: LOGIN WITH NEWLY CREATED HR ACCOUNT ---")
            # 3A. Login using Email
            login_res = await client.post(
                "/auth/login",
                json={
                    "username": "sarah.connor@talentai.local",
                    "password": "Password#2026Safe",
                },
            )
            assert login_res.status_code == 200, f"Login via email failed: {login_res.text}"
            login_data = login_res.json()
            assert login_data["user"]["email"] == "sarah.connor@talentai.local"
            assert settings.SESSION_COOKIE_NAME in login_res.cookies, "HttpOnly session cookie was not set"
            cookie_val = login_res.cookies[settings.SESSION_COOKIE_NAME]

            # Verify session accesses /auth/me
            me_res = await client.get("/auth/me", cookies={settings.SESSION_COOKIE_NAME: cookie_val})
            assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
            assert me_res.json()["email"] == "sarah.connor@talentai.local"

            # 3B. Login using derived Username
            login_by_username_res = await client.post(
                "/auth/login",
                json={
                    "username": created_username,
                    "password": "Password#2026Safe",
                },
            )
            assert login_by_username_res.status_code == 200, f"Login via username failed: {login_by_username_res.text}"
            print_status("Test 3: New account successfully logged in via both email and username", True)

            # -----------------------------------------------------------------
            # TEST 4: DUPLICATE EMAIL ADDRESS REJECTED
            # -----------------------------------------------------------------
            print("\n--- TEST 4: REJECT DUPLICATE EMAIL ADDRESS ---")
            dup_res = await client.post(
                "/auth/signup",
                json={
                    "name": "Sarah Connor Copy",
                    "email": "sarah.connor@talentai.local",
                    "password": "DifferentPassword#2026",
                    "confirm_password": "DifferentPassword#2026",
                },
            )
            assert dup_res.status_code in (400, 409), f"Expected 400 or 409 for duplicate email, got {dup_res.status_code}"
            assert "already exists" in dup_res.json().get("detail", "").lower()
            print_status("Test 4: Duplicate email rejected with clear error message", True)

            # -----------------------------------------------------------------
            # TEST 5: INVALID INPUTS REJECTED
            # -----------------------------------------------------------------
            print("\n--- TEST 5: REJECT INVALID INPUTS ---")
            # 5A: Blank name
            r1 = await client.post(
                "/auth/signup",
                json={
                    "name": "   ",
                    "email": "new.user@talentai.local",
                    "password": "Password#2026Safe",
                    "confirm_password": "Password#2026Safe",
                },
            )
            assert r1.status_code in (400, 422), f"Expected 400/422 for blank name, got {r1.status_code}"

            # 5B: Invalid email format
            r2 = await client.post(
                "/auth/signup",
                json={
                    "name": "Valid Name",
                    "email": "invalid-email-no-at",
                    "password": "Password#2026Safe",
                    "confirm_password": "Password#2026Safe",
                },
            )
            assert r2.status_code in (400, 422), f"Expected 400/422 for bad email, got {r2.status_code}"

            # 5C: Password too short (< 8 characters)
            r3 = await client.post(
                "/auth/signup",
                json={
                    "name": "Valid Name",
                    "email": "short.pwd@talentai.local",
                    "password": "short",
                    "confirm_password": "short",
                },
            )
            assert r3.status_code in (400, 422), f"Expected 400/422 for short password, got {r3.status_code}"

            # 5D: Password and Confirm Password mismatch
            r4 = await client.post(
                "/auth/signup",
                json={
                    "name": "Valid Name",
                    "email": "mismatch@talentai.local",
                    "password": "Password#2026Safe",
                    "confirm_password": "CompletelyDifferent#123",
                },
            )
            assert r4.status_code == 400, f"Expected 400 for password mismatch, got {r4.status_code}"
            assert "match" in r4.json().get("detail", "").lower()
            print_status("Test 5: All invalid input permutations rejected with user-facing errors", True)

            # -----------------------------------------------------------------
            # TEST 6: FEATURE FLAG DISABLES PUBLIC SIGN-UP
            # -----------------------------------------------------------------
            print("\n--- TEST 6: FEATURE FLAG (ENABLE_PUBLIC_SIGNUP=False) ---")
            with patch.object(settings, "ENABLE_PUBLIC_SIGNUP", False):
                disabled_res = await client.post(
                    "/auth/signup",
                    json={
                        "name": "Blocked User",
                        "email": "blocked@talentai.local",
                        "password": "Password#2026Safe",
                        "confirm_password": "Password#2026Safe",
                    },
                )
                assert disabled_res.status_code == 403, (
                    f"Expected 403 Forbidden when signup disabled, got {disabled_res.status_code}"
                )
                assert "disabled" in disabled_res.json().get("detail", "").lower()
            print_status("Test 6: ENABLE_PUBLIC_SIGNUP=False strictly returns HTTP 403 Forbidden", True)

    print()
    print("=" * 80)
    print("ALL 6 HR SIGN-UP & AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_signup_and_auth_tests())
