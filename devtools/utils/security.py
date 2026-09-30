#!/usr/bin/env python3
"""
Shared security helpers for DevTools CLI.

Provides path validation, file-size limits, safe regex compilation,
and CSV formula-injection escaping.
"""

from __future__ import annotations

import os
import re
import signal
from pathlib import Path
from typing import Optional, Union

# Soft caps to reduce DoS / accidental resource exhaustion
MAX_READ_BYTES = 50 * 1024 * 1024  # 50 MiB
MAX_REGEX_PATTERN_LEN = 200
MAX_REGEX_MATCH_TIMEOUT_SEC = 2
FORBIDDEN_WRITE_PREFIXES = (
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/root",
)


class SecurityError(ValueError):
    """Raised when a path or input fails a security check."""


def resolve_path(path: Union[str, Path], *, must_exist: bool = False) -> Path:
    """Resolve a path and reject null bytes / empty values."""
    if path is None or str(path).strip() == "":
        raise SecurityError("Path must not be empty")
    raw = str(path)
    if "\x00" in raw:
        raise SecurityError("Path contains null bytes")
    resolved = Path(raw).expanduser().resolve(strict=False)
    if must_exist and not resolved.exists():
        raise SecurityError(f"Path does not exist: {resolved}")
    return resolved


def assert_within_base(path: Path, base: Path, *, label: str = "path") -> Path:
    """Ensure *path* stays under *base* after resolving symlinks."""
    real_path = path.resolve(strict=False)
    real_base = base.resolve(strict=False)
    try:
        real_path.relative_to(real_base)
    except ValueError as exc:
        raise SecurityError(
            f"Refusing {label} outside allowed base ({real_base}): {real_path}"
        ) from exc
    return real_path


def assert_safe_write_path(path: Union[str, Path]) -> Path:
    """Block writes to sensitive system locations."""
    resolved = resolve_path(path)
    # Never overwrite the tool's own source via ambiguous relative paths without intent —
    # still allow normal project writes, but refuse classic system directories.
    for prefix in FORBIDDEN_WRITE_PREFIXES:
        if str(resolved) == prefix or str(resolved).startswith(prefix + os.sep):
            raise SecurityError(f"Refusing write to protected location: {resolved}")
    if resolved.is_symlink():
        # Resolve through the link and re-check
        target = resolved.resolve(strict=False)
        for prefix in FORBIDDEN_WRITE_PREFIXES:
            if str(target) == prefix or str(target).startswith(prefix + os.sep):
                raise SecurityError(f"Refusing write via symlink to: {target}")
    parent = resolved.parent
    if not parent.exists():
        raise SecurityError(f"Output directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise SecurityError(f"Output directory is not writable: {parent}")
    return resolved


def assert_readable_file(path: Union[str, Path], *, max_bytes: int = MAX_READ_BYTES) -> Path:
    """Validate a file exists, is a regular file, and is within size limits."""
    resolved = resolve_path(path, must_exist=True)
    if resolved.is_symlink():
        # Allow reading through symlinks only if the final target is a regular file
        target = resolved.resolve(strict=True)
        if not target.is_file():
            raise SecurityError(f"Symlink does not point to a regular file: {resolved}")
        resolved = target
    if not resolved.is_file():
        raise SecurityError(f"Not a regular file: {resolved}")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise SecurityError(
            f"File too large ({size} bytes > limit {max_bytes}). "
            "Split the file or raise MAX_READ_BYTES intentionally."
        )
    return resolved


def assert_readable_directory(path: Union[str, Path]) -> Path:
    """Validate a directory exists and is traversable."""
    resolved = resolve_path(path, must_exist=True)
    if not resolved.is_dir():
        raise SecurityError(f"Not a directory: {resolved}")
    if not os.access(resolved, os.R_OK | os.X_OK):
        raise SecurityError(f"Directory is not readable: {resolved}")
    return resolved


def safe_compile_regex(pattern: str, flags: int = 0) -> re.Pattern:
    """Compile a user regex with length limits and a best-effort match timeout."""
    if pattern is None or pattern == "":
        raise SecurityError("Regex pattern must not be empty")
    if len(pattern) > MAX_REGEX_PATTERN_LEN:
        raise SecurityError(
            f"Regex pattern too long ({len(pattern)} > {MAX_REGEX_PATTERN_LEN})"
        )
    # Reject a few well-known nested-quantifier forms that commonly hang
    # (e.g. (a+)+). Length limit + match timeout cover the rest.
    if re.search(r"\([^)]*[+*][^)]*\)[+*{]", pattern):
        raise SecurityError(
            "Regex looks prone to catastrophic backtracking (ReDoS). "
            "Simplify nested quantifiers."
        )
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise SecurityError(f"Invalid regex: {exc}") from exc


def regex_search_with_timeout(
    compiled: re.Pattern, text: str, timeout: int = MAX_REGEX_MATCH_TIMEOUT_SEC
) -> Optional[re.Match]:
    """
    Search with a SIGALRM timeout on Unix. Falls back to plain search elsewhere.
    """
    if not hasattr(signal, "SIGALRM"):
        return compiled.search(text)

    def _handler(signum, frame):  # noqa: ARG001
        raise TimeoutError("regex search timed out")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout)
    try:
        return compiled.search(text)
    except TimeoutError:
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def escape_csv_formula(value) -> str:
    """Neutralize Excel/Sheets formula injection in CSV cells."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def parse_positive_int(value: str, *, name: str = "value", allow_zero: bool = True) -> int:
    """Parse an integer CLI argument safely."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecurityError(f"Invalid integer for {name}: {value!r}") from exc
    if allow_zero:
        if number < 0:
            raise SecurityError(f"{name} must be >= 0, got {number}")
    elif number <= 0:
        raise SecurityError(f"{name} must be > 0, got {number}")
    return number
