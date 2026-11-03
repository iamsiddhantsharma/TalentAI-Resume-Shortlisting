"""
TalentAI — HR & Admin Authentication FastAPI Dependencies

Provides:
- `get_current_hr_user`: Validates that incoming request has an active, authenticated session
  for an authorized team member (HR or Admin).
- `get_current_admin_user`: Validates that the authenticated user possesses the 'admin' role.
"""

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.auth_service import auth_service
from app.config.settings import settings


class HRUser(BaseModel):
    user_id: str
    username: str
    full_name: str
    email: str
    role: str = Field(default="hr", description="Account role ('hr' or 'admin')")
    must_change_password: bool = Field(default=False, description="Whether user must update temporary password")


async def get_current_hr_user(request: Request) -> HRUser:
    """
    Validate that the incoming request carries a valid HR or Admin session.
    Checks HttpOnly session cookie first, then Bearer Authorization header.
    Raises HTTP 401 Unauthorized if missing, expired, or invalid.
    """
    session_token: str | None = None

    # 1. Check HttpOnly cookie
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    # 2. Check Authorization: Bearer <token> fallback (for tests / CLI tools)
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:].strip()

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with an authorized HR account.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    user_dict = await auth_service.validate_session(session_token)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    return HRUser(**user_dict)


async def get_current_admin_user(
    current_user: HRUser = Depends(get_current_hr_user),
) -> HRUser:
    """
    Validate that the authenticated user possesses administrative privileges.
    Raises HTTP 403 Forbidden if user is authenticated but does not have the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required. HR user cannot access this endpoint.",
        )

    return current_user
