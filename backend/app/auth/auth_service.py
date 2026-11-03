"""
TalentAI — HR & Admin Authentication and Access Protection Service

Provides:
1. NIST/OWASP-compliant PBKDF2-HMAC-SHA256 password hashing (600,000 rounds, 16-byte salt).
2. Constant-time credential comparison.
3. In-memory brute-force rate limiting per (client_ip, username).
4. Secure server-side session token management with MongoDB TTL persistence.
5. Role-based access control (Admin and HR roles).
6. Secure temporary password onboarding with mandatory password change on first login.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
import re
import secrets
from typing import Any

from app.config.settings import settings
from app.database.collections import MongoCollections
from app.database.mongodb import mongodb

logger = logging.getLogger(__name__)

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600000
SALT_BYTES = 16

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,50}$")


class AuthError(Exception):
    """Base authentication error."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when authentication credentials do not match."""
    pass


class AccountLockedError(AuthError):
    """Raised when an account/IP is temporarily locked due to repeated failures."""
    def __init__(self, message: str, retry_after_seconds: int = 900):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class HRAuthService:
    def __init__(self) -> None:
        # Failed attempts map: (ip, username_lower) -> list of failure timestamps
        self._failed_attempts: dict[tuple[str, str], list[datetime]] = {}

    def _get_db(self):
        return mongodb.get_database()

    async def create_indexes(self) -> None:
        """Create database indexes for HR/Admin users and sessions."""
        try:
            db = self._get_db()
            users_col = db[MongoCollections.HR_USERS]
            sessions_col = db[MongoCollections.HR_SESSIONS]

            # Unique index on username
            try:
                await users_col.create_index("username", unique=True)
            except Exception as e:
                logger.debug("Username index note: %s", e)

            # Unique sparse index on email (drop and recreate if specs differ)
            try:
                await users_col.create_index("email", unique=True, sparse=True)
            except Exception as e:
                logger.debug("Email index spec conflict, recreating: %s", e)
                try:
                    await users_col.drop_index("email_1")
                    await users_col.create_index("email", unique=True, sparse=True)
                except Exception:
                    pass

            try:
                await users_col.create_index("role")
            except Exception:
                pass

            # TTL index on expires_at for automated session cleanup
            try:
                await sessions_col.create_index("expires_at", expireAfterSeconds=0)
            except Exception:
                pass

            try:
                await sessions_col.create_index("user_id")
            except Exception:
                pass

            logger.info("HR authentication database indexes verified.")
        except Exception as e:
            logger.warning("Failed to create HR authentication indexes: %s", e)

    # =========================================================================
    # PASSWORD HASHING & VERIFICATION (OWASP 600K PBKDF2-HMAC-SHA256)
    # =========================================================================

    def hash_password(self, password: str) -> str:
        """Hash password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        salt = os.urandom(SALT_BYTES)
        derived_key = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        salt_hex = salt.hex()
        key_hex = derived_key.hex()
        return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt_hex}${key_hex}"

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """Verify plain password against stored PBKDF2 hash using constant-time comparison."""
        try:
            parts = password_hash.split("$")
            if len(parts) != 4:
                return False
            algo, iters_str, salt_hex, key_hex = parts
            if algo != f"pbkdf2_{PBKDF2_ALGORITHM}":
                return False
            iterations = int(iters_str)
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)

            candidate_key = hashlib.pbkdf2_hmac(
                PBKDF2_ALGORITHM,
                plain_password.encode("utf-8"),
                salt,
                iterations,
            )
            return hmac.compare_digest(candidate_key, expected_key)
        except Exception:
            return False

    # =========================================================================
    # BRUTE-FORCE RATE LIMITING
    # =========================================================================

    def _check_rate_limit(self, client_ip: str, username: str) -> None:
        """Verify that the client is not in a temporary lockout period."""
        key = (client_ip.strip(), username.strip().lower())
        now = datetime.now(timezone.utc)
        lockout_duration = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        window = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)

        attempts = self._failed_attempts.get(key, [])
        # Filter attempts within current window
        recent_attempts = [t for t in attempts if now - t < window]
        self._failed_attempts[key] = recent_attempts

        if len(recent_attempts) >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            oldest_relevant = recent_attempts[0]
            remaining = int((oldest_relevant + lockout_duration - now).total_seconds())
            remaining = max(1, remaining)
            raise AccountLockedError(
                f"Too many failed login attempts. Please try again in {remaining // 60 + 1} minutes.",
                retry_after_seconds=remaining,
            )

    def _record_failed_attempt(self, client_ip: str, username: str) -> None:
        """Record a failed login timestamp."""
        key = (client_ip.strip(), username.strip().lower())
        now = datetime.now(timezone.utc)
        attempts = self._failed_attempts.get(key, [])
        attempts.append(now)
        self._failed_attempts[key] = attempts

    def _reset_failed_attempts(self, client_ip: str, username: str) -> None:
        """Clear failed attempts upon successful login."""
        key = (client_ip.strip(), username.strip().lower())
        self._failed_attempts.pop(key, None)

    # =========================================================================
    # USER MANAGEMENT (HR & ADMIN ROLES)
    # =========================================================================

    async def create_hr_user(
        self,
        username: str | None = None,
        password: str = "",
        full_name: str = "HR Team Member",
        email: str = "hr@talentai.local",
        role: str = "hr",
        must_change_password: bool = False,
    ) -> dict[str, Any]:
        """Create a new authorized HR or Admin user account."""
        email_clean = email.strip().lower()
        if not email_clean or not EMAIL_REGEX.match(email_clean):
            raise ValueError("Invalid email format.")

        full_name_clean = full_name.strip()
        if not full_name_clean:
            raise ValueError("Full name cannot be empty.")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        role_clean = role.strip().lower()
        if role_clean not in ("hr", "admin"):
            raise ValueError(f"Invalid role '{role}'. Allowed roles are 'hr' and 'admin'.")

        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]

        existing_email = await users_col.find_one({"email": email_clean})
        if existing_email:
            raise ValueError(f"Account with email '{email_clean}' already exists.")

        if not username or not username.strip():
            # Automatically derive a unique, sanitized username from the email prefix
            raw_prefix = email_clean.split("@")[0]
            sanitized = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", raw_prefix)[:30]
            if len(sanitized) < 3:
                sanitized = f"hr_{sanitized}"
            candidate = sanitized
            counter = 1
            while await users_col.find_one({"username": candidate}):
                candidate = f"{sanitized}_{counter}"
                counter += 1
            username_clean = candidate
        else:
            username_clean = username.strip().lower()
            if not USERNAME_REGEX.match(username_clean):
                raise ValueError("Username must be 3-50 characters containing only letters, numbers, hyphens, dots, or underscores.")
            existing_user = await users_col.find_one({"username": username_clean})
            if existing_user:
                raise ValueError(f"Account with username '{username_clean}' already exists.")

        now = datetime.now(timezone.utc)
        user_doc = {
            "username": username_clean,
            "full_name": full_name_clean,
            "email": email_clean,
            "password_hash": self.hash_password(password),
            "role": role_clean,
            "must_change_password": bool(must_change_password),
            "is_active": True,
            "created_at": now,
            "last_login_at": None,
        }

        res = await users_col.insert_one(user_doc)
        user_doc["_id"] = str(res.inserted_id)
        user_doc["user_id"] = str(res.inserted_id)
        logger.info("Created authorized %s account: %s (%s)", role_clean.upper(), username_clean, email_clean)
        return user_doc

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Retrieve user document by username (case-insensitive)."""
        clean = username.strip().lower()
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        return await users_col.find_one({"username": clean})

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Retrieve user document by email (case-insensitive)."""
        clean = email.strip().lower()
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        return await users_col.find_one({"email": clean})

    async def get_user_by_identifier(self, identifier: str) -> dict[str, Any] | None:
        """Retrieve user document by username or email (case-insensitive)."""
        clean = identifier.strip().lower()
        user = await self.get_user_by_username(clean)
        if not user:
            user = await self.get_user_by_email(clean)
        return user

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve user document by user_id string or ObjectId."""
        from bson import ObjectId
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        try:
            doc = await users_col.find_one({"_id": ObjectId(user_id)})
            if doc:
                return doc
        except Exception:
            pass
        return await users_col.find_one({"_id": user_id})

    async def list_hr_users(self) -> list[dict[str, Any]]:
        """List all HR and Admin user accounts (strictly excluding password hashes)."""
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        cursor = users_col.find({}, projection={"password_hash": 0}).sort("created_at", 1)
        users = await cursor.to_list(length=200)
        for u in users:
            u["_id"] = str(u["_id"])
            u["user_id"] = str(u["_id"])
            u["must_change_password"] = u.get("must_change_password", False)
            u["role"] = u.get("role", "hr")
        return users

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> dict[str, Any]:
        """
        Verify existing password and set a new password.
        Clears the must_change_password flag upon successful update.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise InvalidCredentialsError("User account not found.")

        pwd_hash = user.get("password_hash", "")
        if not self.verify_password(current_password, pwd_hash):
            raise InvalidCredentialsError("Current password is incorrect.")

        if current_password == new_password:
            raise ValueError("New password must be different from current password.")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long.")

        new_hash = self.hash_password(new_password)
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        now = datetime.now(timezone.utc)

        await users_col.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password_hash": new_hash,
                    "must_change_password": False,
                    "password_updated_at": now,
                }
            },
        )

        # Update active sessions for this user to reflect must_change_password=False
        sessions_col = db[MongoCollections.HR_SESSIONS]
        await sessions_col.update_many(
            {"user_id": str(user["_id"])},
            {"$set": {"must_change_password": False}},
        )

        logger.info("Password successfully updated for user: %s", user.get("username"))
        return {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "full_name": user.get("full_name", "HR Team Member"),
            "email": user.get("email", ""),
            "role": user.get("role", "hr"),
            "must_change_password": False,
        }

    # =========================================================================
    # AUTHENTICATION & SESSION LIFECYCLE
    # =========================================================================

    async def authenticate_hr_user(
        self,
        username: str,
        password: str,
        client_ip: str = "127.0.0.1",
    ) -> dict[str, Any]:
        """
        Authenticate an HR or Admin team member with rate limiting and password verification.
        Returns the sanitized user document upon success.
        """
        username_clean = username.strip().lower()
        self._check_rate_limit(client_ip, username_clean)

        user = await self.get_user_by_identifier(username_clean)
        if not user or not user.get("is_active", True):
            self._record_failed_attempt(client_ip, username_clean)
            raise InvalidCredentialsError("Invalid username or password.")

        pwd_hash = user.get("password_hash", "")
        if not self.verify_password(password, pwd_hash):
            self._record_failed_attempt(client_ip, username_clean)
            raise InvalidCredentialsError("Invalid username or password.")

        # Success: reset failed counter
        self._reset_failed_attempts(client_ip, username_clean)

        # Update last login timestamp
        db = self._get_db()
        users_col = db[MongoCollections.HR_USERS]
        now = datetime.now(timezone.utc)
        await users_col.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now}})

        sanitized_user = {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "full_name": user.get("full_name", "HR Team Member"),
            "email": user.get("email", ""),
            "role": user.get("role", "hr"),
            "must_change_password": user.get("must_change_password", False),
        }
        return sanitized_user

    async def create_session(self, user: dict[str, Any]) -> str:
        """
        Generate a cryptographically secure random session token and store in MongoDB.
        """
        session_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)

        session_doc = {
            "_id": session_token,
            "session_token": session_token,
            "user_id": str(user["user_id"]),
            "username": user["username"],
            "full_name": user.get("full_name", "HR Team Member"),
            "email": user.get("email", ""),
            "role": user.get("role", "hr"),
            "must_change_password": user.get("must_change_password", False),
            "created_at": now,
            "expires_at": expires_at,
        }

        db = self._get_db()
        sessions_col = db[MongoCollections.HR_SESSIONS]
        await sessions_col.insert_one(session_doc)
        return session_token

    async def validate_session(self, session_token: str) -> dict[str, Any] | None:
        """
        Validate an incoming session token. Returns user session dict if valid, else None.
        """
        if not session_token or not isinstance(session_token, str):
            return None

        db = self._get_db()
        sessions_col = db[MongoCollections.HR_SESSIONS]
        session = await sessions_col.find_one({"_id": session_token})
        if not session:
            return None

        expires_at = session.get("expires_at")
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                # Clean up expired session
                await sessions_col.delete_one({"_id": session_token})
                return None

        return {
            "user_id": session["user_id"],
            "username": session["username"],
            "full_name": session.get("full_name", "HR Team Member"),
            "email": session.get("email", ""),
            "role": session.get("role", "hr"),
            "must_change_password": session.get("must_change_password", False),
        }

    async def invalidate_session(self, session_token: str) -> bool:
        """Delete session on logout."""
        if not session_token:
            return False
        db = self._get_db()
        sessions_col = db[MongoCollections.HR_SESSIONS]
        res = await sessions_col.delete_one({"_id": session_token})
        return res.deleted_count > 0

    # =========================================================================
    # INITIAL ACCOUNT SEEDING
    # =========================================================================

    async def ensure_initial_hr_user(self) -> None:
        """
        Seed initial HR or Admin user if hr_users collection is completely empty AND
        strong credentials have been explicitly configured via environment variables.
        Never creates an account with default, blank, or weak (<8 chars) password.
        """
        try:
            db = self._get_db()
            users_col = db[MongoCollections.HR_USERS]
            count = await users_col.count_documents({})
            if count == 0:
                init_user = settings.INITIAL_HR_USERNAME
                init_pwd = settings.INITIAL_HR_PASSWORD
                if not init_user or not init_user.strip():
                    logger.info("INITIAL_HR_USERNAME not set. Skipping automatic account seeding.")
                    return
                if not init_pwd or len(init_pwd.strip()) < 8:
                    logger.warning(
                        "INITIAL_HR_PASSWORD not set or too short (< 8 chars). "
                        "Refusing to seed insecure default account. "
                        "Use CLI: python -m app.cli.manage_hr bootstrap-admin"
                    )
                    return

                await self.create_hr_user(
                    username=init_user.strip(),
                    password=init_pwd,
                    full_name=settings.INITIAL_HR_NAME,
                    email=settings.INITIAL_HR_EMAIL,
                    role="admin",  # Initial seeded account is an admin
                    must_change_password=False,
                )
                logger.info("Initialized configured administrative team account: %s", init_user.strip())
        except Exception as e:
            logger.warning("Could not check/seed initial account: %s", e)


auth_service = HRAuthService()
