from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # ============================================================
    # APPLICATION
    # ============================================================

    APP_NAME: str
    APP_VERSION: str

    # ============================================================
    # STORAGE
    # ============================================================

    UPLOAD_DIR: str
    EXTRACTED_DIR: str
    FAILED_DIR: str

    # ============================================================
    # UPLOAD & ARCHIVE SAFETY LIMITS
    # ============================================================

    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_FILES_PER_REQUEST: int = 500
    MAX_REQUEST_BODY_SIZE_MB: int = 100
    MAX_RESUMES_PER_BATCH: int = 500
    MAX_ZIP_MEMBERS_COUNT: int = 1000
    MAX_ZIP_UNCOMPRESSED_SIZE_MB: int = 250
    MAX_ZIP_COMPRESSION_RATIO: float = 20.0

    # ============================================================
    # LOGGING
    # ============================================================

    LOG_LEVEL: str

    # ============================================================
    # FILE VALIDATION
    # ============================================================

    ALLOWED_EXTENSIONS: str

    # ============================================================
    # LOCAL LLM - OLLAMA
    # ============================================================

    OLLAMA_BASE_URL: str = (
        "http://127.0.0.1:11434"
    )

    OLLAMA_MODEL: str = (
        "qwen3:8b"
    )

    OLLAMA_TIMEOUT_CONNECT: float = 10.0
    OLLAMA_TIMEOUT_READ: float = 300.0
    OLLAMA_MAX_RETRIES: int = 2
    OLLAMA_RECOVERY_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_HEALTH_CHECK_INTERVAL: float = 2.0
    OLLAMA_NUM_CTX: int = 4096
    OLLAMA_NUM_PREDICT: int = 1024

    # AI Model Lifecycle Management
    OLLAMA_AUTO_LIFECYCLE: bool = True
    OLLAMA_IDLE_TIMEOUT_SECONDS: int = 300
    OLLAMA_STARTUP_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_COMMAND: str = "ollama serve"

    # ============================================================
    # MONGODB
    # ============================================================

    MONGODB_URI: str

    MONGODB_DATABASE: str

    # ============================================================
    # BATCH RETENTION & CLEANUP
    # ============================================================

    BATCH_RETENTION_HOURS: int = 24
    BATCH_CLEANUP_INTERVAL_MINUTES: int = 60

    # ============================================================
    # HR AUTHENTICATION & SESSIONS
    # ============================================================

    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "talentai_change_this_to_a_secure_random_key_in_production"
    SESSION_COOKIE_NAME: str = "talentai_session"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 24 hours
    SESSION_COOKIE_SECURE: bool | None = None  # None = dynamic based on ENVIRONMENT
    SESSION_COOKIE_SAMESITE: str = "lax"

    INITIAL_HR_USERNAME: str | None = None
    INITIAL_HR_PASSWORD: str | None = None
    INITIAL_HR_NAME: str = "HR Team Member"
    INITIAL_HR_EMAIL: str = "hr@talentai.local"

    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Demo-ready public HR signup flag (can be disabled when invite-only/admin-created flow is active)
    ENABLE_PUBLIC_SIGNUP: bool = True

    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def is_cookie_secure(self) -> bool:
        """
        Determine if the session cookie must require HTTPS.
        Explicit SESSION_COOKIE_SECURE overrides; otherwise defaults to True in production.
        """
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.ENVIRONMENT.lower() == "production"

    # ============================================================
    # PYDANTIC SETTINGS
    # ============================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
