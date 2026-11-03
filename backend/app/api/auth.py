"""
TalentAI — Authentication API Router

Endpoints:
- POST /auth/login   (Public, rate-limited: HR credential authentication)
- POST /auth/signup  (Public, configurable: HR account onboarding)
- POST /auth/logout  (Session invalidation and cookie clearing)
- GET  /auth/me      (Session verification and HR user identity)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth.auth_dependencies import HRUser, get_current_hr_user
from app.auth.auth_service import (
    EMAIL_REGEX,
    AccountLockedError,
    InvalidCredentialsError,
    auth_service,
)
from app.config.settings import settings

router = APIRouter(
    prefix="/auth",
    tags=["HR Authentication"],
)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="HR username or email")
    password: str = Field(..., min_length=1, description="HR account password")


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="HR team member full name")
    email: str = Field(..., min_length=3, max_length=120, description="HR email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Password confirmation")


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    full_name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    user: UserProfileResponse
    message: str = "Authentication successful."


class SignupResponse(BaseModel):
    user: UserProfileResponse
    message: str = "Account created successfully. You can now sign in with your credentials."


def get_client_ip(request: Request) -> str:
    """Extract client IP respecting X-Forwarded-For if present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate HR team member",
)
async def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
):
    """
    Authenticate an authorized HR user (via username or email) and establish an HttpOnly session cookie.
    Enforces brute-force rate limiting.
    """
    client_ip = get_client_ip(request)

    try:
        user = await auth_service.authenticate_hr_user(
            username=credentials.username,
            password=credentials.password,
            client_ip=client_ip,
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after_seconds)},
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    session_token = await auth_service.create_session(user)

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )

    return LoginResponse(
        user=UserProfileResponse(**user),
        message="Authentication successful.",
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new HR team member account",
)
async def signup(
    signup_data: SignupRequest,
    request: Request,
):
    """
    Register a new HR team member account.
    Validates name, email format, password security standards (min 8 chars), and confirmation match.
    Enforces uniqueness of email address.
    Can be disabled when admin-only onboarding is active via ENABLE_PUBLIC_SIGNUP=False.
    """
    if not getattr(settings, "ENABLE_PUBLIC_SIGNUP", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public sign-up is currently disabled. Please contact your TalentAI Administrator for an account.",
        )

    name_clean = signup_data.name.strip()
    if not name_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name cannot be empty.",
        )

    email_clean = signup_data.email.strip().lower()
    if not EMAIL_REGEX.match(email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format.",
        )

    if len(signup_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    if signup_data.password != signup_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirm password do not match.",
        )

    try:
        user_doc = await auth_service.create_hr_user(
            username=None,  # Automatically derived from email prefix
            password=signup_data.password,
            full_name=name_clean,
            email=email_clean,
            role="hr",
            must_change_password=False,
        )
    except ValueError as e:
        err_msg = str(e)
        if "already exists" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists. Please sign in instead.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    return SignupResponse(
        user=UserProfileResponse(
            user_id=user_doc["user_id"],
            username=user_doc["username"],
            full_name=user_doc["full_name"],
            email=user_doc["email"],
            role=user_doc["role"],
        ),
        message="Account created successfully! Please sign in with your email and password.",
    )


@router.post(
    "/logout",
    summary="Log out and invalidate HR session",
)
async def logout(
    request: Request,
    response: Response,
):
    """Invalidate current session and clear session cookie."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        await auth_service.invalidate_session(token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )

    return {"message": "Successfully logged out."}


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current authenticated HR user",
)
async def get_me(
    current_user: HRUser = Depends(get_current_hr_user),
):
    """Return the profile of the currently signed-in HR team member."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
    )
