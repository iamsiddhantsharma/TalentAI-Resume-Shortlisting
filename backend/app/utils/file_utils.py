import logging
import os
from pathlib import Path
import shutil
import stat
import time

from app.config.settings import settings

logger = logging.getLogger(__name__)

ERROR_ACCESS_DENIED = 5
ERROR_SHARING_VIOLATION = 32


def create_upload_directories() -> None:
    """
    Create all upload-related directories if they do not exist.
    """

    directories = [
        settings.UPLOAD_DIR,
        settings.EXTRACTED_DIR,
        settings.FAILED_DIR,
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def safe_rmtree(
    path: str | Path,
    max_retries: int = 3,
    initial_delay: float = 0.05,
    ignore_errors: bool = False,
) -> bool:
    """
    Recursively remove a directory tree with Windows permission error handling
    (clearing read-only attributes) and bounded retries for transient locks.

    Guarantees:
    - Never follows symlinks or junctions to external directories outside the tree.
    - Clears only the read-only attribute on the specific file/folder being removed.
    - Distinguishes access denial (read-only attribute) from transient locks (sharing violations).
    - Performs bounded exponential backoff retries for transient filesystem locks.
    - Returns True if the path was successfully removed or does not exist.
    - If ignore_errors is True, catches exceptions, logs diagnostics, and returns False on failure.
    - If ignore_errors is False, raises the underlying exception on permanent failure.
    """
    target = Path(path)

    # Idempotent check: if target doesn't exist and isn't a broken symlink, succeed immediately
    try:
        if not target.exists() and not target.is_symlink():
            return True
    except OSError:
        pass

    # If the target itself is a symlink or junction, remove the link without traversing
    if target.is_symlink():
        try:
            if target.is_dir():
                target.rmdir()
            else:
                target.unlink()
            return True
        except Exception as exc:
            logger.warning("Failed to remove symlink '%s': %s", target, exc)
            if not ignore_errors:
                raise
            return False

    # If the target is a single file, remove it directly
    if target.is_file():
        try:
            try:
                os.chmod(target, target.stat().st_mode | stat.S_IWRITE)
            except Exception:
                pass
            target.unlink()
            return True
        except Exception as exc:
            logger.warning("Failed to remove file '%s': %s", target, exc)
            if not ignore_errors:
                raise
            return False

    def handle_error(func, p, exc_info):
        # Extract exception instance (compatible with Python 3.11 tuple or direct exc)
        err = exc_info[1] if isinstance(exc_info, tuple) else exc_info
        p_path = Path(p)

        if isinstance(err, FileNotFoundError):
            return

        if isinstance(err, PermissionError):
            winerror = getattr(err, "winerror", None)

            # Check if read-only attribute is set
            is_readonly = False
            try:
                st = p_path.stat()
                is_readonly = not bool(st.st_mode & stat.S_IWRITE)
            except Exception:
                pass

            if is_readonly or winerror == ERROR_ACCESS_DENIED:
                # Clear ONLY the read-only flag on this specific file or folder
                try:
                    current_mode = p_path.stat().st_mode
                    os.chmod(p_path, current_mode | stat.S_IWRITE)
                except Exception as chmod_exc:
                    logger.debug("Failed to clear read-only flag on '%s': %s", p_path, chmod_exc)

            # Bounded retry loop for transient locks / sharing violations
            for attempt in range(max_retries):
                try:
                    func(p)
                    return
                except FileNotFoundError:
                    return
                except PermissionError as retry_err:
                    retry_winerror = getattr(retry_err, "winerror", None)
                    if attempt < max_retries - 1:
                        sleep_time = initial_delay * (2 ** attempt)
                        if retry_winerror == ERROR_SHARING_VIOLATION:
                            logger.debug(
                                "Transient lock on '%s' (attempt %d/%d). Retrying in %.3fs...",
                                p_path,
                                attempt + 1,
                                max_retries,
                                sleep_time,
                            )
                        time.sleep(sleep_time)
                    else:
                        raise retry_err

        # If non-PermissionError or retries exhausted, re-raise to caller
        raise err

    def onerror_wrapper(func, p, exc_info):
        handle_error(func, p, exc_info)

    try:
        shutil.rmtree(str(target), onerror=onerror_wrapper)
        return True
    except Exception as exc:
        logger.warning(
            "safe_rmtree failed to remove directory tree '%s': %s: %s",
            target,
            type(exc).__name__,
            exc,
        )
        if not ignore_errors:
            raise
        return False
