"""Shared diagnostic utilities for dependency connectivity."""


def redacted_failure_message(
    *,
    dependency: str,
    dsn_without_credentials: str,
    password: str,
    exc: Exception,
) -> str:
    """Render a password-safe failure message for any dependency probe."""
    raw_message = str(exc).replace(password, "***")
    message = f"{dependency} probe failed for {dsn_without_credentials}: {raw_message}"
    if "***" in message:
        return message
    return f"{message} [credentials redacted: ***]"
