"""Exceptions for Provision ISR API client."""

# ------------------------------------------------------------------
# Core exception hierarchy
# ------------------------------------------------------------------
class ProvisionError(Exception):
    """Base exception for Provision ISR API errors."""


class ProvisionConnectionError(ProvisionError):
    """Connection to device failed."""


class AuthenticationError(ProvisionError):
    """Authentication failed."""


class InvalidRequestError(ProvisionError):
    """Invalid request URL or parameters (Error Code 1)."""


class InvalidXMLFormatError(ProvisionError):
    """Invalid XML format (Error Code 2)."""


class InvalidXMLContentError(ProvisionError):
    """Invalid XML content or out‑of‑range parameters (Error Code 3)."""


class PermissionDeniedError(ProvisionError):
    """Permission denied (Error Code 4)."""


# ------------------------------------------------------------------
# Backwards‑compatibility alias
# ------------------------------------------------------------------
# Some parts of the integration (or even external code) still
# import ``ConnectionError`` from this module.  Adding an alias keeps
# those imports working without having to touch all the callers.
ConnectionError = ProvisionConnectionError   # noqa: N801  (kept for legacy) 
